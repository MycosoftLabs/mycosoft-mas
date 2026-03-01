"""
Google Scholar search client via SerpAPI.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx


class ScholarClient:
    def __init__(self, api_key: Optional[str] = None, timeout_seconds: int = 20):
        self.api_key = api_key or os.getenv("SERPAPI_KEY", "")
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://serpapi.com/search.json"
        self._client: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("SERPAPI_KEY is not configured")

        client = await self._get_client()
        response = await client.get(
            self.base_url,
            params={
                "engine": "google_scholar",
                "q": query,
                "num": max_results,
                "api_key": self.api_key,
            },
        )
        response.raise_for_status()
        payload = response.json()
        results: List[Dict[str, Any]] = []
        for item in payload.get("organic_results", [])[:max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "publication_info": item.get("publication_info", {}),
                    "source": "google_scholar",
                }
            )
        return results
