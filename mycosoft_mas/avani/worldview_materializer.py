"""Materialize MAS WorldState into MINDEX Worldview snapshots under AVANI audit."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from mycosoft_mas.avani.worldview import build_worldstate_snapshot


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mindex_snapshot_url() -> str:
    base = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
    return f"{base}/api/mindex/internal/worldview/snapshots"


async def materialize_worldview_snapshot(
    *,
    region: Optional[Dict[str, Any]] = None,
    source: str = "avani_materializer",
) -> Dict[str, Any]:
    """Collect MAS WorldState, audit it, then publish a read-optimized MINDEX snapshot."""
    from mycosoft_mas.core.routers import avani_router
    from mycosoft_mas.core.routers.worldstate_api import (
        get_world,
        get_world_region,
        get_world_sources,
        get_world_summary,
    )

    await avani_router.ensure_runtime_restored()
    world_payload = await get_world()
    summary_payload = await get_world_summary()
    sources_payload = await get_world_sources()
    region_payload: Optional[Dict[str, Any]] = None
    if region:
        region_payload = await get_world_region(
            lat=region.get("lat"),
            lon=region.get("lon"),
            radius_km=region.get("radius_km"),
        )

    snapshot = build_worldstate_snapshot(world_payload)
    degraded = bool(
        snapshot.degraded
        or world_payload.get("degraded")
        or summary_payload.get("degraded")
        or sources_payload.get("degraded")
    )
    decision = {
        "approved": True,
        "verdict": "allow_with_audit" if degraded else "allow",
        "worldstate_snapshot_id": snapshot.worldstate_snapshot_id,
        "degraded": degraded,
        "confidence": snapshot.confidence,
        "reason": "MAS WorldState materialized for MINDEX Worldview reads.",
    }
    audit_entry = await avani_router.get_ledger().append(
        event_kind="worldview_snapshot_materialization",
        source=source,
        action_type="worldview_materialize",
        decision=decision,
        season=avani_router.get_season_engine().current_season.value,
        metadata={
            "snapshot": snapshot.to_dict(),
            "region": region,
            "summary": summary_payload,
            "sources": sources_payload,
        },
    )

    payload = {
        "snapshot_id": snapshot.worldstate_snapshot_id,
        "captured_at": snapshot.timestamp or _utc_now(),
        "region": region or {},
        "world_payload": world_payload,
        "summary_payload": summary_payload,
        "sources_payload": sources_payload,
        "source_counts": snapshot.source_counts,
        "source_freshness": snapshot.source_freshness,
        "degraded": degraded,
        "confidence": snapshot.confidence,
        "provenance": {
            **snapshot.provenance,
            "source": "mas_worldstate",
            "materializer": source,
            "region_payload": region_payload,
        },
        "avani_verdict": decision["verdict"],
        "audit_trail_id": audit_entry.event_id,
        "entry_hash": audit_entry.entry_hash,
    }

    headers: Dict[str, str] = {}
    internal_token = os.getenv("MINDEX_INTERNAL_TOKEN", "").strip()
    if internal_token:
        headers["X-Internal-Token"] = internal_token

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(_mindex_snapshot_url(), json=payload, headers=headers or None)
            response.raise_for_status()
            mindex_response = response.json()
        return {
            "status": "success",
            "snapshot_id": snapshot.worldstate_snapshot_id,
            "audit_trail_id": audit_entry.event_id,
            "entry_hash": audit_entry.entry_hash,
            "storage_mode": audit_entry.storage,
            "mindex_persisted": True,
            "mindex": mindex_response,
            "snapshot": payload,
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "snapshot_id": snapshot.worldstate_snapshot_id,
            "audit_trail_id": audit_entry.event_id,
            "entry_hash": audit_entry.entry_hash,
            "storage_mode": audit_entry.storage,
            "mindex_persisted": False,
            "error": str(exc),
            "snapshot": payload,
        }
