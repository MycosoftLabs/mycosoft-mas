"""
Dashboard Router — March 19, 2026

Real system metrics from the agent heartbeat service, health checker,
and agent registry. NO hardcoded zeros.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_startup_time = time.time()


def _get_heartbeat_summary() -> Dict[str, Any]:
    """Get real metrics from the heartbeat service."""
    try:
        from mycosoft_mas.core.agent_heartbeat_service import get_heartbeat_service
        return get_heartbeat_service().get_system_summary()
    except Exception:
        return {}


def _get_registry_count() -> int:
    """Get total registered agents from the real registry."""
    try:
        from mycosoft_mas.core.agent_registry import get_agent_registry
        return len(get_agent_registry().list_all())
    except Exception:
        return 0


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


@router.get("/")
async def get_dashboard_data(
    current_user: Dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get dashboard data from real system metrics."""
    summary = _get_heartbeat_summary()
    registry_count = _get_registry_count()

    # Use heartbeat data if available, fall back to registry count
    agent_count = summary.get("total_agents", 0) or registry_count

    return {
        "metrics": {
            "agent_count": agent_count,
            "active_agents": summary.get("active_agents", 0),
            "degraded_agents": summary.get("degraded_agents", 0),
            "error_agents": summary.get("error_agents", 0),
            "task_count": summary.get("total_tasks_completed", 0),
            "error_count": summary.get("total_errors", 0),
            "insights_count": summary.get("total_insights", 0),
            "cpu_usage": summary.get("cpu_usage", 0),
            "memory_usage": summary.get("memory_usage", 0),
            "last_update": summary.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "uptime": _uptime_str(),
            "redis_connected": summary.get("redis_connected", False),
            "heartbeat_count": summary.get("heartbeat_count", 0),
            "registry_agents": registry_count,
        }
    }


@router.get("/health")
async def get_system_health(
    current_user: Dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get system health data from real checks."""
    summary = _get_heartbeat_summary()
    registry_count = _get_registry_count()

    total = summary.get("total_agents", 0) or registry_count
    active = summary.get("active_agents", 0)
    errors = summary.get("error_agents", 0)
    degraded = summary.get("degraded_agents", 0)

    # Calculate health score
    if total == 0:
        health_score = 100
        status = "healthy"
    else:
        health_score = max(0, int(100 - (errors / total * 50) - (degraded / total * 20)))
        if errors > total * 0.3:
            status = "unhealthy"
        elif degraded > total * 0.2 or errors > 0:
            status = "degraded"
        else:
            status = "healthy"

    # Check infrastructure health
    infra_health = {}
    try:
        from mycosoft_mas.monitoring.health_check import HealthChecker
        checker = HealthChecker()
        db_health = await checker.check_database()
        redis_health = await checker.check_redis()
        infra_health = {
            "postgresql": {
                "status": db_health.status.value,
                "latency_ms": db_health.latency_ms,
                "message": db_health.message,
            },
            "redis": {
                "status": redis_health.status.value,
                "latency_ms": redis_health.latency_ms,
                "message": redis_health.message,
            },
        }
    except Exception:
        pass

    return {
        "status": status,
        "uptime": _uptime_str(),
        "system_health": health_score,
        "active_agents": active,
        "total_agents": total,
        "degraded_agents": degraded,
        "error_agents": errors,
        "infrastructure": infra_health,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
