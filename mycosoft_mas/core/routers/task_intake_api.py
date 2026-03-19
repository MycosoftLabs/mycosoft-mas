"""
Unified Task Intake API — March 19, 2026

Canonical entry point for submitting tasks to the MAS. Routes tasks to the
appropriate agent based on intent classification, publishes to Redis for
real-time tracking, and records in the event ledger.

Previously tasks could enter via orchestrator_api, agent_runner_api, a2a_api,
or ingest_api — but there was no single canonical intake with routing + tracking.

NO MOCK DATA — Routes to real agents via the registry + runner.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["Task Intake"])


class TaskSubmission(BaseModel):
    """A task to submit to the MAS."""
    description: str = Field(..., description="What needs to be done")
    task_type: Optional[str] = Field(None, description="Explicit task type (query, etl, search, deploy, etc.)")
    target_agent: Optional[str] = Field(None, description="Specific agent ID to route to")
    priority: str = Field("normal", description="low, normal, high, critical")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Additional task data")
    source: str = Field("user", description="Who submitted (user, agent, n8n, api)")


class TaskStatus(BaseModel):
    task_id: str
    status: str
    agent_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    submitted_at: str
    completed_at: Optional[str] = None


# In-memory task store (recent tasks for dashboard visibility)
_task_store: Dict[str, Dict[str, Any]] = {}


def _route_task_to_agent(task: TaskSubmission) -> Optional[str]:
    """Route a task to the best-fit agent based on keywords and type."""
    if task.target_agent:
        return task.target_agent

    try:
        from mycosoft_mas.core.agent_registry import get_agent_registry
        registry = get_agent_registry()

        # Try type-based routing
        type_to_agent = {
            "query": "mindex-agent",
            "search": "search-agent",
            "etl": "etl-agent",
            "deploy": "deployment-agent",
            "security": "security-agent",
            "finance": "financial-agent",
            "mycology": "mycology-bio-agent",
            "scientific": "lab-agent",
            "earth2": "earth2-orchestrator",
        }
        if task.task_type and task.task_type.lower() in type_to_agent:
            agent_id = type_to_agent[task.task_type.lower()]
            if registry.get(agent_id):
                return agent_id

        # Try keyword-based routing
        description_lower = task.description.lower()
        results = registry.find_by_keyword(description_lower[:50])
        if results:
            return results[0].agent_id

        # Default to manager agent for routing
        return "manager-agent"
    except Exception:
        return "manager-agent"


@router.post("/submit")
async def submit_task(task: TaskSubmission) -> Dict[str, Any]:
    """Submit a task to the MAS for processing.

    The task is routed to the best-fit agent, published to Redis for
    real-time tracking, and recorded in the event ledger.
    """
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    # Route to agent
    agent_id = _route_task_to_agent(task)

    # Store task
    task_record = {
        "task_id": task_id,
        "description": task.description,
        "task_type": task.task_type,
        "target_agent": agent_id,
        "priority": task.priority,
        "payload": task.payload,
        "source": task.source,
        "status": "submitted",
        "submitted_at": now,
        "completed_at": None,
        "result": None,
    }
    _task_store[task_id] = task_record

    # Publish to Redis tasks:progress channel
    try:
        from mycosoft_mas.realtime.redis_pubsub import get_client, Channel

        client = await get_client()
        if client.is_connected():
            await client.publish(
                Channel.TASK_PROGRESS.value,
                {
                    "event": "task_submitted",
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "description": task.description,
                    "priority": task.priority,
                    "source": task.source,
                },
                source="task_intake",
            )
    except Exception as e:
        logger.debug(f"Could not publish task to Redis: {e}")

    # Log to event ledger
    try:
        from mycosoft_mas.myca.event_ledger.ledger_writer import get_ledger
        ledger = get_ledger()
        ledger.log_tool_call(
            agent=task.source,
            tool_name="task_submit",
            args_hash=f"task:{task_id}",
            result_status="success",
        )
    except Exception:
        pass

    # Queue task in the runner if agent is available
    try:
        from mycosoft_mas.core.agent_runner import get_agent_runner
        runner = get_agent_runner()
        for agent in runner._agents:
            aid = getattr(agent, "agent_id", None)
            if aid == agent_id and hasattr(agent, "task_queue"):
                await agent.task_queue.put(task.payload)
                task_record["status"] = "queued"
                break
    except Exception:
        pass

    return {
        "task_id": task_id,
        "status": task_record["status"],
        "routed_to": agent_id,
        "submitted_at": now,
    }


@router.get("/status/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the status of a submitted task."""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task


@router.get("/recent")
async def get_recent_tasks(
    limit: int = 50,
    status: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """Get recent submitted tasks."""
    tasks = list(_task_store.values())

    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if source:
        tasks = [t for t in tasks if t["source"] == source]

    # Sort by submitted_at descending
    tasks.sort(key=lambda t: t["submitted_at"], reverse=True)
    tasks = tasks[:limit]

    return {
        "tasks": tasks,
        "total": len(tasks),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/agents")
async def get_routable_agents() -> Dict[str, Any]:
    """Get list of agents that can receive tasks, with their capabilities."""
    try:
        from mycosoft_mas.core.agent_registry import get_agent_registry
        registry = get_agent_registry()
        agents = registry.list_active()

        return {
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.display_name,
                    "category": a.category.value,
                    "capabilities": [c.value for c in a.capabilities],
                    "keywords": a.keywords,
                }
                for a in agents
            ],
            "total": len(agents),
        }
    except Exception:
        return {"agents": [], "total": 0}
