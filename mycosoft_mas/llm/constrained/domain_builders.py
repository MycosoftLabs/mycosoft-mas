"""
Domain Constraint Builders for STATIC Framework

Builds STATIC constraint indexes from all Mycosoft MAS data domains:
- MINDEX: Fungal species, taxonomy, compounds, genetic data
- CREP: Flight callsigns, vessel IDs, satellite designators, weather stations
- NLM: Nature Learning Model entity identifiers, prediction categories
- Taxonomy: Full hierarchical classification (Kingdom → Species)
- Agents: All 117+ agent IDs and capabilities
- Devices: MycoBrain devices, sensors, electrode arrays
- Users: User identifiers for access-controlled generation
- Signals: Bio-signal types, SDR channels, FCI electrode IDs
- MycoBrain: Compute modes, network IDs, stimulation protocols

Each builder produces a named STATICIndex that the ConstraintEngine can use
to enforce valid-only generation for its domain. This eliminates hallucinated
IDs, invalid taxonomy paths, non-existent device names, etc.

Created: March 3, 2026
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

from mycosoft_mas.llm.constrained.static_index import (
    IndexConfig,
    STATICIndex,
    build_index_from_strings,
    build_static_index,
)

logger = logging.getLogger(__name__)

# Standard byte-level tokenizer for universal string constraint indexing.
# Vocab size 256 maps each byte to a unique token — language-agnostic
# and works for Latin taxonomy, Unicode common names, and binary IDs.
BYTE_VOCAB_SIZE = 256


def _byte_tokenize(s: str) -> List[int]:
    """Byte-level tokenizer for universal string encoding."""
    return list(s.encode("utf-8"))


def _build_string_index(
    name: str,
    strings: List[str],
    vocab_size: int = BYTE_VOCAB_SIZE,
    dense_depth: int = 2,
) -> STATICIndex:
    """Build a STATIC index from a list of valid strings."""
    if not strings:
        raise ValueError(f"No strings provided for index '{name}'")

    # Deduplicate while preserving order
    seen: Set[str] = set()
    unique = []
    for s in strings:
        if s and s not in seen:
            seen.add(s)
            unique.append(s)

    config = IndexConfig(vocab_size=vocab_size, dense_depth=dense_depth)
    index = build_index_from_strings(unique, _byte_tokenize, config)
    logger.info(
        f"Built domain index '{name}': {len(unique)} entries, "
        f"{index.num_states} states, {index.memory_usage_mb():.2f} MB"
    )
    return index


# ---------------------------------------------------------------------------
# Domain: MINDEX (Mycological Index — species, taxonomy, compounds, genetics)
# ---------------------------------------------------------------------------


@dataclass
class MINDEXConstraintConfig:
    """Configuration for MINDEX constraint building."""
    db_path: str = ""
    postgres_url: str = ""
    include_scientific_names: bool = True
    include_common_names: bool = True
    include_mindex_ids: bool = True
    include_compounds: bool = True
    include_genetic_ids: bool = True


async def build_mindex_species_index(
    config: Optional[MINDEXConstraintConfig] = None,
) -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes from MINDEX species database.

    Creates separate indexes for different identifier types:
    - mindex_species_scientific: Scientific names (e.g. "Agaricus bisporus")
    - mindex_species_common: Common names (e.g. "Button mushroom")
    - mindex_species_ids: MINDEX IDs (e.g. "MINDEX-FUN-000123")
    - mindex_compounds: Chemical compound names
    - mindex_genetic_ids: GenBank/genetic accession IDs
    """
    config = config or MINDEXConstraintConfig()
    indexes: Dict[str, STATICIndex] = {}

    species_data = await _fetch_mindex_species(config)

    if config.include_scientific_names and species_data.get("scientific_names"):
        indexes["mindex_species_scientific"] = _build_string_index(
            "mindex_species_scientific",
            species_data["scientific_names"],
        )

    if config.include_common_names and species_data.get("common_names"):
        indexes["mindex_species_common"] = _build_string_index(
            "mindex_species_common",
            species_data["common_names"],
        )

    if config.include_mindex_ids and species_data.get("mindex_ids"):
        indexes["mindex_species_ids"] = _build_string_index(
            "mindex_species_ids",
            species_data["mindex_ids"],
        )

    if config.include_compounds and species_data.get("compounds"):
        indexes["mindex_compounds"] = _build_string_index(
            "mindex_compounds",
            species_data["compounds"],
        )

    if config.include_genetic_ids and species_data.get("genetic_ids"):
        indexes["mindex_genetic_ids"] = _build_string_index(
            "mindex_genetic_ids",
            species_data["genetic_ids"],
        )

    logger.info(f"Built {len(indexes)} MINDEX constraint indexes")
    return indexes


