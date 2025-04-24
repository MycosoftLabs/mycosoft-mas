import pytest
from fastapi.testclient import TestClient
from mycosoft_mas.services.websocket_server import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"} 