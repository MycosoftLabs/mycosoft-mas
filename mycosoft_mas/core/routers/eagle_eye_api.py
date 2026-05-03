"""Eagle Eye — MAS proxy to MINDEX eagle.* APIs (Apr 17, 2026).

n8n or cron can GET /api/eagle-eye/mindex-health on a schedule for stale-source alerts.
MYCA tools can call bbox/time proxies without bypassing MINDEX auth patterns.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter()

MINDEX_BASE = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
if not MINDEX_BASE.endswith("/api/mindex"):
    MINDEX_BASE = f"{MINDEX_BASE}/api/mindex"
MINDEX_INTERNAL_TOKEN = os.environ.get("MINDEX_INTERNAL_TOKEN", "").strip()
MINDEX_API_KEY = os.environ.get("MINDEX_API_KEY", "").strip()


def _mindex_headers() -> Dict[str, str]:
    if MINDEX_INTERNAL_TOKEN:
        return {"X-Internal-Token": MINDEX_INTERNAL_TOKEN, "Accept": "application/json"}
    if MINDEX_API_KEY:
        return {"X-API-Key": MINDEX_API_KEY, "Accept": "application/json"}
    return {"Accept": "application/json"}


async def _proxy_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not MINDEX_INTERNAL_TOKEN and not MINDEX_API_KEY:
        raise HTTPException(status_code=503, detail="MINDEX_INTERNAL_TOKEN or MINDEX_API_KEY not configured")
    url = f"{MINDEX_BASE}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, params=params or {}, headers=_mindex_headers())
        if r.status_code >= 400:
            logger.warning("Eagle Eye MINDEX proxy %s -> %s: %s", path, r.status_code, r.text[:300])
            raise HTTPException(status_code=r.status_code, detail=r.text[:500])
        data = r.json()
        return data if isinstance(data, dict) else {"data": data}


@router.get("/mindex-health")
async def mindex_eagle_health():
    """Row counts in eagle.* (for ops / n8n heartbeat)."""
    return await _proxy_get("/eagle/health/stats")


@router.get("/video-sources")
async def proxy_video_sources(
    lat_min: float = Query(...),
    lat_max: float = Query(...),
    lng_min: float = Query(...),
    lng_max: float = Query(...),
    kind: Optional[str] = None,
    provider: Optional[str] = None,
    limit: int = Query(2000, ge=1, le=20000),
):
    """Bbox query — same contract as MINDEX GET /eagle/video-sources."""
    params: Dict[str, Any] = {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lng_min": lng_min,
        "lng_max": lng_max,
        "limit": limit,
    }
    if kind:
        params["kind"] = kind
    if provider:
        params["provider"] = provider
    return await _proxy_get("/eagle/video-sources", params)


@router.get("/video-events")
async def proxy_video_events(
    observed_after: Optional[str] = None,
    observed_before: Optional[str] = None,
    video_source_id: Optional[str] = None,
    limit: int = Query(500, ge=1, le=10000),
):
    """Time-range query — same as MINDEX GET /eagle/video-events."""
    params: Dict[str, Any] = {"limit": limit}
    if observed_after:
        params["observed_after"] = observed_after
    if observed_before:
        params["observed_before"] = observed_before
    if video_source_id:
        params["video_source_id"] = video_source_id
    return await _proxy_get("/eagle/video-events", params)
