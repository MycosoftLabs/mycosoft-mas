"""
Petri Dish Simulation API.

Provides endpoints for chemical field initialization, stepping, metrics, and calibration.
"""

from __future__ import annotations

import os
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
    return {
        "status": "received",
        "species_name": payload.species_name,
        "initial_params": payload.initial_params,
        "bounds": payload.bounds,
        "sample_count": len(payload.samples),
    }
