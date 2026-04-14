"""
Scientific equipment API routes.
"""

import os
from typing import Optional

import httpx
from fastapi import APIRouter

from mycosoft_mas.scientific.db_models import ScientificDataStore, ScientificEquipmentCreate

router = APIRouter(prefix="/api/scientific", tags=["scientific"])

_store: Optional[ScientificDataStore] = None


async def get_store() -> ScientificDataStore:
    global _store
    if _store is None:
        _store = ScientificDataStore()
        await _store.initialize()
    return _store


@router.get("/equipment/status")
async def get_equipment_status():
    store = await get_store()
    equipment = await store.list_equipment()
    return {"equipment": equipment, "source": "postgresql"}


@router.post("/equipment")
async def create_equipment(payload: ScientificEquipmentCreate):
    store = await get_store()
    return await store.create_equipment(payload)


@router.get("/simulations/live")
async def get_live_simulation_data():
    """
    Aggregate live simulation status from PhysicsNeMo and Earth2 services.
    """
    physics_base = os.getenv("PHYSICSNEMO_API_URL", "http://192.168.0.188:8400")
    physics_path = os.getenv("PHYSICSNEMO_STATUS_ENDPOINT", "/api/physicsnemo/status")
    # Live prediction paths are served by MAS (/api/earth2/...), not the raw Legion :8220 API.
    earth2_base = os.getenv(
        "EARTH2_LIVE_DATA_BASE", os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
    )
    earth2_path = os.getenv("EARTH2_PREDICTIONS_ENDPOINT", "/api/earth2/predictions/latest")

    physics_url = f"{physics_base.rstrip('/')}{physics_path}"
    earth2_url = f"{earth2_base.rstrip('/')}{earth2_path}"

    result = {"physicsnemo": None, "earth2": None}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            physics_resp = await client.get(physics_url)
            physics_resp.raise_for_status()
            result["physicsnemo"] = physics_resp.json()
        except Exception as exc:
            result["physicsnemo"] = {"error": "unavailable", "detail": str(exc), "url": physics_url}

        try:
            earth2_resp = await client.get(earth2_url)
            earth2_resp.raise_for_status()
            result["earth2"] = earth2_resp.json()
        except Exception as exc:
            result["earth2"] = {"error": "unavailable", "detail": str(exc), "url": earth2_url}

    return {"source": "external-services", "data": result}
