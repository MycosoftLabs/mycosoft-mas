"""
Internal Agent Protocol API for async Deep Agent tasks.

This API is additive alongside existing A2A routes and can be enabled
independently with feature flags.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.deep_agents.config import get_deep_agents_config
from mycosoft_mas.deep_agents.domain_hooks import submit_domain_task
from mycosoft_mas.deep_agents.orchestrator import get_deep_agent_orchestrator
from mycosoft_mas.deep_agents.status_mapper import map_deep_to_agent_protocol_state

router = APIRouter(tags=["agent-protocol"])


class AgentProtocolTaskRequest(BaseModel):
    agent_name: str = Field(..., min_length=1)
    task: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)


class AgentProtocolTaskResponse(BaseModel):
    task_id: str
    state: str
    protocol_state: str
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DomainEventRequest(BaseModel):
    domain: str = Field(..., min_length=1)
    task: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)
    preferred_agent: Optional[str] = None


@router.get("/.well-known/agent-protocol.json")
async def agent_protocol_card() -> Dict[str, Any]:
    cfg = get_deep_agents_config()
    if not cfg.protocol_enabled:
        raise HTTPException(status_code=404, detail="Agent protocol not enabled")

    return {
        "name": "MYCA Agent Protocol",
        "version": "0.5.0",
        "description": "Internal MYCA async agent protocol powered by Deep Agents integration.",
        "capabilities": {
            "async_tasks": True,
            "task_status_polling": True,
            "multimodal_context": cfg.filesystem_enabled,
        },
        "routes": {
            "submit": "/agent-protocol/v1/tasks/submit",
            "status": "/agent-protocol/v1/tasks/{task_id}",
            "health": "/agent-protocol/v1/health",
        },
    }


@router.get("/agent-protocol/v1/health")
async def agent_protocol_health() -> Dict[str, Any]:
    cfg = get_deep_agents_config()
    if not cfg.protocol_enabled:
        raise HTTPException(status_code=404, detail="Agent protocol not enabled")
    orchestrator = get_deep_agent_orchestrator()
    await orchestrator.initialize()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deep_agents": orchestrator.health(),
    }


@router.post("/api/deep-agents/domain-event")
async def submit_domain_event(payload: DomainEventRequest) -> Dict[str, Any]:
    """
    Cross-system Deep Agent domain event ingestion endpoint.
    Allows external repos (WEBSITE/MINDEX/NatureOS) to fan domain tasks into MAS.
    """
    cfg = get_deep_agents_config()
    if not cfg.enabled and not cfg.protocol_enabled:
        return {"accepted": False, "reason": "deep agents disabled"}

    await submit_domain_task(
        domain=payload.domain,
        task=payload.task,
        context=payload.context,
        preferred_agent=payload.preferred_agent,
    )
    return {"accepted": True, "domain": payload.domain}


@router.post("/agent-protocol/v1/tasks/submit", response_model=AgentProtocolTaskResponse)
async def submit_agent_protocol_task(
    payload: AgentProtocolTaskRequest,
) -> AgentProtocolTaskResponse:
    cfg = get_deep_agents_config()
    if not cfg.protocol_enabled:
        raise HTTPException(status_code=404, detail="Agent protocol not enabled")

    orchestrator = get_deep_agent_orchestrator()
    record = await orchestrator.submit_task(
        agent_name=payload.agent_name,
        task=payload.task,
        context=payload.context,
    )

    return AgentProtocolTaskResponse(
        task_id=record.task_id,
        state=record.state.value,
        protocol_state=map_deep_to_agent_protocol_state(record.state),
        created_at=record.created_at,
        updated_at=record.updated_at,
        result=record.result,
        error=record.error,
    )


@router.get("/agent-protocol/v1/tasks/{task_id}", response_model=AgentProtocolTaskResponse)
async def get_agent_protocol_task(task_id: str) -> AgentProtocolTaskResponse:
    cfg = get_deep_agents_config()
    if not cfg.protocol_enabled:
        raise HTTPException(status_code=404, detail="Agent protocol not enabled")

    orchestrator = get_deep_agent_orchestrator()
    record = await orchestrator.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return AgentProtocolTaskResponse(
        task_id=record.task_id,
        state=record.state.value,
        protocol_state=map_deep_to_agent_protocol_state(record.state),
        created_at=record.created_at,
        updated_at=record.updated_at,
        result=record.result,
        error=record.error,
    )
