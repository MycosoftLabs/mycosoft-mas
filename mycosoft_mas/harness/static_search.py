"""MINDEX-backed search-in-LLM — unified Earth search → compact context for Nemotron."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from mycosoft_mas.harness.config import HarnessConfig

logger = logging.getLogger(__name__)


def _summarize_results(payload: dict[str, Any], max_chars: int = 12000) -> str:
    """Turn UnifiedSearchResponse-like JSON into a bounded text block for the LLM."""
    results = payload.get("results") or {}
    lines: list[str] = []
    total = int(payload.get("total_count") or 0)
    lines.append(f"MINDEX unified search (domains={payload.get('domains_searched')}, total={total}):")
    for domain, rows in results.items():
        if not rows:
            continue
        chunk = rows[:8] if isinstance(rows, list) else rows
        try:
            blob = json.dumps(chunk, default=str, ensure_ascii=False)[:2000]
        except Exception:
            blob = str(chunk)[:2000]
        lines.append(f"[{domain}]: {blob}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[:max_chars] + "\n…(truncated)"
    return text


class StaticSearch:
    """Retrieve grounding context from MINDEX `/api/mindex/unified-search` (GET)."""

    def __init__(self, config: HarnessConfig) -> None:
        self._base = config.mindex_api_url.rstrip("/")
        self._api_key = config.mindex_api_key
        self._timeout = config.mindex_http_timeout

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            h["X-API-Key"] = self._api_key
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    async def fetch_unified(self, query: str, *, types: str = "biological", limit: int = 12) -> dict[str, Any]:
        """Call MINDEX unified search; returns parsed JSON or empty dict on failure."""
        q = (query or "").strip()
        if len(q) < 2:
            return {}
        url = f"{self._base}/api/mindex/unified-search"
        params = {"q": q, "types": types, "limit": str(limit)}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(url, params=params, headers=self._headers())
                if r.status_code != 200:
                    logger.warning("MINDEX unified-search HTTP %s: %s", r.status_code, r.text[:200])
                    return {}
                return r.json()
        except Exception as e:
            logger.warning("MINDEX unified-search failed: %s", e)
            return {}

    async def build_llm_context(
        self,
        query: str,
        *,
        types: str | None = None,
        limit: int = 12,
    ) -> str:
        """Formatted context block for Nemotron system or user preamble."""
        t = types or "biological"
        raw = await self.fetch_unified(query, types=t, limit=limit)
        if not raw:
            return ""
        return _summarize_results(raw)


def static_search_from_env() -> StaticSearch:
    return StaticSearch(HarnessConfig.from_env())
