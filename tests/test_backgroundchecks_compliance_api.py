from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mycosoft_mas.core.routers import compliance_api


class FakeBackgroundChecksClient:
    is_configured = True

    async def list_reports(self) -> list[dict[str, object]]:
        return [
            {
                "applicant_email": "morgan@example.com",
                "report_key": "report-1",
                "report_sku": "HIRE1",
                "report_status": "pending",
                "timestamp": "2026-07-20T00:00:00Z",
            },
            {
                "applicant_email": "not-allowed@example.com",
                "report_key": "report-2",
                "report_sku": "HIRE1",
                "report_status": "complete",
            },
        ]


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(compliance_api.router)
    app.include_router(compliance_api.posture_router)
    return TestClient(app)


def test_background_checks_requires_integration_api_key(monkeypatch) -> None:
    monkeypatch.setenv("MYCA_POSTURE_API_KEY", "test-posture-key")

    response = _client().get("/api/compliance/background-checks")

    assert response.status_code == 401


def test_background_checks_filters_to_allowlisted_subjects(monkeypatch) -> None:
    monkeypatch.setenv("MYCA_POSTURE_API_KEY", "test-posture-key")
    monkeypatch.setenv("BACKGROUNDCHECKS_ALLOWED_EMPLOYEE_EMAILS", "morgan@example.com,rj@example.com")
    monkeypatch.setattr(compliance_api, "BackgroundChecksClient", FakeBackgroundChecksClient)

    response = _client().get(
        "/api/compliance/background-checks",
        headers={"X-API-Key": "test-posture-key"},
    )

    assert response.status_code == 200
    assert response.json()["subjects"] == [
        {
            "applicant_email": "morgan@example.com",
            "report_key": "report-1",
            "report_sku": "HIRE1",
            "report_status": "pending",
            "timestamp": "2026-07-20T00:00:00Z",
            "expired": None,
        }
    ]


def test_order_is_blocked_when_production_flag_is_false(monkeypatch) -> None:
    monkeypatch.setenv("MYCA_POSTURE_API_KEY", "test-posture-key")
    monkeypatch.setenv("BACKGROUNDCHECKS_ALLOWED_EMPLOYEE_EMAILS", "morgan@example.com")
    monkeypatch.delenv("BACKGROUNDCHECKS_PROD_ORDERS_ALLOWED", raising=False)

    response = _client().post(
        "/api/compliance/background-checks/order",
        headers={"X-API-Key": "test-posture-key"},
        json={
            "applicant_email": "morgan@example.com",
            "report_sku": "HIRE1",
            "terms_agree": True,
        },
    )

    assert response.status_code == 409


def test_posture_never_exposes_preveil_drive_path(monkeypatch) -> None:
    monkeypatch.setenv("MYCA_POSTURE_API_KEY", "test-posture-key")
    monkeypatch.setenv("PREVEIL_DRIVE_PATH", "P:\\PreVeil")
    monkeypatch.delenv("BACKGROUNDCHECKS_API_TOKEN", raising=False)

    response = _client().get("/api/myca/posture", headers={"X-API-Key": "test-posture-key"})

    assert response.status_code == 200
    body = response.json()
    assert body["preveil"]["design"] == "drive_fs"
    assert body["preveil"]["drive_path_configured"] is True
    assert body["preveil"]["pe_l2_3_10_6"]["met"] is False
    assert body["background_checks"]["production_orders_allowed"] is False
    assert body["myca_runtime"]["daily_runtime_live"] is False
    assert "P:\\PreVeil" not in response.text
