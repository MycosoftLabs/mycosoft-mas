"""
Scientific datasets API routes.
"""

import os
from typing import Optional

from fastapi import APIRouter
import httpx

from mycosoft_mas.scientific.db_models import ScientificDataStore, ScientificDatasetCreate

router = APIRouter(prefix="/api/scientific", tags=["scientific"])

_store: Optional[ScientificDataStore] = None


async def get_store() -> ScientificDataStore:
    global _store
    if _store is None:
        _store = ScientificDataStore()
        await _store.initialize()
    return _store


@router.get("/datasets")
async def list_datasets():
    store = await get_store()
    datasets = await store.list_datasets()
    return {"datasets": datasets, "source": "postgresql"}


@router.post("/datasets")
async def create_dataset(payload: ScientificDatasetCreate):
    store = await get_store()
    return await store.create_dataset(payload)


@router.get("/datasets/species")
async def search_species_dataset(query: str):
    """
    Proxy species/taxonomy search to MINDEX.
    """
    mindex_base = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
    search_path = os.getenv("MINDEX_SPECIES_SEARCH_ENDPOINT", "/api/search/species")
    target_url = f"{mindex_base.rstrip('/')}{search_path}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(target_url, params={"q": query})
            resp.raise_for_status()
            payload = resp.json()
            return {"source": "mindex", "query": query, "data": payload}
    except Exception as exc:
        return {
            "source": "mindex",
            "query": query,
            "error": "species_search_unavailable",
            "detail": str(exc),
        }
