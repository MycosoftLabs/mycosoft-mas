from __future__ import annotations

import pytest

from mycosoft_mas.core.routers.gws_boundary_api import gws_boundary_status
from mycosoft_mas.soc.gws_boundary_scan import (
    BoundaryScanService,
    get_boundary_status,
    sanitize_workspace_hit,
)


def test_status_is_not_configured_without_service_account_credentials(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GOOGLE_WORKSPACE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("GOOGLE_WORKSPACE_SA_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_WORKSPACE_REPORTS_TOKEN", raising=False)

    status = BoundaryScanService().configuration_status()

    assert status["configured"] is False
    assert status["status"] == "not-configured"


@pytest.mark.asyncio
async def test_persisted_status_falls_back_to_pending_without_database(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GOOGLE_WORKSPACE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("GOOGLE_WORKSPACE_SA_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_WORKSPACE_REPORTS_TOKEN", raising=False)

    status = await get_boundary_status()

    assert status["configured"] is False
    assert status["status"] == "not-configured"
    assert status["hits"] == []


@pytest.mark.asyncio
async def test_invalid_service_account_configuration_fails_closed(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GOOGLE_WORKSPACE_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("GOOGLE_WORKSPACE_SA_KEY", "not-a-valid-service-account-key")

    result = await BoundaryScanService().run_once()

    assert result["configured"] is True
    assert result["status"] == "error"
    assert result["hits"] == []


@pytest.mark.asyncio
async def test_read_api_returns_location_only_pending_status(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GOOGLE_WORKSPACE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("GOOGLE_WORKSPACE_SA_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_WORKSPACE_REPORTS_TOKEN", raising=False)

    response = await gws_boundary_status()

    assert response["status"] == "not-configured"
    assert response["hits"] == []
    assert "content" not in response
    assert "snippet" not in response


def test_workspace_hit_strips_unapproved_google_response_fields() -> None:
    hit = sanitize_workspace_hit(
        {
            "id": "drive-file-123",
            "name": "CUI//SP-CTI restricted engineering data",
            "owners": [{"emailAddress": "owner@example.com"}],
            "modifiedTime": "2026-07-24T12:00:00Z",
            "webViewLink": "https://drive.example/file",
            "description": "CUI content must never leave its approved boundary",
            "contentHints": {"indexableText": "sensitive body content"},
        },
        marking_token="CUI//",
        detected_at="2026-07-24T12:30:00Z",
    )

    assert hit == {
        "source": "google_drive",
        "container": "my-drive",
        "itemId": "drive-file-123",
        "owner": "owner@example.com",
        "markingToken": "CUI//",
        "detectedAt": "2026-07-24T12:30:00Z",
    }
