"""
Earth Search Orchestrator — MINDEX-first, parallel fan-out, CREP bridge, ingest.

Architecture:
1. MINDEX local first (lowest latency — pre-ingested data from 9 ETL connectors)
2. External connectors in parallel (supplementary real-time data)
3. Merge, deduplicate, generate CREP commands
4. Fire-and-forget ingestion back into MINDEX + Supabase + NLM training

Created: March 15, 2026
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from mycosoft_mas.earth_search.models import (
    DOMAIN_GROUPS,
    EarthSearchDomain,
    EarthSearchQuery,
    EarthSearchResponse,
    EarthSearchResult,
)
from mycosoft_mas.earth_search.connectors.species import SpeciesConnector
from mycosoft_mas.earth_search.connectors.environment import EnvironmentConnector
from mycosoft_mas.earth_search.connectors.climate import ClimateConnector
from mycosoft_mas.earth_search.connectors.transport import TransportConnector
from mycosoft_mas.earth_search.connectors.space import SpaceConnector
from mycosoft_mas.earth_search.connectors.infrastructure import InfrastructureConnector
from mycosoft_mas.earth_search.connectors.telecom import TelecomConnector
from mycosoft_mas.earth_search.connectors.sensors import SensorConnector
from mycosoft_mas.earth_search.connectors.science import ScienceConnector

if TYPE_CHECKING:
    from mycosoft_mas.earth_search.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

# All connector instances (singletons)
_CONNECTORS: List["BaseConnector"] = [
    SpeciesConnector(),
    EnvironmentConnector(),
    ClimateConnector(),
    TransportConnector(),
    SpaceConnector(),
    InfrastructureConnector(),
    TelecomConnector(),
    SensorConnector(),
    ScienceConnector(),
]

# Domain -> CREP layer mapping for map visualization
CREP_LAYER_MAP: Dict[EarthSearchDomain, str] = {
    EarthSearchDomain.FLIGHTS: "flights",
    EarthSearchDomain.VESSELS: "marine",
    EarthSearchDomain.SATELLITES: "satellites",
    EarthSearchDomain.EARTHQUAKES: "earthquakes",
    EarthSearchDomain.WILDFIRES: "wildfires",
    EarthSearchDomain.VOLCANOES: "volcanoes",
    EarthSearchDomain.STORMS: "storms",
    EarthSearchDomain.WEATHER: "weather",
    EarthSearchDomain.ALL_SPECIES: "species",
    EarthSearchDomain.FUNGI: "species",
    EarthSearchDomain.PLANTS: "species",
    EarthSearchDomain.BIRDS: "species",
    EarthSearchDomain.MAMMALS: "species",
    EarthSearchDomain.CELL_TOWERS: "infrastructure",
    EarthSearchDomain.POWER_PLANTS: "infrastructure",
    EarthSearchDomain.POLLUTION_SOURCES: "infrastructure",
    EarthSearchDomain.SOLAR_FLARES: "space_weather",
    EarthSearchDomain.SPACE_WEATHER: "space_weather",
    EarthSearchDomain.INTERNET_CABLES: "infrastructure",
    EarthSearchDomain.AIRPORTS: "transport",
    EarthSearchDomain.SHIPPING_PORTS: "transport",
    EarthSearchDomain.LAUNCHES: "launches",
    EarthSearchDomain.MYCOBRAIN_DEVICES: "devices",
}


async def run_earth_search(query: EarthSearchQuery) -> EarthSearchResponse:
    """
    Execute a planetary-scale search across all relevant data sources in parallel.

    1. Resolve domains from query
    2. Hit MINDEX local first (lowest latency — all pre-ingested data)
    3. Fan out to external connectors in parallel for supplementary data
    4. Merge and deduplicate results
    5. Generate CREP map commands
    6. Fire-and-forget ingestion to MINDEX + Supabase + NLM training
    7. Optionally call LLM for synthesis answer
    """
    start = time.time()
    domains = query.resolved_domains()
    domain_strings = [d.value for d in domains]
    domain_groups = query.domain_groups

    # ── Step 1: MINDEX local (lowest latency) ────────────────────────────────
    mindex_results: List[EarthSearchResult] = []
    try:
        from mycosoft_mas.earth_search.mindex_earth_client import get_mindex_earth_client

        mindex = get_mindex_earth_client()

        mindex_params = {
            "query": query.query,
            "domains": domain_strings if domain_strings else None,
            "domain_groups": domain_groups if domain_groups else None,
            "limit": query.limit,
        }
        if query.geo:
            mindex_params["lat"] = query.geo.lat
            mindex_params["lng"] = query.geo.lng
            mindex_params["radius_km"] = query.geo.radius_km

        mindex_data = await asyncio.wait_for(
            mindex.earth_search(**{k: v for k, v in mindex_params.items() if v is not None}),
            timeout=10.0,
        )

        # Convert MINDEX universal_results to EarthSearchResult
        for r in mindex_data.get("universal_results", mindex_data.get("results", [])):
            if isinstance(r, dict):
                domain_val = r.get("domain", r.get("entity_type", "all_species"))
                try:
                    domain_enum = EarthSearchDomain(domain_val)
                except ValueError:
                    domain_enum = EarthSearchDomain.ALL_SPECIES

                mindex_results.append(
                    EarthSearchResult(
                        result_id=f"mindex-{r.get('id', r.get('entity_id', id(r)))}",
                        domain=domain_enum,
                        source="mindex_local",
                        title=r.get("title", r.get("name", query.query)),
                        description=r.get("description", r.get("summary", "")),
                        data=r.get("data", r),
                        lat=r.get("lat") or r.get("latitude"),
                        lng=r.get("lng") or r.get("longitude"),
                        timestamp=r.get("timestamp") or r.get("observed_at"),
                        confidence=float(r.get("confidence", r.get("score", 0.9))),
                        crep_layer=r.get("crep_layer") or r.get("layer"),
                        crep_entity_id=r.get("crep_entity_id") or r.get("entity_id"),
                        mindex_id=str(r.get("id", "")),
                        url=r.get("url"),
                        image_url=r.get("image_url"),
                    )
                )
    except Exception as e:
        logger.warning("MINDEX earth search failed (will use external connectors): %s", e)

    # ── Step 2: External connectors in parallel ──────────────────────────────
    tasks = []
    for connector in _CONNECTORS:
        tasks.append(
            _safe_connector_search(
                connector,
                query.query,
                domains,
                query.geo,
                query.temporal,
                query.limit,
            )
        )

    all_results_nested = await asyncio.gather(*tasks)

    # ── Step 3: Merge and deduplicate ────────────────────────────────────────
    seen_ids = set()
    results: List[EarthSearchResult] = []
    sources_queried: List[str] = ["mindex_local"] if mindex_results else []

    # MINDEX results first (highest priority — local data)
    for r in mindex_results:
        if r.result_id not in seen_ids:
            seen_ids.add(r.result_id)
            results.append(r)

    # Then external connector results
    for connector, batch in zip(_CONNECTORS, all_results_nested):
        if batch:
            sources_queried.append(connector.source_id)
        for r in batch:
            if r.result_id not in seen_ids:
                seen_ids.add(r.result_id)
                results.append(r)

    # Sort by confidence desc
    results.sort(key=lambda r: r.confidence, reverse=True)
    results = results[: query.limit]

    # Generate CREP commands for map visualization
    crep_commands: List[Dict[str, Any]] = []
    if query.include_crep:
        crep_commands = _generate_crep_commands(results, query)

    # LLM synthesis (optional)
    llm_answer = None
    if query.include_llm:
        llm_answer = await _llm_synthesize(query.query, results)

    # Fire-and-forget ingestion
    try:
        from mycosoft_mas.earth_search.ingestion.pipeline import IngestionPipeline

        pipeline = IngestionPipeline()
        asyncio.create_task(pipeline.ingest_batch(results, query.query, query.session_id))
    except Exception as e:
        logger.debug("Ingestion pipeline schedule failed: %s", e)

    duration_ms = (time.time() - start) * 1000

    return EarthSearchResponse(
        query=query.query,
        domains_searched=domains,
        results=results,
        total_count=len(results),
        sources_queried=sources_queried,
        crep_commands=crep_commands,
        llm_answer=llm_answer,
        ingestion_status={"scheduled": True, "result_count": len(results)},
        timestamp=datetime.now(timezone.utc).isoformat(),
        duration_ms=round(duration_ms, 2),
    )


async def _safe_connector_search(
    connector, query, domains, geo, temporal, limit
) -> List[EarthSearchResult]:
    """Run a single connector's search with error isolation."""
    try:
        return await asyncio.wait_for(
            connector.search(query, domains, geo, temporal, limit),
            timeout=25.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Connector %s timed out", connector.source_id)
        return []
    except Exception as e:
        logger.warning("Connector %s failed: %s", connector.source_id, e)
        return []


def _generate_crep_commands(
    results: List[EarthSearchResult], query: EarthSearchQuery
) -> List[Dict[str, Any]]:
    """Generate CREP command bus commands to visualize search results on the map."""
    commands: List[Dict[str, Any]] = []

    # Collect unique layers to show
    layers_to_show = set()
    geo_results = [r for r in results if r.lat is not None and r.lng is not None]

    for r in geo_results:
        layer = r.crep_layer or CREP_LAYER_MAP.get(r.domain, "default")
        layers_to_show.add(layer)

    # Show relevant layers
    for layer in layers_to_show:
        commands.append({"command": "showLayer", "args": {"layer": layer}})

    # If geo filter, fly to that location
    if query.geo:
        commands.append(
            {
                "command": "flyTo",
                "args": {
                    "lat": query.geo.lat,
                    "lng": query.geo.lng,
                    "zoom": _radius_to_zoom(query.geo.radius_km),
                },
            }
        )
    elif geo_results:
        # Fly to the center of first result
        commands.append(
            {
                "command": "flyTo",
                "args": {
                    "lat": geo_results[0].lat,
                    "lng": geo_results[0].lng,
                    "zoom": 8,
                },
            }
        )

    # Add entity details for top results
    for r in geo_results[:5]:
        if r.crep_entity_id:
            commands.append(
                {
                    "command": "getEntityDetails",
                    "args": {"entityId": r.crep_entity_id, "layer": r.crep_layer},
                }
            )

    return commands


def _radius_to_zoom(radius_km: float) -> int:
    """Convert a search radius in km to an approximate map zoom level."""
    if radius_km < 1:
        return 16
    if radius_km < 5:
        return 14
    if radius_km < 20:
        return 12
    if radius_km < 50:
        return 10
    if radius_km < 200:
        return 8
    if radius_km < 500:
        return 6
    if radius_km < 2000:
        return 4
    return 2


async def _llm_synthesize(query: str, results: List[EarthSearchResult]) -> Optional[str]:
    """Use LLM to synthesize a natural language answer from search results."""
    try:
        from mycosoft_mas.llm.brain import get_brain

        brain = get_brain()
        if not brain:
            return None

        # Build context from top results
        context_parts = []
        for r in results[:10]:
            context_parts.append(f"[{r.domain.value}] {r.title}: {r.description}")

        context = "\n".join(context_parts)
        prompt = (
            f'Based on these search results for "{query}", provide a concise, accurate answer:\n\n'
            f"{context}\n\n"
            f"Answer concisely and factually. Cite specific data points from the results."
        )

        response = await brain.generate(prompt, max_tokens=500)
        return response if isinstance(response, str) else str(response)
    except Exception as e:
        logger.debug("LLM synthesis failed: %s", e)
        return None
