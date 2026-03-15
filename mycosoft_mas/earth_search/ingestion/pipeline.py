"""
Ingestion Pipeline — stores Earth Search results into MINDEX (Postgres/Qdrant) + Supabase + NLM training sink.

Fire-and-forget from the search orchestrator. Deduplicates by result_id.

Created: March 15, 2026
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from mycosoft_mas.earth_search.models import EarthSearchResult

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Ingests Earth Search results into local MINDEX, Supabase, and training sinks."""

    MINDEX_BASE = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
    TRAINING_SINK_DIR = Path("data/earth_search_training")
    SUPABASE_TABLE = "earth_search_results"

    def __init__(self):
        self._mindex_key = os.getenv("MINDEX_API_KEY", "")
        self._supabase_url = os.getenv("SUPABASE_URL", "")
        self._supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_KEY", "")
        self.TRAINING_SINK_DIR.mkdir(parents=True, exist_ok=True)

    async def ingest_batch(self, results: List[EarthSearchResult], query: str, session_id: Optional[str] = None):
        """Ingest a batch of search results into all sinks. Fire-and-forget safe."""
        if not results:
            return

        tasks = [
            self._ingest_mindex(results, query),
            self._ingest_training_sink(results, query, session_id),
        ]
        if self._supabase_url and self._supabase_key:
            tasks.append(self._ingest_supabase(results, query, session_id))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _ingest_mindex(self, results: List[EarthSearchResult], query: str):
        """Store results in local MINDEX Postgres via API."""
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._mindex_key:
            headers["X-API-Key"] = self._mindex_key

        payload = {
            "query": query,
            "results": [r.model_dump(mode="json") for r in results],
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "source": "earth_search",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.MINDEX_BASE}/api/mindex/earth-search/ingest",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code not in (200, 201, 202):
                    logger.warning("MINDEX ingest returned %d: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.warning("MINDEX ingest failed: %s", e)

    async def _ingest_supabase(self, results: List[EarthSearchResult], query: str, session_id: Optional[str]):
        """Store results in Supabase for cloud persistence and web access."""
        headers = {
            "apikey": self._supabase_key,
            "Authorization": f"Bearer {self._supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        rest_url = f"{self._supabase_url.rstrip('/')}/rest/v1/{self.SUPABASE_TABLE}"

        rows = []
        for r in results:
            rows.append({
                "result_id": r.result_id,
                "domain": r.domain.value,
                "source": r.source,
                "title": r.title,
                "description": r.description[:1000] if r.description else "",
                "data": json.dumps(r.data),
                "lat": r.lat,
                "lng": r.lng,
                "timestamp": r.timestamp.isoformat() if isinstance(r.timestamp, datetime) else r.timestamp,
                "confidence": r.confidence,
                "crep_layer": r.crep_layer,
                "mindex_id": r.mindex_id,
                "url": r.url,
                "image_url": r.image_url,
                "query": query,
                "session_id": session_id,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Upsert (POST with Prefer: resolution=merge-duplicates)
                headers["Prefer"] = "return=minimal,resolution=merge-duplicates"
                resp = await client.post(rest_url, json=rows, headers=headers)
                if resp.status_code not in (200, 201):
                    logger.warning("Supabase ingest returned %d: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.warning("Supabase ingest failed: %s", e)

    async def _ingest_training_sink(self, results: List[EarthSearchResult], query: str, session_id: Optional[str]):
        """Append results to JSONL training sink for NLM training."""
        sink_file = self.TRAINING_SINK_DIR / f"earth_search_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        try:
            lines = []
            for r in results:
                lines.append(json.dumps({
                    "query": query,
                    "session_id": session_id,
                    "result": r.model_dump(mode="json"),
                    "ts": datetime.now(timezone.utc).isoformat(),
                }))
            async with asyncio.Lock():
                with open(sink_file, "a", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
        except Exception as e:
            logger.warning("Training sink write failed: %s", e)