async def _fetch_mindex_species(
    config: MINDEXConstraintConfig,
) -> Dict[str, List[str]]:
    """Fetch species data from MINDEX database or API."""
    result: Dict[str, List[str]] = {
        "scientific_names": [],
        "common_names": [],
        "mindex_ids": [],
        "compounds": [],
        "genetic_ids": [],
    }

    # Try SQLite path first
    db_path = config.db_path or os.getenv("MINDEX_DB_PATH", "")
    if db_path and os.path.exists(db_path):
        try:
            import sqlite3

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT scientific_name, canonical_name, common_names, mindex_id "
                "FROM species WHERE scientific_name IS NOT NULL"
            )
            for row in cursor.fetchall():
                sci_name, canonical, common, mid = row
                if sci_name:
                    result["scientific_names"].append(sci_name)
                if canonical:
                    result["scientific_names"].append(canonical)
                if common:
                    for name in common.split(","):
                        name = name.strip()
                        if name:
                            result["common_names"].append(name)
                if mid:
                    result["mindex_ids"].append(mid)

            # Compounds
            try:
                cursor.execute(
                    "SELECT DISTINCT compound_name FROM compounds "
                    "WHERE compound_name IS NOT NULL"
                )
                for (name,) in cursor.fetchall():
                    if name:
                        result["compounds"].append(name)
            except sqlite3.OperationalError:
                pass

            # Genetic IDs
            try:
                cursor.execute(
                    "SELECT DISTINCT accession FROM genetic_data "
                    "WHERE accession IS NOT NULL"
                )
                for (acc,) in cursor.fetchall():
                    if acc:
                        result["genetic_ids"].append(acc)
            except sqlite3.OperationalError:
                pass

            conn.close()
            logger.info(
                f"Loaded MINDEX data from SQLite: "
                f"{len(result['scientific_names'])} species, "
                f"{len(result['common_names'])} common names"
            )
            return result
        except Exception as e:
            logger.warning(f"SQLite MINDEX load failed: {e}")

    # Try PostgreSQL via MINDEX API
    try:
        import httpx

        api_base = config.postgres_url or os.getenv(
            "MINDEX_API_URL", "http://192.168.0.189:8000"
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{api_base}/api/species", params={"limit": 50000})
            if resp.status_code == 200:
                data = resp.json()
                species_list = data if isinstance(data, list) else data.get("species", [])
                for sp in species_list:
                    if sp.get("scientific_name"):
                        result["scientific_names"].append(sp["scientific_name"])
                    if sp.get("common_names"):
                        names = sp["common_names"]
                        if isinstance(names, str):
                            for n in names.split(","):
                                n = n.strip()
                                if n:
                                    result["common_names"].append(n)
                        elif isinstance(names, list):
                            result["common_names"].extend(names)
                    if sp.get("mindex_id"):
                        result["mindex_ids"].append(sp["mindex_id"])
                logger.info(f"Loaded {len(result['scientific_names'])} species from MINDEX API")
    except Exception as e:
        logger.warning(f"MINDEX API fetch failed: {e}")

    return result


# ---------------------------------------------------------------------------
# Domain: TAXONOMY (hierarchical classification across all kingdoms)
# ---------------------------------------------------------------------------


TAXONOMY_RANKS = [
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
]


async def build_taxonomy_index(
    db_path: str = "",
    kingdoms: Optional[List[str]] = None,
) -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for taxonomic classification.

    Creates per-rank constraint indexes plus a hierarchical path index.
    Agnostic to kingdom — works for Fungi, Animalia, Plantae, etc.

    Returns:
        Dict with indexes:
        - taxonomy_kingdoms, taxonomy_phyla, taxonomy_classes, ...
        - taxonomy_paths: Full "Kingdom > Phylum > ... > Species" paths
    """
    kingdoms = kingdoms or ["Fungi", "Animalia", "Plantae", "Protista", "Bacteria"]
    indexes: Dict[str, STATICIndex] = {}

    rank_values: Dict[str, List[str]] = {r: [] for r in TAXONOMY_RANKS}
    paths: List[str] = []

    # Fetch taxonomy from MINDEX
    db = db_path or os.getenv("MINDEX_DB_PATH", "")
    if db and os.path.exists(db):
        try:
            import sqlite3

            conn = sqlite3.connect(db)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT kingdom, phylum, class_name, order_name, family, genus, "
                "species_epithet FROM species WHERE kingdom IS NOT NULL"
            )
            for row in cursor.fetchall():
                path_parts = []
                for i, rank in enumerate(TAXONOMY_RANKS):
                    val = row[i]
                    if val:
                        val = val.strip()
                        if val and val not in rank_values[rank]:
                            rank_values[rank].append(val)
                        path_parts.append(val)
                    else:
                        break
                if path_parts:
                    paths.append(" > ".join(path_parts))
            conn.close()
        except Exception as e:
            logger.warning(f"Taxonomy SQLite load failed: {e}")

    # Add known kingdoms even if DB was empty
    for k in kingdoms:
        if k not in rank_values["kingdom"]:
            rank_values["kingdom"].append(k)

    # Build per-rank indexes
    rank_plural = {
        "kingdom": "kingdoms",
        "phylum": "phyla",
        "class": "classes",
        "order": "orders",
        "family": "families",
        "genus": "genera",
        "species": "species_names",
    }
    for rank, values in rank_values.items():
        if values:
            idx_name = f"taxonomy_{rank_plural.get(rank, rank)}"
            indexes[idx_name] = _build_string_index(idx_name, values)

    if paths:
        indexes["taxonomy_paths"] = _build_string_index("taxonomy_paths", paths)

    logger.info(f"Built {len(indexes)} taxonomy constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: CREP (Common Relevant Environmental Picture)
# ---------------------------------------------------------------------------


async def build_crep_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for CREP data domains.

    Creates constraint indexes for identifiers in each CREP stream:
    - crep_flights: Aircraft callsigns / ICAO codes
    - crep_marine: Vessel MMSI numbers / IMO IDs
    - crep_satellites: NORAD IDs / satellite names
    - crep_weather_stations: WMO station IDs
    - crep_railway: Station codes
    - crep_domains: The CREP domain names themselves
    """
    indexes: Dict[str, STATICIndex] = {}

    # CREP domain identifiers (always available — these are the stream names)
    crep_domains = [
        "flights",
        "marine",
        "satellites",
        "weather",
        "railway",
        "carbon",
        "space_debris",
    ]
    indexes["crep_domains"] = _build_string_index("crep_domains", crep_domains)

    # Try fetching live identifiers from CREP API
    try:
        import httpx

        api_base = os.getenv("CREP_API_URL", "http://192.168.0.187:3000/api/crep")
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Flights — callsigns
            try:
                resp = await client.get(f"{api_base}/flights")
                if resp.status_code == 200:
                    data = resp.json()
                    flights = data if isinstance(data, list) else data.get("flights", [])
                    callsigns = [
                        f.get("callsign", "").strip()
                        for f in flights
                        if f.get("callsign", "").strip()
                    ]
                    if callsigns:
                        indexes["crep_flights"] = _build_string_index(
                            "crep_flights", callsigns
                        )
            except Exception as e:
                logger.debug(f"CREP flights fetch: {e}")

            # Marine — vessel IDs
            try:
                resp = await client.get(f"{api_base}/marine")
                if resp.status_code == 200:
                    data = resp.json()
                    vessels = data if isinstance(data, list) else data.get("vessels", [])
                    vessel_ids = []
                    for v in vessels:
                        mmsi = str(v.get("mmsi", "")).strip()
                        if mmsi:
                            vessel_ids.append(mmsi)
                        name = v.get("name", "").strip()
                        if name:
                            vessel_ids.append(name)
                    if vessel_ids:
                        indexes["crep_marine"] = _build_string_index(
                            "crep_marine", vessel_ids
                        )
            except Exception as e:
                logger.debug(f"CREP marine fetch: {e}")

            # Satellites — NORAD IDs and names
            try:
                resp = await client.get(f"{api_base}/satellites")
                if resp.status_code == 200:
                    data = resp.json()
                    sats = data if isinstance(data, list) else data.get("satellites", [])
                    sat_ids = []
                    for s in sats:
                        norad = str(s.get("norad_id", "")).strip()
                        if norad:
                            sat_ids.append(norad)
                        name = s.get("name", "").strip()
                        if name:
                            sat_ids.append(name)
                    if sat_ids:
                        indexes["crep_satellites"] = _build_string_index(
                            "crep_satellites", sat_ids
                        )
            except Exception as e:
                logger.debug(f"CREP satellites fetch: {e}")

            # Weather stations
            try:
                resp = await client.get(f"{api_base}/weather")
                if resp.status_code == 200:
                    data = resp.json()
                    stations = (
                        data if isinstance(data, list) else data.get("stations", [])
                    )
                    station_ids = [
                        str(s.get("station_id", "")).strip()
                        for s in stations
                        if s.get("station_id")
                    ]
                    if station_ids:
                        indexes["crep_weather_stations"] = _build_string_index(
                            "crep_weather_stations", station_ids
                        )
            except Exception as e:
                logger.debug(f"CREP weather fetch: {e}")

    except Exception as e:
        logger.warning(f"CREP live data fetch failed: {e}")

    logger.info(f"Built {len(indexes)} CREP constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: NLM (Nature Learning Model)
# ---------------------------------------------------------------------------


async def build_nlm_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for NLM data entities.

    - nlm_prediction_types: Valid NLM prediction categories
    - nlm_entity_types: NLM entity classifications
    - nlm_capabilities: NLM capability identifiers
    """
    indexes: Dict[str, STATICIndex] = {}

    # Core NLM prediction types (always available)
    prediction_types = [
        "species_identification",
        "growth_forecast",
        "ecological_analysis",
        "cultivation_recommendation",
        "environmental_assessment",
        "genetic_analysis",
        "compound_prediction",
        "habitat_classification",
        "symbiotic_relationship",
        "toxicity_assessment",
        "nutritional_profile",
        "medicinal_potential",
        "climate_impact",
        "biodiversity_metric",
        "mycelium_network_analysis",
    ]
    indexes["nlm_prediction_types"] = _build_string_index(
        "nlm_prediction_types", prediction_types
    )

    # NLM entity types
    entity_types = [
        "species",
        "genus",
        "family",
        "compound",
        "gene",
        "protein",
        "habitat",
        "substrate",
        "symbiont",
        "observation",
        "experiment",
        "cultivation_protocol",
        "environmental_reading",
        "telemetry_point",
        "network_node",
    ]
    indexes["nlm_entity_types"] = _build_string_index(
        "nlm_entity_types", entity_types
    )

    # NLM capabilities
    capabilities = [
        "identify",
        "classify",
        "predict",
        "analyze",
        "recommend",
        "simulate",
        "translate",
        "synthesize",
        "correlate",
        "forecast",
    ]
    indexes["nlm_capabilities"] = _build_string_index(
        "nlm_capabilities", capabilities
    )

    # Try fetching live NLM model metadata
    try:
        import httpx

        nlm_base = os.getenv("NLM_API_URL", "http://192.168.0.188:8200")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{nlm_base}/health")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("models"):
                    model_ids = [str(m) for m in data["models"] if m]
                    if model_ids:
                        indexes["nlm_model_ids"] = _build_string_index(
                            "nlm_model_ids", model_ids
                        )
    except Exception as e:
        logger.debug(f"NLM API fetch: {e}")

    logger.info(f"Built {len(indexes)} NLM constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: AGENTS (all 117+ MAS agents)
# ---------------------------------------------------------------------------


async def build_agent_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for all MAS agents.

    - agent_ids: All registered agent identifiers
    - agent_capabilities: All known agent capabilities
    - agent_categories: Agent category names
    """
    indexes: Dict[str, STATICIndex] = {}

    # Agent categories (always available from CLAUDE.md registry)
    categories = [
        "corporate",
        "infrastructure",
        "scientific",
        "device",
        "data",
        "integration",
        "financial",
        "security",
        "mycology",
        "earth2",
        "simulation",
        "business",
        "core",
        "custom",
    ]
    indexes["agent_categories"] = _build_string_index(
        "agent_categories", categories
    )

    # Known core agent IDs
    known_agents = [
        "ceo-agent", "cfo-agent", "cto-agent", "coo-agent",
        "legal-agent", "hr-agent", "secretary-agent",
        "sales-agent", "marketing-agent", "project-manager-agent",
        "proxmox-agent", "docker-agent", "network-agent",
        "deployment-agent", "cloudflare-agent",
        "lab-agent", "hypothesis-agent", "simulation-agent",
        "alphafold-agent", "experiment-agent",
        "mycobrain-coordinator", "bme688-agent", "bme690-agent",
        "lora-gateway-agent", "firmware-agent",
        "mindex-agent", "etl-agent", "search-agent",
        "route-monitor-agent",
        "n8n-agent", "supabase-agent", "notion-agent",
        "website-agent", "anthropic-agent",
        "financial-agent", "finance-admin-agent",
        "financial-operations-agent",
        "security-agent", "guardian-agent", "crep-security-agent",
        "mycology-bio-agent", "mycology-knowledge-agent",
        "earth2-orchestrator", "weather-forecast-agent",
        "climate-simulation-agent",
        "mycelium-simulator-agent", "physics-simulator-agent",
        "physicsnemo-agent",
        "orchestrator", "agent-manager", "cluster-manager",
        "opportunity-scout", "wifisense-agent",
        "static-decoding-agent", "grounding-agent",
        "intention-agent", "reflection-agent",
        "gap-agent", "dashboard-agent", "sporebase-agent",
        "digital-twin-agent", "natureos-simulation-agent",
        "network-monitor-agent",
        "corporate-operations-agent", "board-operations-agent",
        "legal-compliance-agent",
    ]
    indexes["agent_ids"] = _build_string_index("agent_ids", known_agents)

    # Common capabilities
    common_caps = [
        "execute", "analyze", "monitor", "report", "predict",
        "classify", "search", "index", "retrieve", "generate",
        "validate", "deploy", "configure", "optimize", "schedule",
        "notify", "alert", "log", "coordinate", "delegate",
        "build_constraint_index", "constrained_decode",
        "constrained_retrieval", "rerank_candidates",
        "species_identification", "taxonomy_lookup",
        "network_monitoring", "device_management",
        "financial_analysis", "security_audit",
        "scientific_experiment", "data_pipeline",
    ]
    indexes["agent_capabilities"] = _build_string_index(
        "agent_capabilities", common_caps
    )

    # Try fetching live registry
    try:
        import httpx

        api_base = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{api_base}/api/registry/agents")
            if resp.status_code == 200:
                data = resp.json()
                agents = data if isinstance(data, list) else data.get("agents", [])
                live_ids = [
                    a.get("agent_id", "").strip()
                    for a in agents
                    if a.get("agent_id", "").strip()
                ]
                if live_ids:
                    # Merge with known
                    all_ids = list(set(known_agents + live_ids))
                    indexes["agent_ids"] = _build_string_index(
                        "agent_ids", all_ids
                    )
                    logger.info(f"Merged {len(live_ids)} live agents into index")
    except Exception as e:
        logger.debug(f"Agent registry fetch: {e}")

    logger.info(f"Built {len(indexes)} agent constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: DEVICES / MYCOBRAIN (sensors, electrodes, devices)
# ---------------------------------------------------------------------------


async def build_device_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for MycoBrain devices and sensors.

    - device_types: Valid device type identifiers
    - device_ids: Known device instance IDs
    - sensor_types: Sensor measurement types
    - mycobrain_modes: MycoBrain compute modes
    - electrode_ids: FCI electrode array identifiers
    - stimulation_types: Valid stimulation method names
    """
    indexes: Dict[str, STATICIndex] = {}

    # Device types
    device_types = [
        "mycobrain", "myconode", "mycotenna", "trufflebot",
        "petraeus", "sporebase", "mushroom1", "alarm",
        "bme688", "bme690", "lora_gateway", "fci_driver",
        "electrode_array", "edge_client",
    ]
    indexes["device_types"] = _build_string_index("device_types", device_types)

    # Sensor reading types
    sensor_types = [
        "temperature", "humidity", "pressure", "co2", "voc",
        "gas_resistance", "altitude", "light", "soil_moisture",
        "ph", "electrical_conductivity", "dissolved_oxygen",
        "air_quality_index", "particulate_matter",
        "mycelium_impedance", "substrate_temperature",
        "fruiting_chamber_humidity", "ambient_noise",
        "vibration", "uv_index",
    ]
    indexes["sensor_types"] = _build_string_index("sensor_types", sensor_types)

    # MycoBrain compute modes
    compute_modes = [
        "graph_solving", "pattern_recognition",
        "optimization", "classification",
        "signal_processing", "anomaly_detection",
        "network_mapping", "stimulus_response",
    ]
    indexes["mycobrain_modes"] = _build_string_index(
        "mycobrain_modes", compute_modes
    )

    # Stimulation types
    stim_types = [
        "electrical", "chemical", "optical", "acoustic",
        "thermal", "mechanical", "electromagnetic",
    ]
    indexes["stimulation_types"] = _build_string_index(
        "stimulation_types", stim_types
    )

    # Electrode IDs (standard 64-electrode array)
    electrode_ids = [f"E{i:03d}" for i in range(64)]
    indexes["electrode_ids"] = _build_string_index("electrode_ids", electrode_ids)

    # Try fetching live device registry
    try:
        import httpx

        api_base = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{api_base}/api/devices")
            if resp.status_code == 200:
                data = resp.json()
                devices = data if isinstance(data, list) else data.get("devices", [])
                live_ids = [
                    d.get("device_id", "").strip()
                    for d in devices
                    if d.get("device_id", "").strip()
                ]
                if live_ids:
                    indexes["device_ids"] = _build_string_index(
                        "device_ids", live_ids
                    )
    except Exception as e:
        logger.debug(f"Device registry fetch: {e}")

    logger.info(f"Built {len(indexes)} device/MycoBrain constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: SIGNALS (bio-signal types, SDR channels, FCI data)
# ---------------------------------------------------------------------------


async def build_signal_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for bio-signal and signal processing domains.

    - signal_types: Valid signal category identifiers
    - sdr_encoding_types: Sparse Distributed Representation encoding schemes
    - fci_channels: FCI recording channel names
    - signal_features: Extractable signal feature names
    """
    indexes: Dict[str, STATICIndex] = {}

    # Signal types from bio/signal processing
    signal_types = [
        "mycelium_electrical", "substrate_impedance",
        "spore_emission", "gas_exchange",
        "bioluminescence", "chemical_gradient",
        "network_propagation", "action_potential",
        "osmotic_pressure", "nutrient_flow",
        "environmental_vibration", "acoustic_emission",
        "thermal_gradient", "humidity_response",
        "light_response", "gravity_response",
    ]
    indexes["signal_types"] = _build_string_index("signal_types", signal_types)

    # SDR encoding types
    sdr_types = [
        "scalar", "category", "datetime", "geospatial",
        "frequency", "amplitude", "phase",
        "spectral_power", "waveform", "binary_hash",
    ]
    indexes["sdr_encoding_types"] = _build_string_index(
        "sdr_encoding_types", sdr_types
    )

    # FCI recording channels (64-channel array, 4 quadrants)
    channels = []
    for quadrant in ["NE", "NW", "SE", "SW"]:
        for ch in range(16):
            channels.append(f"{quadrant}-CH{ch:02d}")
    indexes["fci_channels"] = _build_string_index("fci_channels", channels)

    # Signal features
    features = [
        "amplitude", "frequency", "phase", "power",
        "spectral_density", "peak_count", "rms",
        "zero_crossing_rate", "entropy", "coherence",
        "cross_correlation", "autocorrelation",
        "wavelet_coefficient", "hilbert_transform",
        "spike_rate", "burst_duration",
    ]
    indexes["signal_features"] = _build_string_index(
        "signal_features", features
    )

    logger.info(f"Built {len(indexes)} signal constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: USERS (access-controlled, agnostic user identifiers)
# ---------------------------------------------------------------------------


async def build_user_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for user-related constraints.

    - user_roles: Valid user role identifiers
    - user_permissions: Valid permission strings
    - access_levels: Access level tiers
    """
    indexes: Dict[str, STATICIndex] = {}

    # Roles
    roles = [
        "admin", "operator", "researcher", "viewer",
        "agent", "system", "guest", "developer",
        "data_scientist", "lab_technician",
        "field_researcher", "ceo", "cto", "coo", "cfo",
    ]
    indexes["user_roles"] = _build_string_index("user_roles", roles)

    # Permissions
    permissions = [
        "read", "write", "execute", "admin",
        "deploy", "configure", "monitor",
        "agent_control", "device_control",
        "experiment_run", "data_export",
        "species_edit", "taxonomy_edit",
        "system_config", "security_audit",
        "financial_view", "financial_edit",
    ]
    indexes["user_permissions"] = _build_string_index(
        "user_permissions", permissions
    )

    # Access levels
    access_levels = [
        "public", "internal", "confidential",
        "restricted", "top_secret", "ceo_only",
    ]
    indexes["access_levels"] = _build_string_index(
        "access_levels", access_levels
    )

    # Try fetching live user data from auth system
    try:
        import httpx

        api_base = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{api_base}/api/users")
            if resp.status_code == 200:
                data = resp.json()
                users = data if isinstance(data, list) else data.get("users", [])
                user_ids = [
                    u.get("user_id", "").strip()
                    for u in users
                    if u.get("user_id", "").strip()
                ]
                if user_ids:
                    indexes["user_ids"] = _build_string_index(
                        "user_ids", user_ids
                    )
    except Exception as e:
        logger.debug(f"User registry fetch: {e}")

    logger.info(f"Built {len(indexes)} user constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Master builder — builds ALL domain indexes in one call
# ---------------------------------------------------------------------------


@dataclass
class DomainIndexReport:
    """Report from building all domain constraint indexes."""

    indexes: Dict[str, STATICIndex] = field(default_factory=dict)
    domains_built: List[str] = field(default_factory=list)
    domains_failed: List[str] = field(default_factory=list)
    total_entries: int = 0
    total_states: int = 0
    total_memory_mb: float = 0.0
    build_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_indexes": len(self.indexes),
            "domains_built": self.domains_built,
            "domains_failed": self.domains_failed,
            "total_entries": self.total_entries,
            "total_states": self.total_states,
            "total_memory_mb": round(self.total_memory_mb, 2),
            "build_time_ms": round(self.build_time_ms, 2),
            "indexes": {
                name: idx.to_dict() for name, idx in self.indexes.items()
            },
        }


# Map of domain name → async builder function
DOMAIN_BUILDERS: Dict[str, Callable] = {
    "mindex": build_mindex_species_index,
    "taxonomy": build_taxonomy_index,
    "crep": build_crep_index,
    "nlm": build_nlm_index,
    "agents": build_agent_index,
    "devices": build_device_index,
    "signals": build_signal_index,
    "users": build_user_index,
}


async def build_all_domain_indexes(
    domains: Optional[List[str]] = None,
    mindex_config: Optional[MINDEXConstraintConfig] = None,
) -> DomainIndexReport:
    """
    Build STATIC constraint indexes for all (or selected) MAS data domains.

    This is the master entry point. Runs all domain builders concurrently
    and collects results into a unified report.

    Args:
        domains: Optional list of domain names to build. If None, builds all.
                 Valid: mindex, taxonomy, crep, nlm, agents, devices, signals, users
        mindex_config: Optional MINDEX-specific configuration.

    Returns:
        DomainIndexReport with all built indexes and statistics.
    """
    t0 = time.time()
    report = DomainIndexReport()

    target_domains = domains or list(DOMAIN_BUILDERS.keys())

    async def _run_builder(domain: str) -> Tuple[str, Dict[str, STATICIndex]]:
        builder = DOMAIN_BUILDERS.get(domain)
        if not builder:
            raise ValueError(f"Unknown domain: {domain}")

        if domain == "mindex":
            return domain, await builder(mindex_config)
        elif domain == "taxonomy":
            db = (mindex_config.db_path if mindex_config else "") or ""
            return domain, await builder(db_path=db)
        else:
            return domain, await builder()

    # Run all builders concurrently
    tasks = [_run_builder(d) for d in target_domains]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            domain_name = str(result)
            report.domains_failed.append(domain_name)
            logger.error(f"Domain build failed: {result}")
        else:
            domain_name, domain_indexes = result
            report.domains_built.append(domain_name)
            for idx_name, idx in domain_indexes.items():
                report.indexes[idx_name] = idx
                report.total_entries += idx.num_sequences
                report.total_states += idx.num_states
                report.total_memory_mb += idx.memory_usage_mb()

    report.build_time_ms = (time.time() - t0) * 1000

    logger.info(
        f"Built {len(report.indexes)} total indexes across "
        f"{len(report.domains_built)} domains in {report.build_time_ms:.0f}ms | "
        f"{report.total_states} states | {report.total_memory_mb:.2f} MB"
    )

    return report
