"""MINDEX + optional Supabase access for provenance and harness runs.

Harness writes go to ``POST /api/harness/execution`` when deployed. HTTP reads use
the same keys as :class:`mycosoft_mas.integrations.mindex_client.MINDEXClient`;
keep a single ownership rule: prefer REST via this façade; use Supabase REST only
when explicitly configured (no duplicate writers for the same fact).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

from mycosoft_mas.harness.config import HarnessConfig

logger = logging.getLogger(__name__)


class MindexClient:
    """Harness-side MINDEX HTTP + ``record_execution``.

    For full taxa/observation/DB access, use
    :class:`mycosoft_mas.integrations.mindex_client.MINDEXClient` with the same
    ``MINDEX_API_URL`` / ``MINDEX_API_KEY`` — avoid two writers to the same
    fact without an explicit ownership rule.
    """

    def __init__(self, config: HarnessConfig) -> None:
        self._mindex = config.mindex_api_url.rstrip("/")
        self._api_key = config.mindex_api_key
        self._timeout = config.mindex_http_timeout
        self._supabase_url = (config.supabase_url or "").rstrip("/")
        self._supabase_key = config.supabase_service_key

    def _headers_json(self) -> dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            h["X-API-Key"] = self._api_key
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    async def get_species(self, species_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for path in (f"/species/{species_id}", f"/api/species/{species_id}"):
                try:
                    r = await client.get(
                        f"{self._mindex}{path}",
                        headers=self._headers_json(),
                    )
                    if r.status_code == 200:
                        return r.json()
                except Exception:
                    continue
        return None

    async def record_execution(self, run_id: str, events: list[dict[str, Any]]) -> None:
        """Persist harness run metadata for meta-optimization (best-effort)."""
        payload = {"run_id": run_id, "events": events, "source": "myca-harness"}
        url = f"{self._mindex}/api/harness/execution"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(url, json=payload, headers=self._headers_json())
                if r.status_code in (404, 501):
                    logger.info("MINDEX harness execution endpoint not deployed; skip write")
                    return
                r.raise_for_status()
        except Exception as e:
            logger.warning("record_execution failed: %s", e)

    def verify_merkle_proof(self, leaf: str, siblings: list[str], root: str) -> bool:
        """Recompute Merkle root from leaf + sibling path (SHA-256 pairs)."""
        cur = bytes.fromhex(leaf) if len(leaf) == 64 else hashlib.sha256(leaf.encode()).digest()
        for s in siblings:
            side = bytes.fromhex(s)
            cur = hashlib.sha256(cur + side).digest()
        return cur.hex() == root

    async def supabase_rest(
        self,
        table: str,
        method: str = "GET",
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        if not self._supabase_url or not self._supabase_key:
            raise RuntimeError("Supabase URL/key not configured")
        url = f"{self._supabase_url}/rest/v1/{table}"
        headers = {
            "apikey": self._supabase_key,
            "Authorization": f"Bearer {self._supabase_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.request(method, url, headers=headers, json=json_body)
            r.raise_for_status()
            if r.content:
                return r.json()
        return None
