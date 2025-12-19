"""
Agent Runner API - 24/7 Operation Control
REST endpoints for controlling the continuous agent runner.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..agent_runner import get_agent_runner

router = APIRouter(prefix="/runner", tags=["runner"])


@router.get("/status")
async def get_runner_status() -> Dict[str, Any]:
    """Get current 24/7 runner status."""
    runner = get_agent_runner()
    return await runner.get_status()


@router.post("/start")
async def start_runner() -> Dict[str, Any]:
    """Start the 24/7 agent runner."""
    runner = get_agent_runner()
    if runner.running:
        return {"status": "already_running", "message": "Agent runner is already active"}
    
    # This will be called with agents from the main app
    # For now, start with empty list - agents will be added via register endpoint
    await runner.start([])
    return {"status": "started", "message": "24/7 agent runner started"}


@router.post("/stop")
async def stop_runner() -> Dict[str, Any]:
    """Stop the 24/7 agent runner."""
    runner = get_agent_runner()
    if not runner.running:
        return {"status": "already_stopped", "message": "Agent runner is not running"}
    
    await runner.stop()
    return {"status": "stopped", "message": "24/7 agent runner stopped"}


@router.get("/cycles")
async def get_cycles(limit: int = 50) -> Dict[str, Any]:
    """Get recent work cycles."""
    runner = get_agent_runner()
    cycles = list(runner.cycles.values())[-limit:]
    return {
        "total": len(runner.cycles),
        "returned": len(cycles),
        "cycles": [
            {
                "cycle_id": c.cycle_id,
                "agent_name": c.agent_name,
                "started_at": c.started_at,
                "completed_at": c.completed_at,
                "status": c.status,
                "tasks_processed": c.tasks_processed,
                "summary": c.summary,
            }
            for c in cycles
        ]
    }


@router.get("/insights")
async def get_insights(limit: int = 50) -> Dict[str, Any]:
    """Get recent insights from agents."""
    runner = get_agent_runner()
    insights = runner.insights[-limit:]
    return {
        "total": len(runner.insights),
        "returned": len(insights),
        "insights": [
            {
                "insight_id": i.insight_id,
                "agent_name": i.agent_name,
                "category": i.category,
                "title": i.title,
                "description": i.description,
                "confidence": i.confidence,
                "priority": i.priority,
                "timestamp": i.timestamp,
            }
            for i in insights
        ]
    }


@router.get("/notifications")
async def get_notifications(limit: int = 50) -> Dict[str, Any]:
    """Get recent admin notifications."""
    runner = get_agent_runner()
    notifications = runner.notifications[-limit:]
    return {
        "total": len(runner.notifications),
        "returned": len(notifications),
        "notifications": [
            {
                "notification_id": n.notification_id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "agent": n.agent,
                "priority": n.priority,
                "requires_action": n.requires_action,
                "timestamp": n.timestamp,
            }
            for n in notifications
        ]
    }


@router.post("/wisdom/compile")
async def compile_wisdom() -> Dict[str, Any]:
    """Compile accumulated insights into wisdom."""
    runner = get_agent_runner()
    wisdom = await runner.compile_wisdom()
    return {
        "status": "compiled",
        "wisdom": wisdom,
    }


@router.post("/notify")
async def send_notification(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a custom notification to admin."""
    runner = get_agent_runner()
    
    await runner.notify_admin(
        type=payload.get("type", "custom"),
        title=payload.get("title", "Notification"),
        message=payload.get("message", ""),
        agent=payload.get("agent", "API"),
        priority=payload.get("priority", "normal"),
        requires_action=payload.get("requires_action", False),
        data=payload.get("data", {}),
    )
    
    return {"status": "sent", "message": "Notification queued for admin"}
