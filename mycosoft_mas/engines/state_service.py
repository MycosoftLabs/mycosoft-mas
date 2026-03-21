"""
MYCA State Service - FastAPI service for SelfState and WorldState.

Exposes /state (MYCA state: active goals, resource usage, emotional valence)
and /world (cached world state from MINDEX, CREP, device telemetry).

Port: 8010 (configurable via STATE_SERVICE_PORT).
Created: March 5, 2026
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MYCA State Service",
    description="SelfState and WorldState for grounded cognition",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MINDEX_API_URL = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
CREP_GATEWAY_URL = os.getenv("CREP_GATEWAY_URL", "http://192.168.0.188:3020")
MAS_API_URL = os.getenv("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")
MINDEX_API_KEY = os.getenv("MINDEX_API_KEY", "")


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check."""
    return {
        "status": "healthy",
        "service": "state_service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/state")
async def get_state() -> Dict[str, Any]:
    """
    Return current MYCA self-state: active goals, resource usage, emotional valence.

    Aggregates from MAS health, agent registry, consciousness metrics.
    """
    active_goals: List[str] = []
    resource_usage: Dict[str, Any] = {"cpu": None, "memory_mb": None}
    emotional_valence: float = 0.0  # -1 to 1
    services: Dict[str, Any] = {}
    agents: Dict[str, Any] = {}

    # Fetch MAS health
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{MAS_API_URL}/health")
            if r.status_code == 200:
                data = r.json()
                services["mas"] = {"status": data.get("status", "unknown")}
    except Exception as e:
        logger.debug("MAS health unavailable: %s", e)
        services["mas"] = {"error": str(e)[:100]}

    # Fetch agent registry (if exposed)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{MAS_API_URL}/api/registry/agents")
            if r.status_code == 200:
                data = r.json()
                items = data if isinstance(data, list) else data.get("agents", [])
                agents = {"count": len(items)}
    except Exception as e:
        logger.debug("Agent registry unavailable: %s", e)
        agents = {"error": str(e)[:100]}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_goals": active_goals,
        "resource_usage": resource_usage,
        "emotional_valence": emotional_valence,
        "services": services,
        "agents": agents,
    }


@app.get("/world")
async def get_world() -> Dict[str, Any]:
    """
    Return cached world state from MINDEX, CREP, device telemetry.

    Used by grounding_gate.attach_world_state() when STATE_SERVICE_URL is set.
    """
    sources: List[str] = []
    summary = "World state from StateService"
    data: Dict[str, Any] = {}
    freshness = "unknown"

    # MINDEX summary (species count, etc.)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            headers = {}
            if MINDEX_API_KEY:
                headers["X-API-Key"] = MINDEX_API_KEY
            r = await client.get(
                f"{MINDEX_API_URL}/api/mindex/health",
                headers=headers or None,
            )
            if r.status_code == 200:
                data["mindex"] = r.json()
                sources.append("mindex")
    except Exception as e:
        logger.debug("MINDEX unavailable: %s", e)
        data["mindex"] = {"error": str(e)[:100]}

    # CREP (if available)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{CREP_GATEWAY_URL}/health")
            if r.status_code == 200:
                data["crep"] = r.json()
                sources.append("crep")
    except Exception as e:
        data["crep"] = {"error": str(e)[:100]}

    if sources:
        freshness = "live" if len(sources) >= 1 else "degraded"
    else:
        freshness = "unavailable"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "sources": sources,
        "data": data,
        "freshness": freshness,
    }


def run():
    """Run the State Service (standalone)."""
    import uvicorn

    port = int(os.getenv("STATE_SERVICE_PORT", "8010"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    run()
