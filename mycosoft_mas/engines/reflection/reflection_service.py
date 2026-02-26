"""
ReflectionService - Outcome tracking and learning from responses.

Logs responses, compares predicted vs actual outcomes, creates learning tasks.
Created: February 17, 2026
"""

import logging
import os
from typing import Any, Dict, Optional

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
        logger.warning("MINDEX reflection request failed: %s", e)
        return None


class ReflectionService:
    """Tracks response outcomes and creates learning tasks from gaps."""

    async def log_response(
        self,
        ep_id: str,
        response: str,
        session_id: str,
        prediction: Optional[str] = None,
        actual: Optional[str] = None,
    ) -> Optional[str]:
        """
        Log a response to MINDEX reflection_logs.
        Returns the log entry ID or None on failure.
        """
        body = {
            "ep_id": ep_id,
            "session_id": session_id,
            "response": response[:10000] if response else None,
            "prediction": prediction,
            "actual": actual,
        }
        out = await _mindex_request("POST", "/grounding/reflection-logs", json=body)
        if out and "id" in out:
            return str(out["id"])
        return None

    async def compare_outcome(self, prediction: str, actual: str) -> Dict[str, Any]:
        """
        Compare predicted outcome vs actual. V0: always returns match=True.
        Future: semantic similarity or structured comparison.
        """
        return {
            "match": True,
            "prediction": prediction,
            "actual": actual,
            "confidence": 1.0,
        }

    async def create_learning_task(self, gap: str) -> Optional[str]:
        """
        Create a knowledge gap record for later learning.
        Stores as reflection_log with metadata type=knowledge_gap.
        """
        body = {
            "ep_id": None,
            "session_id": None,
            "response": None,
            "prediction": None,
            "actual": None,
            "metadata": {"type": "knowledge_gap", "gap": gap[:2000]},
        }
        out = await _mindex_request("POST", "/grounding/reflection-logs", json=body)
        if out and "id" in out:
            return str(out["id"])
        return None
