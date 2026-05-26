"""MYCA cross-agent coordination API (capabilities, MCP-over-HTTP hooks)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/myca/coordination", tags=["myca-coordination"])


@router.get("/health")
async def coordination_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "myca-coordination",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/capabilities")
async def coordination_capabilities() -> Dict[str, Any]:
    try:
        from mycosoft_mas.core.agent_registry import get_agent_registry

        registry = get_agent_registry()
        payload = registry.to_dict()
        return {"status": "ok", **payload}
    except Exception as exc:
        return {"status": "unavailable", "message": str(exc), "agents": []}
