"""
SporeBase API Router.

Device fleet, telemetry, samples, lab results, and calibration.
Uses device registry for SporeBase devices; samples/telemetry/calibration
use in-memory store until MINDEX migration is wired.
Created: February 12, 2026
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sporebase", tags=["sporebase"])

# In-memory stores until MINDEX is wired
_samples: Dict[str, Dict[str, Any]] = {}
_sample_results: Dict[str, Dict[str, Any]] = {}
_calibrations: Dict[str, Dict[str, Any]] = {}
_telemetry_store: Dict[str, List[Dict[str, Any]]] = {}


def _get_sporebase_devices() -> List[Dict[str, Any]]:
    """List devices with role sporebase from device registry."""
    try:
        from mycosoft_mas.core.routers.device_registry_api import (
            _device_registry,
            _device_last_seen,
            _get_device_status,
            _cleanup_expired_devices,
        )
        _cleanup_expired_devices()
        out = []
        for device_id, device in _device_registry.items():
            if (device.get("device_role") or "").lower() != "sporebase":
                continue
            status = _get_device_status(device_id)
            out.append({**device, "status": status})
        return out
    except Exception as e:
        logger.warning("SporeBase device list failed: %s", e)
        return []


# --- Pydantic models ---


class CommandBody(BaseModel):
    """Command to SporeBase device (start/stop collection, advance tape)."""
    command: str = Field(..., description="start_collection, stop_collection, advance_tape, etc.")
    params: Dict[str, Any] = Field(default_factory=dict)


class SampleCreate(BaseModel):
    """Create a sample record."""
    device_id: str
    segment_number: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    tape_position: Optional[float] = None
    status: str = "collected"
    lab_id: Optional[str] = None


class LabResultCreate(BaseModel):
    """Lab result for a sample."""
    analysis_type: str = Field(..., description="microscopy, qpcr, sequencing, culture")
    results: Dict[str, Any] = Field(default_factory=dict)
    analyzed_at: Optional[str] = None


class CalibrationCreate(BaseModel):
    """Calibration record for a device."""
    device_id: str
    calibration_type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    performed_at: Optional[str] = None


# --- Endpoints ---


@router.get("/devices")
async def list_sporebase_devices(
    status: Optional[str] = Query(None),
    include_offline: bool = Query(False),
):
    """List all SporeBase devices from the device registry."""
    devices = _get_sporebase_devices()
    if status:
        devices = [d for d in devices if d.get("status") == status]
    if not include_offline:
        devices = [d for d in devices if d.get("status") != "offline"]
    return {"devices": devices, "count": len(devices), "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/devices/{device_id}/telemetry")
async def get_device_telemetry(
    device_id: str,
    since: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
):
    """Get telemetry history for a SporeBase device. Uses MINDEX when available."""
    # Ensure device is a SporeBase in registry
    devices = _get_sporebase_devices()
    if not any(d.get("device_id") == device_id for d in devices):
        raise HTTPException(status_code=404, detail=f"SporeBase device not found: {device_id}")
    # In-memory fallback
    telemetry = _telemetry_store.get(device_id, [])
    if since:
        telemetry = [t for t in telemetry if (t.get("timestamp") or "") >= since]
    telemetry = telemetry[-limit:]
    return {"device_id": device_id, "telemetry": telemetry, "count": len(telemetry)}


@router.post("/devices/{device_id}/command")
async def send_device_command(device_id: str, body: CommandBody):
    """Send command to a SporeBase device (forwarded to MycoBrain service)."""
    try:
        from mycosoft_mas.core.routers.device_registry_api import (
            _device_registry,
            _get_device_status,
            _cleanup_expired_devices,
        )
        import httpx
        _cleanup_expired_devices()
        if device_id not in _device_registry:
            raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
        device = _device_registry[device_id]
        if (_device_registry[device_id].get("device_role") or "").lower() != "sporebase":
            raise HTTPException(status_code=400, detail="Device is not a SporeBase")
        if _get_device_status(device_id) == "offline":
            raise HTTPException(status_code=503, detail="Device is offline")
        host, port = device["host"], device["port"]
        if host.startswith("http"):
            base_url = host.rstrip("/")
        elif device.get("connection_type") == "cloudflare":
            base_url = f"https://{host}"
        else:
            base_url = f"http://{host}:{port}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{base_url}/devices/{device_id}/command",
                json={"command": {"cmd": body.command, **body.params}},
            )
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=r.text)
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("SporeBase command failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/samples")
async def list_samples(
    device_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
):
    """List SporeBase samples. Uses MINDEX when available."""
    samples = list(_samples.values())
    if device_id:
        samples = [s for s in samples if s.get("device_id") == device_id]
    if status:
        samples = [s for s in samples if s.get("status") == status]
    samples = sorted(samples, key=lambda s: s.get("created_at") or "", reverse=True)
    samples = samples[offset : offset + limit]
    return {"samples": samples, "count": len(samples)}


@router.post("/samples")
async def create_sample(body: SampleCreate):
    """Create a sample record. Persisted to MINDEX when migration is applied."""
    sample_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    _samples[sample_id] = {
        "id": sample_id,
        "device_id": body.device_id,
        "segment_number": body.segment_number,
        "start_time": body.start_time,
        "end_time": body.end_time,
        "tape_position": body.tape_position,
        "status": body.status,
        "lab_id": body.lab_id,
        "created_at": now,
    }
    return {"id": sample_id, "status": "created", "created_at": now}


@router.get("/samples/{sample_id}/results")
async def get_sample_results(sample_id: str):
    """Get lab results for a sample."""
    if sample_id not in _samples:
        raise HTTPException(status_code=404, detail="Sample not found")
    results = _sample_results.get(sample_id, [])
    return {"sample_id": sample_id, "results": results}


@router.post("/samples/{sample_id}/results")
async def add_sample_result(sample_id: str, body: LabResultCreate):
    """Add lab result for a sample."""
    if sample_id not in _samples:
        raise HTTPException(status_code=404, detail="Sample not found")
    result_id = str(uuid.uuid4())
    if sample_id not in _sample_results:
        _sample_results[sample_id] = []
    _sample_results[sample_id].append({
        "id": result_id,
        "analysis_type": body.analysis_type,
        "results": body.results,
        "analyzed_at": body.analyzed_at or datetime.now(timezone.utc).isoformat(),
    })
    return {"id": result_id, "status": "created"}


@router.get("/calibration/{calibration_id}")
async def get_calibration(calibration_id: str):
    """Get a calibration record."""
    if calibration_id not in _calibrations:
        raise HTTPException(status_code=404, detail="Calibration not found")
    return _calibrations[calibration_id]


@router.post("/calibration/{calibration_id}")
async def update_calibration(calibration_id: str, body: CalibrationCreate):
    """Create or update a calibration record."""
    now = datetime.now(timezone.utc).isoformat()
    _calibrations[calibration_id] = {
        "id": calibration_id,
        "device_id": body.device_id,
        "calibration_type": body.calibration_type,
        "data": body.data,
        "performed_at": body.performed_at or now,
        "updated_at": now,
    }
    return {"id": calibration_id, "status": "created", "updated_at": now}


@router.post("/order")
async def sporebase_order(body: Dict[str, Any]):
    """Pre-order integration. Not implemented; returns 501."""
    raise HTTPException(
        status_code=501,
        detail="SporeBase pre-order not yet implemented. Contact sales@mycosoft.com.",
    )
