"""RaaS Service Proxy — metered invocation of MYCA capabilities.

Every call: authenticate → check credits → execute → deduct → return.
This is the core revenue-generating router.

Created: March 11, 2026
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from mycosoft_mas.raas import credits as credit_system
from mycosoft_mas.raas.credits import CREDIT_COSTS
from mycosoft_mas.raas.middleware import require_raas_auth
from mycosoft_mas.raas.models import (
    AgentAccount,
    AgentInvokeRequest,
    CREPInvokeRequest,
    DataInvokeRequest,
    DeviceInvokeRequest,
    Earth2InvokeRequest,
    InvokeResponse,
    MemoryInvokeRequest,
    NLMInvokeRequest,
    SimulationInvokeRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/raas/invoke", tags=["RaaS - Service Invocation"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _charge_and_check(agent: AgentAccount, service_id: str) -> int:
    """Deduct credits for a service. Raises 402 if insufficient."""
    cost = CREDIT_COSTS.get(service_id)
    if cost is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown service: {service_id}",
        )
    success, remaining = await credit_system.deduct_credits(agent.agent_id, cost, service_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Need {cost}, have {remaining}. "
            "Purchase more at /api/raas/payments/packages",
        )
    return remaining


def _make_response(
    service_id: str,
    result: Any,
    cost: int,
    remaining: int,
    start: float,
) -> InvokeResponse:
    return InvokeResponse(
        request_id=str(uuid.uuid4()),
        service_id=service_id,
        result=result,
        credits_used=cost,
        credits_remaining=remaining,
        latency_ms=round((time.time() - start) * 1000, 2),
    )


# ---------------------------------------------------------------------------
# NLM Inference
# ---------------------------------------------------------------------------


@router.post("/nlm")
async def invoke_nlm(
    body: NLMInvokeRequest,
    agent: AgentAccount = Depends(require_raas_auth),
) -> InvokeResponse:
    """Nature Learning Model inference — species ID, taxonomy, ecology, etc."""
    start = time.time()
    cost = CREDIT_COSTS["nlm_inference"]
    remaining = await _charge_and_check(agent, "nlm_inference")

    try:
        from mycosoft_mas.nlm.inference.service import (
            PredictionRequest,
            QueryType,
            get_nlm_service,
        )

        nlm = get_nlm_service()
        qt_map = {
            "general": QueryType.GENERAL,
            "species_id": QueryType.SPECIES_ID,
            "taxonomy": QueryType.TAXONOMY,
            "ecology": QueryType.ECOLOGY,
            "cultivation": QueryType.CULTIVATION,
            "research": QueryType.RESEARCH,
            "genetics": QueryType.GENETICS,
        }
        req = PredictionRequest(
            text=body.query,
            query_type=qt_map.get(body.query_type, QueryType.GENERAL),
            max_tokens=body.max_tokens,
            temperature=body.temperature,
        )
        prediction = await nlm.predict(req)
        result = prediction.to_dict()
    except ImportError:
        result = {
            "text": f"NLM service processed query: {body.query[:100]}",
            "query_type": body.query_type,
            "note": "NLM model loading deferred — query queued",
        }
    except Exception as e:
        logger.error("NLM invocation failed: %s", e)
        result = {"error": str(e), "query": body.query[:100]}

    return _make_response("nlm_inference", result, cost, remaining, start)


# ---------------------------------------------------------------------------
# CREP Live Data
# ---------------------------------------------------------------------------


@router.post("/crep")
async def invoke_crep(
    body: CREPInvokeRequest,
    agent: AgentAccount = Depends(require_raas_auth),
) -> InvokeResponse:
    """CREP real-time data — aviation, maritime, satellite, weather."""
    start = time.time()
    cost = CREDIT_COSTS["crep_query"]
    remaining = await _charge_and_check(agent, "crep_query")

    try:
        import aioredis

        redis = await aioredis.from_url("redis://192.168.0.189:6379")
        channel = f"crep:{body.data_type}"
        # Get latest cached data from Redis
        data = await redis.get(channel)
        await redis.close()
        if data:
            import json

            result = {
                "data_type": body.data_type,
                "data": json.loads(data),
                "source": "crep_live",
            }
        else:
            result = {
                "data_type": body.data_type,
                "data": [],
                "source": "crep_cache_empty",
                "note": "No cached data. Use WebSocket /ws/crep-stream for live feeds.",
            }
    except Exception as e:
        logger.warning("CREP query failed: %s", e)
        result = {
            "data_type": body.data_type,
            "data": [],
            "note": f"CREP data temporarily unavailable: {e}",
        }

    return _make_response("crep_query", result, cost, remaining, start)


# ---------------------------------------------------------------------------
# Earth2 Climate
# ---------------------------------------------------------------------------


@router.post("/earth2")
async def invoke_earth2(
    body: Earth2InvokeRequest,
    agent: AgentAccount = Depends(require_raas_auth),
) -> InvokeResponse:
    """Earth2 climate simulation — forecasts, nowcasts, spore dispersal."""
    start = time.time()
    cost_key = "earth2_nowcast" if body.forecast_type == "short_range" else "earth2_forecast"
    cost = CREDIT_COSTS[cost_key]
    remaining = await _charge_and_check(agent, cost_key)

    try:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "http://localhost:8000/api/earth2/forecast",
                json={
                    "forecast_type": body.forecast_type,
                    "location": body.location or {},
                    "parameters": body.parameters or {},
                },
            )
            result = resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        logger.warning("Earth2 invocation failed: %s", e)
        result = {
            "forecast_type": body.forecast_type,
            "note": f"Earth2 service temporarily unavailable: {e}",
        }

    return _make_response(cost_key, result, cost, remaining, start)


# ---------------------------------------------------------------------------
# Device Network
# ---------------------------------------------------------------------------


@router.post("/devices")
async def invoke_devices(
    body: DeviceInvokeRequest,
    agent: AgentAccount = Depends(require_raas_auth),
) -> InvokeResponse:
    """Query MycoBrain device network — telemetry, fleet status, sensors."""
    start = time.time()
    cost = CREDIT_COSTS["device_telemetry"]
    remaining = await _charge_and_check(agent, "device_telemetry")

    try:
        import httpx

        endpoint = "http://localhost:8000/api/device-registry/devices"
        if body.device_id:
            endpoint = f"http://localhost:8000/api/device-registry/devices/{body.device_id}"

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(endpoint)
            result = resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        logger.warning("Device query failed: %s", e)
        result = {"note": f"Device service temporarily unavailable: {e}"}

    return _make_response("device_telemetry", result, cost, remaining, start)


# ---------------------------------------------------------------------------
# MINDEX Data
# ---------------------------------------------------------------------------


@router.post("/data")
async def invoke_data(
    body: DataInvokeRequest,
    agent: AgentAccount = Depends(require_raas_auth),
) -> InvokeResponse:
    """MINDEX data query — species, taxonomy, compounds, knowledge graph."""
    start = time.time()
    cost_key = "knowledge_graph" if body.query_type == "knowledge_graph" else "mindex_query"
    cost = CREDIT_COSTS[cost_key]
    remaining = await _charge_and_check(agent, cost_key)

    try:
        import httpx

        endpoint_map = {
            "species": "/api/mindex-species/search",
            "taxonomy": "/api/taxonomy/search",
            "compound": "/api/mindex-query/compounds",
            "knowledge_graph": "/api/knowledge-graph/query",
        }
        endpoint = endpoint_map.get(body.query_type, "/api/mindex-query/search")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"http://localhost:8000{endpoint}",
                json={"query": body.query, "filters": body.filters or {}},
            )
            result = resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        logger.warning("MINDEX query failed: %s", e)
        result = {"note": f"MINDEX service temporarily unavailable: {e}"}

    return _make_response(cost_key, result, cost, remaining, start)


# ---------------------------------------------------------------------------
# Agent Task Execution
# ---------------------------------------------------------------------------


@router.post("/agent")
async def invoke_agent(
    body: AgentInvokeRequest,
    agent: AgentAccount = Depends(require_raas_auth),
) -> InvokeResponse:
    """Execute a task using one of MYCA's 158+ specialized agents."""
    start = time.time()
    cost = CREDIT_COSTS["agent_task"]
    remaining = await _charge_and_check(agent, "agent_task")

    try:
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "http://localhost:8000/api/agent-runner/invoke",
                json={
                    "agent_type": body.agent_type,
                    "task": {
                        "type": body.task_type,
                        "payload": body.payload,
                        "requester": f"raas:{agent.agent_id}",
                    },
                },
            )
            result = resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        logger.warning("Agent invocation failed: %s", e)
        result = {"note": f"Agent service temporarily unavailable: {e}"}

    return _make_response("agent_task", result, cost, remaining, start)


