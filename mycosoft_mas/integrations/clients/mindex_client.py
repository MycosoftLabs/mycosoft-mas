from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel, Field


class MINDEXItem(BaseModel):
    id: str
    title: str
    score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MINDEXResponse(BaseModel):
    version: str
    items: List[MINDEXItem] = Field(default_factory=list)


class MINDEXClient:
    """
    Minimal MINDEX API client stub.
    Keeps requests typed and versioned to make future integrations safer.
    """

    CONTRACT_VERSION = "v1alpha"

    def __init__(self, base_url: str, api_key: str, timeout: int = 10, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

    async def health(self) -> bool:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(f"{self.base_url}/health", headers=self._headers()) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def search(self, query: str, limit: int = 10) -> MINDEXResponse:
        payload = {"query": query, "limit": limit, "version": self.CONTRACT_VERSION}
        data = await self._post_json("/search", payload)
        return MINDEXResponse(**data)

    async def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        attempt = 0
        last_error: Optional[Exception] = None
        while attempt < self.max_retries:
            attempt += 1
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(url, json=payload, headers=self._headers()) as resp:
                        if resp.status >= 400:
                            raise RuntimeError(f"MINDEX error {resp.status}")
                        return await resp.json()
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(0.5 * attempt)
        raise RuntimeError(f"MINDEX request failed after {self.max_retries} attempts: {last_error}")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
