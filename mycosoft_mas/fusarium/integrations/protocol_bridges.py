from __future__ import annotations

from typing import Any, Dict

import httpx


class PartnerBridge:
    def __init__(self, timeout_s: float = 20.0) -> None:
        self.timeout_s = timeout_s

    async def _post_json(self, url: str, payload: Dict[str, Any], headers: Dict[str, str] | None = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {"result": data}

    async def push_to_palantir(self, endpoint: str, payload: Dict[str, Any], token: str | None = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return await self._post_json(endpoint, payload, headers)

    async def push_to_anduril(self, endpoint: str, payload: Dict[str, Any], token: str | None = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return await self._post_json(endpoint, payload, headers)

    async def export_stix_taxii(self, endpoint: str, stix_bundle: Dict[str, Any], api_key: str | None = None) -> Dict[str, Any]:
        headers = {"X-API-Key": api_key} if api_key else None
        return await self._post_json(endpoint, stix_bundle, headers)

    async def push_jadc2_event(self, endpoint: str, event_payload: Dict[str, Any], token: str | None = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else None
        return await self._post_json(endpoint, event_payload, headers)
