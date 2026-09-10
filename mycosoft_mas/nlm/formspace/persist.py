"""Persist NLM/ITDX artifacts to live MINDEX (189) and MYCA 6-layer memory.

Uses existing nlm.nature_embeddings. No new tables. No mock rows. Not Ollama.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

MINDEX_BASE = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
MINDEX_NMF = f"{MINDEX_BASE}/api/mindex/internal/nlm/nmf"
MEMORY_LAYERS = (
    "ephemeral",
    "session",
    "working",
    "semantic",
    "episodic",
    "system",
)


def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = (
        os.getenv("MINDEX_INTERNAL_TOKEN")
        or (os.getenv("MINDEX_INTERNAL_TOKENS", "").split(",")[0])
        or ""
    ).strip()
    key = (os.getenv("MINDEX_API_KEY") or os.getenv("MINDEX_INTERNAL_KEY") or "").strip()
    if token:
        headers["X-Internal-Token"] = token
    if key:
        headers["X-API-Key"] = key
    return headers


def _packet(kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "kind": kind,
        "schema": "nlm-itdx-retain/sep10-2026",
        "live": False,
        "forecast_qualified": False,
        "p": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }


async def persist_mindex_record(
    kind: str,
    payload: Dict[str, Any],
    source_id: Optional[str] = None,
) -> Dict[str, Any]:
    source = source_id or f"nlm-{kind}-{uuid.uuid4().hex[:12]}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            MINDEX_NMF,
            json={
                "source_id": source,
                "anomaly_score": 0.0,
                "packet": _packet(kind, payload),
            },
            headers=_headers(),
        )
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict) or not data.get("embedding_id"):
        raise RuntimeError("MINDEX persist returned no embedding_id")
    return {
        "ok": True,
        "embedding_id": data.get("embedding_id"),
        "ts": data.get("ts"),
        "source_id": source,
        "get_path": f"/api/mindex/internal/nlm/nmf/{data.get('embedding_id')}",
    }


async def get_mindex_record(embedding_id: str) -> Dict[str, Any]:
    url = f"{MINDEX_NMF}/{embedding_id}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, headers=_headers())
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("MINDEX GET returned a non-object")
    data["ok"] = True
    return data


async def remember_layers(
    content: Dict[str, Any],
    agent_id: str = "nlm-itdx",
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    from mycosoft_mas.core.routers.memory_api import _get_coordinator

    coordinator = await _get_coordinator()
    if not coordinator:
        return {"ok": False, "reason": "Memory coordinator unavailable", "layers": {}}
    layer_ids: Dict[str, Any] = {}
    for layer in MEMORY_LAYERS:
        memory_id = await coordinator.agent_remember(
            agent_id=agent_id,
            content={**content, "layer": layer},
            layer=layer,
            importance=0.8 if layer in {"semantic", "episodic", "system"} else 0.5,
            tags=list(tags or ["nlm", "itdx", "sep10"]),
        )
        layer_ids[layer] = str(memory_id) if memory_id else None
    episode_id = None
    if hasattr(coordinator, "record_episode"):
        episode_id = await coordinator.record_episode(
            agent_id=agent_id,
            event_type="nlm_decision",
            description=str(content.get("summary") or "NLM decision/assumption"),
            participants=["nlm", "myca", "avani"],
            context=content,
            outcome="advisory_unqualified",
            importance=0.8,
        )
    return {
        "ok": all(layer_ids.values()),
        "layers": layer_ids,
        "episode_id": str(episode_id) if episode_id else None,
        "bound_to_ollama": False,
    }


async def recall_decision(query: str, agent_id: str = "nlm-itdx") -> Dict[str, Any]:
    from mycosoft_mas.core.routers.memory_api import _get_coordinator

    coordinator = await _get_coordinator()
    if not coordinator:
        return {"ok": False, "reason": "Memory coordinator unavailable", "memories": []}
    memories = await coordinator.agent_recall(
        agent_id=agent_id,
        query=query,
        layer=None,
        tags=["nlm", "itdx"],
        limit=10,
    )
    return {
        "ok": True,
        "count": len(memories or []),
        "memories": memories or [],
        "bound_to_ollama": False,
    }


async def persist_decision_bundle(payload: Dict[str, Any]) -> Dict[str, Any]:
    mindex = await persist_mindex_record("decision_trace", payload)
    memory = await remember_layers(
        {
            "summary": payload.get("summary") or "NLM decision path",
            "mindex_embedding_id": mindex.get("embedding_id"),
            "p": None,
            "forecast_qualified": False,
            "tasks": payload.get("tasks") or [],
        }
    )
    return {"ok": True, "mindex": mindex, "memory": memory}
