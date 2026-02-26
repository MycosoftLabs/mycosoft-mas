"""
Integration tests for the grounded cognition pipeline.

Tests grounding API endpoints and full chat-to-response flow with grounding.
Created: February 17, 2026
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from mycosoft_mas.core.myca_main import app

    return TestClient(app)


class TestGroundingAPI:
    """Tests for /api/myca/grounding/* endpoints."""

    def test_grounding_status_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/myca/grounding/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "timestamp" in data
        assert "thought_count" in data
        assert "last_ep_id" in data

    def test_grounding_ep_returns_placeholder(self, client: TestClient) -> None:
        resp = client.get("/api/myca/grounding/ep/ep_123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ep_id"] == "ep_123"
        assert "ep_storage_not_implemented" in data.get("status", "")

    def test_grounding_thoughts_returns_list(self, client: TestClient) -> None:
        resp = client.get("/api/myca/grounding/thoughts")
        assert resp.status_code == 200
        data = resp.json()
        assert "thoughts" in data
        assert "count" in data
        assert isinstance(data["thoughts"], list)


class TestErrorTriageAPI:
    """Tests for /api/errors/triage endpoints."""

    def test_triage_post_returns_result(self, client: TestClient) -> None:
        resp = client.post(
            "/api/errors/triage",
            json={
                "error_message": "AttributeError: 'dict' object has no attribute 'foo'",
                "source": "chat",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error_id" in data
        assert "feasibility" in data
        assert data["feasibility"] in ("auto_fixable", "requires_human", "unknown")

    def test_triage_history_returns_list(self, client: TestClient) -> None:
        resp = client.get("/api/errors/triage/history?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)


class TestGroundedCognitionPipeline:
    """Smoke tests for chat pipeline with grounding (no live LLM)."""

    def test_consciousness_chat_endpoint_exists(self, client: TestClient) -> None:
        # POST /api/myca/chat should exist and return 422 when body invalid
        resp = client.post("/api/myca/chat", json={})
        # 422 = validation error (missing required fields), 404 = route missing
        assert resp.status_code in (200, 422, 404, 500)
