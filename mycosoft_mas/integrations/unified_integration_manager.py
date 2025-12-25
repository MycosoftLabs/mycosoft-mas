"""
Unified Integration Manager

This module provides a unified interface for all external system integrations:
- MINDEX: Mycological Index Database (PostgreSQL/PostGIS)
- NATUREOS: Cloud IoT platform
- Website: Mycosoft website (Vercel)
- Notion: Knowledge management and documentation
- N8N: Workflow automation
- Space Weather: NASA, NOAA, solar activity data
- Environmental: Air quality, pollution, radiation sensors
- Earth Science: Earthquakes, tides, buoys, water levels
- Financial Markets: Crypto, stocks, forex data
- Automation Hub: Zapier, IFTTT, Make webhooks

The manager initializes all clients and provides a single interface for:
- Health checks across all systems
- Coordinated operations
- Error handling and retries
- Connection pooling
- Monitoring and metrics

Environment Variables:
    See individual client modules for their specific environment variables.
    See docs/ENV_INTEGRATIONS.md for a complete list.

Usage:
    from mycosoft_mas.integrations.unified_integration_manager import UnifiedIntegrationManager
    
    manager = UnifiedIntegrationManager()
    await manager.initialize()
    health = await manager.check_all_health()
    await manager.close()
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

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

logger = logging.getLogger(__name__)


class UnifiedIntegrationManager:
    """
    Unified manager for all external system integrations.
    
    This manager coordinates:
    - MINDEX database operations
    - NATUREOS device management
    - Website API interactions
    - Notion documentation and knowledge base
    - N8N workflow automation
    - Azure Resource Manager operations
    - Space weather data (NASA, NOAA, solar activity)
    - Environmental sensors (air quality, pollution, radiation)
    - Earth science data (earthquakes, tides, buoys)
    - Financial markets (crypto, stocks, forex)
    - Automation platforms (Zapier, IFTTT, Make)
    
    Provides:
    - Single initialization point
    - Unified health checking
    - Coordinated error handling
    - Connection management
    - Metrics collection
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the unified integration manager.
        
        Args:
            config: Optional configuration dictionary. If not provided, reads from environment variables.
                   Expected structure:
                   {
                       "mindex": {...},
                       "natureos": {...},
                       "website": {...},
                       "notion": {...},
                       "n8n": {...},
                       "azure": {...},
                       "space_weather": {...},
                       "environmental": {...},
                       "earth_science": {...},
                       "financial": {...},
                       "automation": {...}
                   }
        
        Note:
            Each integration client can be configured individually.
            Missing configurations fall back to environment variables.
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize clients (lazy loading - created on first access)
        self._mindex_client = None
        self._natureos_client = None
        self._website_client = None
        self._notion_client = None
        self._n8n_client = None
        self._azure_client = None
        self._space_weather_client = None
        self._environmental_client = None
        self._earth_science_client = None
        self._financial_client = None
        self._automation_client = None
        
        # Status tracking
        self.initialized = False
        self.health_status = {}
        self.last_health_check = None
        
        # Metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_error": None,
            "last_error_time": None
        }
        
        self.logger.info("Unified integration manager initialized")
    
    @property
    def mindex(self) -> MINDEXClient:
        """
        Get MINDEX client instance (lazy initialization).
        
        Returns:
            MINDEXClient: MINDEX database client
        
        Note:
            Client is created on first access.
            Configuration is read from config dict or environment variables.
        """
        if self._mindex_client is None:
            mindex_config = self.config.get("mindex", {})
            self._mindex_client = MINDEXClient(config=mindex_config)
        return self._mindex_client
    
    @property
    def natureos(self) -> NATUREOSClient:
        """
        Get NATUREOS client instance (lazy initialization).
        
        Returns:
            NATUREOSClient: NATUREOS cloud platform client
        """
        if self._natureos_client is None:
            natureos_config = self.config.get("natureos", {})
            self._natureos_client = NATUREOSClient(config=natureos_config)
        return self._natureos_client
    
    @property
    def website(self) -> WebsiteClient:
        """
        Get Website client instance (lazy initialization).
        
        Returns:
            WebsiteClient: Mycosoft website API client
        """
        if self._website_client is None:
            website_config = self.config.get("website", {})
            self._website_client = WebsiteClient(config=website_config)
        return self._website_client
    
    @property
    def notion(self) -> NotionClient:
        """
        Get Notion client instance (lazy initialization).
        
        Returns:
            NotionClient: Notion API client
        """
        if self._notion_client is None:
            notion_config = self.config.get("notion", {})
            self._notion_client = NotionClient(config=notion_config)
        return self._notion_client
    
    @property
    def n8n(self) -> N8NClient:
        """
        Get N8N client instance (lazy initialization).
        
        Returns:
            N8NClient: N8N workflow automation client
        """
        if self._n8n_client is None:
            n8n_config = self.config.get("n8n", {})
            self._n8n_client = N8NClient(config=n8n_config)
        return self._n8n_client

    @property
    def azure(self) -> AzureClient:
        """
        Get Azure client instance (lazy initialization).

        Returns:
            AzureClient: Azure Resource Manager client
        """
        if self._azure_client is None:
            azure_config = self.config.get("azure", {})
            self._azure_client = AzureClient(config=azure_config)
        return self._azure_client
    
    @property
    def space_weather(self) -> SpaceWeatherClient:
        """
        Get Space Weather client instance (lazy initialization).
        
        Provides access to:
        - NASA DONKI (solar events, CMEs, flares)
        - NOAA Space Weather (Kp index, alerts)
        - GOES/ACE/DSCOVR satellite data
        - Weather forecasts and alerts
        
        Returns:
            SpaceWeatherClient: Space weather data client
        """
        if self._space_weather_client is None:
            sw_config = self.config.get("space_weather", {})
            self._space_weather_client = SpaceWeatherClient(config=sw_config)
        return self._space_weather_client
    
    @property
    def environmental(self) -> EnvironmentalClient:
        """
        Get Environmental client instance (lazy initialization).
        
        Provides access to:
        - Air quality data (OpenAQ, EPA AirNow, PurpleAir, IQAir)
        - Radiation monitoring (Safecast, EPA RadNet)
        - Multi-environmental data (BreezoMeter, Ambee)
        
        Returns:
            EnvironmentalClient: Environmental sensor data client
        """
        if self._environmental_client is None:
            env_config = self.config.get("environmental", {})
            self._environmental_client = EnvironmentalClient(config=env_config)
        return self._environmental_client
    
    @property
    def earth_science(self) -> EarthScienceClient:
        """
        Get Earth Science client instance (lazy initialization).
        
        Provides access to:
        - Earthquakes (USGS, IRIS)
        - Tides and currents (NOAA)
        - Buoy data (NDBC)
        - Water levels and streamflow (USGS, USACE)
        - Flood warnings (NWS)
        
        Returns:
            EarthScienceClient: Earth science data client
        """
        if self._earth_science_client is None:
            es_config = self.config.get("earth_science", {})
            self._earth_science_client = EarthScienceClient(config=es_config)
        return self._earth_science_client
    
    @property
    def financial(self) -> FinancialMarketsClient:
        """
        Get Financial Markets client instance (lazy initialization).
        
        Provides access to:
        - Cryptocurrency (CoinMarketCap, CoinGecko)
        - Stocks (Alpha Vantage, Polygon, Finnhub)
        - Forex rates
        - Market news
        
        Returns:
            FinancialMarketsClient: Financial markets data client
        """
        if self._financial_client is None:
            fin_config = self.config.get("financial", {})
            self._financial_client = FinancialMarketsClient(config=fin_config)
        return self._financial_client
    
    @property
    def automation(self) -> AutomationHubClient:
        """
        Get Automation Hub client instance (lazy initialization).
        
        Provides access to:
        - Zapier webhooks
        - IFTTT Maker webhooks
        - Make (Integromat) scenarios
        - Pipedream workflows
        - Activepieces flows
        
        Returns:
            AutomationHubClient: Automation platform client
        """
        if self._automation_client is None:
            auto_config = self.config.get("automation", {})
            self._automation_client = AutomationHubClient(config=auto_config)
        return self._automation_client
    
    async def initialize(self) -> None:
        """
        Initialize all integration clients.
        
        Note:
            Performs health checks on all systems.
            Logs initialization status for each integration.
            Sets initialized flag on success.
        """
        self.logger.info("Initializing all integration clients...")
        
        # Initialize clients (lazy initialization happens on first access)
        # Pre-warm connections by accessing clients
        clients = {
            "MINDEX": self.mindex,
            "NATUREOS": self.natureos,
            "Website": self.website,
            "Notion": self.notion,
            "N8N": self.n8n,
            "Azure": self.azure,
            "SpaceWeather": self.space_weather,
            "Environmental": self.environmental,
            "EarthScience": self.earth_science,
            "Financial": self.financial,
            "Automation": self.automation,
        }
        
        # Perform initial health checks
        health_results = await self.check_all_health()
        
        # Log initialization status
        for name, status in health_results.items():
            if status.get("status") == "ok":
                self.logger.info(f"✓ {name} integration initialized successfully")
            elif status.get("status") == "not_configured":
                self.logger.warning(f"⚠ {name} integration not configured (optional)")
            else:
                self.logger.error(f"✗ {name} integration failed: {status.get('error', 'Unknown error')}")
        
        self.initialized = True
        self.logger.info("Unified integration manager initialization complete")
    
    async def check_all_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Check health status of all integrated systems.
        
        Returns:
            Dictionary mapping integration names to health status:
            {
                "MINDEX": {"status": "ok", "timestamp": "...", ...},
                "NATUREOS": {"status": "ok", ...},
                ...
            }
        
        Note:
            Health checks are performed concurrently for efficiency.
            Each integration's health check includes:
            - Status (ok, error, not_configured)
            - Timestamp
            - Error details (if any)
        """
        self.logger.debug("Checking health of all integrations...")
        
        # Perform health checks concurrently
        health_tasks = {
            "MINDEX": self.mindex.health_check(),
            "NATUREOS": self.natureos.health_check(),
            "Website": self.website.health_check(),
            "Notion": self.notion.health_check(),
            "N8N": self.n8n.health_check(),
            "Azure": self.azure.health_check(),
            "SpaceWeather": self.space_weather.health_check(),
            "Environmental": self.environmental.health_check(),
            "EarthScience": self.earth_science.health_check(),
            "Financial": self.financial.health_check(),
            "Automation": self.automation.health_check(),
        }
        
        results = {}
        for name, task in health_tasks.items():
            try:
                health = await task
                results[name] = health
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        self.health_status = results
        self.last_health_check = datetime.utcnow()
        
        return results
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of all integrations.
        
        Returns:
            Status dictionary with:
            - initialized: Whether manager is initialized
            - health: Health status of all systems
            - metrics: Request metrics
            - last_health_check: Timestamp of last health check
        
        Note:
            Used for monitoring dashboards and status endpoints.
            Provides overview of all system integrations.
        """
        return {
            "initialized": self.initialized,
            "health": self.health_status,
            "metrics": self.metrics,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def sync_mindex_to_notion(
        self,
        database_id: str,
        taxon_ids: Optional[List[int]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Sync MINDEX taxonomy data to Notion database.
        
        Args:
            database_id: Notion database ID
            taxon_ids: Optional list of taxon IDs to sync (syncs all if None)
            limit: Maximum number of records to sync
        
        Returns:
            Sync result with counts and status
        
        Note:
            Creates or updates Notion pages for each taxon.
            Useful for maintaining documentation and knowledge base.
            Can be triggered manually or via scheduled task.
        """
        self.logger.info(f"Syncing MINDEX taxa to Notion database {database_id}")
        
        try:
            # Get taxa from MINDEX
            if taxon_ids:
                taxa = []
                for taxon_id in taxon_ids[:limit]:
                    # Note: MINDEX API would need a get_taxon_by_id method
                    # For now, we'll use get_taxa and filter
                    pass
            else:
                taxa = await self.mindex.get_taxa(limit=limit)
            
            # Sync to Notion
            synced = 0
            errors = 0
            
            for taxon in taxa:
                try:
                    # Create or update Notion page
                    properties = {
                        "Name": {
                            "title": [{"text": {"content": taxon.get("scientific_name", "Unknown")}}]
                        },
                        "Canonical Name": {
                            "rich_text": [{"text": {"content": taxon.get("canonical_name", "")}}]
                        },
                        "Rank": {
                            "select": {"name": taxon.get("rank", "unknown")}
                        }
                    }
                    
                    # Check if page exists (query database)
                    query_result = await self.notion.query_database(
                        database_id=database_id,
                        filter_properties={
                            "property": "Name",
                            "title": {"equals": taxon.get("scientific_name")}
                        }
                    )
                    
                    if query_result.get("results"):
                        # Update existing page
                        page_id = query_result["results"][0]["id"]
                        await self.notion.update_page(page_id, properties)
                    else:
                        # Create new page
                        await self.notion.create_page(database_id=database_id, properties=properties)
                    
                    synced += 1
                except Exception as e:
                    self.logger.error(f"Error syncing taxon {taxon.get('id')}: {e}")
                    errors += 1
            
            result = {
                "synced": synced,
                "errors": errors,
                "total": len(taxa),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Sync complete: {synced} synced, {errors} errors")
            return result
        
        except Exception as e:
            self.logger.error(f"Error in sync_mindex_to_notion: {e}")
            raise
    
    async def trigger_n8n_workflow_for_agent(
        self,
        workflow_id: str,
        agent_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger N8N workflow for agent events.
        
        Args:
            workflow_id: N8N workflow ID or webhook path
            agent_id: Agent identifier
            event_type: Type of event (e.g., "task_completed", "error", "status_change")
            data: Additional event data
        
        Returns:
            Workflow execution result
        
        Note:
            Used for automating responses to agent events.
            Can trigger notifications, logging, or other workflows.
        """
        workflow_data = {
            "agent_id": agent_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **data
        }
        
        return await self.n8n.trigger_workflow(workflow_id, workflow_data)
    
    async def log_to_notion(
        self,
        database_id: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log agent activity or system events to Notion.
        
        Args:
            database_id: Notion database ID
            title: Log entry title
            content: Log content
            metadata: Optional metadata fields
        
        Returns:
            Created Notion page
        
        Note:
            Useful for maintaining audit logs and documentation.
            Can be called by agents to log their activities.
        """
        properties = {
            "Title": {
                "title": [{"text": {"content": title}}]
            },
            "Content": {
                "rich_text": [{"text": {"content": content}}]
            },
            "Timestamp": {
                "date": {"start": datetime.utcnow().isoformat()}
            }
        }
        
        if metadata:
            for key, value in metadata.items():
                if key not in properties:
                    properties[key] = {
                        "rich_text": [{"text": {"content": str(value)}}]
                    }
        
        return await self.notion.create_page(database_id=database_id, properties=properties)
    
    async def close(self) -> None:
        """
        Close all integration clients and clean up resources.
        
        Note:
            Should be called during shutdown.
            Closes all HTTP connections and database pools.
        """
        self.logger.info("Closing all integration clients...")
        
        close_tasks = []
        
        if self._mindex_client:
            close_tasks.append(self._mindex_client.close())
        if self._natureos_client:
            close_tasks.append(self._natureos_client.close())
        if self._website_client:
            close_tasks.append(self._website_client.close())
        if self._notion_client:
            close_tasks.append(self._notion_client.close())
        if self._n8n_client:
            close_tasks.append(self._n8n_client.close())
        if self._azure_client:
            close_tasks.append(self._azure_client.close())
        if self._space_weather_client:
            close_tasks.append(self._space_weather_client.close())
        if self._environmental_client:
            close_tasks.append(self._environmental_client.close())
        if self._earth_science_client:
            close_tasks.append(self._earth_science_client.close())
        if self._financial_client:
            close_tasks.append(self._financial_client.close())
        if self._automation_client:
            close_tasks.append(self._automation_client.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.initialized = False
        self.logger.info("All integration clients closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes all connections."""
        await self.close()

