import json
from typing import Any
from datetime import date, datetime
from decimal import Decimal

from pydantic import ValidationError

from app.db.repositories import get_repository
from app.schemas import ValidarClienteNuevoInput


def _default_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return str(obj)


def _response(payload: dict[str, Any]) -> str:
    """Serializar una respuesta JSON para devolverla al modelo."""
    return json.dumps(payload, ensure_ascii=False, default=_default_serializer)


def validar_y_registrar_cliente_nuevo(
    identificacion: str, nombre_completo: str, telefono: str, correo: str
) -> str:
    """Validar y registrar un cliente nuevo en el repositorio activo."""
    repository = get_repository()
    identification = identificacion.strip()
    if repository.find_customer(identification):
        return _response(
            {"status": "error", "message": "La identificación ya está registrada."}
        )
    try:
        data = ValidarClienteNuevoInput(
            identificacion=identification,
            nombre_completo=nombre_completo,
            telefono=telefono,
            correo=correo,
        )
    except ValidationError as error:
        errors = [f"{item['loc'][0]}: {item['msg']}" for item in error.errors()]
        return _response({"status": "validation_error", "errors": errors})
    customer = repository.create_customer(
        {
            "identification": data.identificacion,
            "full_name": data.nombre_completo,
            "phone": data.telefono,
            "email": str(data.correo),
            "customer_type": "nuevo",
        }
    )
    return _response(
        {
            "status": "success",
            "message": f"Cliente {customer['full_name']} registrado exitosamente.",
            "identificacion": customer["identification"],
            "nombre": customer["full_name"],
            "tipo_cliente": customer["customer_type"],
        }
    )


def validar_cliente_frecuente(identificacion: str) -> str:
    """Buscar un cliente por su identificación."""
    customer = get_repository().find_customer(identificacion.strip())
    if not customer:
        return _response(
            {"status": "not_found", "message": "Identificación no encontrada."}
        )
    return _response(
        {
            "status": "success",
            "message": f"Cliente {customer['full_name']} encontrado.",
            "identificacion": customer["identification"],
            "nombre": customer["full_name"],
            "tipo_cliente": customer["customer_type"],
        }
    )


def consultar_catalogo(
    categoria: str | None = None,
    presupuesto_max: float | None = None,
    uso_destinado: str | None = None,
) -> str:
    """Filtrar el catálogo por categoría, presupuesto y uso."""
    products = get_repository().list_products(
        {"category": categoria, "budget": presupuesto_max, "use": uso_destinado}
    )
    return _response(
        {"status": "success", "total": len(products), "productos": products}
    )


def comparar_productos(skus: list[str]) -> str:
    """Devolver los datos comparables de dos o más productos."""
    unique_skus = list(dict.fromkeys(skus))
    if len(unique_skus) < 2:
        return _response(
            {"status": "validation_error", "message": "Indica al menos dos SKUs."}
        )
    products = get_repository().compare_products(unique_skus)
    missing = [
        sku
        for sku in unique_skus
        if not any(product["sku"] == sku for product in products)
    ]
    if missing:
        return _response({"status": "not_found", "skus_no_encontrados": missing})
    return _response({"status": "success", "productos": products})


def consultar_pedido(
    pedido_id: str | None = None, identificacion_cliente: str | None = None
) -> str:
    """Consultar pedidos y devolver estado, fecha, dirección e items."""
    if not pedido_id and not identificacion_cliente:
        return _response(
            {
                "status": "needs_clarification",
                "message": "Necesito el número de pedido o la identificación.",
            }
        )
    orders = get_repository().find_orders(pedido_id, identificacion_cliente)
    if not orders:
        return _response(
            {"status": "not_found", "message": "No se encontraron pedidos."}
        )
    return _response({"status": "success", "pedidos": orders})


def actualizar_direccion_entrega(pedido_id: str, nueva_direccion: str) -> str:
    """Actualizar la dirección de un pedido existente."""
    updated = get_repository().update_order_address(pedido_id, nueva_direccion.strip())
    if not updated:
        return _response(
            {
                "status": "not_found",
                "message": f"El pedido {pedido_id} no fue encontrado.",
            }
        )
    return _response(
        {
            "status": "success",
            "pedido_id": pedido_id,
            "message": "Dirección actualizada.",
        }
    )


def _normalizar_sku(producto_sku: str) -> str:
    """Normalizar cadenas informales al SKU correspondiente."""
    if not producto_sku:
        return producto_sku
    clean = producto_sku.strip()
    if clean in {"TV-OLED-55", "LAP-DG-01", "LAP-OFF-02", "CEL-PRO-MAX"}:
        return clean
    lower = clean.lower()
    if "tv" in lower or "televisor" in lower or "oled" in lower:
        return "TV-OLED-55"
    if "pro art" in lower or ("laptop" in lower and "diseño" in lower):
        return "LAP-DG-01"
    if "slim" in lower or "business" in lower or "oficina" in lower:
        return "LAP-OFF-02"
    if "celular" in lower or "smartphone" in lower or "cam" in lower:
        return "CEL-PRO-MAX"
    return clean


def validar_cobertura_garantia(identificacion_cliente: str, producto_sku: str) -> str:
    """Calcular la cobertura usando compra y vigencia almacenadas."""
    sku = _normalizar_sku(producto_sku)
    coverage = get_repository().get_coverage(identificacion_cliente.strip(), sku)
    if not coverage:
        return _response(
            {
                "status": "not_covered",
                "covered": False,
                "message": "No existe una compra elegible para ese cliente y producto.",
            }
        )
    return _response({"status": "success", **coverage})


