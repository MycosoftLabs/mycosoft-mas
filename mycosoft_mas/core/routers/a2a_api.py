"""
MYCA A2A (Agent2Agent) Gateway API - February 17, 2026

Implements the A2A Protocol for MAS:
- Agent Card discovery at /.well-known/agent-card.json
- Message send endpoint (A2A JSON-RPC style over HTTP)
- Routes execution through existing MYCA permissioned tool path

A2A Protocol spec: https://a2a-protocol.org/latest/specification
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from mycosoft_mas.integrations.a2a_adapters import (
    CommerceFingerAdapter,
    DeviceFingerAdapter,
    MobilityFingerAdapter,
    WebFingerAdapter,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["a2a"])

# Feature flag - A2A disabled when unset
MYCA_A2A_ENABLED = os.getenv("MYCA_A2A_ENABLED", "true").lower() in ("1", "true", "yes")


# =============================================================================
# A2A Data Models (A2A Protocol v0.3 compatible)
# =============================================================================


class PartModel(BaseModel):
    """A2A Part - text, url, or data content."""

    text: Optional[str] = None
    url: Optional[str] = None
    data: Optional[Any] = None
    mediaType: Optional[str] = None
    filename: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageModel(BaseModel):
    """A2A Message."""

    messageId: str = Field(..., description="Unique message ID")
    contextId: Optional[str] = None
    taskId: Optional[str] = None
    role: str = Field(..., description="ROLE_USER or ROLE_AGENT")
    parts: List[PartModel] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class SendMessageConfiguration(BaseModel):
    """A2A SendMessageConfiguration."""

    acceptedOutputModes: Optional[List[str]] = None
    historyLength: Optional[int] = None
    blocking: Optional[bool] = False


class SendMessageRequest(BaseModel):
    """A2A SendMessageRequest."""

    message: MessageModel
    configuration: Optional[SendMessageConfiguration] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskStatusModel(BaseModel):
    """A2A TaskStatus."""

    state: str = Field(..., description="TASK_STATE_*")
    message: Optional[MessageModel] = None
    timestamp: Optional[str] = None


class ArtifactModel(BaseModel):
    """A2A Artifact."""

    artifactId: str
    name: Optional[str] = None
    description: Optional[str] = None
    parts: List[PartModel] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class TaskModel(BaseModel):
    """A2A Task."""

    id: str
    contextId: str
    status: TaskStatusModel
    artifacts: List[ArtifactModel] = Field(default_factory=list)
    history: List[MessageModel] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class FederatedSendRequest(BaseModel):
    """Outbound federation request to a finger adapter."""

    finger: str = Field(..., description="commerce|web|mobility|device")
    message: str = Field(..., description="Text payload to external A2A agent")
    context_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# Sanitization (per ROUTER_POLICY - treat remote payloads as untrusted)
# =============================================================================


def _sanitize_text(value: str, max_len: int = 50000) -> str:
    """Sanitize text from remote agent payloads."""
    if not isinstance(value, str):
        return ""
    # Remove null bytes and control chars
    sanitized = "".join(c for c in value if ord(c) >= 32 and ord(c) != 127)
    return sanitized[:max_len]


def _extract_user_message(msg: MessageModel) -> str:
    """Extract plain text from A2A message parts."""
    if not msg.parts:
        return ""
    texts: List[str] = []
    for p in msg.parts:
        if p.text:
            texts.append(_sanitize_text(p.text, 10000))
    return " ".join(texts).strip() or ""


def _resolve_finger_adapter(finger: str):
    f = finger.lower().strip()
    if f == "commerce":
        return CommerceFingerAdapter()
    if f == "web":
        return WebFingerAdapter()
    if f == "mobility":
        return MobilityFingerAdapter()
    if f == "device":
        return DeviceFingerAdapter()
    raise HTTPException(status_code=400, detail=f"Unsupported finger: {finger}")


# =============================================================================
# Agent Card (/.well-known/agent-card.json)
# =============================================================================


def _get_agent_card(base_url: str) -> Dict[str, Any]:
    """Build MYCA Agent Card per A2A spec."""
    # Use base_url for interface URL - caller provides request base
    interface_url = f"{base_url.rstrip('/')}/a2a/v1"
    return {
        "name": "MYCA",
        "description": "My Companion AI - the primary AI orchestrator for Mycosoft's Multi-Agent System. Coordinates 200+ specialized agents across mycology research, infrastructure, finance, and scientific computing.",
        "version": "1.0.0",
        "provider": {
            "url": "https://mycosoft.com",
            "organization": "Mycosoft",
        },
        "supportedInterfaces": [
            {
                "url": interface_url,
                "protocolBinding": "HTTP+JSON",
                "protocolVersion": "0.3",
            },
        ],
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "orchestration",
                "name": "Agent Orchestration",
                "description": "Coordinate and delegate to specialized agents for research, infrastructure, finance, and scientific tasks.",
                "tags": ["orchestration", "agents", "delegation", "mycology", "research"],
            },
            {
                "id": "voice-chat",
                "name": "Voice and Chat",
                "description": "Natural language conversation, memory, and context-aware responses.",
                "tags": ["chat", "voice", "conversation", "memory"],
            },
            {
                "id": "search",
                "name": "Search and Knowledge",
                "description": "Query MINDEX, unified search, and knowledge graph for fungal species, compounds, and research.",
                "tags": ["search", "mindex", "knowledge", "species", "compounds"],
            },
            {
                "id": "myca_search",
                "name": "MYCA Search",
                "description": "Execute semantic, keyword, or fuzzy search across MINDEX, Exa, and research sources.",
                "tags": ["search", "nlq", "exa", "mindex"],
            },
            {
                "id": "myca_nlq",
                "name": "MYCA Natural Language Query",
                "description": "Interpret natural language and route to SearchAgent, Metabase, or MINDEX.",
                "tags": ["nlq", "metabase", "analytics", "search"],
            },
        ],
    }


# =============================================================================
# A2A Routes
# =============================================================================


@router.get("/.well-known/agent-card.json")
async def get_agent_card(request: Request) -> JSONResponse:
    """A2A Agent Card discovery - well-known URI."""
    if not MYCA_A2A_ENABLED:
        raise HTTPException(status_code=404, detail="A2A not enabled")
    base = str(request.base_url).rstrip("/")
    card = _get_agent_card(base)
    return JSONResponse(content=card)


@router.get("/a2a/v1/agent-card")
async def get_agent_card_alt(request: Request) -> JSONResponse:
    """Alternate Agent Card endpoint (same content)."""
    return await get_agent_card(request)


@router.post("/a2a/v1/message/send")
async def send_message(request: Request, body: SendMessageRequest) -> JSONResponse:
    """
    A2A Send Message - routes to MYCA voice orchestrator.
    Returns Task with COMPLETED state and artifact containing response (blocking mode).
    """
    if not MYCA_A2A_ENABLED:
        raise HTTPException(status_code=404, detail="A2A not enabled")

    # Sanitize and extract user message
    user_text = _extract_user_message(body.message)
    if not user_text:
        raise HTTPException(status_code=400, detail="Message must contain at least one text part")

    # Protocol telemetry (per Phase 6 rollout observability)
    logger.info(
        "protocol_event protocol=a2a remote_agent=%s tool_name=message/send risk_flags=[] context_id=%s",
        body.metadata.get("remote_agent", "unknown") if body.metadata else "unknown",
        body.message.contextId or "new",
    )

    context_id = body.message.contextId or str(uuid4())
    task_id = str(uuid4())
    body.configuration.blocking if body.configuration else True

    # Route through MYCA voice orchestrator (existing permissioned path)
    try:
        from mycosoft_mas.core.routers.voice_orchestrator_api import (
            VoiceOrchestratorRequest,
            get_orchestrator,
        )

        orch = get_orchestrator()
        meta = body.metadata or {}
        vo_req = VoiceOrchestratorRequest(
            message=user_text,
            conversation_id=context_id,
            session_id=meta.get("session_id"),
            user_id=meta.get("user_id") or "a2a-client",
            source="a2a",
            modality="text",
            want_audio=False,
        )
        resp = await orch.process(vo_req)
        response_text = resp.response_text or resp.response or ""
    except Exception as e:
        logger.exception("A2A orchestration failed: %s", e)
        response_text = f"I encountered an error processing your request: {str(e)}"

    # Build A2A Task response
    now = datetime.now(timezone.utc).isoformat()
    agent_message = MessageModel(
        messageId=str(uuid4()),
        contextId=context_id,
        taskId=task_id,
        role="ROLE_AGENT",
        parts=[PartModel(text=response_text, mediaType="text/plain")],
    )
    artifact = ArtifactModel(
        artifactId=str(uuid4()),
        name="response",
        description="MYCA response",
        parts=[PartModel(text=response_text, mediaType="text/plain")],
    )
    task = TaskModel(
        id=task_id,
        contextId=context_id,
        status=TaskStatusModel(
            state="TASK_STATE_COMPLETED",
            timestamp=now,
        ),
        artifacts=[artifact],
        history=[agent_message],
        metadata={"protocol": "a2a", "source": "myca-orchestrator"},
    )
    return JSONResponse(content=task.model_dump(exclude_none=True))


@router.post("/a2a/v1/fingers/send")
async def federated_send(body: FederatedSendRequest) -> JSONResponse:
    """
    Outbound A2A federation to external fingers.
    """
    if not MYCA_A2A_ENABLED:
        raise HTTPException(status_code=404, detail="A2A not enabled")
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    adapter = _resolve_finger_adapter(body.finger)
    try:
        response = await adapter.ask(
            prompt=_sanitize_text(body.message, 10000),
            metadata=body.metadata or {},
        )
        return JSONResponse(
            content={
                "status": "ok",
                "finger": body.finger,
                "context_id": body.context_id,
                "response": response,
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Federated A2A failed: {exc}") from exc
