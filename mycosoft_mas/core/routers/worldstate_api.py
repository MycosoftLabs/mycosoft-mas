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


def _freshness_val(f: Any) -> str:
    """Extract freshness string from a DataFreshness enum (or return 'unavailable')."""
    return getattr(f, "value", "unavailable") if f else "unavailable"


def _get_world_model():
    """Get canonical WorldModel from consciousness. Returns None if unavailable."""
    try:
        from mycosoft_mas.consciousness import get_consciousness

        consciousness = get_consciousness()
        return getattr(consciousness, "_world_model", None)
    except Exception:
        return None


def _world_state_to_dict(state: Any) -> Dict[str, Any]:
    """Serialize WorldState to API-safe dict.

    Wraps predictions, ecosystem, nlm, earthlive, and presence with
    {data: ..., freshness: ...} for consistent per-sensor freshness.
    """
    if state is None:
        return {}
    out: Dict[str, Any] = {
        "timestamp": getattr(state, "timestamp", None),
        "crep": {
            "data": getattr(state, "crep_data", {}) or {},
            "freshness": _freshness_val(getattr(state, "crep_freshness", None)),
            "flights": getattr(state, "total_flights", 0),
            "vessels": getattr(state, "total_vessels", 0),
            "satellites": getattr(state, "total_satellites", 0),
        },
        "predictions": {
            "data": getattr(state, "predictions", {}) or {},
            "freshness": _freshness_val(getattr(state, "predictions_freshness", None)),
        },
        "ecosystem": {
            "data": getattr(state, "ecosystem_status", {}) or {},
            "freshness": _freshness_val(getattr(state, "ecosystem_freshness", None)),
        },
        "mindex": {
            "available": getattr(state, "knowledge_available", False),
            "stats": getattr(state, "knowledge_stats", {}) or {},
        },
        "devices": {
            "telemetry": getattr(state, "device_telemetry", {}) or {},
            "active_count": getattr(state, "active_devices", 0),
            "freshness": _freshness_val(getattr(state, "device_freshness", None)),
        },
        "nlm": {
            "data": getattr(state, "nlm_insights", {}) or {},
            "freshness": _freshness_val(getattr(state, "nlm_freshness", None)),
        },
        "earthlive": {
            "data": getattr(state, "earthlive_packet", {}) or {},
            "freshness": _freshness_val(getattr(state, "earthlive_freshness", None)),
        },
        "presence": {
            "online_users": getattr(state, "online_users", 0),
            "active_sessions": getattr(state, "active_sessions", 0),
            "staff_online": getattr(state, "staff_online", 0),
            "data": getattr(state, "presence_data", {}) or {},
            "freshness": _freshness_val(getattr(state, "presence_freshness", None)),
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
    world = _world_state_to_dict(state) if state else {}

    # Inject economy summary into world state
    try:
        economy_data = await get_world_economy()
        world["economy"] = economy_data
    except Exception:
        world["economy"] = {"ows_status": "unavailable"}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "world": world,
        "degraded": getattr(wm, "is_degraded", False),
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
        "degraded": getattr(wm, "is_degraded", False),
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
        "degraded": getattr(wm, "is_degraded", False),
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


@router.get("/economy")
async def get_world_economy() -> Dict[str, Any]:
    """
    Economy-focused worldview slice.

    Returns OWS wallet system status, treasury balances, transaction metrics,
    and active wallet counts. Used by agents and dashboards for economic context.
    """
    from mycosoft_mas.agents.crypto.ows_wallet_agent import TREASURY_AGENT_ID

    economy: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ows_status": "unavailable",
        "treasury_balance": {},
        "active_wallets": 0,
        "total_transactions_24h": 0,
        "revenue_24h": 0.0,
        "top_paying_agents": [],
        "supported_chains": ["solana", "ethereum", "bitcoin", "tron", "ton", "cosmos"],
    }

    try:
        from mycosoft_mas.integrations.mindex_client import MINDEXClient

        mindex = MINDEXClient()
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            # Treasury balances
            bal_row = await conn.fetchrow(
                "SELECT * FROM ows_balances WHERE agent_id = $1", TREASURY_AGENT_ID
            )
            if bal_row:
                economy["treasury_balance"] = {
                    "SOL": float(bal_row.get("sol_balance", 0)),
                    "USDC": float(bal_row.get("usdc_balance", 0)),
                    "ETH": float(bal_row.get("eth_balance", 0)),
                    "BTC": float(bal_row.get("btc_balance", 0)),
                }

            # Active wallets
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM ows_wallets WHERE status = 'active'"
            )
            economy["active_wallets"] = count or 0

            # 24h metrics
            from datetime import timedelta

            day_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
            revenue = await conn.fetchval(
                """SELECT COALESCE(SUM(amount), 0) FROM ows_transactions
                   WHERE to_agent_id = $1 AND created_at >= $2 AND status = 'confirmed'""",
                TREASURY_AGENT_ID,
                day_ago,
            )
            tx_count = await conn.fetchval(
                """SELECT COUNT(*) FROM ows_transactions
                   WHERE created_at >= $1 AND status = 'confirmed'""",
                day_ago,
            )
            economy["revenue_24h"] = float(revenue) if revenue else 0.0
            economy["total_transactions_24h"] = tx_count or 0

            # Top paying agents
            top = await conn.fetch(
                """SELECT from_agent_id, SUM(amount) as total
                   FROM ows_transactions
                   WHERE to_agent_id = $1 AND status = 'confirmed'
                   GROUP BY from_agent_id ORDER BY total DESC LIMIT 5""",
                TREASURY_AGENT_ID,
            )
            economy["top_paying_agents"] = [
                {"agent_id": r["from_agent_id"], "total_paid": float(r["total"])}
                for r in top
            ]
            economy["ows_status"] = "active"
    except Exception as e:
        economy["ows_status"] = "degraded"
        economy["error"] = str(e)

    return economy


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
