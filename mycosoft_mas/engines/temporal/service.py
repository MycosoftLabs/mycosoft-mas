"""
TemporalService - Event/episode handling for Grounded Cognition.

Stores and queries temporal episodes via MINDEX API.
Created: February 17, 2026
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MINDEX_URL = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
MINDEX_API_PREFIX = "/api/mindex"
MINDEX_API_KEY = os.environ.get("MINDEX_API_KEY", "")


async def _mindex_request(
    method: str,
    path: str,
    json: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """Call MINDEX API with optional API key."""
    try:
        import httpx

        url = f"{MINDEX_URL}{MINDEX_API_PREFIX}{path}"
        headers = {}
        if MINDEX_API_KEY:
            headers["X-API-Key"] = MINDEX_API_KEY
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.request(method, url, json=json, params=params, headers=headers)
            r.raise_for_status()
            return r.json() if r.content else None
    except Exception as e:
        logger.warning("MINDEX temporal request failed: %s", e)
        return None


class TemporalService:
    """Temporal indexing and episode boundaries for grounded cognition."""

    def should_start_episode(
        self,
        session_id: Optional[str],
        last_ep_ts: Optional[datetime],
        current_ts: datetime,
        idle_threshold_seconds: int = 300,
    ) -> bool:
        """V0: Rule-based event boundary. True if we should start a new episode."""
        if session_id is None:
            return True
        if last_ep_ts is None:
            return True
        return (current_ts - last_ep_ts).total_seconds() > idle_threshold_seconds

    def new_episode_id(self) -> str:
        """Generate a new episode ID."""
        return str(uuid.uuid4())

    async def store_episode(
        self,
        session_id: str,
        start_ts: datetime,
        end_ts: Optional[datetime] = None,
        ep_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Store an episode in MINDEX. Returns the episode ID or None on failure.
        """
        body = {
            "session_id": session_id,
            "start_ts": start_ts.isoformat(),
            "end_ts": end_ts.isoformat() if end_ts else None,
            "ep_ids": ep_ids or [],
            "metadata": metadata,
        }
        out = await _mindex_request("POST", "/grounding/episodes", json=body)
        if out and "id" in out:
            return str(out["id"])
        return None

    async def get_recent_episodes(
        self,
        session_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get recent episodes for a session from MINDEX."""
        out = await _mindex_request(
            "GET",
            "/grounding/episodes/recent",
            params={"session_id": session_id, "limit": limit},
        )
        if isinstance(out, list):
            return out
        return []

    async def close_current_episode(
        self,
        session_id: str,
        end_ts: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """Close the current open episode for the session. Returns episode info or None."""
        params = {"session_id": session_id}
        if end_ts:
            params["end_ts"] = end_ts.isoformat()
        out = await _mindex_request("PATCH", "/grounding/episodes/close", params=params)
        if isinstance(out, dict):
            return out
        return None
