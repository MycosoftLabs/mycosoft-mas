"""
Scientific experiments and observations API routes.
"""

import os
from typing import Optional

from fastapi import APIRouter, Query
import httpx

from mycosoft_mas.scientific.db_models import (
    ScientificDataStore,
    ScientificExperimentCreate,
    ScientificObservationCreate,
)

router = APIRouter(prefix="/api/scientific", tags=["scientific"])

_store: Optional[ScientificDataStore] = None


async def get_store() -> ScientificDataStore:
    global _store
    if _store is None:
        _store = ScientificDataStore()
        await _store.initialize()
    return _store


@router.get("/experiments")
async def list_experiments():
    store = await get_store()
    experiments = await store.list_experiments()
    return {"experiments": experiments, "source": "postgresql"}


@router.post("/experiments")
async def create_experiment(payload: ScientificExperimentCreate):
    store = await get_store()
    return await store.create_experiment(payload)


@router.get("/observations")
async def list_observations(experiment_id: Optional[str] = Query(default=None)):
    store = await get_store()
    observations = await store.list_observations(experiment_id=experiment_id)
    return {"observations": observations, "source": "postgresql"}


@router.post("/observations")
async def create_observation(payload: ScientificObservationCreate):
    store = await get_store()
    return await store.create_observation(payload)


@router.get("/observations/live")
async def get_live_observations(device_id: Optional[str] = Query(default=None)):
    """
    Proxy live observations from NatureOS telemetry endpoints.
    """
    natureos_base = os.getenv("NATUREOS_API_URL", "http://192.168.0.188:8001")
    telemetry_path = os.getenv("NATUREOS_SCIENTIFIC_OBSERVATIONS_ENDPOINT", "/api/devices/telemetry")
    query = f"?device_id={device_id}" if device_id else ""
    target_url = f"{natureos_base.rstrip('/')}{telemetry_path}{query}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(target_url)
            resp.raise_for_status()
            payload = resp.json()
            return {"source": "natureos", "url": target_url, "data": payload}
    except Exception as exc:
        return {
            "source": "natureos",
            "url": target_url,
            "error": "live_telemetry_unavailable",
            "detail": str(exc),
        }
