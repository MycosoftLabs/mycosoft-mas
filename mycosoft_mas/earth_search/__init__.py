"""
Earth Search — Unified planetary-scale search across all life, environment, infrastructure, and events.

Expands the original fungi-only MINDEX search to encompass every searchable domain on Earth:
- All species (fungi, plants, animals, insects, marine life, microorganisms)
- Environmental events (earthquakes, volcanoes, wildfires, storms, floods, lightning)
- Industrial infrastructure (factories, power plants, mining, oil/gas, dams, water treatment)
- Transportation (airports, shipping ports, spaceports, AIS vessels, ADS-B flights)
- Atmospheric/climate (weather, CO2, methane, air quality, MODIS, Landsat, AIRS)
- Space (satellites, solar flares, space weather, SOHO, STEREO A/B, GPS satellites)
- Telecommunications (cell towers, AM/FM antennas, WiFi hotspots, internet cables)
- Military/government (bases, publicly accessible webcams, CCTV)
- Ocean (buoys, marine sensors, ocean temperature, currents)
- Research (PubChem, GenBank, scientific directories, LLM synthesis, mathematics, physics)

All data is ingested into local MINDEX (192.168.0.189) for low-latency access and NLM training.
Dual pipeline: API search + CREP map visualization.

Created: March 15, 2026
"""

from mycosoft_mas.earth_search.models import (
    EarthSearchDomain,
    EarthSearchQuery,
    EarthSearchResult,
    EarthSearchResponse,
    GeoFilter,
    TemporalFilter,
    DataSourceInfo,
)
from mycosoft_mas.earth_search.registry import EARTH_DATA_SOURCES, get_source_info

__all__ = [
    "EarthSearchDomain",
    "EarthSearchQuery",
    "EarthSearchResult",
    "EarthSearchResponse",
    "GeoFilter",
    "TemporalFilter",
    "DataSourceInfo",
    "EARTH_DATA_SOURCES",
    "get_source_info",
]
