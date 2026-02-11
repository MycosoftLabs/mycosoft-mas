"""
MYCA System Status API Router

Provides unified status API for all Mycosoft systems:
- Agent states
- Sensor states (CREP, Earth2, NatureOS, MINDEX, MycoBrain)
- World model snapshot
- N8N workflow status
- LLM provider health
- MINDEX connectivity

Created: Feb 11, 2026
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System Status"])


class SensorStatus(BaseModel):
    """Status of a world sensor."""
    name: str
    connected: bool = False
    last_update: Optional[str] = None
    data_count: int = 0
    error: Optional[str] = None


class AgentStatus(BaseModel):
    """Status of an agent."""
    agent_id: str
    name: str
    status: str = "unknown"
    last_active: Optional[str] = None
    task_count: int = 0


class LLMProviderStatus(BaseModel):
    """Status of an LLM provider."""
    name: str
    available: bool = False
    last_check: Optional[str] = None
    error: Optional[str] = None


class SystemStatusResponse(BaseModel):
    """Complete system status response."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    consciousness_active: bool = True
    
    # Sensors
    crep_status: SensorStatus = Field(default_factory=lambda: SensorStatus(name="CREP"))
    earth2_status: SensorStatus = Field(default_factory=lambda: SensorStatus(name="Earth2"))
    natureos_status: SensorStatus = Field(default_factory=lambda: SensorStatus(name="NatureOS"))
    mindex_status: SensorStatus = Field(default_factory=lambda: SensorStatus(name="MINDEX"))
    mycobrain_status: SensorStatus = Field(default_factory=lambda: SensorStatus(name="MycoBrain"))
    
    # World data
    total_flights: int = 0
    total_vessels: int = 0
    total_satellites: int = 0
    active_devices: int = 0
    
    # Agent status
    total_agents: int = 0
    active_agents: int = 0
    agents: List[AgentStatus] = Field(default_factory=list)
    
    # LLM providers
    llm_providers: List[LLMProviderStatus] = Field(default_factory=list)
    
    # N8N status
    n8n_connected: bool = False
    workflows_active: int = 0
    
    # MINDEX status
    mindex_connected: bool = False
    knowledge_entries: int = 0


async def check_http_health(url: str, timeout: float = 5) -> tuple[bool, Optional[str]]:
    """Check HTTP health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return True, None
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)[:50]


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """
    Get complete system status overview.
    
    Returns status of all:
    - Sensors (CREP, Earth2, NatureOS, MINDEX, MycoBrain)
    - Agents
    - LLM providers
    - N8N workflows
    """
    status = SystemStatusResponse()
    
    # Run all checks in parallel
    tasks = []
    
    # Check CREP
    crep_url = os.environ.get("CREP_API_URL", "http://192.168.0.187:3000/api/crep")
    tasks.append(("crep", check_http_health(f"{crep_url}/health")))
    
    # Check Earth2
    earth2_url = os.environ.get("EARTH2_API_URL", "http://192.168.0.187:3000/api/earth2")
    tasks.append(("earth2", check_http_health(f"{earth2_url}/health")))
    
    # Check MINDEX
    mindex_url = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000")
    tasks.append(("mindex", check_http_health(f"{mindex_url}/health")))
    
    # Check N8N
    n8n_url = os.environ.get("N8N_WEBHOOK_URL", "http://192.168.0.188:5678")
    tasks.append(("n8n", check_http_health(f"{n8n_url.rstrip('/')}/healthz")))
    
    # Check LLM providers
    llm_providers = [
        ("Gemini", os.environ.get("GEMINI_API_KEY", "")),
        ("Claude", os.environ.get("ANTHROPIC_API_KEY", "")),
        ("GPT-4", os.environ.get("OPENAI_API_KEY", "")),
        ("Groq", os.environ.get("GROQ_API_KEY", "")),
        ("xAI", os.environ.get("XAI_API_KEY", "")),
    ]
    
    # Execute all checks
    results = {}
    for name, coro in tasks:
        try:
            results[name] = await coro
        except Exception as e:
            results[name] = (False, str(e))
    
    # Update CREP status
    connected, error = results.get("crep", (False, "Not checked"))
    status.crep_status = SensorStatus(
        name="CREP",
        connected=connected,
        last_update=datetime.now(timezone.utc).isoformat() if connected else None,
        error=error
    )
    
    # Update Earth2 status
    connected, error = results.get("earth2", (False, "Not checked"))
    status.earth2_status = SensorStatus(
        name="Earth2",
        connected=connected,
        last_update=datetime.now(timezone.utc).isoformat() if connected else None,
        error=error
    )
    
    # Update MINDEX status
    connected, error = results.get("mindex", (False, "Not checked"))
    status.mindex_status = SensorStatus(
        name="MINDEX",
        connected=connected,
        last_update=datetime.now(timezone.utc).isoformat() if connected else None,
        error=error
    )
    status.mindex_connected = connected
    
    # Update N8N status
    connected, error = results.get("n8n", (False, "Not checked"))
    status.n8n_connected = connected
    
    # Update LLM provider status
    now = datetime.now(timezone.utc).isoformat()
    for name, key in llm_providers:
        has_key = bool(key and len(key) > 10)
        status.llm_providers.append(LLMProviderStatus(
            name=name,
            available=has_key,
            last_check=now,
            error=None if has_key else "No API key configured"
        ))
    
    # Try to get agent status from orchestrator
    try:
        orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://127.0.0.1:8000")
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{orchestrator_url}/api/orchestrator/agents")
            if response.status_code == 200:
                data = response.json()
                agents = data.get("agents", [])
                status.total_agents = len(agents)
                status.active_agents = sum(1 for a in agents if a.get("status") == "active")
                status.agents = [
                    AgentStatus(
                        agent_id=a.get("agent_id", "unknown"),
                        name=a.get("name", "unknown"),
                        status=a.get("status", "unknown"),
                        last_active=a.get("last_active"),
                        task_count=a.get("task_count", 0)
                    )
                    for a in agents[:10]  # Limit to first 10
                ]
    except Exception as e:
        logger.warning(f"Could not get agent status: {e}")
    
    # Try to get CREP data counts
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{crep_url}/status")
            if response.status_code == 200:
                data = response.json()
                status.total_flights = data.get("flights", {}).get("count", 0)
                status.total_vessels = data.get("vessels", {}).get("count", 0)
                status.total_satellites = data.get("satellites", {}).get("count", 0)
    except Exception as e:
        logger.debug(f"Could not get CREP counts: {e}")
    
    return status


@router.get("/health")
async def system_health():
    """Quick health check for the MAS system."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "myca-mas",
        "version": "3.0.0"
    }


