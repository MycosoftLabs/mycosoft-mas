"""
MYCA Reflection API - February 17, 2026

Exposes reflection history and manual logging for grounded cognition.
Proxies to MINDEX reflection_logs.
"""

import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Body, HTTPException, Query

router = APIRouter(prefix="/api/reflection", tags=["reflection", "myca"])

MINDEX_URL = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
MINDEX_PREFIX = "/api/mindex/grounding"
MINDEX_API_KEY = os.environ.get("MINDEX_API_KEY", "")


def _headers() -> Dict[str, str]:
    h: Dict[str, str] = {}
    if MINDEX_API_KEY:
        h["X-API-Key"] = MINDEX_API_KEY
    return h


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_reflection_history(
    session_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """
    Get recent reflection log entries from MINDEX.
    """
    try:
        params: Dict[str, Any] = {"limit": limit}
        if session_id:
            params["session_id"] = session_id
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{MINDEX_URL}{MINDEX_PREFIX}/reflection-logs/history",
                params=params,
                headers=_headers(),
            )
            if r.status_code == 200:
                return r.json()
            raise HTTPException(status_code=r.status_code, detail=r.text[:300])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log")
async def log_reflection(
    ep_id: Optional[str] = Body(None),
    response: Optional[str] = Body(None),
    session_id: Optional[str] = Body(None),
    prediction: Optional[str] = Body(None),
    actual: Optional[str] = Body(None),
    metadata: Optional[Dict[str, Any]] = Body(None),
) -> Dict[str, Any]:
    """
    Manually log a reflection entry (for testing).
    """
    try:
        body: Dict[str, Any] = {
            "ep_id": ep_id,
            "session_id": session_id,
            "response": response[:10000] if response else None,
            "prediction": prediction,
            "actual": actual,
            "metadata": metadata or {},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{MINDEX_URL}{MINDEX_PREFIX}/reflection-logs",
                json=body,
                headers=_headers(),
            )
            if r.status_code in (200, 201):
                return r.json()
            raise HTTPException(status_code=r.status_code, detail=r.text[:300])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
