"""Orquestador principal del agente inteligente de atención al cliente."""

import json
import re
from pathlib import Path
from uuid import uuid4

from app.client import DEFAULT_MODEL, get_client
from app.schemas import SessionState
from app.db.repositories import get_repository
from app.tooling import TOOL_MAPPING, TOOLS_SCHEMA

SYSTEM_PROMPT = (
    Path(__file__).parent / "prompts" / "system_prompt.md"
).read_text(encoding="utf-8")


class RetailAgent:
    """Mantener la conversación y coordinar las tools del agente."""

    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id or str(uuid4())
        self.repository = get_repository()
        self.repository.create_session(self.session_id)
        self.state = SessionState()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _actualizar_memoria(self, tool_name: str, args: dict, result_json: str) -> None:
        """Actualizar el estado visible a partir de una respuesta de tool."""
        try:
            result = json.loads(result_json)
        except json.JSONDecodeError:
            return
        if result.get("status") not in {"success", "escalated"}:
            return

        identificacion = (
            result.get("identificacion")
            or result.get("customer_identification")
            or args.get("identificacion_cliente")
            or args.get("identificacion")
        )

        if tool_name == "consultar_pedido":
            orders = result.get("pedidos", [])
            if orders and isinstance(orders, list):
                first_order = orders[0]
                if not identificacion and isinstance(first_order, dict):
                    identificacion = first_order.get("customer_identification")
                order_id = args.get("pedido_id") or (
                    first_order.get("order_id") if isinstance(first_order, dict) else None
                )
                if order_id:
                    self.state.ultimo_pedido_consultado = order_id
        elif args.get("pedido_id"):
            self.state.ultimo_pedido_consultado = args["pedido_id"]

        if identificacion:
            identificacion_str = str(identificacion).strip()
            self.state.cliente_identificacion = identificacion_str
            self.repository.link_session_customer(self.session_id, identificacion_str)
            if not self.state.cliente_nombre or not self.state.tipo_cliente:
                customer_info = self.repository.find_customer(identificacion_str)
                if customer_info:
                    self.state.cliente_nombre = customer_info.get("full_name") or customer_info.get("nombre")
                    self.state.tipo_cliente = customer_info.get("customer_type") or customer_info.get("tipo")

        if result.get("nombre"):
            self.state.cliente_nombre = result["nombre"]
        if result.get("full_name"):
            self.state.cliente_nombre = result["full_name"]
        if result.get("tipo_cliente"):
            self.state.tipo_cliente = result["tipo_cliente"]
        if result.get("customer_type"):
            self.state.tipo_cliente = result["customer_type"]

        if tool_name in {"consultar_catalogo", "comparar_productos"}:
            products = result.get("productos", [])
            for product in products:
                name = product.get("name") or product.get("nombre")
                if name and name not in self.state.productos_consultados:
                    self.state.productos_consultados.append(name)

        if args.get("presupuesto_max") is not None:
            self.state.presupuesto_mencionado = args["presupuesto_max"]

        if args.get("uso_destinado"):
            preference = args["uso_destinado"].strip()
            if preference and preference not in self.state.preferencias_usuario:
                self.state.preferencias_usuario.append(preference)
    
    @staticmethod
    def _catalog_request(user_input: str) -> dict | None:
        """Detectar una solicitud de recomendación y extraer sus filtros básicos."""
        normalized = user_input.lower()
        sales_terms = (
            "laptop",
            "portátil",
            "portatil",
            "computador",
            "computadora",
            "pc",
            "equipo",
            "producto",
            "recomienda",
            "recomendar",
        )
        if not any(term in normalized for term in sales_terms):
            return None

        request = {"categoria": None, "presupuesto_max": None, "uso_destinado": None}
        if any(term in normalized for term in ("laptop", "portátil", "portatil", "computador", "computadora", "pc", "equipo")):
            request["categoria"] = "computadores"
        if "diseño gráfico" in normalized or "diseno grafico" in normalized:
            request["uso_destinado"] = "diseño gráfico"
        elif "gaming" in normalized or "videojuego" in normalized:
            request["uso_destinado"] = "gaming"
        elif "oficina" in normalized or "trabajo" in normalized:
            request["uso_destinado"] = "oficina"

        budget_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(millones?|millon|mil(?:\s|$))", normalized)
        if budget_match:
            amount = float(budget_match.group(1).replace(",", "."))
            unit = budget_match.group(2)
            request["presupuesto_max"] = amount * (1_000_000 if "millon" in unit else 1_000)
        else:
            number_match = re.search(r"(?:menos de|hasta|presupuesto de)\s*\$?\s*([\d.,]+)", normalized)
            if number_match:
                request["presupuesto_max"] = float(number_match.group(1).replace(".", "").replace(",", "."))

        return request

    def _build_system_prompt(self) -> str:
        """Construir el prompt de sistema inyectando el estado de memoria actual."""
        context_items = []
        if self.state.cliente_identificacion:
            context_items.append(f"- Identificación del cliente: {self.state.cliente_identificacion}")
        if self.state.cliente_nombre:
            context_items.append(f"- Nombre del cliente: {self.state.cliente_nombre}")
        if self.state.tipo_cliente:
            context_items.append(f"- Tipo de cliente: {self.state.tipo_cliente}")
        if self.state.ultimo_pedido_consultado:
            context_items.append(f"- Último pedido consultado: {self.state.ultimo_pedido_consultado}")
        if self.state.presupuesto_mencionado:
            context_items.append(f"- Presupuesto mencionado: ${self.state.presupuesto_mencionado:,.0f} COP")
        if self.state.productos_consultados:
            context_items.append(f"- Productos consultados: {', '.join(self.state.productos_consultados)}")
        if self.state.preferencias_usuario:
            context_items.append(f"- Preferencias expresadas: {', '.join(self.state.preferencias_usuario)}")

        if context_items:
            context_str = "\n".join(context_items)
            return f"{SYSTEM_PROMPT}\n\n[MEMORIA DE SESIÓN ACTUAL]:\n{context_str}"
        return SYSTEM_PROMPT

    def chat(self, user_input: str) -> str:
        """Enviar un mensaje y resolver las tools solicitadas por el modelo."""
        api_client = get_client()
        self.messages[0] = {"role": "system", "content": self._build_system_prompt()}
        self.messages.append({"role": "user", "content": user_input})
        self.repository.save_message(self.session_id, "user", user_input)
        catalog_request = self._catalog_request(user_input)
        tool_choice = (
            {"type": "function", "function": {"name": "consultar_catalogo"}}
            if catalog_request
            else "auto"
        )
        response = api_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=self.messages,
            tools=TOOLS_SCHEMA,
            tool_choice=tool_choice,
        )
        response_message = response.choices[0].message
        while response_message.tool_calls:
            self.messages.append(response_message.model_dump(exclude_none=True))
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_to_call = TOOL_MAPPING.get(function_name)
                if function_to_call is None:
                    raise ValueError(f"Tool no registrada: {function_name}")
                arguments = json.loads(tool_call.function.arguments)
                if function_name == "consultar_catalogo" and catalog_request:
                    arguments = {
                        key: value
                        for key, value in catalog_request.items()
                        if value is not None
                    }
                function_response = function_to_call(**arguments)
                self._actualizar_memoria(function_name, arguments, function_response)
                self.messages[0] = {"role": "system", "content": self._build_system_prompt()}
                self.repository.save_message(self.session_id, "tool", function_response)
                self.messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": function_response})
            response = api_client.chat.completions.create(model=DEFAULT_MODEL, messages=self.messages, tools=TOOLS_SCHEMA)
            response_message = response.choices[0].message
        content = response_message.content or "No pude generar una respuesta."
        self.messages.append({"role": "assistant", "content": content})
        self.repository.save_message(self.session_id, "assistant", content)
        return content
