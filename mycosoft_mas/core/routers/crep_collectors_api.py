"""
CREP collector management API.

Readiness and control endpoints for Worldview/CREP ingestion collectors.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from mycosoft_mas.collectors import get_orchestrator, start_default_collectors

router = APIRouter(prefix="/api/crep/collectors", tags=["crep", "collectors"])


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/health")
async def health() -> Dict[str, Any]:
    """Health check for collector management routes."""
    orchestrator = get_orchestrator()
    return {
        "status": "healthy",
        "running": orchestrator._running,
        "collector_count": len(orchestrator.collectors),
        "timestamp": _timestamp(),
    }


@router.get("/status")
async def status() -> Dict[str, Any]:
    """Return current collector status and audit context."""
    orchestrator = get_orchestrator()
    return {
        "timestamp": _timestamp(),
        "status": orchestrator.get_status(),
        "audit": orchestrator.get_audit_log(limit=25),
    }


@router.post("/start")
async def start() -> Dict[str, Any]:
    """Start default CREP collectors if they are not already running."""
    orchestrator = get_orchestrator()
    if orchestrator._running:
        return {
            "timestamp": _timestamp(),
            "started": False,
            "detail": "Collectors already running",
            "status": orchestrator.get_status(),
        }

    await start_default_collectors()
    return {
        "timestamp": _timestamp(),
        "started": True,
        "status": get_orchestrator().get_status(),
    }


@router.post("/stop")
async def stop() -> Dict[str, Any]:
    """Stop running CREP collectors."""
    orchestrator = get_orchestrator()
    if not orchestrator._running:
        return {
            "timestamp": _timestamp(),
            "stopped": False,
            "detail": "Collectors already stopped",
            "status": orchestrator.get_status(),
        }

    try:
        await orchestrator.stop()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to stop collectors: {exc}") from exc

    return {
        "timestamp": _timestamp(),
        "stopped": True,
        "status": orchestrator.get_status(),
    }
