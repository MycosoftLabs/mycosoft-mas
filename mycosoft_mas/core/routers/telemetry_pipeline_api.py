"""
Telemetry Pipeline API - MycoBrain → MAS → MINDEX

Exposes endpoints to trigger and manage the biospheric telemetry pipeline.
Part of the MYCA Opposable Thumb Architecture.
"""

from __future__ import annotations

from fastapi import APIRouter

from mycosoft_mas.services.telemetry_pipeline import (
    forward_mycobrain_to_mindex,
    get_pipeline_status,
    start_telemetry_pipeline,
    stop_telemetry_pipeline,
)

router = APIRouter(prefix="/api/telemetry", tags=["telemetry-pipeline"])


@router.get("/status")
async def telemetry_status():
    """Return telemetry pipeline status (running, last result, config)."""
    return get_pipeline_status()


@router.post("/forward")
async def trigger_forward():
    """
    Manually trigger a single telemetry forward cycle.
    Polls MycoBrain, forwards to MINDEX.
    """
    result = await forward_mycobrain_to_mindex()
    return {"status": "ok", **result}


@router.post("/pipeline/start")
async def pipeline_start():
    """Start the background telemetry pipeline (polls every 60s)."""
    start_telemetry_pipeline()
    return {"status": "started", "message": "Telemetry pipeline started"}


@router.post("/pipeline/stop")
async def pipeline_stop():
    """Stop the background telemetry pipeline."""
    stop_telemetry_pipeline()
    return {"status": "stopped", "message": "Telemetry pipeline stopped"}
