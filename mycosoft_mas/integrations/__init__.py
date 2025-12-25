"""
Mycosoft MAS Integration Modules

This package provides integration clients for external systems:
- MINDEX: Mycological Index Database (PostgreSQL/PostGIS)
- NATUREOS: Cloud IoT platform
- Website: Mycosoft website API
- Notion: Knowledge management and documentation
- N8N: Workflow automation
- Azure: Resource Manager access
- Space Weather: NASA, NOAA, solar activity data
- Environmental: Air quality, pollution, radiation sensors
- Earth Science: Earthquakes, tides, buoys, water levels
- Financial Markets: Crypto, stocks, forex data
- Automation Hub: Zapier, IFTTT, Make webhooks

The unified integration manager provides a single interface for all integrations.

Usage:
    from mycosoft_mas.integrations import UnifiedIntegrationManager
    
    manager = UnifiedIntegrationManager()
    await manager.initialize()
    
    # Access individual clients
    taxa = await manager.mindex.get_taxa(limit=10)
    devices = await manager.natureos.list_devices()
    earthquakes = await manager.earth_science.get_earthquakes(min_magnitude=5.0)
    solar_wind = await manager.space_weather.get_solar_wind()
    
    # Check health
    health = await manager.check_all_health()
    
    await manager.close()
"""

from .mindex_client import MINDEXClient
from .natureos_client import NATUREOSClient
from .website_client import WebsiteClient
from .notion_client import NotionClient
from .n8n_client import N8NClient
from .azure_client import AzureClient
from .space_weather_client import SpaceWeatherClient
from .environmental_client import EnvironmentalClient
from .earth_science_client import EarthScienceClient
from .financial_markets_client import FinancialMarketsClient
from .automation_hub_client import AutomationHubClient
from .unified_integration_manager import UnifiedIntegrationManager

__all__ = [
    "MINDEXClient",
    "NATUREOSClient",
    "WebsiteClient",
    "NotionClient",
    "N8NClient",
    "AzureClient",
    "SpaceWeatherClient",
    "EnvironmentalClient",
    "EarthScienceClient",
    "FinancialMarketsClient",
    "AutomationHubClient",
    "UnifiedIntegrationManager"
]

