"""
Website Integration Client

Client for interacting with Website API.
"""

import os
import logging
from typing import Dict, Any, Optional
from .base_client import BaseIntegrationClient, IntegrationError

logger = logging.getLogger(__name__)


class WebsiteClient(BaseIntegrationClient):
    """Client for Website API."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize Website client.
        
        Args:
            base_url: Website API base URL
            api_key: Website API key
            **kwargs: Additional base client parameters
        """
        base_url = base_url or os.getenv("WEBSITE_API_URL", "https://api.website.example.com")
        api_key = api_key or os.getenv("WEBSITE_API_KEY")
        
        super().__init__(base_url, api_key, **kwargs)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def get_content(
        self,
        content_type: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get content from Website API.
        
        Args:
            content_type: Content type
            filters: Optional filters
        
        Returns:
            Content data
        """
        params = filters or {}
        response = await self._request("GET", f"/api/v1/content/{content_type}", params=params)
        return response.get("data", {})
    
    async def update_content(
        self,
        content_type: str,
        content_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update content in Website API.
        
        Args:
            content_type: Content type
            content_id: Content ID
            data: Updated data
        
        Returns:
            Updated content
        """
        response = await self._request("PUT", f"/api/v1/content/{content_type}/{content_id}", json=data)
        return response.get("data", {})
