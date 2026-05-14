from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mycosoft_mas.avani.audit.ledger import AvaniAuditLedger
from mycosoft_mas.avani.audit.season_state import AvaniSeasonStateStore
from mycosoft_mas.core.routers import avani_router


class FailingMindexClient:
    async def _get_db_pool(self):
        raise RuntimeError("database unavailable in test")


def _build_client(tmp_path):
    avani_router._season_engine = None
    avani_router._governor = None
    avani_router._runtime_restored = False
    avani_router._audit_ledger = AvaniAuditLedger(
        mindex_client=FailingMindexClient(), fallback_dir=tmp_path
    )
    avani_router._season_store = AvaniSeasonStateStore(
        mindex_client=FailingMindexClient(), fallback_dir=tmp_path
    )
    app = FastAPI()
    app.include_router(avani_router.router)
    return app, TestClient(app)


def _override_dependencies(app: FastAPI, path: str, scope: str):
    route = next(route for route in app.routes if getattr(route, "path", None) == path)
    for dependency in route.dependant.dependencies:
        async def fake_auth():
            return {"user_id": "test-user", "scopes": [scope]}

        app.dependency_overrides[dependency.call] = fake_auth


def test_public_health_is_unauthenticated(tmp_path):
    _, client = _build_client(tmp_path)
    response = client.get("/api/avani/health")
    assert response.status_code == 200
    assert response.json()["system"] == "avani-governor"
    assert response.json()["audit"]["chain_valid"] is True


def test_protected_stats_requires_api_key(tmp_path):
    _, client = _build_client(tmp_path)
    response = client.get("/api/avani/stats")
    assert response.status_code == 401


def test_evaluate_message_with_scope_logs_audit(tmp_path):
    app, client = _build_client(tmp_path)
    _override_dependencies(app, "/api/avani/evaluate-message", "avani:evaluate")

    response = client.post(
        "/api/avani/evaluate-message",
        json={"message": "hello", "user_id": "u1", "action_type": "chat"},
    )

    assert response.status_code == 200
    assert response.json()["verdict"] == "allow"


def test_ecological_review_is_queryable_from_audit_log(tmp_path):
    app, client = _build_client(tmp_path)
    _override_dependencies(app, "/api/avani/ecological-review", "avani:evaluate")
    _override_dependencies(app, "/api/avani/ecological-audit-log", "avani:audit:read")

    review = client.post(
        "/api/avani/ecological-review",
        json={"classification": "unknown", "marine_mammal_score": 0.8},
    )
    audit = client.get("/api/avani/ecological-audit-log")

    assert review.status_code == 200
    assert review.json()["action"] == "gate_for_human_review"
    assert audit.status_code == 200
    assert audit.json()["total"] == 1
    assert audit.json()["audit_entries"][0]["event_kind"] == "ecological_review"


def test_worldview_review_with_scope_logs_audit(tmp_path):
    app, client = _build_client(tmp_path)
    _override_dependencies(app, "/api/avani/worldview/review", "avani:evaluate")
    _override_dependencies(app, "/api/avani/decisions/recent", "avani:audit:read")

    response = client.post(
        "/api/avani/worldview/review",
        json={
            "worldview_request_id": "req-1",
            "data": [{"id": "taxon-1"}],
            "source_domains": ["species"],
            "caller": {"plan": "pro", "user_type": "agent"},
        },
    )
    audit = client.get("/api/avani/decisions/recent")

    assert response.status_code == 200
    assert response.json()["avani_verdict"] == "allow"
    assert response.json()["audit_trail_id"].startswith("avani-")
    assert any(e["event_kind"] == "worldview_review" for e in audit.json()["decisions"])


def test_grounding_check_requires_evidence(tmp_path):
    app, client = _build_client(tmp_path)
    _override_dependencies(app, "/api/avani/grounding-check", "avani:evaluate")

    response = client.post(
        "/api/avani/grounding-check",
        json={"claim": "forecast is safe", "confidence": 0.9, "evidence": {}},
    )

    assert response.status_code == 200
    assert response.json()["approved"] is False
    assert response.json()["verdict"] == "require_approval"


def test_action_preflight_with_scope_returns_standard_decision(tmp_path):
    app, client = _build_client(tmp_path)
    _override_dependencies(app, "/api/avani/preflight", "avani:evaluate")

    response = client.post(
        "/api/avani/preflight",
        json={
            "source_agent": "test-agent",
            "action_type": "generate_workflow",
            "description": "Generate a read-only reporting workflow.",
            "risk_tier": "medium",
        },
    )

    assert response.status_code == 200
    assert response.json()["approved"] is True
    assert response.json()["verdict"] == "allow"
    assert response.json()["storage_mode"] == "jsonl_fallback"


def test_device_preflight_blocks_missing_rollback_and_logs_audit(tmp_path):
    app, client = _build_client(tmp_path)
    _override_dependencies(app, "/api/avani/device/preflight", "avani:evaluate")
    _override_dependencies(app, "/api/avani/decisions/recent", "avani:audit:read")

    response = client.post(
        "/api/avani/device/preflight",
        json={
            "device_id": "sensor-1",
            "action": "deploy",
            "operator_id": "operator-1",
            "telemetry": {"status": "online"},
            "ecological_impact": 0.4,
            "reversibility": 0.7,
        },
    )
    audit = client.get("/api/avani/decisions/recent")

    assert response.status_code == 200
    assert response.json()["approved"] is False
    assert response.json()["verdict"] == "require_approval"
    assert any(e["event_kind"] == "device_preflight" for e in audit.json()["decisions"])


def test_operator_status_reports_audit_and_recent_denials(tmp_path):
    app, client = _build_client(tmp_path)
    _override_dependencies(app, "/api/avani/device/preflight", "avani:evaluate")
    _override_dependencies(app, "/api/avani/operator/status", "avani:audit:read")

    client.post(
        "/api/avani/device/preflight",
        json={
            "device_id": "sensor-1",
            "action": "deploy",
            "operator_id": "operator-1",
            "telemetry": {"status": "offline"},
            "rollback_plan": "Recall by service vessel.",
        },
    )
    response = client.get("/api/avani/operator/status")

    assert response.status_code == 200
    assert response.json()["audit"]["chain_valid"] is True
    assert response.json()["operational_state"]["fail_closed_actions"] is True
    assert response.json()["recent"]["denials"]
