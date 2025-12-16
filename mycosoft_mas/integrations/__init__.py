"""
Mycosoft MAS Integration Modules

This package provides integration clients for external systems:
- MINDEX: Mycological Index Database (PostgreSQL/PostGIS)
- NATUREOS: Cloud IoT platform
- Website: Mycosoft website API
- Notion: Knowledge management and documentation
- N8N: Workflow automation
- Azure: Resource Manager access

The unified integration manager provides a single interface for all integrations.

Usage:
    from mycosoft_mas.integrations import UnifiedIntegrationManager
    
    manager = UnifiedIntegrationManager()
    await manager.initialize()
    
    # Access individual clients
    taxa = await manager.mindex.get_taxa(limit=10)
    devices = await manager.natureos.list_devices()
    
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
from .unified_integration_manager import UnifiedIntegrationManager

__all__ = [
    "MINDEXClient",
    "NATUREOSClient",
    "WebsiteClient",
    "NotionClient",
    "N8NClient",
    "AzureClient",
    "UnifiedIntegrationManager"
]

