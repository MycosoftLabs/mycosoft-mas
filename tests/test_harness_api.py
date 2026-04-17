"""FastAPI route tests for harness router (no full MAS app)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mycosoft_mas.harness.api import reset_engine_for_tests, router as harness_router
from mycosoft_mas.harness.models import HarnessResult, RouteType


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(harness_router)
    reset_engine_for_tests()
    yield TestClient(app)
    reset_engine_for_tests()


def test_harness_health(client: TestClient):
    r = client.get("/api/harness/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["component"] == "myca-harness"


def test_harness_packet_mocked_engine(client: TestClient):
    mock_eng = MagicMock()
    mock_eng.run = AsyncMock(
        return_value=HarnessResult(
            route=RouteType.NEMOTRON,
            text="synthetic",
            sources=["nemotron"],
        )
    )
    with patch("mycosoft_mas.harness.api.get_engine", return_value=mock_eng):
        r = client.post(
            "/api/harness/packet",
            json={"query": "hello harness", "metadata": {"no_grounding": True}},
        )
    assert r.status_code == 200
    assert r.json()["text"] == "synthetic"
    mock_eng.run.assert_called_once()
