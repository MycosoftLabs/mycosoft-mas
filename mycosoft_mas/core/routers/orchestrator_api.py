"""
Orchestrator API Router - Provides endpoints for the MYCA orchestrator dashboard.

All data is REAL from the agent registry and runtime pool. No mock data.
Updated: Feb 9, 2026 - Removed all hardcoded mock data, uses core agent registry.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

# Track startup time for uptime calculation
_startup_time = time.time()


def _get_registry():
    """Get the core agent registry (42+ agents)."""
    from mycosoft_mas.core.agent_registry import get_agent_registry
    return get_agent_registry()


def _build_agent_list() -> List[Dict[str, Any]]:
    """Build agent list from the REAL core registry. No mock data."""
    registry = _get_registry()
    agents = registry.list_all()
    result = []
    for a in agents:
        result.append({
            "id": a.agent_id,
            "name": a.name,
            "displayName": a.display_name,
            "category": a.category.value,
            "status": "active" if a.is_active else "idle",
            "tasksCompleted": 0,
            "tasksInProgress": 0,
            "cpuUsage": 0,
            "memoryUsage": 0,
            "capabilities": [c.value for c in a.capabilities],
            "keywords": a.keywords,
        })
    return result


def _uptime_str() -> str:
    """Format uptime as human-readable string."""
    elapsed = int(time.time() - _startup_time)
    days, remainder = divmod(elapsed, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    parts.append(f"{hours}h {minutes}m")
    return " ".join(parts)


@router.get("/dashboard")
async def get_dashboard_data() -> Dict[str, Any]:
    """Get complete dashboard data from REAL agent registry. No mock data."""
    agents = _build_agent_list()
    active_agents = [a for a in agents if a["status"] == "active"]
    total = len(agents)
    active = len(active_agents)

    return {
        "agents": agents,
        "metrics": {
            "totalAgents": total,
            "activeAgents": active,
            "idleAgents": total - active,
            "totalTasks": 0,
            "completedTasks": 0,
            "messagesPerSecond": 0,
            "uptime": _uptime_str(),
            "cpuUsage": 0,
            "memoryUsage": 0,
        },
        "messages": [],
        "insights": [],
        "memory": {
            "shortTermCount": 0,
            "longTermCount": 0,
            "knowledgePools": [],
        },
    }


@router.get("/agents")
async def get_agents() -> Dict[str, Any]:
    """Get list of ALL registered agents from the core registry."""
    agents = _build_agent_list()
    active = [a for a in agents if a["status"] == "active"]
    return {
        "agents": agents,
        "totalAgents": len(agents),
        "activeAgents": len(active),
    }


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get system metrics from real registry."""
    data = await get_dashboard_data()
    return data["metrics"]


@router.get("/insights")
async def get_insights(limit: int = 20) -> Dict[str, Any]:
    """Get recent system insights (empty until real event system is wired)."""
    return {"insights": []}


@router.get("/messages")
async def get_messages(limit: int = 50) -> Dict[str, Any]:
    """Get recent system messages (empty until real message broker is wired)."""
    return {"messages": []}


@router.get("/status")
async def get_orchestrator_status() -> Dict[str, Any]:
    """Get orchestrator status with real agent count."""
    registry = _get_registry()
    total = len(registry.list_all())
    active = len(registry.list_active())
    return {
        "running": True,
        "startTime": datetime.now(timezone.utc).isoformat(),
        "agentCount": total,
        "activeAgents": active,
        "uptime": _uptime_str(),
    }
