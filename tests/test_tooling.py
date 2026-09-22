import json

from app.database import DB_CHAT_MESSAGES, DB_CHAT_SESSIONS, DB_GARANTIAS
from app.agent import RetailAgent
from app.db.repositories import get_repository
from app.tooling import (
    comparar_productos,
    consultar_garantia,
    consultar_pedido,
    registrar_solicitud_garantia,
    validar_cobertura_garantia,
)


def test_response_serializer_handles_date():
    from datetime import date
    from app.tooling import _response

    result = json.loads(_response({"date": date(2026, 9, 25)}))
    assert result["date"] == "2026-09-25"


def test_catalog_and_comparison():
    from app.tooling import consultar_catalogo

    catalog = json.loads(consultar_catalogo("computadores", 5000000))
    comparison = json.loads(comparar_productos(["LAP-DG-01", "LAP-OFF-02"]))

    assert catalog["total"] == 2
    assert comparison["status"] == "success"
    assert len(comparison["productos"]) == 2


def test_order_requires_identifier():
    result = json.loads(consultar_pedido())

    assert result["status"] == "needs_clarification"


def test_warranty_coverage_and_ticket():
    coverage = json.loads(validar_cobertura_garantia("10101010", "LAP-DG-01"))
    tv_coverage = json.loads(validar_cobertura_garantia("10101010", "televisor"))
    ticket = json.loads(
        registrar_solicitud_garantia("10101010", "TV-OLED-55", "No enciende")
    )
    status = json.loads(consultar_garantia("10101010", "TV-OLED-55"))

    assert coverage["covered"] is True
    assert tv_coverage["covered"] is True
    assert tv_coverage["product_sku"] == "TV-OLED-55"
    assert ticket["status"] == "success"
    assert status["tickets"]
    DB_GARANTIAS.pop(ticket["ticket_id"], None)


def test_unknown_product_is_not_registered():
    result = json.loads(
        registrar_solicitud_garantia("10101010", "UNKNOWN-SKU", "No enciende")
    )

    assert result["status"] == "escalated"
    assert result["covered"] is False


def test_agent_memory_keeps_customer_preference_and_order():
    agent = RetailAgent()
    agent._actualizar_memoria(
        "validar_cliente_frecuente",
        {},
        '{"status":"success","identificacion":"10101010","nombre":"Liceth Guerrero","tipo_cliente":"frecuente"}',
    )
    agent._actualizar_memoria(
        "consultar_catalogo",
        {"presupuesto_max": 5000000, "uso_destinado": "diseño gráfico"},
        '{"status":"success","productos":[{"name":"Laptop Pro Art 16"}]}',
    )
    agent._actualizar_memoria(
        "consultar_pedido",
        {},
        '{"status":"success","pedidos":[{"order_id":"PED-1001"}]}',
    )

    assert agent.state.cliente_nombre == "Liceth Guerrero"
    assert agent.state.tipo_cliente == "frecuente"
    assert agent.state.presupuesto_mencionado == 5000000
    assert agent.state.preferencias_usuario == ["diseño gráfico"]
    assert agent.state.ultimo_pedido_consultado == "PED-1001"


def test_agent_memory_updates_from_order_query():
    agent = RetailAgent()
    agent._actualizar_memoria(
        "consultar_pedido",
        {"pedido_id": "PED-1001"},
        '{"status":"success","pedidos":[{"order_id":"PED-1001","customer_identification":"10101010","status":"En camino"}]}',
    )

    assert agent.state.ultimo_pedido_consultado == "PED-1001"
    assert agent.state.cliente_identificacion == "10101010"
    assert agent.state.cliente_nombre == "Liceth Guerrero"
    assert agent.state.tipo_cliente == "frecuente"


def test_catalog_request_normalizes_sales_prompt():
    request = RetailAgent._catalog_request(
        "Necesito un portátil para diseño gráfico por menos de 5 millones de pesos"
    )

    assert request == {
        "categoria": "computadores",
        "presupuesto_max": 5000000,
        "uso_destinado": "diseño gráfico",
    }


def test_persist_session_messages():
    repository = get_repository()
    session_id = "test-session"
    repository.create_session(session_id)
    repository.save_message(session_id, "user", "Hola")
    repository.save_message(session_id, "assistant", "Hola, soy Nexo.")

    assert DB_CHAT_SESSIONS[session_id]["session_id"] == session_id
    assert sum(message["session_id"] == session_id for message in DB_CHAT_MESSAGES) == 2
