"""Public Fusarium GETs must not 500/502 when MINDEX is empty or degraded."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mycosoft_mas.core.routers.fusarium_api import (
    MindexFetch,
    _get,
    _mindex_api_base,
    _public_list,
    get_active_threats,
    get_current_dispersal,
    get_fungal_species,
    get_risk_zones,
)


def test_mindex_api_base_appends_prefix(monkeypatch):
    monkeypatch.setenv("MINDEX_API_URL", "http://192.168.0.189:8000")
    assert _mindex_api_base() == "http://192.168.0.189:8000/api/mindex"


def test_mindex_api_base_keeps_existing_prefix(monkeypatch):
    monkeypatch.setenv("MINDEX_API_URL", "http://192.168.0.189:8000/api/mindex")
    assert _mindex_api_base() == "http://192.168.0.189:8000/api/mindex"


def test_public_list_unqualified_when_empty():
    fetch = MindexFetch(True, 200, {"assessments": []}, "ok", "/taco/assessments")
    payload = _public_list("threats", [], fetch)
    assert payload["qualification"] == "UNQUALIFIED"
    assert payload["reason"] == "empty"
    assert payload["threats"] == []
    assert payload["items"] == []
    assert payload["source_status"] == 200


def test_public_list_unqualified_when_upstream_error():
    fetch = MindexFetch(False, 401, {}, "upstream_error", "/taco/assessments")
    payload = _public_list("threats", [], fetch)
    assert payload["qualification"] == "UNQUALIFIED"
    assert payload["source_status"] == 401
    assert payload["reason"] == "upstream_error"


@pytest.mark.asyncio
async def test_get_does_not_raise_on_mindex_401():
    response = MagicMock()
    response.status_code = 401
    response.json.return_value = {"detail": "Missing internal service token"}

    mock_client = AsyncMock()
    mock_client.get.return_value = response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with patch("mycosoft_mas.core.routers.fusarium_api.httpx.AsyncClient", return_value=mock_client):
        fetch = await _get("/taco/assessments", {"limit": 1})

    assert fetch.ok is False
    assert fetch.status == 401
    assert fetch.data["assessments"] == []


@pytest.mark.asyncio
async def test_public_endpoints_return_unqualified_empty():
    failed = MindexFetch(False, 401, {"assessments": [], "environments": [], "data": []}, "upstream_error", "/taco/assessments")
    with patch("mycosoft_mas.core.routers.fusarium_api._get", new=AsyncMock(return_value=failed)):
        threats = await get_active_threats(limit=50)
        zones = await get_risk_zones()
        species = await get_fungal_species(limit=20)
        dispersal = await get_current_dispersal()

    assert threats["qualification"] == "UNQUALIFIED"
    assert threats["threats"] == []
    assert zones["qualification"] == "UNQUALIFIED"
    assert zones["risk_zones"] == []
    assert species["qualification"] == "UNQUALIFIED"
    assert species["species"] == []
    assert dispersal["qualification"] == "UNQUALIFIED"
    assert dispersal["assessments"] == []
    assert dispersal["ocean_environments"] == []
