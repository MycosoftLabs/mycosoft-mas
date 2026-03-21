"""
Presence API Router

Exposes live presence data (online users, sessions, staff) for MYCA and external consumers.
Proxies to the Website presence API.

Created: February 24, 2026
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter

try:
    from sse_starlette.sse import EventSourceResponse

    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/presence", tags=["presence"])

PRESENCE_URL = os.environ.get("PRESENCE_API_URL", "http://192.168.0.187:3000/api/presence")
SERVICE_KEY = os.environ.get("PRESENCE_SERVICE_KEY", "")


def _headers() -> Dict[str, str]:
    h: Dict[str, str] = {"Accept": "application/json"}
    if SERVICE_KEY:
        h["X-Service-Key"] = SERVICE_KEY
    return h


@router.get("/online")
async def get_online() -> Dict[str, Any]:
    """List currently online users."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{PRESENCE_URL.rstrip('/')}/online", headers=_headers())
            if r.status_code == 200:
                return r.json()
            return {"online": [], "count": 0}
    except Exception as e:
        logger.warning(f"Presence online fetch failed: {e}")
        return {"online": [], "count": 0}


@router.get("/sessions")
async def get_sessions() -> Dict[str, Any]:
    """List active sessions."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{PRESENCE_URL.rstrip('/')}/sessions", headers=_headers())
            if r.status_code == 200:
                return r.json()
            return {"sessions": []}
    except Exception as e:
        logger.warning(f"Presence sessions fetch failed: {e}")
        return {"sessions": []}


@router.get("/staff")
async def get_staff() -> Dict[str, Any]:
    """List staff/admin/superuser presence."""
    try:
        data = await get_online()
        online = data.get("online", [])
        staff = [
            u
            for u in online
            if u.get("is_superuser")
            or (u.get("role") or "").lower() in ("staff", "admin", "owner", "superuser")
        ]
        return {"staff": staff, "count": len(staff)}
    except Exception as e:
        logger.warning(f"Presence staff fetch failed: {e}")
        return {"staff": [], "count": 0}


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Presence statistics."""
    try:
        online_data = await get_online()
        sessions_data = await get_sessions()
        online = online_data.get("online", [])
        sessions = sessions_data.get("sessions", [])
        staff_count = sum(
            1
            for u in online
            if u.get("is_superuser")
            or (u.get("role") or "").lower() in ("staff", "admin", "owner", "superuser")
        )
        return {
            "online_users": len(online),
            "active_sessions": len(sessions),
            "staff_online": staff_count,
        }
    except Exception as e:
        logger.warning(f"Presence stats fetch failed: {e}")
        return {"online_users": 0, "active_sessions": 0, "staff_online": 0}


@router.get("/stream")
async def presence_stream():
    """SSE stream of presence changes (updates every 5 seconds)."""
    if not SSE_AVAILABLE:
        from fastapi import HTTPException

        raise HTTPException(500, "SSE not available: sse-starlette not installed")

    async def event_generator():
        while True:
            try:
                stats = await get_stats()
                online_data = await get_online()
                payload = {**stats, "online": online_data.get("online", [])}
                yield {"data": json.dumps(payload)}
            except Exception as e:
                logger.warning(f"Presence stream error: {e}")
                yield {"data": json.dumps({"error": str(e)})}
            await asyncio.sleep(5)

    return EventSourceResponse(event_generator())
