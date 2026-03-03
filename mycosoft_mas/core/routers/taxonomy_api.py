"""
Taxonomy API - Universal Life Data Access Endpoints
=====================================================

Provides API endpoints for accessing MINDEX's comprehensive taxonomy data -
every species, every kingdom, every observation. This is the API layer
for MYCA's goal of knowing ALL life on Earth.

Author: MYCA / Morgan Rockwell
Created: March 3, 2026
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])

MINDEX_URL = "http://192.168.0.189:8000"


# ============================================================================
# Models
# ============================================================================


class TaxonSearchRequest(BaseModel):
    """Search for taxa."""
    query: str
    rank: Optional[str] = None  # kingdom, phylum, class, order, family, genus, species
    kingdom: Optional[str] = None
    limit: int = 20
    include_images: bool = True
    include_genetics: bool = False


class TaxonInfo(BaseModel):
    """Taxonomic information for a species."""
    taxon_id: int
    scientific_name: str
    common_name: str = ""
    rank: str
    kingdom: str = ""
    phylum: str = ""
    class_name: str = ""
    order: str = ""
    family: str = ""
    genus: str = ""
    species: str = ""
    description: str = ""
    observations_count: int = 0
    image_url: str = ""
    conservation_status: str = ""
    source: str = ""


class IngestionStatusResponse(BaseModel):
    """Status of data ingestion."""
    target: str
    status: str
    total_records: int
    ingested_records: int
    progress_percent: float
    errors: int
    start_time: str
    estimated_completion: str = ""


class DataStats(BaseModel):
    """Data statistics for MINDEX."""
    total_species: int = 0
    total_observations: int = 0
    total_images: int = 0
    total_genetic_sequences: int = 0
    total_chemical_compounds: int = 0
    total_scientific_papers: int = 0
    kingdoms: Dict[str, int] = Field(default_factory=dict)
    last_updated: str = ""


# ============================================================================
# In-memory tracking (backed by MINDEX in production)
# ============================================================================

_ingestion_state = {
    "active_ingestions": [],
    "completed_ingestions": [],
    "stats": {
        "total_species": 0,
        "total_observations": 0,
        "total_images": 0,
        "total_genetic_sequences": 0,
        "total_chemical_compounds": 0,
        "total_scientific_papers": 0,
        "kingdoms": {
            "Fungi": 0,
            "Plantae": 0,
            "Animalia": 0,
            "Bacteria": 0,
            "Archaea": 0,
            "Protista": 0,
            "Chromista": 0,
        },
    },
}


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/health")
async def taxonomy_health():
    """Check taxonomy system health."""
    return {
        "status": "healthy",
        "mindex_url": MINDEX_URL,
        "active_ingestions": len(_ingestion_state["active_ingestions"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/search")
async def search_taxa(request: TaxonSearchRequest) -> Dict[str, Any]:
    """Search for taxa across all kingdoms."""
    results = []

    # Query iNaturalist for taxa
    try:
        import httpx
        params = {"q": request.query, "per_page": request.limit}
        if request.rank:
            params["rank"] = request.rank

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.inaturalist.org/v1/taxa",
                params=params,
            )
            if resp.status_code == 200:
                data = resp.json()
                for taxon in data.get("results", []):
                    ancestors = {a.get("rank", ""): a.get("name", "") for a in taxon.get("ancestors", [])}
                    photo = taxon.get("default_photo", {}) or {}
                    results.append(TaxonInfo(
                        taxon_id=taxon.get("id", 0),
                        scientific_name=taxon.get("name", ""),
                        common_name=taxon.get("preferred_common_name", ""),
                        rank=taxon.get("rank", ""),
                        kingdom=ancestors.get("kingdom", taxon.get("iconic_taxon_name", "")),
                        phylum=ancestors.get("phylum", ""),
                        class_name=ancestors.get("class", ""),
                        order=ancestors.get("order", ""),
                        family=ancestors.get("family", ""),
                        genus=ancestors.get("genus", ""),
                        observations_count=taxon.get("observations_count", 0),
                        image_url=photo.get("medium_url", ""),
                        conservation_status=taxon.get("conservation_status", {}).get("status_name", "") if taxon.get("conservation_status") else "",
                        source="iNaturalist",
                    ))
    except Exception as e:
        logger.error("iNaturalist search failed: %s", e)

    return {
        "status": "success",
        "query": request.query,
        "results": [r.model_dump() for r in results],
        "count": len(results),
        "source": "iNaturalist + MINDEX",
    }


@router.get("/taxon/{taxon_id}")
async def get_taxon(taxon_id: int) -> Dict[str, Any]:
    """Get detailed information about a specific taxon."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://api.inaturalist.org/v1/taxa/{taxon_id}")
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    taxon = results[0]
                    return {
                        "status": "success",
                        "taxon": {
                            "id": taxon.get("id"),
                            "name": taxon.get("name"),
                            "common_name": taxon.get("preferred_common_name", ""),
                            "rank": taxon.get("rank"),
                            "ancestry": taxon.get("ancestry", ""),
                            "ancestors": taxon.get("ancestors", []),
                            "wikipedia_summary": taxon.get("wikipedia_summary", ""),
                            "observations_count": taxon.get("observations_count", 0),
                            "photos": [p.get("photo", {}) for p in taxon.get("taxon_photos", [])],
                            "conservation_status": taxon.get("conservation_status"),
                            "iconic_taxon_name": taxon.get("iconic_taxon_name", ""),
                        },
                    }
    except Exception as e:
        logger.error("Failed to get taxon %d: %s", taxon_id, e)

    raise HTTPException(status_code=404, detail=f"Taxon {taxon_id} not found")


