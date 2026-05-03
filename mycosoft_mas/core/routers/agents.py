import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException

from ..security import get_current_user

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)

# Register static paths before /{agent_id} (May 02, 2026 — MYCA Alive P1D activity visibility)

api_agents_alias = APIRouter(prefix="/api/agents", tags=["agents-activity"])


def _agent_activity_payload(limit: int, since: Optional[int]) -> Dict[str, Any]:
    """Shared body for /agents/activity and /api/agents/activity."""
    from mycosoft_mas.myca.event_ledger.agent_activity_ledger import read_recent_lines

    events = read_recent_lines(max_lines=max(1, min(limit, 2000)))
    if since is not None:
        events = [e for e in events if isinstance(e, dict) and e.get("ts", 0) >= since]
    return {
        "count": len(events),
        "events": events,
        "ledger": "myca/event_ledger/agent_activity.jsonl",
        "since": since,
    }


@router.get("/activity")
async def get_agent_activity_ledger(
    limit: int = 200,
    since: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Recent JSONL activity from myca/event_ledger/agent_activity.jsonl.

    `since` is optional Unix timestamp — only events with ts >= since are returned
    (MYCA Alive: /api/agents/activity?since=... for 24h windows).

    Intentionally no Auth0 dependency so NatureOS BFF and topology can read activity;
    data is non-secret operational metadata only.
    """
    return _agent_activity_payload(limit, since)


@api_agents_alias.get("/activity")
async def get_api_agents_activity_ledger(
    limit: int = 200,
    since: Optional[int] = None,
) -> Dict[str, Any]:
    """Alias: BFFs and docs expect /api/agents/activity (same payload as /agents/activity)."""
    return _agent_activity_payload(limit, since)


def _heartbeat_stale_payload_for_agents(agents: Sequence[Any], stale_after_seconds: int) -> Dict[str, Any]:
    """Registered agents with no recent heartbeat (MYCA Alive P1D)."""
    now = datetime.now(timezone.utc)
    try:
        cutoff = now - timedelta(seconds=max(60, stale_after_seconds))
    except Exception:
        cutoff = now - timedelta(hours=24)

    def _aware(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    rows: List[Dict[str, Any]] = []
    stale_count = 0
    for a in agents:
        lh = _aware(a.last_heartbeat)
        stale = lh is None or lh < cutoff
        if stale:
            stale_count += 1
        cat = getattr(a.category, "value", a.category)
        rows.append(
            {
                "id": str(a.id),
                "name": a.name,
                "category": cat,
                "last_heartbeat": a.last_heartbeat.isoformat() if a.last_heartbeat else None,
                "stale": stale,
            }
        )

    return {
        "stale_after_seconds": stale_after_seconds,
        "total_registered": len(rows),
        "stale_count": stale_count,
        "agents": rows,
        "as_of": now.isoformat(),
    }


@router.get("/heartbeat/summary")
async def get_agent_heartbeat_stale_summary(
    stale_after_seconds: int = 86400,
) -> Dict[str, Any]:
    """
    Per-agent registry heartbeat with `stale` if last_heartbeat is older than `stale_after_seconds`
    (default 24h). Drives red indicators when combined with the JSONL activity ledger.
    No Auth0: operational metadata only.
    """
    from mycosoft_mas.registry.agent_registry import get_agent_registry

    reg = await get_agent_registry()
    return _heartbeat_stale_payload_for_agents(reg.get_all_agents(), stale_after_seconds)


@api_agents_alias.get("/heartbeat/summary")
async def get_api_agents_heartbeat_stale_summary(
    stale_after_seconds: int = 86400,
) -> Dict[str, Any]:
    from mycosoft_mas.registry.agent_registry import get_agent_registry

    reg = await get_agent_registry()
    return _heartbeat_stale_payload_for_agents(reg.get_all_agents(), stale_after_seconds)


@router.get("/")
async def get_agents(current_user: Dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Get all registered agents from the agent registry."""
    try:
        from mycosoft_mas.registry.agent_registry import AgentRegistry

        registry = AgentRegistry()
        agents = registry.get_all_agents()

        # Convert to dict format for API response
        return [
            {
                "id": str(agent.id),
                "name": agent.name,
                "category": agent.category.value,
                "description": agent.description,
                "status": agent.status.value,
                "capabilities": len(agent.capabilities),
                "version": agent.version,
                "registered_at": agent.registered_at.isoformat(),
                "last_heartbeat": (
                    agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
                ),
            }
            for agent in agents
        ]
    except Exception as e:
        logger.error(f"Error fetching agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching agents: {str(e)}")


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str, current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get agent by ID from the agent registry."""
    try:
        from mycosoft_mas.registry.agent_registry import AgentRegistry

        registry = AgentRegistry()
        agent = registry.get_agent(agent_id)

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        return {
            "id": str(agent.id),
            "name": agent.name,
            "category": agent.category.value,
            "description": agent.description,
            "module_path": agent.module_path,
            "class_name": agent.class_name,
            "status": agent.status.value,
            "version": agent.version,
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "requires_auth": cap.requires_auth,
                    "rate_limited": cap.rate_limited,
                }
                for cap in agent.capabilities
            ],
            "dependencies": agent.dependencies,
            "metadata": agent.metadata,
            "registered_at": agent.registered_at.isoformat(),
            "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching agent: {str(e)}")


@router.post("/{agent_id}/restart")
async def restart_agent(
    agent_id: str, current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Restart an agent - triggers agent lifecycle management."""
    try:
        from mycosoft_mas.registry.agent_registry import AgentRegistry

        registry = AgentRegistry()
        agent = registry.get_agent(agent_id)

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # Update agent status to initializing
        registry.update_agent_status(agent_id, "initializing")

        logger.info(f"Restart requested for agent: {agent.name} ({agent_id})")

        # Agent lifecycle management requires:
        # 1. Process supervisor to track agent processes
        # 2. Graceful shutdown with state saving
        # 3. Process restart with state restoration
        # 4. Health check verification after restart
        # 5. Registry update during lifecycle changes
        # Current status: Request logged, state updated to initializing

        return {
            "status": "accepted",
            "message": f"Agent {agent.name} restart request logged. Full lifecycle management implementation in progress.",
            "agent_id": agent_id,
            "agent_name": agent.name,
            "current_status": agent.status.value,
            "implementation_note": "Agent process supervision system under development. See docs/CODE_AUDIT_FEB13_2026.md for details.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error restarting agent: {str(e)}")


@router.get("/anomalies")
async def get_anomalies(
    limit: int = 50, severity: Optional[str] = None, current_user: Dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get detected anomalies from all anomaly detection agents.

    Queries:
    - ImmuneSystemAgent for security threats and vulnerabilities
    - DataAnalysisAgent for data anomalies
    - EnvironmentalPatternAgent for environmental anomalies
    - MyceliumPatternAgent for pattern anomalies

    Args:
        limit: Maximum number of anomalies to return (default 50)
        severity: Filter by severity level (critical, high, medium, low)

    Returns:
        List of anomaly detection results
    """
    anomalies = []

    try:
        # Query agent registry for anomaly detection agents
        from mycosoft_mas.registry.agent_registry import AgentRegistry

        registry = AgentRegistry()

        # Get agents that might have anomaly detection capabilities
        all_agents = registry.get_all_agents()
        anomaly_agents = [
            agent
            for agent in all_agents
            if any(
                cap
                in [
                    "anomaly_detection",
                    "threat_detection",
                    "security_monitoring",
                    "pattern_analysis",
                ]
                for cap in agent.capabilities
            )
        ]

        logger.info(f"Found {len(anomaly_agents)} anomaly detection agents")

        # For each agent, query their status/metrics for anomalies
        for agent in anomaly_agents:
            try:
                # Get agent metrics which may include anomaly data
                agent_metrics = agent.metadata.get("recent_anomalies", [])
                if isinstance(agent_metrics, list):
                    anomalies.extend(agent_metrics)
            except Exception as e:
                logger.warning(f"Could not fetch anomalies from {agent.name}: {e}")

        # Filter by severity if specified
        if severity:
            anomalies = [a for a in anomalies if a.get("severity") == severity.lower()]

        # Sort by timestamp (most recent first) and limit
        anomalies.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        anomalies = anomalies[:limit]

        logger.info(f"Returning {len(anomalies)} anomalies (limit={limit}, severity={severity})")

        return {
            "anomalies": anomalies,
            "count": len(anomalies),
            "total_agents_queried": len(anomaly_agents),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "active",
            "message": f"Queried {len(anomaly_agents)} anomaly detection agents",
        }

    except Exception as e:
        logger.error(f"Error fetching anomalies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching anomalies: {str(e)}")
