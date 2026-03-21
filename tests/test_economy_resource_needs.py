"""Contract tests for GET /api/economy/resources/needs."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from mycosoft_mas.core.routers.economy_api import (
    RECORDED_PURCHASES_CAP,
    RESOURCE_NEEDS_NO_FORECAST_MESSAGE,
)


def _make_state(
    wallets: Dict[str, Dict[str, Any]],
    resource_purchases: List[Any] | None = None,
) -> Dict[str, Any]:
    return {
        "wallets": wallets,
        "resource_purchases": resource_purchases if resource_purchases is not None else [],
    }


@pytest.fixture
def client() -> TestClient:
    from mycosoft_mas.core.myca_main import app

    return TestClient(app)


def test_resource_needs_contract_empty_purchases(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    from mycosoft_mas.core.routers import economy_api

    def fake_get_state() -> Dict[str, Any]:
        return _make_state(
            wallets={
                "a": {"balance": 1.5, "currency": "USD"},
                "b": {"balance": 2.5, "currency": "USD"},
            },
            resource_purchases=[],
        )

    monkeypatch.setattr(economy_api.economy_store, "get_state", fake_get_state)
    r = client.get("/api/economy/resources/needs")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["needs"] == []
    assert body["total_estimated_cost"] is None
    assert body["revenue_needed"] is None
    assert body["current_balance"] == 4.0
    assert body["recorded_purchases"] == []
    assert body["message"] == RESOURCE_NEEDS_NO_FORECAST_MESSAGE


def test_resource_needs_tail_cap_and_order(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    from mycosoft_mas.core.routers import economy_api

    n = RECORDED_PURCHASES_CAP + 10
    purchases = [{"id": i} for i in range(n)]

    def fake_get_state() -> Dict[str, Any]:
        return _make_state(
            wallets={"w": {"balance": 10.0, "currency": "SOL"}},
            resource_purchases=purchases,
        )

    monkeypatch.setattr(economy_api.economy_store, "get_state", fake_get_state)
    r = client.get("/api/economy/resources/needs")
    assert r.status_code == 200
    body = r.json()
    expected_tail = [{"id": i} for i in range(10, n)]
    assert body["recorded_purchases"] == expected_tail
    assert len(body["recorded_purchases"]) == RECORDED_PURCHASES_CAP
    assert body["current_balance"] == 10.0


def test_resource_needs_none_purchases_treated_as_empty(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    from mycosoft_mas.core.routers import economy_api

    def fake_get_state() -> Dict[str, Any]:
        s = _make_state(wallets={"w": {"balance": 0.0}})
        s["resource_purchases"] = None
        return s

    monkeypatch.setattr(economy_api.economy_store, "get_state", fake_get_state)
    r = client.get("/api/economy/resources/needs")
    assert r.status_code == 200
    assert r.json()["recorded_purchases"] == []
