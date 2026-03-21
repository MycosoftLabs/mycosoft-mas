"""
Domain Constraint Builders for STATIC Framework

Universal constraint index layer for the entire Mycosoft ecosystem.
Every entity that MINDEX can hold — every living creature, every AI agent,
every signal stream, every vehicle, every company, every molecule — gets a
STATIC constraint index so LLMs can never hallucinate invalid references.

Core Domains (v1):
- MINDEX: Fungal species, taxonomy, compounds, genetic data
- CREP: Flight callsigns, vessel IDs, satellite designators, weather stations
- NLM: Nature Learning Model entity identifiers, prediction categories
- Taxonomy: Full hierarchical classification (Kingdom → Species)
- Agents: All 117+ agent IDs and capabilities
- Devices: MycoBrain devices, sensors, electrode arrays
- Users: User identifiers for access-controlled generation
- Signals: Bio-signal types, SDR channels, FCI electrode IDs

Universal Domains (v2):
- Biosphere: ALL kingdoms of life — every animal, insect, bird, mammal,
  marine organism, plant, fungus, virus, bacterium, protozoan, archaea.
  Conservation status, ecological roles, trophic levels.
- Environment: 24/7 environmental signal types, measurement units,
  atmospheric/oceanic/terrestrial/space monitoring parameters.
- Infrastructure: AI models, frontier LLMs, robots, vehicles, applications,
  companies, organizations, protocols, services.
- Geospatial: Biomes, ecosystems, habitats, climate zones, ocean zones,
  coordinate systems, administrative regions.
- Observation: Observation methods, data formats, compression algorithms,
  storage tiers, freshness categories, quality metrics.
- Search: MINDEX query types, result types, ranking signals, index
  categories, data pipeline stages.

Created: March 3, 2026
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


from mycosoft_mas.llm.constrained.static_index import (
    IndexConfig,
    STATICIndex,
    build_index_from_strings,
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

    # Gene regions used in DNA sequence queries
    gene_regions = [
        "ITS",
        "ITS1",
        "ITS2",
        "LSU",
        "SSU",
        "28S",
        "18S",
        "5.8S",
        "16S",
        "26S",
        "COX1",
        "COI",
        "COX2",
        "COX3",
        "TEF1",
        "TEF1-alpha",
        "EF1-alpha",
        "RPB1",
        "RPB2",
        "ACT",
        "TUB2",
        "beta-tubulin",
        "CAL",
        "calmodulin",
        "GAPDH",
        "HIS3",
        "MCM7",
        "TOP1",
        "ATP6",
        "NAD1",
        "matK",
        "rbcL",
        "trnL",
        "psbA-trnH",
        "cytb",
        "ND1",
        "ND2",
        "ND4",
        "ND5",
        "12S",
        "D-loop",
        "control_region",
    ]
    indexes["mindex_gene_regions"] = _build_string_index("mindex_gene_regions", gene_regions)

    # Compound classes used in compound search filters
    compound_classes = [
        "Alkaloid",
        "Terpenoid",
        "Polyketide",
        "Peptide",
        "Polysaccharide",
        "Lipid",
        "Phenol",
        "Flavonoid",
        "Steroid",
        "Terpene",
        "Sesquiterpene",
        "Diterpene",
        "Triterpene",
        "Monoterpene",
        "Lactone",
        "Quinone",
        "Coumarin",
        "Xanthone",
        "Anthraquinone",
        "Indole",
        "Beta-glucan",
        "Chitin",
        "Ergosterol",
        "Lovastatin",
        "Psilocybin",
        "Muscarine",
        "Amatoxin",
        "Phallotoxin",
        "Orellanine",
        "Coprine",
        "Ibotenic_acid",
        "Muscimol",
        "Lentinan",
        "Schizophyllan",
        "Grifolan",
        "Pleuran",
        "Ganoderic_acid",
        "Cordycepin",
        "Hericenone",
        "Erinacine",
    ]
    indexes["mindex_compound_classes"] = _build_string_index(
        "mindex_compound_classes", compound_classes
    )

    # Bioactivity types for compound analysis
    bioactivity_types = [
        "antimicrobial",
        "antifungal",
        "antibacterial",
        "antiviral",
        "antitumor",
        "anticancer",
        "cytotoxic",
        "antiproliferative",
        "immunomodulatory",
        "immunostimulant",
        "immunosuppressant",
        "anti-inflammatory",
        "antioxidant",
        "neuroprotective",
        "hepatoprotective",
        "cardioprotective",
        "nephroprotective",
        "hypoglycemic",
        "hypocholesterolemic",
        "antihypertensive",
        "anticoagulant",
        "antithrombotic",
        "prebiotic",
        "nootropic",
        "adaptogenic",
        "anxiolytic",
        "antidepressant",
        "wound_healing",
        "radioprotective",
        "antiallergic",
    ]
    indexes["mindex_bioactivity_types"] = _build_string_index(
        "mindex_bioactivity_types", bioactivity_types
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
                    "SELECT DISTINCT accession FROM genetic_data " "WHERE accession IS NOT NULL"
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

        api_base = config.postgres_url or os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
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
                        indexes["crep_flights"] = _build_string_index("crep_flights", callsigns)
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
                        indexes["crep_marine"] = _build_string_index("crep_marine", vessel_ids)
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
                        indexes["crep_satellites"] = _build_string_index("crep_satellites", sat_ids)
            except Exception as e:
                logger.debug(f"CREP satellites fetch: {e}")

            # Weather stations
            try:
                resp = await client.get(f"{api_base}/weather")
                if resp.status_code == 200:
                    data = resp.json()
                    stations = data if isinstance(data, list) else data.get("stations", [])
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
    indexes["nlm_prediction_types"] = _build_string_index("nlm_prediction_types", prediction_types)

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
    indexes["nlm_entity_types"] = _build_string_index("nlm_entity_types", entity_types)

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
    indexes["nlm_capabilities"] = _build_string_index("nlm_capabilities", capabilities)

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
                        indexes["nlm_model_ids"] = _build_string_index("nlm_model_ids", model_ids)
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
    indexes["agent_categories"] = _build_string_index("agent_categories", categories)

    # Known core agent IDs
    known_agents = [
        "ceo-agent",
        "cfo-agent",
        "cto-agent",
        "coo-agent",
        "legal-agent",
        "hr-agent",
        "secretary-agent",
        "sales-agent",
        "marketing-agent",
        "project-manager-agent",
        "proxmox-agent",
        "docker-agent",
        "network-agent",
        "deployment-agent",
        "cloudflare-agent",
        "lab-agent",
        "hypothesis-agent",
        "simulation-agent",
        "alphafold-agent",
        "experiment-agent",
        "mycobrain-coordinator",
        "bme688-agent",
        "bme690-agent",
        "lora-gateway-agent",
        "firmware-agent",
        "mindex-agent",
        "etl-agent",
        "search-agent",
        "route-monitor-agent",
        "n8n-agent",
        "supabase-agent",
        "notion-agent",
        "website-agent",
        "anthropic-agent",
        "financial-agent",
        "finance-admin-agent",
        "financial-operations-agent",
        "security-agent",
        "guardian-agent",
        "crep-security-agent",
        "mycology-bio-agent",
        "mycology-knowledge-agent",
        "earth2-orchestrator",
        "weather-forecast-agent",
        "climate-simulation-agent",
        "mycelium-simulator-agent",
        "physics-simulator-agent",
        "physicsnemo-agent",
        "orchestrator",
        "agent-manager",
        "cluster-manager",
        "opportunity-scout",
        "wifisense-agent",
        "static-decoding-agent",
        "grounding-agent",
        "intention-agent",
        "reflection-agent",
        "gap-agent",
        "dashboard-agent",
        "sporebase-agent",
        "digital-twin-agent",
        "natureos-simulation-agent",
        "network-monitor-agent",
        "corporate-operations-agent",
        "board-operations-agent",
        "legal-compliance-agent",
    ]
    indexes["agent_ids"] = _build_string_index("agent_ids", known_agents)

    # Common capabilities
    common_caps = [
        "execute",
        "analyze",
        "monitor",
        "report",
        "predict",
        "classify",
        "search",
        "index",
        "retrieve",
        "generate",
        "validate",
        "deploy",
        "configure",
        "optimize",
        "schedule",
        "notify",
        "alert",
        "log",
        "coordinate",
        "delegate",
        "build_constraint_index",
        "constrained_decode",
        "constrained_retrieval",
        "rerank_candidates",
        "species_identification",
        "taxonomy_lookup",
        "network_monitoring",
        "device_management",
        "financial_analysis",
        "security_audit",
        "scientific_experiment",
        "data_pipeline",
    ]
    indexes["agent_capabilities"] = _build_string_index("agent_capabilities", common_caps)

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
                    a.get("agent_id", "").strip() for a in agents if a.get("agent_id", "").strip()
                ]
                if live_ids:
                    # Merge with known
                    all_ids = list(set(known_agents + live_ids))
                    indexes["agent_ids"] = _build_string_index("agent_ids", all_ids)
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
        "mycobrain",
        "myconode",
        "mycotenna",
        "trufflebot",
        "petraeus",
        "sporebase",
        "mushroom1",
        "alarm",
        "bme688",
        "bme690",
        "lora_gateway",
        "fci_driver",
        "electrode_array",
        "edge_client",
    ]
    indexes["device_types"] = _build_string_index("device_types", device_types)

    # Sensor reading types
    sensor_types = [
        "temperature",
        "humidity",
        "pressure",
        "co2",
        "voc",
        "gas_resistance",
        "altitude",
        "light",
        "soil_moisture",
        "ph",
        "electrical_conductivity",
        "dissolved_oxygen",
        "air_quality_index",
        "particulate_matter",
        "mycelium_impedance",
        "substrate_temperature",
        "fruiting_chamber_humidity",
        "ambient_noise",
        "vibration",
        "uv_index",
    ]
    indexes["sensor_types"] = _build_string_index("sensor_types", sensor_types)

    # MycoBrain compute modes
    compute_modes = [
        "graph_solving",
        "pattern_recognition",
        "optimization",
        "classification",
        "signal_processing",
        "anomaly_detection",
        "network_mapping",
        "stimulus_response",
    ]
    indexes["mycobrain_modes"] = _build_string_index("mycobrain_modes", compute_modes)

    # Stimulation types
    stim_types = [
        "electrical",
        "chemical",
        "optical",
        "acoustic",
        "thermal",
        "mechanical",
        "electromagnetic",
    ]
    indexes["stimulation_types"] = _build_string_index("stimulation_types", stim_types)

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
                    indexes["device_ids"] = _build_string_index("device_ids", live_ids)
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
        "mycelium_electrical",
        "substrate_impedance",
        "spore_emission",
        "gas_exchange",
        "bioluminescence",
        "chemical_gradient",
        "network_propagation",
        "action_potential",
        "osmotic_pressure",
        "nutrient_flow",
        "environmental_vibration",
        "acoustic_emission",
        "thermal_gradient",
        "humidity_response",
        "light_response",
        "gravity_response",
    ]
    indexes["signal_types"] = _build_string_index("signal_types", signal_types)

    # SDR encoding types
    sdr_types = [
        "scalar",
        "category",
        "datetime",
        "geospatial",
        "frequency",
        "amplitude",
        "phase",
        "spectral_power",
        "waveform",
        "binary_hash",
    ]
    indexes["sdr_encoding_types"] = _build_string_index("sdr_encoding_types", sdr_types)

    # FCI recording channels (64-channel array, 4 quadrants)
    channels = []
    for quadrant in ["NE", "NW", "SE", "SW"]:
        for ch in range(16):
            channels.append(f"{quadrant}-CH{ch:02d}")
    indexes["fci_channels"] = _build_string_index("fci_channels", channels)

    # Signal features
    features = [
        "amplitude",
        "frequency",
        "phase",
        "power",
        "spectral_density",
        "peak_count",
        "rms",
        "zero_crossing_rate",
        "entropy",
        "coherence",
        "cross_correlation",
        "autocorrelation",
        "wavelet_coefficient",
        "hilbert_transform",
        "spike_rate",
        "burst_duration",
    ]
    indexes["signal_features"] = _build_string_index("signal_features", features)

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
        "admin",
        "operator",
        "researcher",
        "viewer",
        "agent",
        "system",
        "guest",
        "developer",
        "data_scientist",
        "lab_technician",
        "field_researcher",
        "ceo",
        "cto",
        "coo",
        "cfo",
    ]
    indexes["user_roles"] = _build_string_index("user_roles", roles)

    # Permissions
    permissions = [
        "read",
        "write",
        "execute",
        "admin",
        "deploy",
        "configure",
        "monitor",
        "agent_control",
        "device_control",
        "experiment_run",
        "data_export",
        "species_edit",
        "taxonomy_edit",
        "system_config",
        "security_audit",
        "financial_view",
        "financial_edit",
    ]
    indexes["user_permissions"] = _build_string_index("user_permissions", permissions)

    # Access levels
    access_levels = [
        "public",
        "internal",
        "confidential",
        "restricted",
        "top_secret",
        "ceo_only",
    ]
    indexes["access_levels"] = _build_string_index("access_levels", access_levels)

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
                    u.get("user_id", "").strip() for u in users if u.get("user_id", "").strip()
                ]
                if user_ids:
                    indexes["user_ids"] = _build_string_index("user_ids", user_ids)
    except Exception as e:
        logger.debug(f"User registry fetch: {e}")

    logger.info(f"Built {len(indexes)} user constraint indexes")
    return indexes


# ===========================================================================
# UNIVERSAL DOMAINS (v2) — Every entity class that exists
# ===========================================================================


# ---------------------------------------------------------------------------
# Domain: BIOSPHERE (every kingdom of life on Earth)
# ---------------------------------------------------------------------------


async def build_biosphere_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for ALL biological life on Earth.

    This is the species-agnostic, kingdom-agnostic universal biological
    constraint layer. Every animal, insect, bird, mammal, marine organism,
    plant, fungus, virus, bacterium, protozoan, and archaeon must be
    addressable through constrained generation.

    Indexes:
    - bio_kingdoms: All domains/kingdoms of life
    - bio_animalia_classes: Major animal classes (Mammalia, Aves, etc.)
    - bio_phyla: All recognized phyla across kingdoms
    - bio_conservation_status: IUCN and custom conservation statuses
    - bio_ecological_roles: Ecological function identifiers
    - bio_trophic_levels: Trophic level classifications
    - bio_reproduction_types: Reproductive strategy identifiers
    - bio_habitat_types: Habitat classification for organisms
    - bio_organism_forms: Life form categories across all kingdoms
    """
    indexes: Dict[str, STATICIndex] = {}

    # All domains and kingdoms of life (3-domain / 7-kingdom merged)
    kingdoms = [
        # Domains of life
        "Bacteria",
        "Archaea",
        "Eukarya",
        # Traditional kingdoms
        "Animalia",
        "Plantae",
        "Fungi",
        "Protista",
        "Chromista",
        "Protozoa",
        # Acellular
        "Virus",
        "Viroid",
        "Prion",
    ]
    indexes["bio_kingdoms"] = _build_string_index("bio_kingdoms", kingdoms)

    # All major phyla across ALL kingdoms
    phyla = [
        # Animalia
        "Chordata",
        "Arthropoda",
        "Mollusca",
        "Annelida",
        "Cnidaria",
        "Echinodermata",
        "Platyhelminthes",
        "Nematoda",
        "Porifera",
        "Bryozoa",
        "Rotifera",
        "Tardigrada",
        "Onychophora",
        "Hemichordata",
        "Ctenophora",
        "Chaetognatha",
        "Nemertea",
        "Brachiopoda",
        "Sipuncula",
        "Priapulida",
        "Loricifera",
        # Plantae
        "Tracheophyta",
        "Bryophyta",
        "Marchantiophyta",
        "Anthocerotophyta",
        "Chlorophyta",
        "Charophyta",
        "Rhodophyta",
        "Glaucophyta",
        # Fungi
        "Ascomycota",
        "Basidiomycota",
        "Zygomycota",
        "Chytridiomycota",
        "Glomeromycota",
        "Microsporidia",
        "Blastocladiomycota",
        "Neocallimastigomycota",
        "Cryptomycota",
        "Mucoromycota",
        # Protista / Chromista
        "Apicomplexa",
        "Ciliophora",
        "Euglenozoa",
        "Amoebozoa",
        "Foraminifera",
        "Radiolaria",
        "Dinoflagellata",
        "Bacillariophyta",
        "Phaeophyta",
        "Oomycota",
        "Haptophyta",
        "Cryptophyta",
        # Bacteria
        "Proteobacteria",
        "Firmicutes",
        "Actinobacteria",
        "Bacteroidetes",
        "Cyanobacteria",
        "Spirochaetes",
        "Tenericutes",
        "Fusobacteria",
        "Acidobacteria",
        "Verrucomicrobia",
        "Planctomycetes",
        "Chlamydiae",
        "Deinococcus-Thermus",
        "Chloroflexi",
        # Archaea
        "Euryarchaeota",
        "Crenarchaeota",
        "Thaumarchaeota",
        "Korarchaeota",
        "Nanoarchaeota",
        "Asgardarchaeota",
        # Viruses (Baltimore groups as pseudo-phyla)
        "dsDNA_viruses",
        "ssDNA_viruses",
        "dsRNA_viruses",
        "ssRNA_positive",
        "ssRNA_negative",
        "ssRNA_RT",
        "dsDNA_RT",
    ]
    indexes["bio_phyla"] = _build_string_index("bio_phyla", phyla)

    # Major animal classes (for constrained animal identification)
    animalia_classes = [
        # Mammals
        "Mammalia",
        # Birds
        "Aves",
        # Reptiles
        "Reptilia",
        # Amphibians
        "Amphibia",
        # Fish
        "Actinopterygii",
        "Chondrichthyes",
        "Sarcopterygii",
        "Myxini",
        "Hyperoartia",
        # Insects & Arthropods
        "Insecta",
        "Arachnida",
        "Crustacea",
        "Chilopoda",
        "Diplopoda",
        "Merostomata",
        "Pycnogonida",
        "Remipedia",
        # Mollusks
        "Gastropoda",
        "Bivalvia",
        "Cephalopoda",
        "Polyplacophora",
        # Marine invertebrates
        "Anthozoa",
        "Scyphozoa",
        "Hydrozoa",
        "Echinoidea",
        "Asteroidea",
        "Holothuroidea",
        "Ophiuroidea",
        "Crinoidea",
        # Worms
        "Polychaeta",
        "Oligochaeta",
        "Hirudinea",
        # Microscopic animals
        "Bdelloidea",
        "Eutardigrada",
    ]
    indexes["bio_animalia_classes"] = _build_string_index("bio_animalia_classes", animalia_classes)

    # Organism life form categories (species-agnostic classification)
    organism_forms = [
        # By size/complexity
        "microbe",
        "unicellular",
        "multicellular",
        "colonial",
        # Animals
        "mammal",
        "bird",
        "reptile",
        "amphibian",
        "fish",
        "insect",
        "arachnid",
        "crustacean",
        "mollusk",
        "coral",
        "jellyfish",
        "sponge",
        "worm",
        "echinoderm",
        # Marine
        "marine_mammal",
        "shark",
        "ray",
        "bony_fish",
        "cephalopod",
        "sea_turtle",
        "marine_invertebrate",
        "plankton",
        "nekton",
        "benthos",
        # Plants
        "tree",
        "shrub",
        "herb",
        "grass",
        "vine",
        "fern",
        "moss",
        "liverwort",
        "algae",
        "seaweed",
        "lichen",
        "succulent",
        "epiphyte",
        "aquatic_plant",
        # Fungi
        "mushroom",
        "mold",
        "yeast",
        "bracket_fungus",
        "mycorrhiza",
        "endophyte",
        "saprotroph",
        # Microorganisms
        "bacterium",
        "archaeon",
        "protozoan",
        "virus",
        "viroid",
        "prion",
        "phage",
        # Ecological forms
        "parasite",
        "symbiont",
        "commensal",
        "decomposer",
        "producer",
        "consumer",
        "predator",
        "prey",
        "pollinator",
        "seed_disperser",
        "nitrogen_fixer",
    ]
    indexes["bio_organism_forms"] = _build_string_index("bio_organism_forms", organism_forms)

    # IUCN Conservation statuses
    conservation_status = [
        "NE",
        "DD",
        "LC",
        "NT",
        "VU",
        "EN",
        "CR",
        "EW",
        "EX",
        "not_evaluated",
        "data_deficient",
        "least_concern",
        "near_threatened",
        "vulnerable",
        "endangered",
        "critically_endangered",
        "extinct_in_wild",
        "extinct",
        "CITES_I",
        "CITES_II",
        "CITES_III",
        "protected",
        "threatened",
        "invasive",
        "endemic",
    ]
    indexes["bio_conservation_status"] = _build_string_index(
        "bio_conservation_status", conservation_status
    )

    # Ecological roles
    ecological_roles = [
        "autotroph",
        "heterotroph",
        "mixotroph",
        "producer",
        "primary_consumer",
        "secondary_consumer",
        "tertiary_consumer",
        "apex_predator",
        "decomposer",
        "detritivore",
        "herbivore",
        "carnivore",
        "omnivore",
        "parasitoid",
        "hyperparasite",
        "mutualist",
        "pollinator",
        "seed_disperser",
        "nitrogen_fixer",
        "mycorrhizal_partner",
        "biofilm_former",
        "bioluminescent",
        "keystone_species",
        "indicator_species",
        "pioneer_species",
        "foundation_species",
        "umbrella_species",
        "flagship_species",
        "ecosystem_engineer",
        "invasive_species",
    ]
    indexes["bio_ecological_roles"] = _build_string_index("bio_ecological_roles", ecological_roles)

    # Trophic levels
    trophic_levels = [
        "T0_decomposer",
        "T1_producer",
        "T2_primary_consumer",
        "T3_secondary_consumer",
        "T4_tertiary_consumer",
        "T5_apex_predator",
        "detrital",
    ]
    indexes["bio_trophic_levels"] = _build_string_index("bio_trophic_levels", trophic_levels)

    logger.info(f"Built {len(indexes)} biosphere constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: ENVIRONMENT (24/7 global environmental monitoring parameters)
# ---------------------------------------------------------------------------


async def build_environment_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for 24/7 environmental monitoring.

    Every environmental signal logged, analyzed, compressed, stored,
    and referenced by MINDEX needs constrained identifiers.

    Indexes:
    - env_atmospheric: Atmospheric measurement parameters
    - env_oceanic: Ocean monitoring parameters
    - env_terrestrial: Land/soil monitoring parameters
    - env_space: Space weather and cosmic monitoring
    - env_biological: Biological monitoring signals
    - env_units: Valid measurement units across all domains
    - env_data_quality: Data quality and freshness indicators
    - env_temporal: Time-series and observation window identifiers
    """
    indexes: Dict[str, STATICIndex] = {}

    # Atmospheric parameters
    atmospheric = [
        "temperature",
        "humidity",
        "pressure",
        "wind_speed",
        "wind_direction",
        "precipitation",
        "precipitation_rate",
        "dew_point",
        "cloud_cover",
        "cloud_base_height",
        "visibility",
        "uv_index",
        "solar_radiation",
        "photosynthetically_active_radiation",
        "net_radiation",
        "air_quality_index",
        "pm2_5",
        "pm10",
        "ozone_concentration",
        "co2_concentration",
        "methane_concentration",
        "nox_concentration",
        "sulfur_dioxide",
        "carbon_monoxide",
        "volatile_organic_compounds",
        "pollen_count",
        "lightning_density",
        "atmospheric_stability",
        "boundary_layer_height",
        "aerosol_optical_depth",
        "total_column_water_vapor",
        "convective_available_potential_energy",
    ]
    indexes["env_atmospheric"] = _build_string_index("env_atmospheric", atmospheric)

    # Oceanic parameters
    oceanic = [
        "sea_surface_temperature",
        "sea_surface_salinity",
        "ocean_current_speed",
        "ocean_current_direction",
        "wave_height",
        "wave_period",
        "wave_direction",
        "tidal_level",
        "tidal_range",
        "storm_surge",
        "ocean_ph",
        "dissolved_oxygen",
        "chlorophyll_a",
        "turbidity",
        "sea_ice_extent",
        "sea_ice_thickness",
        "sea_level_anomaly",
        "ocean_heat_content",
        "mixed_layer_depth",
        "thermocline_depth",
        "primary_productivity",
        "phytoplankton_biomass",
        "coral_bleaching_index",
        "harmful_algal_bloom",
        "deep_ocean_temperature",
        "abyssal_pressure",
    ]
    indexes["env_oceanic"] = _build_string_index("env_oceanic", oceanic)

    # Terrestrial parameters
    terrestrial = [
        "soil_moisture",
        "soil_temperature",
        "soil_ph",
        "groundwater_level",
        "river_discharge",
        "stream_flow",
        "lake_level",
        "reservoir_storage",
        "snow_depth",
        "snow_water_equivalent",
        "frost_depth",
        "permafrost_temperature",
        "land_surface_temperature",
        "vegetation_index_ndvi",
        "leaf_area_index",
        "evapotranspiration",
        "gross_primary_productivity",
        "net_ecosystem_exchange",
        "seismic_activity",
        "volcanic_activity",
        "landslide_risk",
        "flood_level",
        "fire_weather_index",
        "drought_index",
        "erosion_rate",
        "sediment_transport",
    ]
    indexes["env_terrestrial"] = _build_string_index("env_terrestrial", terrestrial)

    # Space weather and cosmic parameters
    space = [
        "solar_wind_speed",
        "solar_wind_density",
        "interplanetary_magnetic_field",
        "solar_flux_f10_7",
        "sunspot_number",
        "solar_flare_class",
        "geomagnetic_kp_index",
        "geomagnetic_dst_index",
        "auroral_electrojet",
        "cosmic_ray_flux",
        "proton_flux",
        "electron_flux",
        "magnetopause_standoff",
        "radiation_belt_flux",
        "total_electron_content",
        "scintillation_index",
        "galactic_cosmic_ray_intensity",
        "coronal_mass_ejection_speed",
    ]
    indexes["env_space"] = _build_string_index("env_space", space)

    # Biological monitoring parameters
    biological = [
        "species_count",
        "population_density",
        "biodiversity_index_shannon",
        "biodiversity_index_simpson",
        "migration_event",
        "breeding_season_start",
        "phenological_stage",
        "bloom_detection",
        "invasive_species_detection",
        "disease_outbreak",
        "antibiotic_resistance_level",
        "zoonotic_risk",
        "pollinator_activity",
        "bird_call_frequency",
        "bat_echolocation_activity",
        "whale_song_detection",
        "fish_stock_estimate",
        "coral_health_index",
        "forest_canopy_density",
        "deforestation_rate",
        "wetland_extent",
        "mangrove_coverage",
        "microbiome_diversity",
        "soil_organism_activity",
    ]
    indexes["env_biological"] = _build_string_index("env_biological", biological)

    # Measurement units (universal)
    units = [
        # Temperature
        "celsius",
        "fahrenheit",
        "kelvin",
        # Pressure
        "hPa",
        "mbar",
        "mmHg",
        "atm",
        "psi",
        "Pa",
        "kPa",
        # Speed
        "m_s",
        "km_h",
        "mph",
        "knots",
        "ft_s",
        # Distance / Depth
        "meters",
        "kilometers",
        "miles",
        "nautical_miles",
        "feet",
        "inches",
        "centimeters",
        "millimeters",
        "micrometers",
        "nanometers",
        "fathoms",
        # Mass / Concentration
        "kg",
        "g",
        "mg",
        "ug",
        "ng",
        "ppm",
        "ppb",
        "ppt",
        "mg_L",
        "ug_L",
        "mol_L",
        "mmol_L",
        # Area / Volume
        "m2",
        "km2",
        "ha",
        "acres",
        "L",
        "mL",
        "m3",
        # Radiation / Energy
        "W_m2",
        "J",
        "kJ",
        "MJ",
        "eV",
        "keV",
        "MeV",
        "sfu",
        "dB",
        "dBm",
        # Time
        "seconds",
        "minutes",
        "hours",
        "days",
        # Biological
        "cells_mL",
        "cfu_mL",
        "individuals_km2",
        "species_per_sample",
        "nats",
        "bits",
        # Dimensionless
        "percent",
        "fraction",
        "index",
        "ratio",
        "count",
        "boolean",
    ]
    indexes["env_units"] = _build_string_index("env_units", units)

    # Data quality and freshness
    data_quality = [
        # Freshness categories
        "realtime",
        "near_realtime",
        "hourly",
        "daily",
        "weekly",
        "monthly",
        "seasonal",
        "annual",
        "historical",
        # Quality flags
        "validated",
        "provisional",
        "estimated",
        "interpolated",
        "modeled",
        "satellite_derived",
        "in_situ",
        "reanalysis",
        "quality_controlled",
        "raw",
        "calibrated",
        "suspect",
        "erroneous",
        "missing",
        "gap_filled",
    ]
    indexes["env_data_quality"] = _build_string_index("env_data_quality", data_quality)

    # Temporal identifiers
    temporal = [
        "observation",
        "forecast_1h",
        "forecast_3h",
        "forecast_6h",
        "forecast_12h",
        "forecast_24h",
        "forecast_48h",
        "forecast_72h",
        "forecast_5d",
        "forecast_7d",
        "forecast_10d",
        "forecast_14d",
        "forecast_30d",
        "forecast_seasonal",
        "forecast_annual",
        "climatology",
        "anomaly",
        "trend",
        "running_mean",
        "rolling_24h",
        "rolling_7d",
        "rolling_30d",
        "peak",
        "trough",
        "threshold_exceedance",
        "onset",
        "cessation",
        "duration",
        "recurrence_interval",
    ]
    indexes["env_temporal"] = _build_string_index("env_temporal", temporal)

    logger.info(f"Built {len(indexes)} environment constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: INFRASTRUCTURE (AI, robots, vehicles, apps, companies, protocols)
# ---------------------------------------------------------------------------


async def build_infrastructure_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for all artificial/organizational entities.

    Every AI model, robot, vehicle, application, company, organization,
    and protocol that MINDEX tracks needs constrained identifiers.

    Indexes:
    - infra_ai_model_types: AI/ML model categories (LLM, AGI, ASI, etc.)
    - infra_frontier_models: Known frontier model families
    - infra_robot_types: Robot and autonomous system types
    - infra_vehicle_types: Vehicle classification
    - infra_app_types: Application and service categories
    - infra_org_types: Organization and entity type classifications
    - infra_protocols: Communication and data protocols
    - infra_compute_tiers: Compute and infrastructure tiers
    """
    indexes: Dict[str, STATICIndex] = {}

    # AI/ML model types and capability tiers
    ai_model_types = [
        # Capability tiers
        "narrow_ai",
        "general_ai",
        "artificial_general_intelligence",
        "artificial_superintelligence",
        "frontier_model",
        "foundation_model",
        "large_language_model",
        # Architecture types
        "transformer",
        "diffusion",
        "gan",
        "vae",
        "rnn",
        "cnn",
        "graph_neural_network",
        "reinforcement_learning",
        "neuro_symbolic",
        "mixture_of_experts",
        "state_space_model",
        "multimodal_model",
        "vision_language_model",
        "world_model",
        "embodied_agent",
        # Function types
        "text_generation",
        "image_generation",
        "video_generation",
        "audio_generation",
        "code_generation",
        "reasoning",
        "planning",
        "tool_use",
        "retrieval_augmented",
        "classification",
        "regression",
        "clustering",
        "anomaly_detection",
        "recommendation",
        "translation",
        "speech_recognition",
        "speech_synthesis",
        "object_detection",
        "segmentation",
        "protein_folding",
        "molecular_design",
        "weather_prediction",
        "climate_modeling",
        # Deployment
        "cloud_hosted",
        "edge_deployed",
        "on_device",
        "federated",
        "distilled",
        "quantized",
        "fine_tuned",
    ]
    indexes["infra_ai_model_types"] = _build_string_index("infra_ai_model_types", ai_model_types)

    # Known frontier model families (for constrained model references)
    frontier_models = [
        # Anthropic
        "claude_opus",
        "claude_sonnet",
        "claude_haiku",
        "claude_4",
        "claude_4_5",
        "claude_4_6",
        # OpenAI
        "gpt_4",
        "gpt_4o",
        "gpt_4_turbo",
        "gpt_5",
        "o1",
        "o1_mini",
        "o1_pro",
        "o3",
        "o3_mini",
        # Google
        "gemini_ultra",
        "gemini_pro",
        "gemini_nano",
        "gemini_2",
        "gemini_2_5",
        # Meta
        "llama_3",
        "llama_3_1",
        "llama_4",
        # Mistral
        "mistral_large",
        "mistral_medium",
        "mistral_small",
        "mixtral",
        "codestral",
        # xAI
        "grok_2",
        "grok_3",
        # NVIDIA
        "nemotron",
        "physicsnemo",
        # Open source
        "deepseek_v3",
        "deepseek_r1",
        "qwen_2_5",
        "yi_large",
        "command_r",
        "command_r_plus",
        # Mycosoft
        "myca",
        "nlm",
        "natureos_model",
    ]
    indexes["infra_frontier_models"] = _build_string_index("infra_frontier_models", frontier_models)

    # Robot and autonomous system types
    robot_types = [
        "humanoid",
        "quadruped",
        "hexapod",
        "wheeled",
        "tracked",
        "aerial_drone",
        "underwater_rov",
        "underwater_auv",
        "surface_vessel_autonomous",
        "manipulator_arm",
        "mobile_manipulator",
        "swarm_robot",
        "soft_robot",
        "bio_hybrid_robot",
        "nanobot",
        "microbot",
        "surgical_robot",
        "warehouse_robot",
        "delivery_robot",
        "agricultural_robot",
        "forestry_robot",
        "inspection_robot",
        "search_rescue_robot",
        "space_rover",
        "satellite_servicer",
        "companion_robot",
        "telepresence_robot",
        # Mycosoft specific
        "trufflebot",
        "mycobot",
        "sporebot",
    ]
    indexes["infra_robot_types"] = _build_string_index("infra_robot_types", robot_types)

    # Vehicle classifications
    vehicle_types = [
        # Air
        "fixed_wing",
        "rotary_wing",
        "tiltrotor",
        "lighter_than_air",
        "glider",
        "uav",
        "evtol",
        "commercial_aircraft",
        "military_aircraft",
        "general_aviation",
        "space_launch_vehicle",
        # Ground
        "automobile",
        "truck",
        "bus",
        "motorcycle",
        "bicycle",
        "train",
        "tram",
        "subway",
        "autonomous_vehicle",
        "electric_vehicle",
        # Water
        "cargo_ship",
        "tanker",
        "container_ship",
        "cruise_ship",
        "ferry",
        "fishing_vessel",
        "sailboat",
        "motorboat",
        "submarine",
        "research_vessel",
        "icebreaker",
        # Space
        "satellite",
        "space_station",
        "space_probe",
        "crewed_spacecraft",
        "cargo_spacecraft",
        "space_debris",
    ]
    indexes["infra_vehicle_types"] = _build_string_index("infra_vehicle_types", vehicle_types)

    # Application and service types
    app_types = [
        "web_application",
        "mobile_application",
        "desktop_application",
        "api_service",
        "microservice",
        "serverless_function",
        "database",
        "cache",
        "message_queue",
        "event_stream",
        "monitoring_service",
        "logging_service",
        "alerting_service",
        "authentication_service",
        "authorization_service",
        "search_engine",
        "recommendation_engine",
        "data_pipeline",
        "etl_service",
        "ml_pipeline",
        "ci_cd_pipeline",
        "container_orchestrator",
        "load_balancer",
        "cdn",
        "dns_service",
        "iot_platform",
        "edge_computing_node",
        "blockchain_node",
        "smart_contract",
        "digital_twin",
        "simulation_engine",
    ]
    indexes["infra_app_types"] = _build_string_index("infra_app_types", app_types)

    # Organization and entity types
    org_types = [
        "corporation",
        "startup",
        "nonprofit",
        "government_agency",
        "military_organization",
        "university",
        "research_institute",
        "hospital",
        "school",
        "museum",
        "library",
        "international_organization",
        "ngo",
        "cooperative",
        "foundation",
        "trust",
        "consortium",
        "joint_venture",
        "subsidiary",
        "regulatory_body",
        "standards_organization",
        "open_source_project",
        "community",
        "ai_lab",
        "national_lab",
        "space_agency",
        "weather_service",
        "conservation_organization",
        "individual",
        "family",
        "household",
    ]
    indexes["infra_org_types"] = _build_string_index("infra_org_types", org_types)

    # Communication and data protocols
    protocols = [
        # Network
        "http",
        "https",
        "websocket",
        "grpc",
        "mqtt",
        "amqp",
        "coap",
        "lorawan",
        "zigbee",
        "bluetooth",
        "bluetooth_le",
        "wifi",
        "ethernet",
        "tcp",
        "udp",
        "quic",
        "ipv4",
        "ipv6",
        # Data formats
        "json",
        "protobuf",
        "avro",
        "parquet",
        "arrow",
        "msgpack",
        "cbor",
        "xml",
        "csv",
        "hdf5",
        "netcdf",
        "geojson",
        "geopackage",
        "shapefile",
        # Scientific / Bio
        "fasta",
        "fastq",
        "bam",
        "vcf",
        "pdb",
        "mmcif",
        "newick",
        "nexus",
        "phyloxml",
        # Streaming
        "kafka",
        "nats",
        "redis_streams",
        "sse",
        "rtmp",
        "hls",
        "webrtc",
        # IoT
        "modbus",
        "opcua",
        "bacnet",
        "canbus",
    ]
    indexes["infra_protocols"] = _build_string_index("infra_protocols", protocols)

    logger.info(f"Built {len(indexes)} infrastructure constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: GEOSPATIAL (biomes, ecosystems, habitats, climate zones)
# ---------------------------------------------------------------------------


async def build_geospatial_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for geospatial and ecological classification.

    Every geographic entity that MINDEX references needs constrained
    identifiers — biomes, ecosystems, climate zones, ocean zones, etc.

    Indexes:
    - geo_biomes: Major terrestrial and aquatic biome types
    - geo_ecosystems: Ecosystem classification
    - geo_habitats: Habitat types for organism placement
    - geo_climate_zones: Climate zone identifiers
    - geo_ocean_zones: Ocean depth and region zones
    - geo_coordinate_systems: Valid coordinate reference systems
    - geo_admin_levels: Administrative boundary levels
    """
    indexes: Dict[str, STATICIndex] = {}

    # WWF terrestrial and aquatic biomes
    biomes = [
        # Terrestrial
        "tropical_moist_broadleaf",
        "tropical_dry_broadleaf",
        "tropical_coniferous",
        "temperate_broadleaf_mixed",
        "temperate_coniferous",
        "boreal_taiga",
        "tropical_grassland_savanna",
        "temperate_grassland",
        "flooded_grassland",
        "montane_grassland",
        "tundra",
        "mediterranean",
        "desert_xeric_shrubland",
        "mangrove",
        # Freshwater
        "large_river",
        "small_river",
        "large_lake",
        "small_lake",
        "wetland",
        "xeric_basin",
        "endorheic_basin",
        "floodplain",
        # Marine
        "polar_sea",
        "temperate_shelf",
        "temperate_upwelling",
        "tropical_upwelling",
        "tropical_coral",
        "pelagic_open_ocean",
        "deep_sea",
        "hydrothermal_vent",
        "cold_seep",
        "continental_shelf",
        "abyssal_plain",
        "ocean_trench",
        "seamount",
        "mid_ocean_ridge",
        # Transitional
        "estuary",
        "intertidal",
        "salt_marsh",
        "seagrass_bed",
        "kelp_forest",
        "coastal_dune",
        "riparian",
        "cave_subterranean",
    ]
    indexes["geo_biomes"] = _build_string_index("geo_biomes", biomes)

    # Climate zones (Koppen-Geiger)
    climate_zones = [
        "Af",
        "Am",
        "Aw",
        "As",  # Tropical
        "BWh",
        "BWk",
        "BSh",
        "BSk",  # Arid
        "Csa",
        "Csb",
        "Csc",  # Temperate dry summer
        "Cwa",
        "Cwb",
        "Cwc",  # Temperate dry winter
        "Cfa",
        "Cfb",
        "Cfc",  # Temperate no dry season
        "Dsa",
        "Dsb",
        "Dsc",
        "Dsd",  # Continental dry summer
        "Dwa",
        "Dwb",
        "Dwc",
        "Dwd",  # Continental dry winter
        "Dfa",
        "Dfb",
        "Dfc",
        "Dfd",  # Continental no dry season
        "ET",
        "EF",  # Polar
        "tropical",
        "arid",
        "temperate",
        "continental",
        "polar",
        "equatorial",
        "subtropical",
        "subarctic",
        "alpine",
        "maritime",
        "monsoon",
        "steppe",
        "tundra_climate",
    ]
    indexes["geo_climate_zones"] = _build_string_index("geo_climate_zones", climate_zones)

    # Ocean zones
    ocean_zones = [
        # Depth zones
        "epipelagic",
        "mesopelagic",
        "bathypelagic",
        "abyssopelagic",
        "hadopelagic",
        # Benthic zones
        "supralittoral",
        "intertidal_zone",
        "sublittoral",
        "bathyal",
        "abyssal",
        "hadal",
        # Ocean regions
        "pacific",
        "atlantic",
        "indian",
        "southern_ocean",
        "arctic_ocean",
        "mediterranean_sea",
        "caribbean_sea",
        "south_china_sea",
        "bering_sea",
        # Features
        "continental_margin",
        "abyssal_plain",
        "mid_ocean_ridge",
        "ocean_trench",
        "seamount",
        "guyot",
        "coral_reef",
        "atoll",
        "barrier_reef",
        "fringing_reef",
    ]
    indexes["geo_ocean_zones"] = _build_string_index("geo_ocean_zones", ocean_zones)

    # Habitat types (IUCN habitat classification)
    habitats = [
        "forest",
        "savanna",
        "shrubland",
        "grassland",
        "wetland_inland",
        "rocky_areas",
        "caves_subterranean",
        "desert",
        "marine_neritic",
        "marine_oceanic",
        "marine_deep_benthic",
        "marine_intertidal",
        "marine_coastal_supratidal",
        "artificial_terrestrial",
        "artificial_aquatic",
        "introduced_vegetation",
        "urban",
        "suburban",
        "rural",
        "agricultural",
        "plantation",
        "pasture",
        "arable_land",
        "garden",
        "park",
        "cemetery",
        "mine",
        "quarry",
        "landfill",
    ]
    indexes["geo_habitats"] = _build_string_index("geo_habitats", habitats)

    logger.info(f"Built {len(indexes)} geospatial constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: OBSERVATION (data lifecycle — formats, compression, storage)
# ---------------------------------------------------------------------------


async def build_observation_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for the observation and data lifecycle.

    Every piece of data flowing through MINDEX has metadata about how
    it was collected, formatted, compressed, stored, and queried.

    Indexes:
    - obs_methods: Observation and measurement methods
    - obs_data_formats: Data serialization and file formats
    - obs_compression: Compression algorithms and strategies
    - obs_storage_tiers: Storage tier classifications
    - obs_pipeline_stages: Data pipeline stage identifiers
    - obs_quality_metrics: Data quality metric names
    """
    indexes: Dict[str, STATICIndex] = {}

    # Observation methods
    methods = [
        # Remote sensing
        "satellite_optical",
        "satellite_radar",
        "satellite_lidar",
        "aerial_survey",
        "drone_survey",
        "photogrammetry",
        # In-situ
        "weather_station",
        "buoy",
        "tide_gauge",
        "seismometer",
        "rain_gauge",
        "radiosonde",
        "dropsonde",
        "argo_float",
        "glider",
        "mooring",
        # Biological
        "field_observation",
        "camera_trap",
        "acoustic_monitoring",
        "edna_sampling",
        "transect_survey",
        "point_count",
        "mark_recapture",
        "telemetry_tracking",
        "citizen_science",
        "microscopy",
        "spectroscopy",
        "chromatography",
        "flow_cytometry",
        "electrophoresis",
        "pcr",
        "dna_sequencing",
        "rna_sequencing",
        "proteomics",
        "metabolomics",
        "metagenomics",
        # IoT / Automated
        "iot_sensor",
        "edge_device",
        "scada",
        "smart_meter",
        "traffic_sensor",
        "air_quality_monitor",
        # AI-assisted
        "computer_vision",
        "nlp_extraction",
        "anomaly_detector",
        "classification_model",
        "regression_model",
    ]
    indexes["obs_methods"] = _build_string_index("obs_methods", methods)

    # Data formats
    data_formats = [
        # Structured
        "json",
        "jsonl",
        "csv",
        "tsv",
        "parquet",
        "avro",
        "orc",
        "protobuf",
        "msgpack",
        "cbor",
        "arrow",
        "feather",
        # Scientific
        "hdf5",
        "netcdf",
        "zarr",
        "grib",
        "bufr",
        "fits",
        "dicom",
        "nifti",
        # Geospatial
        "geojson",
        "geotiff",
        "shapefile",
        "geopackage",
        "kml",
        "wkt",
        "wkb",
        "cog",
        # Biological
        "fasta",
        "fastq",
        "bam",
        "sam",
        "vcf",
        "gff",
        "bed",
        "pdb",
        "mmcif",
        "sdf",
        "mol2",
        "newick",
        "nexus",
        "phyloxml",
        # Media
        "png",
        "jpeg",
        "tiff",
        "webp",
        "svg",
        "mp3",
        "wav",
        "flac",
        "ogg",
        "mp4",
        "webm",
        "mkv",
        # Document
        "pdf",
        "markdown",
        "latex",
        "html",
        "xml",
        # Database
        "sqlite",
        "postgresql_dump",
        "mongodb_bson",
    ]
    indexes["obs_data_formats"] = _build_string_index("obs_data_formats", data_formats)

    # Compression algorithms
    compression = [
        "none",
        "gzip",
        "bzip2",
        "xz",
        "lz4",
        "zstd",
        "snappy",
        "lzo",
        "brotli",
        "deflate",
        "delta_encoding",
        "run_length_encoding",
        "dictionary_encoding",
        "bit_packing",
        "gorilla_compression",
        "chimp_compression",
        "simple8b",
        "pfor",
        "varint",
        "blosc",
        "fpzip",
        "sz",
        "zfp",
        "lossy_jpeg",
        "lossy_quantization",
        "static_csr_compression",  # Our own STATIC sparse compression
    ]
    indexes["obs_compression"] = _build_string_index("obs_compression", compression)

    # Storage tiers
    storage_tiers = [
        "hot",
        "warm",
        "cold",
        "archive",
        "deep_archive",
        "in_memory",
        "ssd_cache",
        "nvme",
        "ssd",
        "hdd",
        "object_storage",
        "tape",
        "glacier",
        "distributed",
        "replicated",
        "erasure_coded",
        "local",
        "regional",
        "global",
        "qdrant_vector",
        "redis_cache",
        "postgres_primary",
        "timescaledb",
        "influxdb",
        "clickhouse",
    ]
    indexes["obs_storage_tiers"] = _build_string_index("obs_storage_tiers", storage_tiers)

    # Pipeline stages
    pipeline_stages = [
        "ingest",
        "validate",
        "deduplicate",
        "normalize",
        "enrich",
        "transform",
        "aggregate",
        "downsample",
        "compress",
        "encrypt",
        "index",
        "store",
        "replicate",
        "backup",
        "archive",
        "query",
        "retrieve",
        "decompress",
        "deserialize",
        "filter",
        "join",
        "window",
        "compute",
        "alert",
        "publish",
        "export",
        "visualize",
        "train",
        "evaluate",
        "predict",
        "explain",
    ]
    indexes["obs_pipeline_stages"] = _build_string_index("obs_pipeline_stages", pipeline_stages)

    logger.info(f"Built {len(indexes)} observation constraint indexes")
    return indexes


# ---------------------------------------------------------------------------
# Domain: SEARCH (MINDEX query optimization, search and retrieval)
# ---------------------------------------------------------------------------


async def build_search_index() -> Dict[str, STATICIndex]:
    """
    Build STATIC indexes for MINDEX search and retrieval operations.

    MINDEX as the universal index needs constrained identifiers for
    query types, result categories, ranking signals, and index
    management operations.

    Indexes:
    - search_query_types: Valid query type identifiers
    - search_result_types: Result category identifiers
    - search_ranking_signals: Ranking and scoring signal names
    - search_index_types: Index type identifiers
    - search_entity_types: Universal entity type taxonomy for MINDEX
    """
    indexes: Dict[str, STATICIndex] = {}

    # Query types
    query_types = [
        "keyword",
        "semantic",
        "vector_similarity",
        "full_text",
        "fuzzy",
        "prefix",
        "wildcard",
        "regex",
        "range",
        "geospatial_radius",
        "geospatial_bbox",
        "temporal_range",
        "taxonomic_path",
        "nearest_neighbor",
        "hybrid_search",
        "faceted",
        "filtered",
        "aggregation",
        "graph_traversal",
        "path_query",
        "constrained_generation",
        "reranking",
        "multi_index",
        "cross_domain",
        "federated",
        "autocomplete",
        "suggestion",
        "spell_correct",
        "question_answering",
        "summarization",
    ]
    indexes["search_query_types"] = _build_string_index("search_query_types", query_types)

    # Result types
    result_types = [
        "species_record",
        "observation_record",
        "environmental_reading",
        "signal_stream",
        "agent_record",
        "device_record",
        "user_record",
        "document",
        "image",
        "audio",
        "video",
        "dataset",
        "model_artifact",
        "experiment_result",
        "taxonomy_node",
        "geographic_feature",
        "chemical_compound",
        "genetic_sequence",
        "protein_structure",
        "pathway",
        "organization",
        "person",
        "event",
        "publication",
        "patent",
        "regulation",
        "vector_embedding",
        "knowledge_graph_node",
        "time_series",
        "spatial_raster",
        "spatial_vector",
    ]
    indexes["search_result_types"] = _build_string_index("search_result_types", result_types)

    # Ranking signals
    ranking_signals = [
        "relevance_score",
        "semantic_similarity",
        "bm25_score",
        "tf_idf_score",
        "recency",
        "freshness",
        "popularity",
        "authority",
        "citation_count",
        "data_quality_score",
        "completeness",
        "geographic_proximity",
        "taxonomic_distance",
        "genetic_similarity",
        "ecological_affinity",
        "user_preference",
        "collaborative_filtering",
        "constraint_compliance",
        "diversity_score",
        "novelty_score",
        "serendipity_score",
        "coverage_score",
        "precision_score",
    ]
    indexes["search_ranking_signals"] = _build_string_index(
        "search_ranking_signals", ranking_signals
    )

    # Universal MINDEX entity type taxonomy
    # This is THE master list of everything MINDEX can store
    entity_types = [
        # Biological
        "species",
        "genus",
        "family",
        "order",
        "class",
        "phylum",
        "kingdom",
        "domain_of_life",
        "population",
        "community",
        "ecosystem",
        "gene",
        "protein",
        "metabolite",
        "compound",
        "pathway",
        "genome",
        "metagenome",
        # Environmental
        "observation",
        "measurement",
        "signal_stream",
        "time_series",
        "spatial_raster",
        "spatial_vector",
        "weather_event",
        "climate_record",
        "natural_disaster",
        # Artificial
        "ai_model",
        "agent",
        "robot",
        "vehicle",
        "device",
        "sensor",
        "actuator",
        "application",
        "service",
        "api_endpoint",
        "database",
        "dataset",
        "model_artifact",
        # Organizational
        "organization",
        "person",
        "team",
        "project",
        "experiment",
        "protocol",
        "publication",
        "patent",
        "regulation",
        "standard",
        # Geospatial
        "location",
        "region",
        "biome",
        "habitat",
        "protected_area",
        "watershed",
        "geological_formation",
        # Informational
        "document",
        "image",
        "audio",
        "video",
        "knowledge_graph_node",
        "vector_embedding",
        "constraint_index",
        "taxonomy_node",
    ]
    indexes["search_entity_types"] = _build_string_index("search_entity_types", entity_types)

    # Knowledge graph node types
    graph_node_types = [
        "species",
        "genus",
        "family",
        "order",
        "class",
        "phylum",
        "kingdom",
        "compound",
        "gene",
        "protein",
        "pathway",
        "habitat",
        "observation",
        "experiment",
        "publication",
        "person",
        "organization",
        "device",
        "agent",
        "location",
        "substrate",
        "symbiont",
        "cultivation_protocol",
        "environmental_reading",
        "telemetry_point",
        "dataset",
        "image",
        "sequence",
        "sample",
        "culture",
    ]
    indexes["search_graph_node_types"] = _build_string_index(
        "search_graph_node_types", graph_node_types
    )

    # Knowledge graph edge/relationship types
    graph_edge_types = [
        "produces",
        "inhibits",
        "activates",
        "binds_to",
        "is_a",
        "part_of",
        "has_part",
        "derived_from",
        "found_in",
        "grows_on",
        "symbiotic_with",
        "parasitic_on",
        "cultivated_by",
        "discovered_by",
        "published_in",
        "observed_at",
        "collected_from",
        "analyzed_by",
        "similar_to",
        "homologous_to",
        "orthologous_to",
        "encodes",
        "regulates",
        "catalyzes",
        "transports",
        "contains",
        "measured_by",
        "correlated_with",
        "precedes",
        "follows",
        "co_occurs_with",
        "treats",
        "causes",
        "prevents",
        "associated_with",
    ]
    indexes["search_graph_edge_types"] = _build_string_index(
        "search_graph_edge_types", graph_edge_types
    )

    logger.info(f"Built {len(indexes)} search/MINDEX constraint indexes")
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
            "indexes": {name: idx.to_dict() for name, idx in self.indexes.items()},
        }


# Map of domain name → async builder function
DOMAIN_BUILDERS: Dict[str, Callable] = {
    # Core domains (v1)
    "mindex": build_mindex_species_index,
    "taxonomy": build_taxonomy_index,
    "crep": build_crep_index,
    "nlm": build_nlm_index,
    "agents": build_agent_index,
    "devices": build_device_index,
    "signals": build_signal_index,
    "users": build_user_index,
    # Universal domains (v2)
    "biosphere": build_biosphere_index,
    "environment": build_environment_index,
    "infrastructure": build_infrastructure_index,
    "geospatial": build_geospatial_index,
    "observation": build_observation_index,
    "search": build_search_index,
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
                 Valid: mindex, taxonomy, crep, nlm, agents, devices, signals,
                 users, biosphere, environment, infrastructure, geospatial,
                 observation, search
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
