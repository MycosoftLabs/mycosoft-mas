import pytest
from fastapi.testclient import TestClient

from mycosoft_mas import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "healthy"


def test_live_endpoint(client: TestClient) -> None:
    resp = client.get("/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "alive"
    assert body.get("service") == "mas"
    assert "version" in body
