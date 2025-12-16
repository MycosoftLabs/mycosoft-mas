"""
Mycosoft MAS - Integration Clients

This module provides client stubs for external integrations.
Each client follows a consistent pattern with:
- Base URL and API key configuration
- Retry logic with exponential backoff
- Typed request/response models
- Error handling

Usage:
    from mycosoft_mas.clients import MINDEXClient, NatureOSClient
    
    # Initialize client
    mindex = MINDEXClient(
        base_url="https://api.mindex.io",
        api_key="your-api-key",
    )
    
    # Make requests
    result = await mindex.search(query="fungal species")
"""

from mycosoft_mas.clients.base import BaseClient, ClientConfig, ClientError
from mycosoft_mas.clients.mindex import MINDEXClient
from mycosoft_mas.clients.natureos import NatureOSClient

__all__ = [
    "BaseClient",
    "ClientConfig",
    "ClientError",
    "MINDEXClient",
    "NatureOSClient",
]
