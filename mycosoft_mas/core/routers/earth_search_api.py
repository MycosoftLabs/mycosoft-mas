"""
Earth Search API — planetary-scale unified search endpoint.

POST /api/earth-search/query — search across all life, environment, infrastructure, space, telemetry
GET  /api/earth-search/domains — list all searchable domains and data sources
GET  /api/earth-search/health — connector health status
POST /api/earth-search/ingest — manual ingest trigger for external data

Dual pipeline: results + CREP map commands for simultaneous API and visualization access.
All results are ingested into local MINDEX + Supabase for low-latency re-query and NLM training.

Created: March 15, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.earth_search.models import (
    DOMAIN_GROUPS,
    EarthSearchDomain,
    EarthSearchQuery,
    EarthSearchResponse,
    GeoFilter,
)
from mycosoft_mas.earth_search.registry import (
    EARTH_DATA_SOURCES,
    get_all_realtime_sources,
    get_sources_for_domain,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/earth-search", tags=["earth-search"])


# ── Query ────────────────────────────────────────────────────────────────────


@router.post("/query", response_model=EarthSearchResponse)
async def earth_search_query(request: EarthSearchQuery) -> EarthSearchResponse:
    """
    Execute a planetary-scale search across all relevant data sources in parallel.

    - Auto-detects domains from query text if none specified
    - Fans out to all matching connectors in parallel
    - Returns results with geospatial coordinates + CREP map commands
    - Fire-and-forget ingests results into MINDEX + Supabase + NLM training sink
    """
    try:
        from mycosoft_mas.earth_search.orchestrator import run_earth_search

        return await run_earth_search(request)
    except Exception as e:
        logger.error("Earth search failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e


# ── Domains ──────────────────────────────────────────────────────────────────


class DomainInfo(BaseModel):
    domain: str
    group: str
    source_count: int
    sources: List[str]
    has_realtime: bool


@router.get("/domains")
async def list_domains() -> Dict[str, Any]:
    """List all searchable domains with their data sources."""
    domain_infos = []
    for domain in EarthSearchDomain:
        sources = get_sources_for_domain(domain)
        group = "other"
        for g, members in DOMAIN_GROUPS.items():
            if domain in members:
                group = g
                break
        domain_infos.append(
            DomainInfo(
                domain=domain.value,
                group=group,
                source_count=len(sources),
                sources=[s.source_id for s in sources],
                has_realtime=any(s.realtime for s in sources),
            )
        )

    return {
        "total_domains": len(EarthSearchDomain),
        "domain_groups": list(DOMAIN_GROUPS.keys()),
        "total_sources": len(EARTH_DATA_SOURCES),
        "realtime_sources": len(get_all_realtime_sources()),
        "domains": [d.model_dump() for d in domain_infos],
    }


# ── Data Sources ─────────────────────────────────────────────────────────────


@router.get("/sources")
async def list_sources() -> Dict[str, Any]:
    """List all data sources with metadata."""
    return {
        "total": len(EARTH_DATA_SOURCES),
        "sources": [s.model_dump() for s in EARTH_DATA_SOURCES],
    }


# ── Health ───────────────────────────────────────────────────────────────────


@router.get("/health")
async def earth_search_health() -> Dict[str, Any]:
    """Check Earth Search system health."""
    return {
        "status": "healthy",
        "total_domains": len(EarthSearchDomain),
        "total_sources": len(EARTH_DATA_SOURCES),
        "realtime_sources": len(get_all_realtime_sources()),
        "domain_groups": list(DOMAIN_GROUPS.keys()),
    }


# ── CREP Bridge ──────────────────────────────────────────────────────────────


class CREPSearchRequest(BaseModel):
    """Search with automatic CREP map visualization."""

    query: str = Field(..., min_length=1)
    domains: List[EarthSearchDomain] = Field(default_factory=list)
    lat: Optional[float] = None
    lng: Optional[float] = None
    radius_km: float = 100
    limit: int = 20


@router.post("/crep")
async def earth_search_crep(request: CREPSearchRequest) -> Dict[str, Any]:
    """
    Search and simultaneously render results on the CREP map.
    Returns both search results and CREP command sequence.
    """
    geo = (
        GeoFilter(lat=request.lat, lng=request.lng, radius_km=request.radius_km)
        if request.lat and request.lng
        else None
    )

    search_query = EarthSearchQuery(
        query=request.query,
        domains=request.domains,
        geo=geo,
        limit=request.limit,
        include_crep=True,
    )

    try:
        from mycosoft_mas.earth_search.orchestrator import run_earth_search

        response = await run_earth_search(search_query)

        # Also emit CREP commands via Redis pub/sub for real-time map update
        try:
            from mycosoft_mas.crep.command_bus import emit_crep_commands

            if response.crep_commands:
                await emit_crep_commands(response.crep_commands)
        except Exception as e:
            logger.debug("CREP command emission failed (non-critical): %s", e)

        return response.model_dump(mode="json")
    except Exception as e:
        logger.error("Earth search CREP failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e


# ── Manual Ingest ────────────────────────────────────────────────────────────


class IngestRequest(BaseModel):
    """Manually trigger ingestion of external data."""

    domain: EarthSearchDomain
    source: str
    records: List[Dict[str, Any]]


@router.post("/ingest")
async def manual_ingest(request: IngestRequest) -> Dict[str, Any]:
    """Manually ingest external data into MINDEX + Supabase."""
    import uuid

    from mycosoft_mas.earth_search.ingestion.pipeline import IngestionPipeline

    results = []
    for rec in request.records:
        results.append(
            EarthSearchResult(
                result_id=rec.get("id", f"manual-{uuid.uuid4().hex[:8]}"),
                domain=request.domain,
                source=request.source,
                title=rec.get("title", ""),
                description=rec.get("description", ""),
                data=rec.get("data", {}),
                lat=rec.get("lat"),
                lng=rec.get("lng"),
                confidence=rec.get("confidence", 0.5),
            )
        )

    pipeline = IngestionPipeline()
    await pipeline.ingest_batch(results, f"manual_ingest:{request.domain.value}")
    return {"status": "ingested", "count": len(results)}


# Import needed for manual ingest endpoint
from mycosoft_mas.earth_search.models import EarthSearchResult  # noqa: E402
