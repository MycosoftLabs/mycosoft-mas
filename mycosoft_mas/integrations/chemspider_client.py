"""
ChemSpider (RSC Compounds) Integration Client.

Chemical compound search and metadata. Used by: LabAgent, MINDEX ETL,
scientific agents. MINDEX ETL has full implementation; this client is for
MAS agents that need compound lookups.

Environment Variables:
    CHEMSPIDER_API_KEY: API key from https://developer.rsc.org/
    CHEMSPIDER_API_URL: Base URL (default https://api.rsc.org/compounds/v1)
"""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_CHEMSPIDER_URL = "https://api.rsc.org/compounds/v1"


class ChemSpiderClient:
    """Thin client for RSC ChemSpider/Compounds API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", os.getenv("CHEMSPIDER_API_KEY", ""))
        self.base_url = self.config.get("base_url", os.getenv("CHEMSPIDER_API_URL", DEFAULT_CHEMSPIDER_URL)).rstrip("/")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "apikey": self.api_key,
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def search_by_name(self, name: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search compounds by name; returns list of record IDs and metadata if available."""
        if not self.api_key:
            logger.warning("ChemSpider client: no CHEMSPIDER_API_KEY set")
            return []
        client = await self._get_client()
        try:
            r = await client.post(
                "/filter/name",
                json={"name": name, "maxResults": max_results},
            )
            r.raise_for_status()
            data = r.json()
            return data.get("results", []) or []
        except Exception as e:
            logger.warning("ChemSpider search_by_name failed: %s", e)
            return []

    async def get_compound_details(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Fetch compound details by record ID."""
        if not self.api_key:
            return None
        client = await self._get_client()
        try:
            r = await client.get(f"/records/{record_id}/details")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("ChemSpider get_compound_details failed: %s", e)
            return None