def consultar_garantia(identificacion_cliente: str, producto_sku: str) -> str:
    """Consultar cobertura y tickets de un cliente y producto."""
    repository = get_repository()
    sku = _normalizar_sku(producto_sku)
    ident = identificacion_cliente.strip()
    coverage = repository.get_coverage(ident, sku)
    tickets = repository.list_warranty_tickets(ident, sku)
    if not coverage and not tickets:
        return _response(
            {
                "status": "not_found",
                "message": "No hay cobertura ni tickets para ese producto.",
            }
        )
    return _response({"status": "success", "cobertura": coverage, "tickets": tickets})


def registrar_solicitud_garantia(
    identificacion_cliente: str, producto_sku: str, falla_reportada: str
) -> str:
    """Registrar un ticket solo cuando la cobertura esté vigente."""
    repository = get_repository()
    sku = _normalizar_sku(producto_sku)
    ident = identificacion_cliente.strip()
    coverage = repository.get_coverage(ident, sku)
    if not coverage:
        return _response(
            {
                "status": "escalated",
                "covered": False,
                "message": "No se pudo validar una cobertura vigente; el caso requiere revisión humana.",
            }
        )
    if not coverage.get("covered"):
        return _response(
            {
                "status": "escalated",
                "covered": False,
                "message": "La cobertura está vencida; el caso requiere revisión humana.",
            }
        )
    ticket = repository.create_warranty_ticket(
        {
            "customer_identification": ident,
            "product_sku": sku,
            "reported_failure": falla_reportada,
        }
    )
    return _response(
        {
            "status": "success",
            "covered": True,
            "ticket_id": ticket["ticket_id"],
            "message": f"Garantía registrada. Ticket asignado: {ticket['ticket_id']}.",
        }
    )


def escalar_a_humano(motivo: str) -> str:
    """Marcar un caso para atención humana."""
    return _response(
        {
            "status": "escalated",
            "message": f"Caso transferido a un asesor humano. Motivo: {motivo}.",
        }
    )


def _parameter_schema(properties: dict, required: list[str] | None = None) -> dict:
    """Construir el esquema JSON usado por el tool calling."""
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "validar_y_registrar_cliente_nuevo",
            "description": "Valida y registra un cliente nuevo.",
            "parameters": _parameter_schema(
                {
                    "identificacion": {"type": "string"},
                    "nombre_completo": {"type": "string"},
                    "telefono": {"type": "string"},
                    "correo": {"type": "string"},
                },
                ["identificacion", "nombre_completo", "telefono", "correo"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validar_cliente_frecuente",
            "description": "Busca un cliente registrado.",
            "parameters": _parameter_schema(
                {"identificacion": {"type": "string"}}, ["identificacion"]
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_catalogo",
            "description": "Consulta productos, precios y especificaciones verificadas.",
            "parameters": _parameter_schema(
                {
                    "categoria": {"type": "string"},
                    "presupuesto_max": {"type": "number"},
                    "uso_destinado": {"type": "string"},
                }
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "comparar_productos",
            "description": "Compara dos o más productos por SKU.",
            "parameters": _parameter_schema(
                {"skus": {"type": "array", "items": {"type": "string"}}}, ["skus"]
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_pedido",
            "description": "Consulta el estado, fecha estimada, dirección e ítems de un pedido usando 'pedido_id' (ej. PED-1001) O 'identificacion_cliente' (ej. 10101010). Se debe invocar inmediatamente si se tiene cualquiera de los dos datos.",
            "parameters": _parameter_schema(
                {
                    "pedido_id": {
                        "type": "string",
                        "description": "Número o código del pedido (opcional si se provee identificacion_cliente).",
                    },
                    "identificacion_cliente": {
                        "type": "string",
                        "description": "Número de cédula o identificación del cliente (opcional si se provee pedido_id).",
                    },
                }
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_direccion_entrega",
            "description": "Actualiza la dirección de un pedido.",
            "parameters": _parameter_schema(
                {
                    "pedido_id": {"type": "string"},
                    "nueva_direccion": {"type": "string"},
                },
                ["pedido_id", "nueva_direccion"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validar_cobertura_garantia",
            "description": "Calcula cobertura usando compra y vigencia verificadas.",
            "parameters": _parameter_schema(
                {
                    "identificacion_cliente": {"type": "string"},
                    "producto_sku": {"type": "string"},
                },
                ["identificacion_cliente", "producto_sku"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_garantia",
            "description": "Consulta cobertura y tickets de garantía.",
            "parameters": _parameter_schema(
                {
                    "identificacion_cliente": {"type": "string"},
                    "producto_sku": {"type": "string"},
                },
                ["identificacion_cliente", "producto_sku"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_solicitud_garantia",
            "description": "Valida cobertura y registra una solicitud de garantía.",
            "parameters": _parameter_schema(
                {
                    "identificacion_cliente": {"type": "string"},
                    "producto_sku": {"type": "string"},
                    "falla_reportada": {"type": "string"},
                },
                ["identificacion_cliente", "producto_sku", "falla_reportada"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalar_a_humano",
            "description": "Transfiere el caso a un asesor humano.",
            "parameters": _parameter_schema({"motivo": {"type": "string"}}, ["motivo"]),
        },
    },
]

TOOL_MAPPING = {
    "validar_y_registrar_cliente_nuevo": validar_y_registrar_cliente_nuevo,
    "validar_cliente_frecuente": validar_cliente_frecuente,
    "consultar_catalogo": consultar_catalogo,
    "comparar_productos": comparar_productos,
    "consultar_pedido": consultar_pedido,
    "actualizar_direccion_entrega": actualizar_direccion_entrega,
    "validar_cobertura_garantia": validar_cobertura_garantia,
    "consultar_garantia": consultar_garantia,
    "registrar_solicitud_garantia": registrar_solicitud_garantia,
    "escalar_a_humano": escalar_a_humano,
}
