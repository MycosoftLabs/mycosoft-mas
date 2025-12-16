"""
Base Integration Client

Provides common functionality for all integration clients.
"""

import os
import logging
import httpx
import asyncio
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    """Base exception for integration errors."""
    pass


class IntegrationTimeoutError(IntegrationError):
    """Timeout error for integrations."""
    pass


class IntegrationAuthError(IntegrationError):
    """Authentication error for integrations."""
    pass


class BaseIntegrationClient(ABC):
    """Base class for integration clients."""
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize integration client.
        
        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
        
        Returns:
            Response data
        """
        client = await self._get_client()
        url = endpoint.lstrip('/')
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise IntegrationAuthError(f"Authentication failed: {e}")
                elif e.response.status_code == 429:
                    # Rate limit - wait longer
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    last_error = e
                    continue
                elif e.response.status_code >= 500:
                    # Server error - retry
                    last_error = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                else:
                    raise IntegrationError(f"API error: {e}")
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise IntegrationTimeoutError(f"Request timeout: {e}")
            except Exception as e:
                raise IntegrationError(f"Unexpected error: {e}")
        
        if last_error:
            raise IntegrationError(f"Request failed after {self.max_retries} attempts: {last_error}")
    
    async def health_check(self) -> bool:
        """Check if the integration is healthy."""
        try:
            # Try a simple endpoint
            await self._request("GET", "/health")
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