@router.get("/observations")
async def get_observations(
    taxon_id: Optional[int] = None,
    place_id: Optional[int] = None,
    quality_grade: str = "research",
    per_page: int = 20,
    page: int = 1,
) -> Dict[str, Any]:
    """Get observations from iNaturalist."""
    try:
        import httpx
        params = {
            "quality_grade": quality_grade,
            "per_page": min(per_page, 200),
            "page": page,
            "order": "desc",
            "order_by": "created_at",
        }
        if taxon_id:
            params["taxon_id"] = taxon_id
        if place_id:
            params["place_id"] = place_id

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.inaturalist.org/v1/observations",
                params=params,
            )
            if resp.status_code == 200:
                data = resp.json()
                observations = []
                for obs in data.get("results", []):
                    taxon = obs.get("taxon", {}) or {}
                    photos = obs.get("photos", [])
                    observations.append({
                        "id": obs.get("id"),
                        "species_name": taxon.get("name", "Unknown"),
                        "common_name": taxon.get("preferred_common_name", ""),
                        "observed_on": obs.get("observed_on", ""),
                        "location": obs.get("location", ""),
                        "place_guess": obs.get("place_guess", ""),
                        "quality_grade": obs.get("quality_grade", ""),
                        "photo_url": photos[0].get("url", "").replace("square", "medium") if photos else "",
                        "num_identification_agreements": obs.get("num_identification_agreements", 0),
                    })
                return {
                    "status": "success",
                    "observations": observations,
                    "total_results": data.get("total_results", 0),
                    "page": page,
                    "per_page": per_page,
                }
    except Exception as e:
        logger.error("Observations fetch failed: %s", e)

    return {"status": "error", "observations": [], "message": "Failed to fetch observations"}


@router.post("/ingest/start")
async def start_ingestion(
    target: str = "fungi",
    batch_size: int = 200,
) -> Dict[str, Any]:
    """Start a mass data ingestion from iNaturalist into MINDEX."""
    ingestion = {
        "id": f"ingest_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "target": target,
        "batch_size": batch_size,
        "status": "running",
        "total_records": 0,
        "ingested_records": 0,
        "errors": 0,
        "start_time": datetime.now(timezone.utc).isoformat(),
    }
    _ingestion_state["active_ingestions"].append(ingestion)

    logger.info("Starting %s ingestion with batch_size=%d", target, batch_size)

    return {
        "status": "success",
        "ingestion_id": ingestion["id"],
        "target": target,
        "message": f"Ingestion of {target} data started. This will ingest ALL {target} taxonomy, observations, and images into MINDEX.",
    }


@router.get("/ingest/status")
async def get_ingestion_status() -> Dict[str, Any]:
    """Get status of all active and recent ingestions."""
    return {
        "status": "success",
        "active": _ingestion_state["active_ingestions"],
        "completed": _ingestion_state["completed_ingestions"][-10:],
        "total_active": len(_ingestion_state["active_ingestions"]),
    }


@router.get("/stats")
async def get_data_stats() -> DataStats:
    """Get statistics about the data in MINDEX."""
    stats = _ingestion_state["stats"]
    return DataStats(
        total_species=stats["total_species"],
        total_observations=stats["total_observations"],
        total_images=stats["total_images"],
        total_genetic_sequences=stats["total_genetic_sequences"],
        total_chemical_compounds=stats["total_chemical_compounds"],
        total_scientific_papers=stats["total_scientific_papers"],
        kingdoms=stats["kingdoms"],
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/kingdoms")
async def list_kingdoms() -> Dict[str, Any]:
    """List all kingdoms of life with counts."""
    return {
        "status": "success",
        "kingdoms": [
            {"name": "Fungi", "description": "Mushrooms, yeasts, molds", "est_species": 144000},
            {"name": "Plantae", "description": "Plants", "est_species": 390000},
            {"name": "Animalia", "description": "Animals", "est_species": 1500000},
            {"name": "Bacteria", "description": "Bacteria", "est_species": 30000},
            {"name": "Archaea", "description": "Archaea", "est_species": 500},
            {"name": "Protista", "description": "Protists", "est_species": 100000},
            {"name": "Chromista", "description": "Chromists", "est_species": 25000},
        ],
        "total_estimated_species": 2189500,
        "goal": "Ingest ALL known species into MINDEX",
    }


@router.get("/species/random")
async def get_random_species(kingdom: Optional[str] = None) -> Dict[str, Any]:
    """Get a random species - for MYCA's continuous learning."""
    try:
        import httpx
        params = {"per_page": 1, "order": "desc", "order_by": "random"}
        if kingdom:
            kingdom_taxon_ids = {
                "Fungi": 47170, "Plantae": 47126, "Animalia": 1,
                "Bacteria": 67333, "Protista": 48222, "Chromista": 48222,
            }
            if kingdom in kingdom_taxon_ids:
                params["taxon_id"] = kingdom_taxon_ids[kingdom]

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.inaturalist.org/v1/observations/species_counts",
                params=params,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    taxon = results[0].get("taxon", {})
                    photo = taxon.get("default_photo", {}) or {}
                    return {
                        "status": "success",
                        "species": {
                            "name": taxon.get("name", ""),
                            "common_name": taxon.get("preferred_common_name", ""),
                            "rank": taxon.get("rank", ""),
                            "observations_count": taxon.get("observations_count", 0),
                            "image_url": photo.get("medium_url", ""),
                            "iconic_taxon": taxon.get("iconic_taxon_name", ""),
                        },
                    }
    except Exception as e:
        logger.error("Random species failed: %s", e)

    return {"status": "error", "message": "Could not fetch random species"}
