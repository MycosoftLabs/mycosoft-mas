"""
PhysicsNeMo API Router
February 9, 2026
"""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/physics", tags=["physicsnemo"])
PHYSICSNEMO_API_URL = os.getenv("PHYSICSNEMO_API_URL", "http://localhost:8400").rstrip("/")


class GenericSimulationRequest(BaseModel):
    simulation_type: str = Field(description="diffusion|fluid|heat|reaction|neural-operator|pinn")
    params: Dict[str, Any] = Field(default_factory=dict)


async def _proxy(method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.request(method, f"{PHYSICSNEMO_API_URL}{path}", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            raise HTTPException(status_code=502, detail=f"PhysicsNeMo error: {detail}") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"PhysicsNeMo unavailable: {exc}") from exc


@router.get("/health")
async def health() -> Dict[str, Any]:
    return await _proxy("GET", "/health")


@router.get("/gpu")
async def gpu_status() -> Dict[str, Any]:
    return await _proxy("GET", "/gpu/status")


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    return await _proxy("GET", "/physics/models")


@router.post("/simulate")
async def simulate(payload: GenericSimulationRequest) -> Dict[str, Any]:
    route_map = {
        "diffusion": "/physics/diffusion",
        "fluid": "/physics/fluid-flow",
        "heat": "/physics/heat-transfer",
        "reaction": "/physics/reaction",
        "neural-operator": "/physics/neural-operator",
        "pinn": "/physics/pinn",
    }
    target = route_map.get(payload.simulation_type)
    if not target:
        raise HTTPException(status_code=400, detail=f"Unsupported simulation_type: {payload.simulation_type}")
    return await _proxy("POST", target, payload=payload.params)


@router.post("/diffusion")
async def simulate_diffusion(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _proxy("POST", "/physics/diffusion", payload=params)


@router.post("/fluid")
async def simulate_fluid(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _proxy("POST", "/physics/fluid-flow", payload=params)


@router.post("/heat")
async def simulate_heat(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _proxy("POST", "/physics/heat-transfer", payload=params)


@router.post("/reaction")
async def simulate_reaction(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _proxy("POST", "/physics/reaction", payload=params)
