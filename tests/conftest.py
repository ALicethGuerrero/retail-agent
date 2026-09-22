import pytest


@pytest.fixture(autouse=True)
def use_mock_repository(monkeypatch):
    monkeypatch.setenv("USE_MOCK_DATA", "true")
