"""
Orchestrator API Router — March 19, 2026

Provides endpoints for the MYCA orchestrator dashboard (AI Studio / PersonaPlex).
All data is REAL from the agent registry, heartbeat service, and runner.

Updated: March 19, 2026 — Wired to heartbeat service for real runtime metrics.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from dataclasses import asdict
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


def _get_heartbeat_metrics() -> Dict[str, Any]:
    """Get per-agent runtime metrics from the heartbeat service."""
    try:
        from mycosoft_mas.core.agent_heartbeat_service import get_heartbeat_service
        svc = get_heartbeat_service()
        return {
            agent_id: m.to_dict()
            for agent_id, m in svc.agent_metrics.items()
        }
    except Exception:
        return {}


def _get_heartbeat_summary() -> Dict[str, Any]:
    """Get aggregate system metrics from the heartbeat service."""
    try:
        from mycosoft_mas.core.agent_heartbeat_service import get_heartbeat_service
        return get_heartbeat_service().get_system_summary()
    except Exception:
        return {}


def _get_runner_status() -> Dict[str, Any]:
    """Get runner status (recent cycles, insights, notifications)."""
    try:
        from mycosoft_mas.core.agent_runner import get_agent_runner
        import asyncio
        runner = get_agent_runner()
        # Return synchronous data (no await needed for these attributes)
        return {
            "running": runner.running,
            "agent_count": len(runner._agents),
            "total_cycles": len(runner.cycles),
            "total_insights": len(runner.insights),
            "total_notifications": len(runner.notifications),
            "recent_notifications": [
                asdict(n) for n in runner.notifications[-20:]
            ],
            "recent_insights": [
                asdict(i) for i in runner.insights[-20:]
            ],
        }
    except Exception:
        return {}


def _build_agent_list() -> List[Dict[str, Any]]:
    """Build agent list from REAL registry + REAL runtime metrics."""
    registry = _get_registry()
    agents = registry.list_all()
    hb_metrics = _get_heartbeat_metrics()
    result = []
    for a in agents:
        metrics = hb_metrics.get(a.agent_id, {})
        runtime_status = metrics.get("status", "idle") if metrics else "idle"
        # If agent is in registry and marked active, show at least "idle"
        if a.is_active and runtime_status == "idle" and not metrics:
            runtime_status = "registered"

        result.append({
            "id": a.agent_id,
            "name": a.name,
            "displayName": a.display_name,
            "category": a.category.value,
            "status": runtime_status,
            "tasksCompleted": metrics.get("tasks_completed", 0),
            "tasksFailed": metrics.get("tasks_failed", 0),
            "insightsGenerated": metrics.get("insights_generated", 0),
            "cycleCount": metrics.get("cycle_count", 0),
            "lastCycleTime": metrics.get("last_cycle_time"),
            "consecutiveErrors": metrics.get("consecutive_errors", 0),
            "lastError": metrics.get("last_error"),
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
    """Get complete dashboard data from REAL agent registry + runtime metrics."""
    agents = _build_agent_list()
    summary = _get_heartbeat_summary()
    runner = _get_runner_status()

    total = len(agents)
    active = sum(1 for a in agents if a["status"] in ("active", "registered"))
    idle = sum(1 for a in agents if a["status"] == "idle")

    # Get Redis pub/sub stats for messages/second
    try:
        from mycosoft_mas.realtime.redis_pubsub import get_client
        client = await get_client()
        pubsub_stats = client.get_stats()
        msgs_published = pubsub_stats.get("messages_published", 0)
    except Exception:
        msgs_published = 0

    return {
        "agents": agents,
        "metrics": {
            "totalAgents": total,
            "activeAgents": active,
            "idleAgents": idle,
            "errorAgents": summary.get("error_agents", 0),
            "degradedAgents": summary.get("degraded_agents", 0),
            "totalTasks": summary.get("total_tasks_completed", 0),
            "completedTasks": summary.get("total_tasks_completed", 0),
            "totalErrors": summary.get("total_errors", 0),
            "totalInsights": summary.get("total_insights", 0),
            "messagesPublished": msgs_published,
            "uptime": _uptime_str(),
            "cpuUsage": summary.get("cpu_usage", 0),
            "memoryUsage": summary.get("memory_usage", 0),
            "redisConnected": summary.get("redis_connected", False),
        },
        "messages": runner.get("recent_notifications", []),
        "insights": runner.get("recent_insights", []),
        "runner": {
            "running": runner.get("running", False),
            "totalCycles": runner.get("total_cycles", 0),
            "agentsLoaded": runner.get("agent_count", 0),
        },
    }


@router.get("/agents")
async def get_agents() -> Dict[str, Any]:
    """Get list of ALL registered agents with real runtime status."""
    agents = _build_agent_list()
    active = [a for a in agents if a["status"] in ("active", "registered")]
    return {
        "agents": agents,
        "totalAgents": len(agents),
        "activeAgents": len(active),
    }


@router.get("/agents/{agent_id}")
async def get_agent_detail(agent_id: str) -> Dict[str, Any]:
    """Get detailed info for a specific agent."""
    registry = _get_registry()
    definition = registry.get(agent_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    hb_metrics = _get_heartbeat_metrics()
    metrics = hb_metrics.get(agent_id, {})

    return {
        "id": definition.agent_id,
        "name": definition.name,
        "displayName": definition.display_name,
        "description": definition.description,
        "category": definition.category.value,
        "capabilities": [c.value for c in definition.capabilities],
        "modulePath": definition.module_path,
        "className": definition.class_name,
        "keywords": definition.keywords,
        "voiceTriggers": definition.voice_triggers,
        "requiresConfirmation": definition.requires_confirmation,
        "isActive": definition.is_active,
        "runtime": metrics,
    }


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get real system metrics from heartbeat service."""
    summary = _get_heartbeat_summary()
    agents = _build_agent_list()
    return {
        "totalAgents": len(agents),
        "activeAgents": summary.get("active_agents", 0),
        "totalTasks": summary.get("total_tasks_completed", 0),
        "totalErrors": summary.get("total_errors", 0),
        "totalInsights": summary.get("total_insights", 0),
        "cpuUsage": summary.get("cpu_usage", 0),
        "memoryUsage": summary.get("memory_usage", 0),
        "uptime": _uptime_str(),
        "redisConnected": summary.get("redis_connected", False),
    }


@router.get("/insights")
async def get_insights(limit: int = 20) -> Dict[str, Any]:
    """Get recent system insights from the agent runner."""
    runner = _get_runner_status()
    insights = runner.get("recent_insights", [])[:limit]
    return {"insights": insights, "total": len(insights)}


@router.get("/messages")
async def get_messages(limit: int = 50) -> Dict[str, Any]:
    """Get recent system messages/notifications from the agent runner."""
    runner = _get_runner_status()
    messages = runner.get("recent_notifications", [])[:limit]
    return {"messages": messages, "total": len(messages)}


@router.get("/status")
async def get_orchestrator_status() -> Dict[str, Any]:
    """Get orchestrator status with real runtime data."""
    registry = _get_registry()
    summary = _get_heartbeat_summary()
    runner = _get_runner_status()
    total = len(registry.list_all())

    return {
        "running": runner.get("running", True),
        "startTime": datetime.fromtimestamp(_startup_time, tz=timezone.utc).isoformat(),
        "agentCount": total,
        "activeAgents": summary.get("active_agents", 0),
        "runnerCycles": runner.get("total_cycles", 0),
        "uptime": _uptime_str(),
        "redisConnected": summary.get("redis_connected", False),
    }
