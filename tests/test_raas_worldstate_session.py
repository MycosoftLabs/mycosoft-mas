"""Tests for RaaS worldstate session lifecycle API.

Verifies: 401 without API key, 402 when balance exhausted, 200 flows for
start/heartbeat/stop/balance/usage, and end-to-end agent flow (money in/out).
Uses a minimal FastAPI app with the session router; auth and worldstate_session
are overridden/mocked so no real MINDEX DB is required.

Created: March 14, 2026
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from mycosoft_mas.raas.middleware import require_raas_auth
from mycosoft_mas.raas.models import AgentAccount, WorldstateBalance, WorldstateSessionSummary
from mycosoft_mas.raas.session_lifecycle import router as raas_session_router

# Build minimal app with only the RaaS worldstate session router
app = FastAPI()
app.include_router(raas_session_router)


async def fake_raas_auth(request: Request) -> AgentAccount:
    """Fake auth: 401 if no X-API-Key, else return test agent (no DB)."""
    if not request.headers.get("X-API-Key"):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="X-API-Key header missing")
    return AgentAccount(agent_id="test-agent", agent_name="Test Agent")


app.dependency_overrides[require_raas_auth] = fake_raas_auth

# Default headers for authenticated requests
AUTH_HEADERS = {"X-API-Key": "test-key"}


def test_session_start_401_no_key():
    """POST /start without X-API-Key returns 401."""
    client = TestClient(app)
    r = client.post("/api/raas/worldstate/start", headers={})
    assert r.status_code == 401
    assert "X-API-Key" in (r.json().get("detail") or "")


@patch("mycosoft_mas.raas.session_lifecycle.start_session", new_callable=AsyncMock)
def test_session_start_402_insufficient_balance(m_start):
    """POST /start when balance is 0 returns 402 and X-Balance-Minutes: 0."""
    m_start.return_value = (None, 0, "insufficient_balance")
    client = TestClient(app)
    r = client.post("/api/raas/worldstate/start", headers=AUTH_HEADERS)
    assert r.status_code == 402
    assert r.headers.get("X-Balance-Minutes") == "0"
    assert "insufficient" in (r.json().get("detail") or "").lower()


@patch("mycosoft_mas.raas.session_lifecycle.start_session", new_callable=AsyncMock)
def test_session_start_200(m_start):
    """POST /start with balance returns 200, session_id and balance_minutes."""
    m_start.return_value = ("ws_abc123", 60, None)
    client = TestClient(app)
    r = client.post("/api/raas/worldstate/start", headers=AUTH_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "ws_abc123"
    assert data["balance_minutes"] == 60


@patch("mycosoft_mas.raas.session_lifecycle.heartbeat_session", new_callable=AsyncMock)
def test_session_heartbeat_402_insufficient_balance(m_heartbeat):
    """POST /heartbeat when balance exhausted returns 402."""
    m_heartbeat.return_value = (False, 0, 0, "insufficient_balance")
    client = TestClient(app)
    r = client.post(
        "/api/raas/worldstate/heartbeat",
        headers=AUTH_HEADERS,
        json={"session_id": "ws_abc123"},
    )
    assert r.status_code == 402
    assert r.headers.get("X-Balance-Minutes") == "0"


@patch("mycosoft_mas.raas.session_lifecycle.heartbeat_session", new_callable=AsyncMock)
def test_session_heartbeat_200(m_heartbeat):
    """POST /heartbeat success returns 200 with balance and minutes_used."""
    m_heartbeat.return_value = (True, 59, 1, None)
    client = TestClient(app)
    r = client.post(
        "/api/raas/worldstate/heartbeat",
        headers=AUTH_HEADERS,
        json={"session_id": "ws_abc123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "ws_abc123"
    assert data["balance_minutes"] == 59
    assert data["minutes_used_this_session"] == 1


@patch("mycosoft_mas.raas.session_lifecycle.stop_session", new_callable=AsyncMock)
def test_session_stop_200(m_stop):
    """POST /stop returns 200 with total_minutes_used and balance."""
    m_stop.return_value = (True, 2, 58, None)
    client = TestClient(app)
    r = client.post(
        "/api/raas/worldstate/stop",
        headers=AUTH_HEADERS,
        json={"session_id": "ws_abc123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "ws_abc123"
    assert data["total_minutes_used"] == 2
    assert data["balance_minutes"] == 58


@patch("mycosoft_mas.raas.session_lifecycle.get_balance", new_callable=AsyncMock)
def test_balance_200(m_balance):
    """GET /balance returns 200 with WorldstateBalance."""
    m_balance.return_value = WorldstateBalance(
        agent_id="test-agent",
        balance_minutes=58,
        total_purchased_minutes=60,
        total_used_minutes=2,
    )
    client = TestClient(app)
    r = client.get("/api/raas/worldstate/balance", headers=AUTH_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["agent_id"] == "test-agent"
    assert data["balance_minutes"] == 58
    assert data["total_used_minutes"] == 2


@patch("mycosoft_mas.raas.session_lifecycle.get_usage", new_callable=AsyncMock)
def test_usage_200(m_usage):
    """GET /usage returns 200 with balance and recent_sessions."""
    bal = WorldstateBalance(
        agent_id="test-agent",
        balance_minutes=58,
        total_purchased_minutes=60,
        total_used_minutes=2,
    )
    sess = WorldstateSessionSummary(
        session_id="ws_abc123",
        agent_id="test-agent",
        started_at=None,
        last_heartbeat_at=None,
        stopped_at=None,
        minutes_used=2,
    )
    m_usage.return_value = (bal, None, [sess])
    client = TestClient(app)
    r = client.get("/api/raas/worldstate/usage", headers=AUTH_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["agent_id"] == "test-agent"
    assert data["balance_minutes"] == 58
    assert data["active_session_id"] is None
    assert len(data["recent_sessions"]) == 1
    assert data["recent_sessions"][0]["session_id"] == "ws_abc123"
    assert data["recent_sessions"][0]["minutes_used"] == 2


@patch("mycosoft_mas.raas.session_lifecycle.start_session", new_callable=AsyncMock)
@patch("mycosoft_mas.raas.session_lifecycle.heartbeat_session", new_callable=AsyncMock)
@patch("mycosoft_mas.raas.session_lifecycle.stop_session", new_callable=AsyncMock)
@patch("mycosoft_mas.raas.session_lifecycle.get_balance", new_callable=AsyncMock)
@patch("mycosoft_mas.raas.session_lifecycle.get_usage", new_callable=AsyncMock)
def test_agent_flow_money_in_and_out(m_usage, m_balance, m_stop, m_heartbeat, m_start):
    """Agent flow: start -> heartbeat -> stop -> balance/usage; money (minutes) flows correctly."""
    client = TestClient(app)
    # Start: 60 minutes
    m_start.return_value = ("ws_flow1", 60, None)
    r1 = client.post("/api/raas/worldstate/start", headers=AUTH_HEADERS)
    assert r1.status_code == 200
    assert r1.json()["balance_minutes"] == 60
    session_id = r1.json()["session_id"]
    # Heartbeat: deduct 1 minute -> 59
    m_heartbeat.return_value = (True, 59, 1, None)
    r2 = client.post(
        "/api/raas/worldstate/heartbeat",
        headers=AUTH_HEADERS,
        json={"session_id": session_id},
    )
    assert r2.status_code == 200
    assert r2.json()["balance_minutes"] == 59
    assert r2.json()["minutes_used_this_session"] == 1
    # Stop: total 1 minute used, balance 59
    m_stop.return_value = (True, 1, 59, None)
    r3 = client.post(
        "/api/raas/worldstate/stop",
        headers=AUTH_HEADERS,
        json={"session_id": session_id},
    )
    assert r3.status_code == 200
    assert r3.json()["total_minutes_used"] == 1
    assert r3.json()["balance_minutes"] == 59
    # Balance reflects 59
    m_balance.return_value = WorldstateBalance(
        agent_id="test-agent",
        balance_minutes=59,
        total_purchased_minutes=60,
        total_used_minutes=1,
    )
    r4 = client.get("/api/raas/worldstate/balance", headers=AUTH_HEADERS)
    assert r4.status_code == 200
    assert r4.json()["balance_minutes"] == 59
    assert r4.json()["total_used_minutes"] == 1
    # Usage reflects session
    m_usage.return_value = (
        WorldstateBalance(
            agent_id="test-agent",
            balance_minutes=59,
            total_purchased_minutes=60,
            total_used_minutes=1,
        ),
        None,
        [
            WorldstateSessionSummary(
                session_id=session_id,
                agent_id="test-agent",
                started_at=None,
                last_heartbeat_at=None,
                stopped_at=None,
                minutes_used=1,
            )
        ],
    )
    r5 = client.get("/api/raas/worldstate/usage", headers=AUTH_HEADERS)
    assert r5.status_code == 200
    assert r5.json()["balance_minutes"] == 59
    assert r5.json()["total_used_minutes"] == 1
    assert len(r5.json()["recent_sessions"]) == 1
    assert r5.json()["recent_sessions"][0]["minutes_used"] == 1
