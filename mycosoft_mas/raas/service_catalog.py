"""RaaS Service Catalog — public service discovery and pricing.

External agents query this to learn what MYCA offers and how much it costs.
No authentication required — the catalog is public for discovery.

Created: March 11, 2026
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from mycosoft_mas.raas.credits import CREDIT_COSTS
from mycosoft_mas.raas.models import ServiceCategory, ServiceDefinition

router = APIRouter(prefix="/api/raas/services", tags=["RaaS - Service Catalog"])


# ---------------------------------------------------------------------------
# Service definitions (references real internal endpoints)
# ---------------------------------------------------------------------------

_SERVICES: List[ServiceDefinition] = [
    # --- NLM Inference ---
    ServiceDefinition(
        service_id="nlm_predict",
        name="NLM Prediction",
        description=(
            "Nature Learning Model inference — general natural language queries, "
            "species identification, taxonomy, ecology, cultivation protocols, "
            "research synthesis, and genetic analysis."
        ),
        category="nlm",
        credit_cost=CREDIT_COSTS["nlm_inference"],
        input_schema={
            "query": "string (required)",
            "query_type": "general|species_id|taxonomy|ecology|cultivation|research|genetics",
            "max_tokens": "int (default 1024)",
            "temperature": "float (default 0.7)",
        },
        output_schema={
            "text": "string — generated response",
            "confidence": "float 0-1",
            "sources": "list of source references",
            "tokens_used": "int",
        },
    ),
    # --- CREP Live Data ---
    ServiceDefinition(
        service_id="crep_aviation",
        name="CREP Aviation Data",
        description="Real-time global aircraft tracking data from CREP sensors.",
        category="crep",
        credit_cost=CREDIT_COSTS["crep_query"],
        input_schema={"data_type": "aviation", "filters": "optional dict"},
        output_schema={"data": "list of aviation records", "timestamp": "ISO datetime"},
    ),
    ServiceDefinition(
        service_id="crep_maritime",
        name="CREP Maritime Data",
        description="Real-time global ship position and maritime data.",
        category="crep",
        credit_cost=CREDIT_COSTS["crep_query"],
        input_schema={"data_type": "maritime", "filters": "optional dict"},
        output_schema={"data": "list of maritime records", "timestamp": "ISO datetime"},
    ),
    ServiceDefinition(
        service_id="crep_satellite",
        name="CREP Satellite Data",
        description="Orbital satellite positions and imagery metadata.",
        category="crep",
        credit_cost=CREDIT_COSTS["crep_query"],
        input_schema={"data_type": "satellite", "filters": "optional dict"},
        output_schema={"data": "list of satellite records", "timestamp": "ISO datetime"},
    ),
    ServiceDefinition(
        service_id="crep_weather",
        name="CREP Weather Data",
        description="Real-time meteorological data from global sensor network.",
        category="crep",
        credit_cost=CREDIT_COSTS["crep_query"],
        input_schema={"data_type": "weather", "filters": "optional dict"},
        output_schema={"data": "list of weather records", "timestamp": "ISO datetime"},
    ),
    # --- Earth2 Climate ---
    ServiceDefinition(
        service_id="earth2_forecast",
        name="Earth2 Medium-Range Forecast",
        description="AI-powered weather forecast up to 15 days using NVIDIA Earth-2.",
        category="earth2",
        credit_cost=CREDIT_COSTS["earth2_forecast"],
        input_schema={
            "forecast_type": "medium_range",
            "location": "{lat, lon} or {bbox: [w,s,e,n]}",
            "parameters": "optional forecast parameters",
        },
        output_schema={
            "forecast_data": "array of forecast points",
            "model": "earth2",
            "horizon_hours": "int",
        },
    ),
    ServiceDefinition(
        service_id="earth2_nowcast",
        name="Earth2 Short-Range Nowcast",
        description="Minutes-to-hours nowcast for immediate weather conditions.",
        category="earth2",
        credit_cost=CREDIT_COSTS["earth2_nowcast"],
        input_schema={
            "forecast_type": "short_range",
            "location": "{lat, lon}",
        },
        output_schema={"nowcast_data": "array", "valid_minutes": "int"},
    ),
    ServiceDefinition(
        service_id="earth2_spore",
        name="Earth2 Spore Dispersal Forecast",
        description="Fungal spore dispersal modeling using Earth-2 wind fields.",
        category="earth2",
        credit_cost=CREDIT_COSTS["earth2_forecast"],
        input_schema={
            "forecast_type": "spore_dispersal",
            "location": "{lat, lon}",
            "parameters": "{species, release_height}",
        },
        output_schema={"dispersal_map": "GeoJSON", "concentration_grid": "array"},
    ),
    # --- Device Network ---
    ServiceDefinition(
        service_id="device_list",
        name="Device Registry List",
        description="List registered MycoBrain IoT devices and their capabilities.",
        category="devices",
        credit_cost=CREDIT_COSTS["device_telemetry"],
        input_schema={"query_type": "list", "filters": "optional"},
        output_schema={"devices": "list of device records"},
    ),
    ServiceDefinition(
        service_id="device_telemetry",
        name="Device Telemetry Query",
        description="Query sensor readings from MycoBrain environmental sensors (BME688/690, LoRa, spectral).",
        category="devices",
        credit_cost=CREDIT_COSTS["device_telemetry"],
        input_schema={"device_id": "string", "query_type": "telemetry"},
        output_schema={"readings": "list of sensor values", "device_id": "string"},
    ),
    # --- MINDEX Data ---
    ServiceDefinition(
        service_id="mindex_species",
        name="Species Lookup",
        description="Query the MINDEX species database — taxonomy, morphology, ecology, compounds.",
        category="mindex",
        credit_cost=CREDIT_COSTS["mindex_query"],
        input_schema={"query_type": "species", "query": "species name or search term"},
        output_schema={"results": "list of species records", "total": "int"},
    ),
    ServiceDefinition(
        service_id="mindex_taxonomy",
        name="Taxonomy Search",
        description="Hierarchical taxonomy search across biological kingdoms.",
        category="mindex",
        credit_cost=CREDIT_COSTS["mindex_query"],
        input_schema={"query_type": "taxonomy", "query": "taxon name"},
        output_schema={"taxonomy": "hierarchical classification", "children": "list"},
    ),
    ServiceDefinition(
        service_id="mindex_compound",
        name="Compound Query",
        description="Search bioactive compounds, metabolites, and chemical structures.",
        category="mindex",
        credit_cost=CREDIT_COSTS["mindex_query"],
        input_schema={"query_type": "compound", "query": "compound name or formula"},
        output_schema={"compounds": "list of compound records"},
    ),
    ServiceDefinition(
        service_id="knowledge_graph",
        name="Knowledge Graph Query",
        description="Traverse the Mycosoft knowledge graph — entities, relationships, paths.",
        category="mindex",
        credit_cost=CREDIT_COSTS["knowledge_graph"],
        input_schema={"query_type": "knowledge_graph", "query": "entity or relationship query"},
        output_schema={"nodes": "list", "edges": "list", "paths": "list"},
    ),
    # --- Agent Services ---
    ServiceDefinition(
        service_id="agent_task",
        name="Agent Task Execution",
        description=(
            "Execute a task using one of MYCA's 158+ specialized agents — "
            "scientific, financial, infrastructure, data, integration, and more."
        ),
        category="agents",
        credit_cost=CREDIT_COSTS["agent_task"],
        input_schema={
            "agent_type": "string — agent category or specific agent",
            "task_type": "string — task identifier",
            "payload": "dict — task-specific parameters",
        },
        output_schema={"task_id": "string", "result": "dict", "agent_used": "string"},
    ),
    # --- Memory & Search ---
    ServiceDefinition(
        service_id="memory_search",
        name="Semantic Memory Search",
        description="Search MYCA's 6-layer memory system — semantic, episodic, knowledge graph.",
        category="memory",
        credit_cost=CREDIT_COSTS["memory_search"],
        input_schema={
            "query": "string",
            "search_type": "semantic|fulltext|graph",
            "limit": "int (1-100)",
        },
        output_schema={"results": "list of memory records", "total": "int"},
    ),
    # --- Simulations ---
    ServiceDefinition(
        service_id="simulation_petri",
        name="Petri Dish Simulation",
        description="Simulate fungal growth patterns in a virtual petri dish environment.",
        category="simulations",
        credit_cost=CREDIT_COSTS["simulation"],
        input_schema={"sim_type": "petri", "parameters": "dict"},
        output_schema={"simulation_result": "dict", "steps": "int"},
    ),
    ServiceDefinition(
        service_id="simulation_mycelium",
        name="Mycelium Network Simulation",
        description="Model mycelium network growth, nutrient transport, and connectivity.",
        category="simulations",
        credit_cost=CREDIT_COSTS["simulation"],
        input_schema={"sim_type": "mycelium", "parameters": "dict"},
        output_schema={"network_graph": "dict", "metrics": "dict"},
    ),
    ServiceDefinition(
        service_id="simulation_physics",
        name="Physics Reasoning",
        description="PhysicsNeMo-powered reasoning about physical systems and dynamics.",
        category="simulations",
        credit_cost=CREDIT_COSTS["simulation"],
        input_schema={"sim_type": "physics", "parameters": "dict"},
        output_schema={"reasoning": "string", "predictions": "list"},
    ),
]

_CATEGORIES: List[ServiceCategory] = [
    ServiceCategory(
        category_id="nlm",
        name="Nature Learning Model",
        description="AI inference specialized in mycology, ecology, taxonomy, and natural science.",
        services=[s for s in _SERVICES if s.category == "nlm"],
    ),
    ServiceCategory(
        category_id="crep",
        name="CREP Live Data",
        description="Real-time global data — aviation, maritime, satellite, weather.",
        services=[s for s in _SERVICES if s.category == "crep"],
    ),
    ServiceCategory(
        category_id="earth2",
        name="Earth2 Climate Simulations",
        description="NVIDIA Earth-2 powered weather forecasts, nowcasts, and spore dispersal.",
        services=[s for s in _SERVICES if s.category == "earth2"],
    ),
    ServiceCategory(
        category_id="devices",
        name="Device Network",
        description="MycoBrain IoT device fleet — environmental sensors, telemetry, control.",
        services=[s for s in _SERVICES if s.category == "devices"],
    ),
    ServiceCategory(
        category_id="mindex",
        name="MINDEX Data & Knowledge",
        description="Species database, taxonomy, compounds, and knowledge graph queries.",
        services=[s for s in _SERVICES if s.category == "mindex"],
    ),
    ServiceCategory(
        category_id="agents",
        name="Agent Task Execution",
        description="Execute tasks using MYCA's 158+ specialized AI agents.",
        services=[s for s in _SERVICES if s.category == "agents"],
    ),
    ServiceCategory(
        category_id="memory",
        name="Memory & Semantic Search",
        description="Search MYCA's 6-layer memory and knowledge graph.",
        services=[s for s in _SERVICES if s.category == "memory"],
    ),
    ServiceCategory(
        category_id="simulations",
        name="Simulations",
        description="Biological and physics simulations — petri dish, mycelium, PhysicsNeMo.",
        services=[s for s in _SERVICES if s.category == "simulations"],
    ),
]

_SERVICE_MAP: Dict[str, ServiceDefinition] = {s.service_id: s for s in _SERVICES}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_service(service_id: str) -> ServiceDefinition | None:
    """Look up a service by ID."""
    return _SERVICE_MAP.get(service_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_services() -> Dict[str, Any]:
    """List all available RaaS services with pricing."""
    return {
        "status": "ok",
        "total_services": len(_SERVICES),
        "categories": [cat.model_dump() for cat in _CATEGORIES],
    }


@router.get("/categories")
async def list_categories() -> Dict[str, Any]:
    """List service categories with counts."""
    return {
        "status": "ok",
        "categories": [
            {
                "category_id": cat.category_id,
                "name": cat.name,
                "description": cat.description,
                "service_count": len(cat.services),
            }
            for cat in _CATEGORIES
        ],
    }


@router.get("/{service_id}")
async def get_service_detail(service_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific service."""
    svc = _SERVICE_MAP.get(service_id)
    if not svc:
        return {"status": "error", "detail": f"Service '{service_id}' not found"}
    return {"status": "ok", "service": svc.model_dump()}
