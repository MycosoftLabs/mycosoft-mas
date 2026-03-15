"""
Base Connector — common HTTP client, rate limiting, and result normalization.

Created: March 15, 2026
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from mycosoft_mas.earth_search.models import (
    EarthSearchDomain,
    EarthSearchResult,
    GeoFilter,
    TemporalFilter,
)

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Abstract base for all Earth Search data source connectors."""

    source_id: str = ""
    rate_limit_rps: float = 2.0  # requests per second

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request: float = 0.0

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "MYCOSOFT-EarthSearch/1.0 (https://mycosoft.io)",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def _rate_limit(self):
        now = time.time()
        min_interval = 1.0 / self.rate_limit_rps
        elapsed = now - self._last_request
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request = time.time()

    async def _get(self, url: str, params: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None) -> Optional[Any]:
        await self._rate_limit()
        client = await self._http()
        try:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("%s GET %s returned %d", self.source_id, url, resp.status_code)
        except Exception as e:
            logger.warning("%s GET %s error: %s", self.source_id, url, e)
        return None

    async def _post(self, url: str, json_body: Optional[Dict[str, Any]] = None,
                    data: Optional[str] = None,
                    headers: Optional[Dict[str, str]] = None) -> Optional[Any]:
        await self._rate_limit()
        client = await self._http()
        try:
            resp = await client.post(url, json=json_body, content=data, headers=headers)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning("%s POST %s returned %d", self.source_id, url, resp.status_code)
        except Exception as e:
            logger.warning("%s POST %s error: %s", self.source_id, url, e)
        return None

    @abstractmethod
    async def search(
        self,
        query: str,
        domains: List[EarthSearchDomain],
        geo: Optional[GeoFilter] = None,
        temporal: Optional[TemporalFilter] = None,
        limit: int = 20,
    ) -> List[EarthSearchResult]:
        """Search this connector's data sources."""
        ...

    def _env(self, key: str, default: str = "") -> str:
        return os.getenv(key, default)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
