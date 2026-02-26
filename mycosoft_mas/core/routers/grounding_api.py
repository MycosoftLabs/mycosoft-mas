"""
MYCA Grounding API

Exposes grounding gate status and ThoughtObjects for the grounded cognition stack.
Created: February 17, 2026
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/myca/grounding", tags=["grounding", "myca"])

GROUNDED_COGNITION_ENABLED = os.getenv("MYCA_GROUNDED_COGNITION", "0") == "1"


@router.get("/status")
async def grounding_status() -> Dict[str, Any]:
    """
    Return current grounding gate status.

    Returns:
        - enabled: whether grounded cognition is on
        - last_ep_id: last experience packet ID (if available)
        - thought_count: number of ThoughtObjects in workspace
        - self_state_sources: presence, services, agents
    """
    status: Dict[str, Any] = {
        "enabled": GROUNDED_COGNITION_ENABLED,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thought_count": 0,
        "last_ep_id": None,
    }
    try:
        from mycosoft_mas.consciousness import get_consciousness

        consciousness = get_consciousness()
        wm = getattr(consciousness, "_working_memory", None)
        if wm and hasattr(wm, "get_thoughts"):
            thoughts = wm.get_thoughts(top_k=20)
            status["thought_count"] = len(thoughts)
        if wm and hasattr(wm, "_last_ep_id"):
            status["last_ep_id"] = getattr(wm, "_last_ep_id", None)
    except Exception:
        pass
    return status


@router.get("/ep/{ep_id}")
async def get_ep(ep_id: str) -> Dict[str, Any]:
    """
    Inspect an Experience Packet by ID.

    Note: EP storage is not yet implemented. This endpoint returns
    a placeholder indicating the feature is planned.
    """
    return {
        "ep_id": ep_id,
        "status": "ep_storage_not_implemented",
        "message": "Experience Packet persistence will be added in Phase 2.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _thought_to_dict(t: Any) -> Dict[str, Any]:
    """Serialize ThoughtObject to dict."""
    if not hasattr(t, "__dict__"):
        return {"raw": str(t)}
    d: Dict[str, Any] = {}
    for k, v in t.__dict__.items():
        if k.startswith("_"):
            continue
        if hasattr(v, "value"):
            d[k] = v.value
        elif isinstance(v, list):
            d[k] = v
        elif isinstance(v, (str, int, float, bool)) or v is None:
            d[k] = v
        else:
            d[k] = str(v)
    return d


@router.get("/thoughts")
async def get_thoughts(top_k: int = 10) -> Dict[str, Any]:
    """
    Return current ThoughtObjects from the workspace.

    These are structured thoughts with evidence links used by grounded cognition.
    """
    thoughts: List[Dict[str, Any]] = []
    try:
        from mycosoft_mas.consciousness import get_consciousness

        consciousness = get_consciousness()
        wm = getattr(consciousness, "_working_memory", None)
        if wm and hasattr(wm, "get_thoughts"):
            raw = wm.get_thoughts(top_k=top_k)
            thoughts = [_thought_to_dict(t) for t in raw]
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to get thoughts")

    return {
        "thoughts": thoughts,
        "count": len(thoughts),
        "enabled": GROUNDED_COGNITION_ENABLED,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
