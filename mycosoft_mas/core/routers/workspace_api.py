"""
MYCA Workspace API — endpoints for staff interactions and workspace management.

Runs on MYCA VM 191 (192.168.0.191:8000).
Provides REST endpoints for all of MYCA's workspace operations:
  - Sending/receiving messages to staff
  - Task management
  - Platform status
  - Webhook receivers for Slack, Discord, Signal
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SendMessageRequest(BaseModel):
    recipient: str = Field(..., description="Staff member name (morgan, rj, garret)")
    message: str = Field(..., min_length=1, max_length=10000)
    platform: Optional[str] = Field(None, description="Override platform (slack, signal, email, etc.)")


class CreateTaskRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    assigned_by: str = ""
    due_date: Optional[str] = None
    priority: str = "medium"
    sync_to: List[str] = Field(default_factory=list, description="Sync to: asana, notion")


class UpdateTaskRequest(BaseModel):
    title: str
    status: str = Field(..., description="pending, in_progress, completed, cancelled")


class NotifyStaffRequest(BaseModel):
    recipients: List[str] = Field(default_factory=list, description="Staff names, empty = all")
    message: str
    urgency: str = Field("normal", description="normal, urgent, critical")


class SetPresenceRequest(BaseModel):
    status: str = Field("online", description="online, away, dnd")
    status_text: str = ""


class WebhookPayload(BaseModel):
    platform: str
    event_type: str
    data: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# In-memory workspace (replaced by WorkspaceAgent when available)
# ---------------------------------------------------------------------------

_workspace_agent = None


def _get_agent():
    global _workspace_agent
    if _workspace_agent is None:
        try:
            from mycosoft_mas.agents.workspace_agent import WorkspaceAgent
            _workspace_agent = WorkspaceAgent(
                agent_id="workspace_agent",
                name="MYCA Workspace",
                config={},
            )
        except Exception as e:
            logger.warning("WorkspaceAgent not available: %s", e)
    return _workspace_agent


# ---------------------------------------------------------------------------
# Health / Status
# ---------------------------------------------------------------------------

@router.get("/health")
async def workspace_health():
    """Workspace health check."""
    return {
        "status": "healthy",
        "service": "myca-workspace",
        "vm": "192.168.0.191",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
async def workspace_status():
    """Full workspace status — platforms, tasks, conversations."""
    agent = _get_agent()
    if agent:
        result = await agent.process_task({"type": "workspace_status"})
        return result
    return {
        "status": "success",
        "workspace": {
            "vm_ip": "192.168.0.191",
            "platforms": {},
            "note": "WorkspaceAgent not initialized",
        },
    }


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------

@router.post("/send")
async def send_message(req: SendMessageRequest):
    """Send a message to a staff member."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "WorkspaceAgent not available")
    return await agent.process_task({
        "type": "send_message",
        "parameters": req.model_dump(),
    })


@router.get("/messages")
async def check_messages(platforms: str = "slack,discord,signal"):
    """Check for new messages across platforms."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "WorkspaceAgent not available")
    return await agent.process_task({
        "type": "check_messages",
        "parameters": {"platforms": platforms.split(",")},
    })


@router.post("/notify")
async def notify_staff(req: NotifyStaffRequest):
    """Send notification to staff members."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "WorkspaceAgent not available")
    return await agent.process_task({
        "type": "notify_staff",
        "parameters": req.model_dump(),
    })


# ---------------------------------------------------------------------------
# Task Management
# ---------------------------------------------------------------------------

@router.post("/tasks")
async def create_task(req: CreateTaskRequest):
    """Create a new tracked task."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "WorkspaceAgent not available")
    return await agent.process_task({
        "type": "create_task",
        "parameters": req.model_dump(),
    })


@router.patch("/tasks")
async def update_task(req: UpdateTaskRequest):
    """Update a task's status."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "WorkspaceAgent not available")
    return await agent.process_task({
        "type": "update_task",
        "parameters": req.model_dump(),
    })


# ---------------------------------------------------------------------------
# Presence
# ---------------------------------------------------------------------------

@router.post("/presence")
async def set_presence(req: SetPresenceRequest):
    """Set MYCA's presence across platforms."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "WorkspaceAgent not available")
    return await agent.process_task({
        "type": "set_presence",
        "parameters": req.model_dump(),
    })


# ---------------------------------------------------------------------------
# Daily Briefing
# ---------------------------------------------------------------------------

@router.post("/briefing")
async def daily_briefing():
    """Generate and send daily briefing to CEO."""
    agent = _get_agent()
    if not agent:
        raise HTTPException(503, "WorkspaceAgent not available")
    return await agent.process_task({"type": "daily_briefing"})


# ---------------------------------------------------------------------------
# Webhooks (Slack, Discord, Signal incoming)
# ---------------------------------------------------------------------------

@router.post("/webhook/{platform}")
async def receive_webhook(platform: str, request: Request):
    """Receive incoming webhooks from platforms (Slack events, Discord, etc.)."""
    body = await request.json()
    logger.info("Webhook received from %s: %s", platform, str(body)[:200])

    # Slack challenge verification
    if platform == "slack" and "challenge" in body:
        return {"challenge": body["challenge"]}

    agent = _get_agent()
    if agent:
        await agent.process_task({
            "type": "route_message",
            "parameters": {
                "platform": platform,
                "sender": body.get("user", body.get("sender", "unknown")),
                "content": body.get("text", body.get("message", "")),
            },
        })

    return {"status": "received", "platform": platform}


# ---------------------------------------------------------------------------
# Staff Directory
# ---------------------------------------------------------------------------

@router.get("/staff")
async def list_staff():
    """List known staff members and their platforms."""
    agent = _get_agent()
    if agent:
        return {
            "status": "success",
            "staff": agent.staff_directory,
        }
    from mycosoft_mas.agents.workspace_agent import STAFF_DIRECTORY
    return {"status": "success", "staff": STAFF_DIRECTORY}
