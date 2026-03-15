"""
Earth Search Connectors — API clients for all planetary data sources.

Each connector implements a common interface: search(query, geo, temporal, limit) -> List[EarthSearchResult].
Connectors are grouped by domain category.

Created: March 15, 2026
"""

from mycosoft_mas.earth_search.connectors.base import BaseConnector
from mycosoft_mas.earth_search.connectors.species import SpeciesConnector
from mycosoft_mas.earth_search.connectors.environment import EnvironmentConnector
from mycosoft_mas.earth_search.connectors.climate import ClimateConnector
from mycosoft_mas.earth_search.connectors.transport import TransportConnector
from mycosoft_mas.earth_search.connectors.space import SpaceConnector
from mycosoft_mas.earth_search.connectors.infrastructure import InfrastructureConnector
from mycosoft_mas.earth_search.connectors.telecom import TelecomConnector
from mycosoft_mas.earth_search.connectors.sensors import SensorConnector
from mycosoft_mas.earth_search.connectors.science import ScienceConnector

__all__ = [
    "BaseConnector",
    "SpeciesConnector",
    "EnvironmentConnector",
    "ClimateConnector",
    "TransportConnector",
    "SpaceConnector",
    "InfrastructureConnector",
    "TelecomConnector",
    "SensorConnector",
    "ScienceConnector",
]
