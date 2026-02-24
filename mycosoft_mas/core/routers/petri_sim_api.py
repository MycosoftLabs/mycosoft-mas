"""
Petri Dish Simulation API.

Provides endpoints for chemical field initialization, stepping, metrics,
calibration, session lifecycle, and batch runs.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Dict, List, Optional, Any

import httpx
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/simulation/petri", tags=["simulation"])


class ChemicalInitRequest(BaseModel):
    fields: Dict[str, List[List[float]]]


class ChemicalStepRequest(BaseModel):
    fields: Dict[str, List[List[float]]]
    diffusion_rates: Dict[str, float]
    dt: float = Field(gt=0)
    decay_rates: Optional[Dict[str, float]] = None
    reaction_params: Dict[str, Dict[str, float]]


class CalibrationRequest(BaseModel):
    species_name: str
    initial_params: Dict[str, float]
    bounds: Dict[str, List[float]]
    samples: List[List[List[int]]]


class SessionCreateRequest(BaseModel):
    width: int = 64
    height: int = 64
    agar_type: str = "maltExtract"


class BatchRunRequest(BaseModel):
    iterations: int = Field(ge=1, le=10000)
    dt: float = Field(gt=0)
    initial_fields: Optional[Dict[str, List[List[float]]]] = None


class ScaleBatchRequest(BaseModel):
    """High-volume batch: up to 1M iterations, chunked execution."""
    iterations: int = Field(ge=1, le=1_000_000)
    dt: float = Field(gt=0)
    initial_fields: Optional[Dict[str, List[List[float]]]] = None
    summary_only: bool = True


class AgentControlRequest(BaseModel):
    """MYCA/agent-driven Petri control with guardrails."""
    action: str  # adjust_env | contamination_response | multi_run | monitor
    source: str = "agent"
    params: Dict[str, Any] = Field(default_factory=dict)


# In-memory session store (per-process; replace with Redis/DB for multi-instance)
_sessions: Dict[str, Dict[str, Any]] = {}


async def _notify_nlm_outcome(outcome_type: str, summary: Dict[str, Any], metrics: Optional[Dict[str, Any]] = None) -> None:
    """Fire-and-forget NLM notification for learning workflows."""
    try:
        from mycosoft_mas.simulation.petri_persistence import notify_nlm_petri_outcome
        await notify_nlm_petri_outcome(
            session_id=summary.get("session_id", "batch"),
            outcome_type=outcome_type,
            summary=summary,
            metrics=metrics,
        )
    except Exception:
        pass
_latest_fields: Optional[Dict[str, List[List[float]]]] = None


@router.post("/chemical/init")
async def initialize_chemical_fields(payload: ChemicalInitRequest) -> Dict[str, Any]:
    global _latest_fields
    if not payload.fields:
        raise HTTPException(status_code=400, detail="fields must not be empty")
    _latest_fields = payload.fields
    first_field = next(iter(payload.fields.values()))
    height = len(first_field)
    width = len(first_field[0]) if height > 0 else 0
    return {"status": "initialized", "width": width, "height": height}


@router.post("/chemical/step")
async def step_chemical_fields(payload: ChemicalStepRequest) -> Dict[str, Any]:
    global _latest_fields
    petridishsim_url = os.environ.get("PETRIDISHSIM_URL", "")
    if not petridishsim_url:
        raise HTTPException(status_code=500, detail="PETRIDISHSIM_URL is not configured")

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(f"{petridishsim_url}/chemical/step", json=payload.dict())
        response.raise_for_status()
        data = response.json()

    _latest_fields = data.get("fields")
    return data


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    if not _latest_fields:
        return {"status": "unavailable", "metrics": {}}

    metrics: Dict[str, float] = {}
    for name, grid in _latest_fields.items():
        array = np.array(grid, dtype=np.float32)
        metrics[f"{name}_mean"] = float(np.mean(array))
        metrics[f"{name}_max"] = float(np.max(array))
    return {"status": "ok", "metrics": metrics}


@router.post("/calibrate")
async def calibrate(payload: CalibrationRequest) -> Dict[str, Any]:
    if not payload.samples:
        raise HTTPException(status_code=400, detail="samples must not be empty")
    # Run calibration optimizer if petridishsim is available
    petridishsim_url = os.environ.get("PETRIDISHSIM_URL", "")
    if petridishsim_url:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Forward to petridishsim calibration if it has such an endpoint
                res = await client.post(
                    f"{petridishsim_url.rstrip('/')}/calibrate",
                    json={
                        "species_name": payload.species_name,
                        "initial_params": payload.initial_params,
                        "bounds": payload.bounds,
                        "samples": payload.samples,
                    },
                )
                if res.status_code == 200:
                    cal_result = res.json()
                    asyncio.create_task(_notify_nlm_outcome(
                        "calibration_complete",
                        {"species_name": payload.species_name, "calibrated_params": cal_result.get("calibrated_params", {})},
                        cal_result,
                    ))
                    return cal_result
        except Exception:
            pass
    return {
        "status": "received",
        "species_name": payload.species_name,
        "initial_params": payload.initial_params,
        "bounds": payload.bounds,
        "sample_count": len(payload.samples),
        "calibrated_params": payload.initial_params,
    }


# --- Session lifecycle ---


@router.post("/session/create")
async def session_create(payload: SessionCreateRequest) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "id": session_id,
        "width": payload.width,
        "height": payload.height,
        "agar_type": payload.agar_type,
        "virtual_hours": 0,
        "created_at": time.time(),
        "fields": None,
    }
    return {"session_id": session_id, "status": "created"}


@router.get("/session/{session_id}")
async def session_get(session_id: str) -> Dict[str, Any]:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sessions[session_id]


@router.post("/session/{session_id}/reset")
async def session_reset(session_id: str) -> Dict[str, Any]:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    s = _sessions[session_id]
    s["virtual_hours"] = 0
    s["fields"] = None
    return {"status": "reset"}


# --- Stream / status ---


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    petridishsim_url = os.environ.get("PETRIDISHSIM_URL", "")
    petri_ok = False
    if petridishsim_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{petridishsim_url.rstrip('/')}/health")
                petri_ok = r.status_code == 200
        except Exception:
            pass
    return {
        "mas": "ok",
        "petridishsim_configured": bool(petridishsim_url),
        "petridishsim_reachable": petri_ok,
        "sessions_count": len(_sessions),
        "latest_fields_available": _latest_fields is not None,
    }


# --- Batch runs ---


@router.post("/batch")
async def batch_run(payload: BatchRunRequest) -> Dict[str, Any]:
    global _latest_fields
    petridishsim_url = os.environ.get("PETRIDISHSIM_URL", "")
    if not petridishsim_url:
        raise HTTPException(status_code=500, detail="PETRIDISHSIM_URL is not configured")

    results: List[Dict[str, Any]] = []
    fields = payload.initial_fields or _latest_fields
    if not fields:
        raise HTTPException(status_code=400, detail="No initial fields; call /chemical/init first")

    first = next(iter(fields.values()))
    h, w = len(first), len(first[0]) if first else 0
    diffusion_rates = {k: 0.1 for k in fields}
    reaction_params = {k: {} for k in fields}

    for i in range(payload.iterations):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{petridishsim_url.rstrip('/')}/chemical/step",
                    json={
                        "fields": fields,
                        "diffusion_rates": diffusion_rates,
                        "dt": payload.dt,
                        "reaction_params": reaction_params,
                    },
                )
                r.raise_for_status()
                data = r.json()
                fields = data.get("fields", fields)
                if (i + 1) % max(1, payload.iterations // 10) == 0 or i == payload.iterations - 1:
                    metrics = {}
                    for name, grid in (fields or {}).items():
                        arr = np.array(grid, dtype=np.float32)
                        metrics[f"{name}_mean"] = float(np.mean(arr))
                    results.append({"iteration": i + 1, "metrics": metrics})
        except Exception as e:
            return {
                "status": "partial",
                "completed_iterations": len(results),
                "error": str(e),
                "results": results,
            }

    _latest_fields = fields
    asyncio.create_task(_notify_nlm_outcome(
        "batch_complete",
        {"iterations": payload.iterations, "sample_count": len(results)},
        {"results": results[-10:]} if results else None,
    ))
    return {"status": "ok", "iterations": payload.iterations, "results": results}


# --- Agent/MYCA control (live monitor, adjust, autonomy) ---

# Guardrails: allowed param ranges for autonomous adjustments
ENV_GUARDRAILS = {
    "temperature": (15.0, 35.0),
    "humidity": (30.0, 99.0),
    "ph": (4.0, 9.0),
    "speed": (0.5, 3.0),
}


@router.post("/agent/control")
async def agent_control(payload: AgentControlRequest) -> Dict[str, Any]:
    """
    MYCA/agent-driven Petri control: environment adjustments, contamination response,
    multi-run orchestration, monitoring. Actions are logged for audit.
    """
    from mycosoft_mas.simulation.petri_persistence import log_petri_agent_action, get_petri_audit_trail

    action = (payload.action or "").strip().lower()
    if action not in ("adjust_env", "contamination_response", "multi_run", "monitor"):
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    result: Dict[str, Any] = {}
    petridishsim_url = os.environ.get("PETRIDISHSIM_URL", "")

    if action == "monitor":
        # Return current status and metrics
        result = await get_status()
        result["audit_recent"] = get_petri_audit_trail(limit=5)
        log_petri_agent_action("monitor", payload.source, payload.params, result)
        return result

    if action == "adjust_env":
        # Clamp params to guardrails
        adj = payload.params
        clamped = {}
        for k, v in adj.items():
            if k in ENV_GUARDRAILS:
                lo, hi = ENV_GUARDRAILS[k]
                try:
                    clamped[k] = max(lo, min(hi, float(v)))
                except (TypeError, ValueError):
                    pass
        if not clamped:
            return {"status": "ignored", "message": "No valid env params to adjust"}
        result = {"status": "applied", "adjusted": clamped}
        log_petri_agent_action("adjust_env", payload.source, payload.params, result)
        return result

    if action == "contamination_response":
        # Strategy: isolate, reduce_speed, or adjust_ph
        strategy = (payload.params.get("strategy") or "reduce_speed").lower()
        if strategy not in ("isolate", "reduce_speed", "adjust_ph"):
            strategy = "reduce_speed"
        result = {"status": "applied", "strategy": strategy}
        log_petri_agent_action("contamination_response", payload.source, payload.params, result)
        return result

    if action == "multi_run":
        # Orchestrate batch run with agent-specified params
        iters = min(1000, max(1, int(payload.params.get("iterations", 10))))
        dt = max(0.01, min(1.0, float(payload.params.get("dt", 0.1))))
        if not petridishsim_url:
            result = {"status": "error", "message": "PETRIDISHSIM_URL not configured"}
        else:
            batch_payload = BatchRunRequest(iterations=iters, dt=dt)
            result = await batch_run(batch_payload)
        log_petri_agent_action("multi_run", payload.source, payload.params, result)
        return result

    return result


# --- Scale batch (thousands/millions) ---


@router.post("/batch/scale")
async def batch_scale(payload: ScaleBatchRequest) -> Dict[str, Any]:
    """
    High-volume batch: queue-based, chunked execution, resource caps.
    For iterations > 1000, returns job_id immediately; poll /batch/scale/{job_id} for status.
    """
    from mycosoft_mas.simulation.petri_batch_engine import run_scale_batch

    fields = payload.initial_fields or _latest_fields
    if not fields:
        raise HTTPException(status_code=400, detail="No initial fields; call /chemical/init first")

    return await run_scale_batch(
        iterations=payload.iterations,
        dt=payload.dt,
        initial_fields=fields,
        summary_only=payload.summary_only,
    )


@router.get("/batch/scale/{job_id}")
async def batch_scale_status(job_id: str) -> Dict[str, Any]:
    """Get status and result of a scale batch job."""
    from mycosoft_mas.simulation.petri_batch_engine import get_job_status

    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.post("/batch/scale/{job_id}/cancel")
async def batch_scale_cancel(job_id: str) -> Dict[str, Any]:
    """Cancel a running scale batch job."""
    from mycosoft_mas.simulation.petri_batch_engine import cancel_job

    if cancel_job(job_id):
        return {"status": "cancelled", "job_id": job_id}
    raise HTTPException(status_code=400, detail="Job not found or not cancellable")


@router.get("/agent/audit")
async def agent_audit_trail(limit: int = 50) -> Dict[str, Any]:
    """Return audit trail of agent-driven Petri actions."""
    from mycosoft_mas.simulation.petri_persistence import get_petri_audit_trail
    return {"entries": get_petri_audit_trail(limit=min(100, max(1, limit)))}
