"""
NatureOS Integration Client

Client for interacting with NatureOS API.
"""

import os
import logging
from typing import Dict, Any, Optional
from .base_client import BaseIntegrationClient, IntegrationError

logger = logging.getLogger(__name__)


class NatureOSClient(BaseIntegrationClient):
    """Client for NatureOS API."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize NatureOS client.
        
        Args:
            base_url: NatureOS API base URL
            api_key: NatureOS API key
            tenant_id: Tenant ID
            **kwargs: Additional base client parameters
        """
        base_url = base_url or os.getenv("NATUREOS_API_URL", "https://api.natureos.example.com")
        api_key = api_key or os.getenv("NATUREOS_API_KEY")
        tenant_id = tenant_id or os.getenv("NATUREOS_TENANT_ID")
        
        super().__init__(base_url, api_key, **kwargs)
        self.tenant_id = tenant_id
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def _get_client(self):
        """Override to add tenant ID to headers."""
        client = await super()._get_client()
        if self.tenant_id:
            client.headers["X-Tenant-ID"] = self.tenant_id
        return client
    
    async def get_entities(
        self,
        entity_type: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get entities from NatureOS.
        
        Args:
            entity_type: Entity type
            filters: Optional filters
        
        Returns:
            Entity data
        """
        params = filters or {}
        response = await self._request("GET", f"/api/v1/entities/{entity_type}", params=params)
        return response.get("data", {})
    
    async def create_entity(
        self,
        entity_type: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create an entity in NatureOS.
        
        Args:
            entity_type: Entity type
            data: Entity data
        
        Returns:
            Created entity
        """
        response = await self._request("POST", f"/api/v1/entities/{entity_type}", json=data)
        return response.get("data", {})
