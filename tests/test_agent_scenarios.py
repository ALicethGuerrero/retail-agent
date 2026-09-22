import json
from types import SimpleNamespace

from app.agent import RetailAgent


class FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: dict):
        self.id = call_id
        self.function = SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        )


class FakeMessage:
    def __init__(self, content: str | None = None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, exclude_none=True):
        result = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            result["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in self.tool_calls
            ]
        return {key: value for key, value in result.items() if value is not None}


class FakeOpenAIClient:
    def __init__(self, messages):
        self.calls = []
        self._messages = iter(messages)
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=next(self._messages))])


def test_scenario_sales_forces_catalog_and_recommends(monkeypatch):
    client = FakeOpenAIClient(
        [
            FakeMessage(
                tool_calls=[
                    FakeToolCall("catalog-1", "consultar_catalogo", {})
                ]
            ),
            FakeMessage(
                "La Laptop Pro Art 16 cuesta $4.800.000 y es adecuada para diseño gráfico."
            ),
        ]
    )
    monkeypatch.setattr("app.agent.orchestrator.get_client", lambda: client)

    agent = RetailAgent(session_id="scenario-sales")
    response = agent.chat(
        "Necesito un portátil para diseño gráfico por menos de 5 millones de pesos"
    )

    first_call = client.calls[0]
    assert first_call["tool_choice"] == {
        "type": "function",
        "function": {"name": "consultar_catalogo"},
    }
    assert agent.state.productos_consultados == ["Laptop Pro Art 16"]
    assert agent.state.presupuesto_mencionado == 5000000
    assert response.startswith("La Laptop Pro Art 16")


def test_scenario_order_requests_missing_identifier(monkeypatch):
    client = FakeOpenAIClient(
        [FakeMessage("Para consultar el pedido, indicar el número de pedido o la identificación.")]
    )
    monkeypatch.setattr("app.agent.orchestrator.get_client", lambda: client)

    agent = RetailAgent(session_id="scenario-order")
    response = agent.chat("Quiero saber dónde está mi pedido")

    assert response.startswith("Para consultar el pedido")
    assert len(client.calls) == 1
    assert client.calls[0]["tool_choice"] == "auto"


def test_scenario_order_with_identification_calls_tool(monkeypatch):
    client = FakeOpenAIClient(
        [
            FakeMessage(
                tool_calls=[
                    FakeToolCall(
                        "order-1",
                        "consultar_pedido",
                        {"identificacion_cliente": "10101010"},
                    )
                ]
            ),
            FakeMessage("Tu pedido PED-1001 se encuentra En camino a centro de distribución."),
        ]
    )
    monkeypatch.setattr("app.agent.orchestrator.get_client", lambda: client)

    agent = RetailAgent(session_id="scenario-order-with-id")
    agent.state.cliente_identificacion = "10101010"
    response = agent.chat("Quiero saber dónde está mi pedido")

    first_call = client.calls[0]
    assert first_call["messages"][0]["role"] == "system"
    assert "Identificación del cliente: 10101010" in first_call["messages"][0]["content"]
    assert response.startswith("Tu pedido PED-1001")


def test_scenario_warranty_validates_and_creates_ticket(monkeypatch):
    client = FakeOpenAIClient(
        [
            FakeMessage(
                tool_calls=[
                    FakeToolCall(
                        "coverage-1",
                        "validar_cobertura_garantia",
                        {
                            "identificacion_cliente": "10101010",
                            "producto_sku": "LAP-DG-01",
                        },
                    )
                ]
            ),
            FakeMessage(
                tool_calls=[
                    FakeToolCall(
                        "ticket-1",
                        "registrar_solicitud_garantia",
                        {
                            "identificacion_cliente": "10101010",
                            "producto_sku": "LAP-DG-01",
                            "falla_reportada": "No enciende",
                        },
                    )
                ]
            ),
            FakeMessage("La garantía está vigente y quedó registrado el ticket TK-8001."),
        ]
    )
    monkeypatch.setattr("app.agent.orchestrator.get_client", lambda: client)

    agent = RetailAgent(session_id="scenario-warranty")
    response = agent.chat(
        "Mi portátil no enciende y tiene garantía. Quiero tramitarla."
    )

    tool_names = [
        call.function.name
        for message in agent.messages
        if isinstance(message, dict) and message.get("tool_calls")
        for call in message["tool_calls"]
        for call in [SimpleNamespace(function=SimpleNamespace(name=call["function"]["name"]))]
    ]
    assert tool_names == [
        "validar_cobertura_garantia",
        "registrar_solicitud_garantia",
    ]
    assert "TK-8001" in response
    assert len(client.calls) == 3
