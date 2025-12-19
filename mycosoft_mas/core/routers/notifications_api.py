"""
Admin Notifications API
Endpoints for sending and managing notifications to Morgan.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from mycosoft_mas.services.admin_notifications import get_admin_notification_service, notify_morgan

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationRequest(BaseModel):
    """Request model for sending notifications."""
    title: str
    message: str
    type: str = "info"  # info, success, warning, error, task_complete, insight, discovery
    agent: str = "MYCA"
    priority: str = "normal"  # low, normal, high, critical
    data: Optional[Dict[str, Any]] = None
    requires_action: bool = False
    channels: Optional[List[str]] = None  # sms, email, webhook, push


@router.post("/send")
async def send_notification(request: NotificationRequest) -> Dict[str, Any]:
    """Send a notification to Morgan (super admin)."""
    try:
        result = await notify_morgan(
            title=request.title,
            message=request.message,
            type=request.type,
            agent=request.agent,
            priority=request.priority,
            data=request.data,
            requires_action=request.requires_action,
            channels=request.channels,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_notification_history(limit: int = 100) -> Dict[str, Any]:
    """Get notification history."""
    service = get_admin_notification_service()
    history = await service.get_history(limit)
    return {
        "total": len(history),
        "notifications": history,
    }


@router.post("/test")
async def test_notification() -> Dict[str, Any]:
    """Send a test notification to verify the system is working."""
    result = await notify_morgan(
        title="Test Notification",
        message="This is a test notification from MYCA. If you received this, the notification system is working correctly.",
        type="info",
        agent="MYCA",
        priority="normal",
    )
    return {
        "status": "test_sent",
        "result": result,
    }