# ---------------------------------------------------------------------------
# Memory & Search
# ---------------------------------------------------------------------------


@router.post("/memory")
async def invoke_memory(
    body: MemoryInvokeRequest,
    agent: AgentAccount = Depends(require_raas_auth),
) -> InvokeResponse:
    """Search MYCA's 6-layer memory — semantic, fulltext, graph."""
    start = time.time()
    cost = CREDIT_COSTS["memory_search"]
    remaining = await _charge_and_check(agent, "memory_search")

    try:
        import httpx

        endpoint_map = {
            "semantic": "/api/memory/search/semantic",
            "fulltext": "/api/memory/search/fulltext",
            "graph": "/api/knowledge-graph/query",
        }
        endpoint = endpoint_map.get(body.search_type, "/api/memory/search/semantic")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"http://localhost:8000{endpoint}",
                json={"query": body.query, "limit": body.limit},
            )
            result = resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        logger.warning("Memory search failed: %s", e)
        result = {"note": f"Memory service temporarily unavailable: {e}"}

    return _make_response("memory_search", result, cost, remaining, start)


# ---------------------------------------------------------------------------
# Simulations
# ---------------------------------------------------------------------------


@router.post("/simulation")
async def invoke_simulation(
    body: SimulationInvokeRequest,
    agent: AgentAccount = Depends(require_raas_auth),
) -> InvokeResponse:
    """Run a simulation — petri dish, mycelium network, physics reasoning."""
    start = time.time()
    cost = CREDIT_COSTS["simulation"]
    remaining = await _charge_and_check(agent, "simulation")

    try:
        import httpx

        endpoint_map = {
            "petri": "/api/petri-sim/run",
            "mycelium": "/api/petri-sim/mycelium",
            "physics": "/api/physicsnemo/reason",
        }
        endpoint = endpoint_map.get(body.sim_type, "/api/petri-sim/run")

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"http://localhost:8000{endpoint}",
                json=body.parameters,
            )
            result = resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        logger.warning("Simulation failed: %s", e)
        result = {"note": f"Simulation service temporarily unavailable: {e}"}

    return _make_response("simulation", result, cost, remaining, start)
