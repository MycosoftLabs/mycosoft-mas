"""
MYCA Grounding API

Exposes grounding gate status and ThoughtObjects for the grounded cognition stack.
Created: February 17, 2026
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException

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

    Fetches from MINDEX experience_packets table via MAS proxy to MINDEX.
    """
    try:
        import os
        import httpx
        url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
        path = f"/api/mindex/grounding/experience-packets/{ep_id}"
        headers = {}
        if os.getenv("MINDEX_API_KEY"):
            headers["X-API-Key"] = os.getenv("MINDEX_API_KEY")
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{url}{path}", headers=headers or None)
            if r.status_code == 200:
                return r.json()
            if r.status_code != 200:
                return {
                    "ep_id": ep_id,
                    "status": "ep_storage_not_implemented",
                    "detail": f"Experience packet store unavailable (upstream status {r.status_code}).",
                }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "ep_id": ep_id,
            "status": "ep_storage_not_implemented",
            "detail": str(e)[:200],
        }


@router.post("/ep")
async def create_ep(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Store an Experience Packet (for testing). Requires id, ground_truth.
    """
    try:
        import os
        import httpx
        ep_id = body.get("id") or f"ep_{__import__('uuid').uuid4().hex[:16]}"
        url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
        path = "/api/mindex/grounding/experience-packets"
        payload = {
            "id": ep_id,
            "session_id": body.get("session_id"),
            "user_id": body.get("user_id"),
            "ground_truth": body.get("ground_truth", {}),
            "self_state": body.get("self_state"),
            "world_state": body.get("world_state"),
            "observation": body.get("observation", {}),
            "uncertainty": body.get("uncertainty", {}),
            "provenance": body.get("provenance", {}),
        }
        headers = {}
        if os.getenv("MINDEX_API_KEY"):
            headers["X-API-Key"] = os.getenv("MINDEX_API_KEY")
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(f"{url}{path}", json=payload, headers=headers or None)
            if r.status_code in (200, 201):
                return r.json()
            raise HTTPException(status_code=r.status_code, detail=r.text[:200])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/ep/recent")
async def get_recent_packets(
    session_id: Optional[str] = None,
    limit: int = 20,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List recent experience packets, optionally filtered by session and domain.
    Proxies to MINDEX; domain filters by world_state.sources containing the given string.
    """
    try:
        import httpx
        url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
        params = {"limit": min(limit, 100)}
        if session_id:
            params["session_id"] = session_id
        path = "/api/mindex/grounding/experience-packets"
        headers = {}
        if os.getenv("MINDEX_API_KEY"):
            headers["X-API-Key"] = os.getenv("MINDEX_API_KEY")
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{url}{path}", params=params, headers=headers or None)
            if r.status_code != 200:
                return {"packets": [], "count": 0, "detail": f"upstream status {r.status_code}"}
            data = r.json()
        packets = data if isinstance(data, list) else data.get("packets", data)
        if domain and packets:
            filtered = []
            for p in packets:
                ws = p.get("world_state") or {}
                sources = ws.get("sources") if isinstance(ws, dict) else []
                if isinstance(sources, list) and any(
                    domain.lower() in str(s).lower() for s in sources
                ):
                    filtered.append(p)
            packets = filtered
        return {"packets": packets, "count": len(packets)}
    except Exception as e:
        return {"packets": [], "count": 0, "detail": str(e)[:200]}


@router.get("/staleness")
async def get_staleness() -> Dict[str, Any]:
    """
    Return world model source freshness for debugging and packet inspection.
    Uses canonical WorldModel if available.
    """
    try:
        from mycosoft_mas.consciousness import get_consciousness
        consciousness = get_consciousness()
        wm = getattr(consciousness, "_world_model", None)
        if wm is None:
            return {"sources": {}, "detail": "WorldModel not available"}
        summary = getattr(wm, "get_summary", None)
        if summary:
            s = await summary() if asyncio.iscoroutinefunction(summary) else summary()
            return {"sources": s.get("sources", s) if isinstance(s, dict) else s}
        # Fallback: return cache if WorldModel has it
        cache = getattr(wm, "_cache", None)
        if cache:
            return {"sources": dict(cache) if isinstance(cache, dict) else {}}
        return {"sources": {}, "detail": "no freshness data"}
    except Exception as e:
        return {"sources": {}, "detail": str(e)[:200]}


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
