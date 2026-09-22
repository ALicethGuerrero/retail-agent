import json
from pathlib import Path

from app.client import DEFAULT_MODEL, get_client
from app.schemas import SessionState
from app.tooling import TOOL_MAPPING, TOOLS_SCHEMA

SYSTEM_PROMPT = (
    Path(__file__).parent / "prompts" / "system_prompt.md"
).read_text(encoding="utf-8")


class RetailAgent:
    """Mantener la conversación y coordinar las tools del agente."""

    def __init__(self) -> None:
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
        if result.get("identificacion"):
            self.state.cliente_identificacion = result["identificacion"]
        if result.get("nombre"):
            self.state.cliente_nombre = result["nombre"]
        if result.get("tipo_cliente"):
            self.state.tipo_cliente = result["tipo_cliente"]
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
        if tool_name == "consultar_pedido":
            orders = result.get("pedidos", [])
            if result.get("pedido_id"):
                self.state.ultimo_pedido_consultado = result["pedido_id"]
            elif len(orders) == 1:
                self.state.ultimo_pedido_consultado = orders[0].get("order_id")

    def chat(self, user_input: str) -> str:
        """Enviar un mensaje y resolver las tools solicitadas por el modelo."""
        api_client = get_client()
        self.messages.append({"role": "user", "content": user_input})
        response = api_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=self.messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
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
                function_response = function_to_call(**arguments)
                self._actualizar_memoria(function_name, arguments, function_response)
                self.messages.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": function_response})
            response = api_client.chat.completions.create(model=DEFAULT_MODEL, messages=self.messages, tools=TOOLS_SCHEMA)
            response_message = response.choices[0].message
        content = response_message.content or "No pude generar una respuesta."
        self.messages.append({"role": "assistant", "content": content})
        return content
