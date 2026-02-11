"""
N8N Webhook Handlers API Router

Provides webhook endpoints for N8N workflow automation to call back into MAS:
- /webhooks/n8n/agent-task - Receive agent task requests from N8N
- /webhooks/n8n/tool-result - Receive tool execution results
- /webhooks/n8n/notification - Receive system notifications
- /webhooks/n8n/voice-command - Receive voice command results
- /webhooks/n8n/workflow-complete - Receive workflow completion notifications

Created: Feb 11, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/n8n", tags=["N8N Webhooks"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AgentTaskRequest(BaseModel):
    """Request from N8N to execute an agent task."""
    workflow_id: str
    workflow_name: Optional[str] = None
    task_type: str = "general"
    target_agent: Optional[str] = None
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: str = "normal"  # low, normal, high, urgent
    callback_url: Optional[str] = None


class ToolResultRequest(BaseModel):
    """Tool execution result from N8N."""
    tool_name: str
    execution_id: str
    status: str  # success, error, timeout
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class NotificationRequest(BaseModel):
    """System notification from N8N."""
    type: str  # info, warning, error, alert
    title: str
    message: str
    source: str = "n8n"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    require_acknowledgement: bool = False


class VoiceCommandRequest(BaseModel):
    """Voice command result from N8N voice workflows."""
    session_id: str
    command: str
    intent: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    response_text: Optional[str] = None


class WorkflowCompleteRequest(BaseModel):
    """Workflow completion notification from N8N."""
    workflow_id: str
    workflow_name: str
    execution_id: str
    status: str  # success, error, timeout
    started_at: str
    completed_at: str
    nodes_executed: int = 0
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class WebhookResponse(BaseModel):
    """Standard webhook response."""
    success: bool
    message: str
    task_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# In-memory task tracking (would use Redis in production)
# ============================================================================

_pending_tasks: Dict[str, Dict[str, Any]] = {}
_completed_tasks: Dict[str, Dict[str, Any]] = {}
_notifications: List[Dict[str, Any]] = []


# ============================================================================
# Webhook Endpoints
# ============================================================================

@router.post("/agent-task", response_model=WebhookResponse)
async def receive_agent_task(
    request: AgentTaskRequest,
    background_tasks: BackgroundTasks
):
    """
    Receive an agent task request from N8N.
    
    N8N can trigger this to have MYCA delegate a task to a specific agent.
    """
    task_id = str(uuid4())
    
    logger.info(f"Received agent task from N8N workflow {request.workflow_id}: {request.task_type}")
    
    # Store pending task
    _pending_tasks[task_id] = {
        "id": task_id,
        "type": "agent_task",
        "workflow_id": request.workflow_id,
        "target_agent": request.target_agent,
        "message": request.message,
        "priority": request.priority,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "callback_url": request.callback_url,
    }
    
    # Schedule background processing
    background_tasks.add_task(process_agent_task, task_id, request)
    
    return WebhookResponse(
        success=True,
        message=f"Agent task queued for {request.target_agent or 'routing'}",
        task_id=task_id
    )


async def process_agent_task(task_id: str, request: AgentTaskRequest):
    """Process an agent task in the background."""
    try:
        # Update status
        _pending_tasks[task_id]["status"] = "processing"
        
        result = None
        
        # Try to dispatch to specific agent
        if request.target_agent:
            try:
                from mycosoft_mas.consciousness.unified_router import get_unified_router
                router = get_unified_router()
                
                response_parts = []
                async for chunk in router.route(
                    message=request.message,
                    context={
                        "workflow_id": request.workflow_id,
                        "priority": request.priority,
                        "source": "n8n",
                    }
                ):
                    response_parts.append(chunk)
                
                result = "".join(response_parts)
                
            except Exception as e:
                logger.error(f"Agent dispatch failed: {e}")
                result = f"Error dispatching to agent: {e}"
        
        # Move to completed
        _completed_tasks[task_id] = {
            **_pending_tasks.pop(task_id),
            "status": "completed",
            "result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Send callback if specified
        if request.callback_url:
            await send_callback(request.callback_url, {
                "task_id": task_id,
                "status": "completed",
                "result": result
            })
            
    except Exception as e:
        logger.error(f"Error processing agent task {task_id}: {e}")
        if task_id in _pending_tasks:
            _pending_tasks[task_id]["status"] = "error"
            _pending_tasks[task_id]["error"] = str(e)


@router.post("/tool-result", response_model=WebhookResponse)
async def receive_tool_result(request: ToolResultRequest):
    """
    Receive a tool execution result from N8N.
    
    When N8N executes tools on behalf of MYCA, it reports results here.
    """
    logger.info(f"Received tool result for {request.tool_name}: {request.status}")
    
    # Store the result for any waiting processes
    result_id = str(uuid4())
    
    _completed_tasks[result_id] = {
        "id": result_id,
        "type": "tool_result",
        "tool_name": request.tool_name,
        "execution_id": request.execution_id,
        "status": request.status,
        "result": request.result,
        "error": request.error,
        "duration_ms": request.duration_ms,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    
    return WebhookResponse(
        success=True,
        message=f"Tool result received for {request.tool_name}",
        task_id=result_id
    )


@router.post("/notification", response_model=WebhookResponse)
async def receive_notification(request: NotificationRequest):
    """
    Receive a system notification from N8N.
    
    N8N can send notifications that MYCA should be aware of.
    """
    logger.info(f"Received notification from N8N: {request.type} - {request.title}")
    
    notification = {
        "id": str(uuid4()),
        "type": request.type,
        "title": request.title,
        "message": request.message,
        "source": request.source,
        "metadata": request.metadata,
        "require_acknowledgement": request.require_acknowledgement,
        "acknowledged": False,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    
    _notifications.append(notification)
    
    # Keep only last 100 notifications
    if len(_notifications) > 100:
        _notifications.pop(0)
    
    # Log based on type
    if request.type == "error":
        logger.error(f"N8N Error: {request.title} - {request.message}")
    elif request.type == "warning":
        logger.warning(f"N8N Warning: {request.title}")
    elif request.type == "alert":
        logger.warning(f"N8N Alert: {request.title}")
    
    return WebhookResponse(
        success=True,
        message=f"Notification received: {request.title}",
        task_id=notification["id"]
    )


@router.post("/voice-command", response_model=WebhookResponse)
async def receive_voice_command(
    request: VoiceCommandRequest,
    background_tasks: BackgroundTasks
):
    """
    Receive a voice command result from N8N voice workflows.
    
    When N8N processes voice input (via myca/voice workflow), 
    it sends the result here for MYCA to act on.
    """
    logger.info(f"Received voice command: {request.command[:50]}...")
    
    task_id = str(uuid4())
    
    # Store for processing
    _pending_tasks[task_id] = {
        "id": task_id,
        "type": "voice_command",
        "session_id": request.session_id,
        "command": request.command,
        "intent": request.intent,
        "entities": request.entities,
        "confidence": request.confidence,
        "response_text": request.response_text,
        "status": "pending",
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Process in background
    background_tasks.add_task(process_voice_command, task_id, request)
    
    return WebhookResponse(
        success=True,
        message="Voice command received",
        task_id=task_id
    )


async def process_voice_command(task_id: str, request: VoiceCommandRequest):
    """Process a voice command in the background."""
    try:
        _pending_tasks[task_id]["status"] = "processing"
        
        # Route through unified router
        from mycosoft_mas.consciousness.unified_router import get_unified_router
        router = get_unified_router()
        
        response_parts = []
        async for chunk in router.route(
            message=request.command,
            context={
                "session_id": request.session_id,
                "source": "voice",
                "intent": request.intent,
                "entities": request.entities,
            }
        ):
            response_parts.append(chunk)
        
        response = "".join(response_parts)
        
        _completed_tasks[task_id] = {
            **_pending_tasks.pop(task_id),
            "status": "completed",
            "response": response,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error processing voice command {task_id}: {e}")
        if task_id in _pending_tasks:
            _pending_tasks[task_id]["status"] = "error"
            _pending_tasks[task_id]["error"] = str(e)


@router.post("/workflow-complete", response_model=WebhookResponse)
async def receive_workflow_complete(request: WorkflowCompleteRequest):
    """
    Receive a workflow completion notification from N8N.
    
    Tracks workflow execution history for analysis and learning.
    """
    logger.info(f"Workflow completed: {request.workflow_name} ({request.status})")
    
    # Store in memory
    _completed_tasks[request.execution_id] = {
        "id": request.execution_id,
        "type": "workflow_complete",
        "workflow_id": request.workflow_id,
        "workflow_name": request.workflow_name,
        "status": request.status,
        "started_at": request.started_at,
        "completed_at": request.completed_at,
        "nodes_executed": request.nodes_executed,
        "output_data": request.output_data,
        "error_message": request.error_message,
    }
    
    # Try to record in memory coordinator
    try:
        from mycosoft_mas.memory.coordinator import get_memory_coordinator
        coordinator = await get_memory_coordinator()
        
        await coordinator.record_workflow_complete(
            execution_id=request.execution_id,
            status=request.status,
            output_data=request.output_data,
            error_message=request.error_message,
            nodes_executed=request.nodes_executed
        )
    except Exception as e:
        logger.warning(f"Could not record workflow completion in memory: {e}")
    
    return WebhookResponse(
        success=True,
        message=f"Workflow {request.workflow_name} completion recorded",
        task_id=request.execution_id
    )


# ============================================================================
# Status and Query Endpoints
# ============================================================================

@router.get("/tasks/pending")
async def get_pending_tasks():
    """Get list of pending tasks from N8N."""
    return {
        "tasks": list(_pending_tasks.values()),
        "count": len(_pending_tasks),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/tasks/completed")
async def get_completed_tasks(limit: int = 20):
    """Get recent completed tasks."""
    tasks = list(_completed_tasks.values())[-limit:]
    return {
        "tasks": tasks,
        "count": len(tasks),
        "total": len(_completed_tasks),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task by ID."""
    if task_id in _pending_tasks:
        return _pending_tasks[task_id]
    if task_id in _completed_tasks:
        return _completed_tasks[task_id]
    raise HTTPException(status_code=404, detail="Task not found")


@router.get("/notifications")
async def get_notifications(unacknowledged_only: bool = False):
    """Get recent notifications."""
    notifications = _notifications
    if unacknowledged_only:
        notifications = [n for n in notifications if not n.get("acknowledged")]
    
    return {
        "notifications": notifications[-50:],
        "count": len(notifications),
        "unacknowledged": sum(1 for n in notifications if not n.get("acknowledged")),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/notifications/{notification_id}/acknowledge")
async def acknowledge_notification(notification_id: str):
    """Acknowledge a notification."""
    for notification in _notifications:
        if notification["id"] == notification_id:
            notification["acknowledged"] = True
            notification["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
            return {"success": True, "message": "Notification acknowledged"}
    
    raise HTTPException(status_code=404, detail="Notification not found")


# ============================================================================
# Helper Functions
# ============================================================================

async def send_callback(url: str, data: Dict[str, Any]):
    """Send callback to N8N or other service."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=data)
    except Exception as e:
        logger.warning(f"Callback to {url} failed: {e}")
