"""
Search registration and training sinks — off hot path.

After search completes, persist to MINDEX answer schema and register for ETL/NLM/LLM training.
All I/O is fire-and-forget so the search response is not blocked.

Created: March 14, 2026
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# MINDEX API base; search answers live at {base}/api/mindex/search/answers
_MINDEX_BASE = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
MINDEX_SEARCH_ANSWERS_URL = f"{_MINDEX_BASE}/api/mindex/search/answers"
TRAINING_SINK_PATH = Path(os.getenv("SEARCH_TRAINING_SINK_PATH", "data/search_training_sink.jsonl"))


def _normalize_query(q: str) -> str:
    return q.strip().lower() if q else ""


def _result_hash(query: str, payload: Dict[str, Any]) -> str:
    """Stable hash for query + top result summary for dedup/cache."""
    parts = [_normalize_query(query)]
    for key in ("keyword", "semantic"):
        results = payload.get("results", {}).get(key) or []
        for i, r in enumerate(results[:3]):
            if isinstance(r, dict):
                parts.append(str(r.get("id") or r.get("scientific_name") or r.get("title") or r))
            else:
                parts.append(str(r))
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _snippet_from_payload(payload: Dict[str, Any], max_len: int = 1000) -> str:
    """Build a short displayable snippet from search result payload."""
    parts: List[str] = []
    focus = payload.get("focus") or ""
    if focus:
        parts.append(focus[:500])
    for key in ("keyword", "semantic"):
        results = payload.get("results", {}).get(key) or []
        for r in results[:2]:
            if isinstance(r, dict):
                name = r.get("scientific_name") or r.get("title") or r.get("name") or ""
                desc = r.get("description") or r.get("summary") or ""
                if name or desc:
                    parts.append((name + " " + desc).strip()[:300])
            elif isinstance(r, str):
                parts.append(r[:300])
    text = " ".join(parts).strip()
    return text[:max_len] if text else "Search completed."


async def persist_search_to_mindex(
    query: str,
    payload: Dict[str, Any],
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Persist normalized query and answer snippet to MINDEX search schema.
    Called off hot path (e.g. asyncio.create_task). Swallows errors.
    """
    norm = _normalize_query(query)
    if not norm:
        return
    snippet = _snippet_from_payload(payload)
    prov = {
        "result_hash": _result_hash(query, payload),
        "sources": list((payload.get("results") or {}).keys()),
        "timestamp": payload.get("timestamp"),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            body = {
                "normalized_query": norm,
                "snippet_text": snippet,
                "source_type": "orchestrator",
                "source_id": "mas-search",
                "provenance": prov,
                "session_id": session_id,
                "user_id": user_id,
            }
            r = await client.post(MINDEX_SEARCH_ANSWERS_URL, json=body)
            if r.is_success:
                logger.debug("MINDEX answer snippet persisted for query=%s", norm[:50])
            else:
                logger.warning("MINDEX persist failed: %s %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.warning("MINDEX search registration failed: %s", e)


async def register_training_sink(query: str, payload: Dict[str, Any]) -> None:
    """
    Append query + result summary to the training sink file for NLM/LLM curation.
    Off hot path; failures are logged only.
    """
    norm = _normalize_query(query)
    if not norm:
        return
    try:
        TRAINING_SINK_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "query": norm,
            "result_hash": _result_hash(query, payload),
            "focus": payload.get("focus"),
            "sources": list((payload.get("results") or {}).keys()),
            "timestamp": payload.get("timestamp"),
        }
        with open(TRAINING_SINK_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.debug("Training sink appended for query=%s", norm[:50])
    except Exception as e:
        logger.warning("Training sink append failed: %s", e)


async def register_etl_intake_if_live(query: str, payload: Dict[str, Any]) -> None:
    """
    If this query required live specialist/external fetches, register an ETL intake task.
    Stub: log and optionally enqueue for future ETL jobs.
    """
    specialist = (payload.get("results") or {}).get("specialist") or {}
    if not specialist:
        return
    # Had specialist results — could push to a queue or call ETL endpoint
    logger.info(
        "ETL intake candidate: query=%s sources=%s",
        query[:80],
        list(specialist.keys()),
    )
