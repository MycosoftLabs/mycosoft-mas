"""
MAS Worldstate API

Read-only passive awareness API for canonical WorldState.
Consumed by website search, CREP dashboard, Earth Simulator, and MYCA context.
Command APIs (CREP commands, Earth2 simulation) remain specialist and separate.

Created: March 14, 2026
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/myca/world", tags=["worldstate", "myca"])


def _get_world_model():
    """Get canonical WorldModel from consciousness. Returns None if unavailable."""
    try:
        from mycosoft_mas.consciousness import get_consciousness

        consciousness = get_consciousness()
        return getattr(consciousness, "_world_model", None)
    except Exception:
        return None


def _world_state_to_dict(state: Any) -> Dict[str, Any]:
    """Serialize WorldState to API-safe dict."""
    if state is None:
        return {}
    out: Dict[str, Any] = {
        "timestamp": getattr(state, "timestamp", None),
        "crep": {
            "data": getattr(state, "crep_data", {}) or {},
            "freshness": getattr(getattr(state, "crep_freshness", None), "value", "unavailable"),
            "flights": getattr(state, "total_flights", 0),
            "vessels": getattr(state, "total_vessels", 0),
            "satellites": getattr(state, "total_satellites", 0),
        },
        "predictions": getattr(state, "predictions", {}) or {},
        "ecosystem": getattr(state, "ecosystem_status", {}) or {},
        "mindex": {
            "available": getattr(state, "knowledge_available", False),
            "stats": getattr(state, "knowledge_stats", {}) or {},
        },
        "devices": {
            "telemetry": getattr(state, "device_telemetry", {}) or {},
            "active_count": getattr(state, "active_devices", 0),
            "freshness": getattr(getattr(state, "device_freshness", None), "value", "unavailable"),
        },
        "nlm": getattr(state, "nlm_insights", {}) or {},
        "earthlive": getattr(state, "earthlive_packet", {}) or {},
        "presence": {
            "online_users": getattr(state, "online_users", 0),
            "active_sessions": getattr(state, "active_sessions", 0),
            "staff_online": getattr(state, "staff_online", 0),
            "data": getattr(state, "presence_data", {}) or {},
        },
    }
    if hasattr(state, "timestamp") and state.timestamp:
        if hasattr(state.timestamp, "isoformat"):
            out["timestamp"] = state.timestamp.isoformat()
        else:
            out["timestamp"] = str(state.timestamp)
    return out


@router.get("")
async def get_world() -> Dict[str, Any]:
    """
    Return the full canonical world state.

    Read-only. Uses the same WorldModel and WorldState MYCA uses internally.
    """
    wm = _get_world_model()
    if wm is None:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": "WorldModel not available",
            "degraded": True,
        }
    state = wm.get_current_state()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "world": _world_state_to_dict(state) if state else {},
        "degraded": False,
    }


@router.get("/summary")
async def get_world_summary() -> Dict[str, Any]:
    """
    Return a natural language summary of the current world state.

    Same summary MYCA uses for live context and packet grounding.
    """
    wm = _get_world_model()
    if wm is None:
        return {
            "summary": "World state: WorldModel not available.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "degraded": True,
        }
    summary_fn = getattr(wm, "get_summary", None)
    if summary_fn:
        s = await summary_fn() if asyncio.iscoroutinefunction(summary_fn) else summary_fn()
    else:
        s = "World state: limited data available"
    return {
        "summary": s if isinstance(s, str) else str(s),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "degraded": False,
    }


@router.get("/region")
async def get_world_region(
    lat: Optional[float] = Query(None, description="Center latitude"),
    lon: Optional[float] = Query(None, description="Center longitude"),
    radius_km: Optional[float] = Query(None, description="Radius in km"),
) -> Dict[str, Any]:
    """
    Return world state summary for a geographic region.

    When lat/lon/radius_km are provided, the response includes region_requested
    for future geo-filtering. Current implementation returns the full world
    state; regional filtering of CREP/earthlive will be added in a future update.
    """
    wm = _get_world_model()
    if wm is None:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": "WorldModel not available",
            "degraded": True,
            "region_requested": lat is not None and lon is not None,
        }
    state = wm.get_current_state()
    summary_text = state.to_summary() if state else "No world state available."
    result: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary_text,
        "world": _world_state_to_dict(state) if state else {},
        "degraded": False,
        "region_requested": lat is not None and lon is not None,
    }
    if lat is not None and lon is not None:
        result["region"] = {
            "lat": lat,
            "lon": lon,
            "radius_km": radius_km,
            "note": "Regional filtering of CREP/earthlive entities not yet implemented; full state returned.",
        }
    return result


@router.get("/sources")
async def get_world_sources() -> Dict[str, Any]:
    """
    Return source-level freshness and status for all world feeds.

    Use for diagnostics and staleness inspection.
    """
    wm = _get_world_model()
    if wm is None:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": {},
            "detail": "WorldModel not available",
        }
    state = wm.get_current_state()
    if state is None:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": {},
            "detail": "No world state available.",
        }

    def _freshness_val(f) -> str:
        return getattr(f, "value", "unavailable") if f else "unavailable"

    sources: Dict[str, Any] = {
        "crep": {"freshness": _freshness_val(state.crep_freshness)},
        "predictions": {"freshness": _freshness_val(state.predictions_freshness)},
        "ecosystem": {"freshness": _freshness_val(state.ecosystem_freshness)},
        "mindex": {
            "available": state.knowledge_available,
            "freshness": "live" if state.knowledge_available else "unavailable",
        },
        "devices": {"freshness": _freshness_val(state.device_freshness)},
        "nlm": {"freshness": _freshness_val(state.nlm_freshness)},
        "earthlive": {"freshness": _freshness_val(state.earthlive_freshness)},
        "presence": {"freshness": _freshness_val(state.presence_freshness)},
    }
    if hasattr(wm, "sensor_status"):
        sources["sensor_status"] = wm.sensor_status
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "state_timestamp": state.timestamp.isoformat() if state.timestamp else None,
        "sources": sources,
    }


@router.get("/diff")
async def get_world_diff() -> Dict[str, Any]:
    """
    Return what changed since the previous world state snapshot.

    Historical snapshots require copy-on-archive in WorldModel; when not yet
    implemented, returns current state with a note.
    """
    wm = _get_world_model()
    if wm is None:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": "WorldModel not available",
            "changes": [],
        }
    history = getattr(wm, "_history", [])
    if len(history) < 2:
        curr = wm.get_current_state()
        curr_summary = curr.to_summary() if curr else "No world state available."
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": "Historical snapshots not yet available; diff requires at least 2 archived states.",
            "changes": [],
            "current_summary": curr_summary,
        }
    prev = history[-2]
    curr = wm.get_current_state()
    changes: list = []
    if getattr(curr, "total_flights", 0) != getattr(prev, "total_flights", 0):
        changes.append(
            {
                "field": "total_flights",
                "from": getattr(prev, "total_flights", 0),
                "to": getattr(curr, "total_flights", 0),
            }
        )
    if getattr(curr, "total_vessels", 0) != getattr(prev, "total_vessels", 0):
        changes.append(
            {
                "field": "total_vessels",
                "from": getattr(prev, "total_vessels", 0),
                "to": getattr(curr, "total_vessels", 0),
            }
        )
    if getattr(curr, "online_users", 0) != getattr(prev, "online_users", 0):
        changes.append(
            {
                "field": "online_users",
                "from": getattr(prev, "online_users", 0),
                "to": getattr(curr, "online_users", 0),
            }
        )
    if getattr(curr, "active_devices", 0) != getattr(prev, "active_devices", 0):
        changes.append(
            {
                "field": "active_devices",
                "from": getattr(prev, "active_devices", 0),
                "to": getattr(curr, "active_devices", 0),
            }
        )
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changes": changes,
        "previous_timestamp": (
            prev.timestamp.isoformat() if getattr(prev, "timestamp", None) else None
        ),
        "current_timestamp": curr.timestamp.isoformat() if curr.timestamp else None,
    }
