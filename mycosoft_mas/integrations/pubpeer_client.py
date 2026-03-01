"""
PubPeer API client integration.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx


class PubPeerClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 20,
    ):
        self.base_url = (base_url or os.getenv("PUBPEER_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("PUBPEER_API_KEY", "")
        self.timeout_seconds = timeout_seconds
        self._client: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {"Accept": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def get_comments(self, paper_id: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("PUBPEER_API_URL is not configured")
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/comments/{paper_id}")
        response.raise_for_status()
        return response.json()
