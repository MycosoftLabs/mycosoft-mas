"""
MAS proxy to MINDEX Library + SINE APIs (June 4, 2026).

Thin passthrough for agents and n8n — website BFF continues to call MINDEX directly.
Prefix: /api/mas/mindex/library
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mas/mindex/library", tags=["mindex-library-proxy"])

MINDEX_BASE = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
if not MINDEX_BASE.endswith("/api/mindex"):
    MINDEX_BASE = f"{MINDEX_BASE}/api/mindex"
MINDEX_INTERNAL_TOKEN = os.environ.get("MINDEX_INTERNAL_TOKEN", "").strip()
MINDEX_API_KEY = os.environ.get("MINDEX_API_KEY", "").strip()


def _mindex_headers(json_body: bool = False) -> Dict[str, str]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    if json_body:
        headers["Content-Type"] = "application/json"
    if MINDEX_INTERNAL_TOKEN:
        headers["X-Internal-Token"] = MINDEX_INTERNAL_TOKEN
    elif MINDEX_API_KEY:
        headers["X-API-Key"] = MINDEX_API_KEY
    return headers


async def _proxy(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not MINDEX_INTERNAL_TOKEN and not MINDEX_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="MINDEX_INTERNAL_TOKEN or MINDEX_API_KEY not configured on MAS",
        )
    url = f"{MINDEX_BASE}{path}"
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.request(
            method,
            url,
            params=params,
            json=body,
            headers=_mindex_headers(json_body=body is not None),
        )
        if response.status_code >= 400:
            logger.warning("MINDEX library proxy %s %s -> %s", method, path, response.status_code)
            raise HTTPException(status_code=response.status_code, detail=response.text[:500])
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}


@router.get("/health")
async def library_proxy_health() -> Dict[str, Any]:
    """MAS-side health: MINDEX library catalog reachability."""
    try:
        data = await _proxy("GET", "/library/catalog", params={"limit": 1})
        return {
            "status": "ok",
            "mindex_base": MINDEX_BASE,
            "db_registered_total": data.get("db_registered_total"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/catalog")
async def proxy_catalog(
    limit: int = Query(100, ge=1, le=500),
    path: Optional[str] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"limit": limit}
    if path:
        params["path"] = path
    return await _proxy("GET", "/library/catalog", params=params)


@router.get("/blobs")
async def proxy_list_blobs(
    category: str = Query("acoustic"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"category": category, "limit": limit, "offset": offset}
    if q:
        params["q"] = q
    return await _proxy("GET", "/library/blobs", params=params)


@router.get("/blobs/{blob_id}")
async def proxy_get_blob(blob_id: str) -> Dict[str, Any]:
    return await _proxy("GET", f"/library/blobs/{blob_id}")


@router.post("/blobs/{blob_id}/classify")
async def proxy_classify_blob(
    blob_id: str,
    detectors: Optional[str] = Query(None),
) -> Dict[str, Any]:
    params = {"detectors": detectors} if detectors else None
    return await _proxy("POST", f"/library/blobs/{blob_id}/classify", params=params)


@router.post("/blobs/{blob_id}/analyze")
async def proxy_analyze_blob(
    blob_id: str,
    detectors: Optional[str] = Query(None),
) -> Dict[str, Any]:
    params = {"detectors": detectors} if detectors else None
    return await _proxy("POST", f"/sine/blobs/{blob_id}/analyze", params=params)


@router.get("/sine/human-tags")
async def proxy_human_tags(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    training_eligible_only: bool = Query(True),
) -> Dict[str, Any]:
    return await _proxy(
        "GET",
        "/sine/training/human-tags",
        params={
            "limit": limit,
            "offset": offset,
            "training_eligible_only": training_eligible_only,
        },
    )


@router.post("/blobs/{blob_id}/wave-annotation")
async def proxy_wave_annotation(blob_id: str, request: Request) -> Dict[str, Any]:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid_payload")
    return await _proxy("POST", f"/library/blobs/{blob_id}/wave-annotation", body=body)


@router.post("/blobs/{blob_id}/human-identification")
async def proxy_human_identification(blob_id: str, request: Request) -> Dict[str, Any]:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid_payload")
    return await _proxy("POST", f"/library/blobs/{blob_id}/human-identification", body=body)
