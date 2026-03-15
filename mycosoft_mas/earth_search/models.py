"""
Earth Search Models — Pydantic schemas for planetary-scale unified search.

Every searchable domain on Earth is represented here with geospatial, temporal,
and categorical filtering. Results carry provenance, coordinates, and CREP map hints.

Created: March 15, 2026
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EarthSearchDomain(str, Enum):
    """All searchable domains on Earth."""

    # --- Life / Species ---
    ALL_SPECIES = "all_species"
    FUNGI = "fungi"
    PLANTS = "plants"
    BIRDS = "birds"
    MAMMALS = "mammals"
    REPTILES = "reptiles"
    AMPHIBIANS = "amphibians"
    INSECTS = "insects"
    MARINE_LIFE = "marine_life"
    FISH = "fish"
    MICROORGANISMS = "microorganisms"
    INVERTEBRATES = "invertebrates"

    # --- Chemistry / Genetics / Research ---
    COMPOUNDS = "compounds"
    GENETICS = "genetics"
    RESEARCH = "research"

    # --- Environmental Events ---
    EARTHQUAKES = "earthquakes"
    VOLCANOES = "volcanoes"
    WILDFIRES = "wildfires"
    STORMS = "storms"
    LIGHTNING = "lightning"
    TORNADOES = "tornadoes"
    FLOODS = "floods"
    TSUNAMIS = "tsunamis"

    # --- Atmospheric / Climate ---
    WEATHER = "weather"
    CO2 = "co2"
    METHANE = "methane"
    AIR_QUALITY = "air_quality"
    GROUND_QUALITY = "ground_quality"
    OCEAN_TEMPERATURE = "ocean_temperature"
    MODIS = "modis"
    LANDSAT = "landsat"
    AIRS = "airs"

    # --- Transportation ---
    FLIGHTS = "flights"
    VESSELS = "vessels"
    AIRPORTS = "airports"
    SHIPPING_PORTS = "shipping_ports"
    SPACEPORTS = "spaceports"
    RAILWAYS = "railways"

    # --- Industrial Infrastructure ---
    FACTORIES = "factories"
    POWER_PLANTS = "power_plants"
    MINING = "mining"
    OIL_GAS = "oil_gas"
    DAMS = "dams"
    WATER_TREATMENT = "water_treatment"
    RIVERS = "rivers"
    POLLUTION_SOURCES = "pollution_sources"

    # --- Space ---
    SATELLITES = "satellites"
    SPACE_WEATHER = "space_weather"
    SOLAR_FLARES = "solar_flares"
    SPACE_DEBRIS = "space_debris"
    LAUNCHES = "launches"
    NASA_FEEDS = "nasa_feeds"
    NOAA_FEEDS = "noaa_feeds"

    # --- Telecommunications ---
    CELL_TOWERS = "cell_towers"
    AM_FM_ANTENNAS = "am_fm_antennas"
    WIFI_HOTSPOTS = "wifi_hotspots"
    INTERNET_CABLES = "internet_cables"
    SIGNAL_MAPS = "signal_maps"

    # --- Military / Government ---
    MILITARY_BASES = "military_bases"
    WEBCAMS = "webcams"

    # --- Sensors / Buoys ---
    OCEAN_BUOYS = "ocean_buoys"
    WEATHER_STATIONS = "weather_stations"
    SEISMIC_STATIONS = "seismic_stations"

    # --- Device Telemetry ---
    MYCOBRAIN_DEVICES = "mycobrain_devices"

    # --- Knowledge / LLM ---
    LLM_SYNTHESIS = "llm_synthesis"
    MATHEMATICS = "mathematics"
    PHYSICS = "physics"


# Domain groupings for batch queries
DOMAIN_GROUPS: Dict[str, List[EarthSearchDomain]] = {
    "life": [
        EarthSearchDomain.ALL_SPECIES, EarthSearchDomain.FUNGI,
        EarthSearchDomain.PLANTS, EarthSearchDomain.BIRDS,
        EarthSearchDomain.MAMMALS, EarthSearchDomain.REPTILES,
        EarthSearchDomain.AMPHIBIANS, EarthSearchDomain.INSECTS,
        EarthSearchDomain.MARINE_LIFE, EarthSearchDomain.FISH,
        EarthSearchDomain.MICROORGANISMS, EarthSearchDomain.INVERTEBRATES,
    ],
    "environment": [
        EarthSearchDomain.EARTHQUAKES, EarthSearchDomain.VOLCANOES,
        EarthSearchDomain.WILDFIRES, EarthSearchDomain.STORMS,
        EarthSearchDomain.LIGHTNING, EarthSearchDomain.TORNADOES,
        EarthSearchDomain.FLOODS, EarthSearchDomain.TSUNAMIS,
    ],
    "climate": [
        EarthSearchDomain.WEATHER, EarthSearchDomain.CO2,
        EarthSearchDomain.METHANE, EarthSearchDomain.AIR_QUALITY,
        EarthSearchDomain.GROUND_QUALITY, EarthSearchDomain.OCEAN_TEMPERATURE,
        EarthSearchDomain.MODIS, EarthSearchDomain.LANDSAT, EarthSearchDomain.AIRS,
    ],
    "transport": [
        EarthSearchDomain.FLIGHTS, EarthSearchDomain.VESSELS,
        EarthSearchDomain.AIRPORTS, EarthSearchDomain.SHIPPING_PORTS,
        EarthSearchDomain.SPACEPORTS, EarthSearchDomain.RAILWAYS,
    ],
    "infrastructure": [
        EarthSearchDomain.FACTORIES, EarthSearchDomain.POWER_PLANTS,
        EarthSearchDomain.MINING, EarthSearchDomain.OIL_GAS,
        EarthSearchDomain.DAMS, EarthSearchDomain.WATER_TREATMENT,
        EarthSearchDomain.RIVERS, EarthSearchDomain.POLLUTION_SOURCES,
    ],
    "space": [
        EarthSearchDomain.SATELLITES, EarthSearchDomain.SPACE_WEATHER,
        EarthSearchDomain.SOLAR_FLARES, EarthSearchDomain.SPACE_DEBRIS,
        EarthSearchDomain.LAUNCHES, EarthSearchDomain.NASA_FEEDS,
        EarthSearchDomain.NOAA_FEEDS,
    ],
    "telecom": [
        EarthSearchDomain.CELL_TOWERS, EarthSearchDomain.AM_FM_ANTENNAS,
        EarthSearchDomain.WIFI_HOTSPOTS, EarthSearchDomain.INTERNET_CABLES,
        EarthSearchDomain.SIGNAL_MAPS,
    ],
    "sensors": [
        EarthSearchDomain.OCEAN_BUOYS, EarthSearchDomain.WEATHER_STATIONS,
        EarthSearchDomain.SEISMIC_STATIONS, EarthSearchDomain.MYCOBRAIN_DEVICES,
    ],
    "science": [
        EarthSearchDomain.COMPOUNDS, EarthSearchDomain.GENETICS,
        EarthSearchDomain.RESEARCH, EarthSearchDomain.LLM_SYNTHESIS,
        EarthSearchDomain.MATHEMATICS, EarthSearchDomain.PHYSICS,
    ],
}


class GeoFilter(BaseModel):
    """Geographic bounding for search."""
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(100, gt=0, le=20000)
    bbox: Optional[Dict[str, float]] = Field(
        None, description="Bounding box: {north, south, east, west}"
    )


class TemporalFilter(BaseModel):
    """Time-range filter."""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    realtime: bool = Field(False, description="Return only live/streaming data")


class EarthSearchQuery(BaseModel):
    """Planetary-scale search request."""
    query: str = Field(..., min_length=1, description="Natural language or keyword query")
    domains: List[EarthSearchDomain] = Field(
        default_factory=list,
        description="Domains to search. Empty = auto-detect from query.",
    )
    domain_groups: List[str] = Field(
        default_factory=list,
        description="Domain group names (life, environment, climate, transport, etc.)",
    )
    geo: Optional[GeoFilter] = None
    temporal: Optional[TemporalFilter] = None
    limit: int = Field(20, ge=1, le=500)
    include_crep: bool = Field(True, description="Include CREP map visualization data")
    include_llm: bool = Field(False, description="Include LLM synthesis/answer")
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    def resolved_domains(self) -> List[EarthSearchDomain]:
        """Resolve domain groups into flat domain list."""
        domains = list(self.domains)
        for group in self.domain_groups:
            domains.extend(DOMAIN_GROUPS.get(group, []))
        return list(set(domains)) if domains else list(EarthSearchDomain)


class DataSourceInfo(BaseModel):
    """Metadata about a data source."""
    source_id: str
    name: str
    api_url: Optional[str] = None
    domains: List[EarthSearchDomain]
    requires_key: bool = False
    realtime: bool = False
    description: str = ""


class EarthSearchResult(BaseModel):
    """Single search result with geospatial provenance."""
    result_id: str
    domain: EarthSearchDomain
    source: str
    title: str
    description: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    lat: Optional[float] = None
    lng: Optional[float] = None
    timestamp: Optional[datetime] = None
    confidence: float = Field(0.5, ge=0, le=1)
    crep_layer: Optional[str] = Field(None, description="CREP layer for map display")
    crep_entity_id: Optional[str] = Field(None, description="CREP entity ID for flyTo")
    mindex_id: Optional[str] = Field(None, description="Local MINDEX record ID if ingested")
    url: Optional[str] = None
    image_url: Optional[str] = None


class EarthSearchResponse(BaseModel):
    """Full response from Earth Search."""
    query: str
    domains_searched: List[EarthSearchDomain]
    results: List[EarthSearchResult] = Field(default_factory=list)
    total_count: int = 0
    sources_queried: List[str] = Field(default_factory=list)
    crep_commands: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="CREP commands to visualize results on map",
    )
    llm_answer: Optional[str] = None
    ingestion_status: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    duration_ms: float = 0