@router.get("/sensors")
async def get_sensor_status():
    """Get status of all world sensors."""
    sensors = []
    
    # Define sensors to check
    sensor_checks = [
        ("CREP", os.environ.get("CREP_API_URL", "http://192.168.0.187:3000/api/crep"), "/health"),
        ("Earth2", os.environ.get("EARTH2_API_URL", "http://192.168.0.187:3000/api/earth2"), "/health"),
        ("NatureOS", os.environ.get("NATUREOS_API_URL", "http://192.168.0.187:3000/api/natureos"), "/health"),
        ("MINDEX", os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000"), "/health"),
        ("MycoBrain", os.environ.get("MYCOBRAIN_API_URL", "http://192.168.0.188:8001/api/devices"), "/health"),
    ]
    
    for name, base_url, path in sensor_checks:
        connected, error = await check_http_health(f"{base_url}{path}")
        sensors.append({
            "name": name,
            "connected": connected,
            "url": base_url,
            "error": error
        })
    
    return {
        "sensors": sensors,
        "total": len(sensors),
        "connected": sum(1 for s in sensors if s["connected"]),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/llm")
async def get_llm_status():
    """Get status of LLM providers."""
    providers = []
    
    llm_configs = [
        ("Gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com"),
        ("Claude", "ANTHROPIC_API_KEY", "https://api.anthropic.com"),
        ("GPT-4", "OPENAI_API_KEY", "https://api.openai.com"),
        ("Groq", "GROQ_API_KEY", "https://api.groq.com"),
        ("xAI", "XAI_API_KEY", "https://api.x.ai"),
    ]
    
    for name, env_var, base_url in llm_configs:
        key = os.environ.get(env_var, "")
        has_key = bool(key and len(key) > 10)
        providers.append({
            "name": name,
            "configured": has_key,
            "key_prefix": key[:8] + "..." if has_key else None,
            "base_url": base_url
        })
    
    return {
        "providers": providers,
        "total": len(providers),
        "configured": sum(1 for p in providers if p["configured"]),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/agents")
async def get_agents_status():
    """Get status of all registered agents."""
    try:
        orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://127.0.0.1:8000")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{orchestrator_url}/api/orchestrator/agents")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Failed to get agents: {e}")
    
    return {
        "agents": [],
        "total": 0,
        "active": 0,
        "error": "Could not connect to orchestrator"
    }


@router.get("/world")
async def get_world_status():
    """Get current world model status."""
    try:
        from mycosoft_mas.consciousness.world_model import get_world_model
        world_model = get_world_model()
        
        if world_model:
            state = await world_model.get_state()
            return {
                "available": True,
                "state": state,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        logger.warning(f"Could not get world model: {e}")
    
    return {
        "available": False,
        "state": None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/n8n")
async def get_n8n_status():
    """Get N8N workflow automation status."""
    n8n_url = os.environ.get("N8N_WEBHOOK_URL", "http://192.168.0.188:5678")
    
    connected, error = await check_http_health(f"{n8n_url.rstrip('/')}/healthz")
    
    workflows = []
    if connected:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # N8N API to list workflows
                response = await client.get(
                    f"{n8n_url.rstrip('/')}/api/v1/workflows",
                    headers={"X-N8N-API-KEY": os.environ.get("N8N_API_KEY", "")}
                )
                if response.status_code == 200:
                    data = response.json()
                    workflows = data.get("data", [])[:10]
        except Exception as e:
            logger.debug(f"Could not list N8N workflows: {e}")
    
    return {
        "connected": connected,
        "url": n8n_url,
        "error": error,
        "workflows_count": len(workflows),
        "workflows": [
            {"id": w.get("id"), "name": w.get("name"), "active": w.get("active")}
            for w in workflows
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
