"""
Admin Notification Service for Morgan
Sends notifications via multiple channels: Twilio SMS, Email, Push, n8n webhooks.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import httpx

logger = logging.getLogger(__name__)

# Configuration
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "+1234567890")  # Morgan's phone
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "morgan@mycosoft.com")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678")
TWILIO_ENABLED = bool(os.getenv("TWILIO_ACCOUNT_SID"))


@dataclass
class NotificationPayload:
    """Notification payload structure."""
    title: str
    message: str
    type: str
    agent: str
    priority: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None
    requires_action: bool = False


class AdminNotificationService:
    """
    Send notifications to Morgan (super admin) via multiple channels.
    
    Channels:
    - Twilio SMS (for critical/high priority)
    - Email (for all notifications)
    - n8n Webhook (for workflow integration)
    - Push notification (for mobile)
    """

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None
        self._notification_history: List[NotificationPayload] = []

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30)
        return self._http_client

    async def notify(
        self,
        title: str,
        message: str,
        type: str = "info",
        agent: str = "MYCA",
        priority: str = "normal",
        data: Optional[Dict[str, Any]] = None,
        requires_action: bool = False,
        channels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send notification to Morgan via specified channels.
        
        Args:
            title: Notification title
            message: Notification body
            type: Type (info, success, warning, error, task_complete, insight, discovery)
            agent: Source agent name
            priority: Priority level (low, normal, high, critical)
            data: Additional data payload
            requires_action: Whether Morgan needs to take action
            channels: List of channels to use (defaults based on priority)
        """
        payload = NotificationPayload(
            title=title,
            message=message,
            type=type,
            agent=agent,
            priority=priority,
            timestamp=datetime.now().isoformat(),
            data=data,
            requires_action=requires_action,
        )
        
        self._notification_history.append(payload)
        
        # Determine channels based on priority if not specified
        if channels is None:
            if priority == "critical":
                channels = ["sms", "email", "webhook", "push"]
            elif priority == "high":
                channels = ["sms", "email", "webhook"]
            elif priority == "normal":
                channels = ["email", "webhook"]
            else:
                channels = ["webhook"]
        
        results = {}
        
        # Send to each channel
        if "sms" in channels:
            results["sms"] = await self._send_sms(payload)
        
        if "email" in channels:
            results["email"] = await self._send_email(payload)
        
        if "webhook" in channels:
            results["webhook"] = await self._send_webhook(payload)
        
        if "push" in channels:
            results["push"] = await self._send_push(payload)
        
        logger.info(f"[ADMIN NOTIFICATION] {priority.upper()}: {title} -> Channels: {channels}")
        
        return {
            "status": "sent",
            "payload": asdict(payload),
            "channels": results,
        }

    async def _send_sms(self, payload: NotificationPayload) -> Dict[str, Any]:
        """Send SMS via Twilio."""
        if not TWILIO_ENABLED:
            return {"status": "skipped", "reason": "Twilio not configured"}
        
        try:
            client = await self._get_client()
            
            # Send via MAS Twilio endpoint
            sms_message = f"[MYCA {payload.priority.upper()}] {payload.title}\n\n{payload.message}"
            if payload.requires_action:
                sms_message += "\n\n⚠️ ACTION REQUIRED"
            
            response = await client.post(
                "http://localhost:8001/twilio/sms/send",
                json={
                    "to": ADMIN_PHONE,
                    "message": sms_message,
                }
            )
            
            if response.status_code == 200:
                return {"status": "sent", "to": ADMIN_PHONE}
            else:
                return {"status": "error", "error": response.text}
                
        except Exception as e:
            logger.error(f"SMS notification failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _send_email(self, payload: NotificationPayload) -> Dict[str, Any]:
        """Send email notification via n8n or SMTP."""
        try:
            client = await self._get_client()
            
            # Use n8n email workflow
            email_payload = {
                "to": ADMIN_EMAIL,
                "subject": f"[MYCA {payload.priority.upper()}] {payload.title}",
                "body": self._format_email_body(payload),
                "priority": payload.priority,
            }
            
            response = await client.post(
                f"{N8N_WEBHOOK_URL}/webhook/myca/email",
                json=email_payload,
            )
            
            if response.status_code == 200:
                return {"status": "sent", "to": ADMIN_EMAIL}
            else:
                return {"status": "webhook_error", "error": "n8n email workflow not available"}
                
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return {"status": "error", "error": str(e)}

    def _format_email_body(self, payload: NotificationPayload) -> str:
        """Format notification as email HTML."""
        priority_colors = {
            "critical": "#dc2626",
            "high": "#ea580c",
            "normal": "#2563eb",
            "low": "#6b7280",
        }
        color = priority_colors.get(payload.priority, "#2563eb")
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">{payload.title}</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">From: {payload.agent} | {payload.type.upper()}</p>
            </div>
            <div style="background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0;">
                <p style="font-size: 16px; color: #1e293b; line-height: 1.6;">{payload.message}</p>
                
                {"<p style='color: #dc2626; font-weight: bold;'>⚠️ ACTION REQUIRED</p>" if payload.requires_action else ""}
                
                {f"<pre style='background: #1e293b; color: #e2e8f0; padding: 15px; border-radius: 4px; overflow-x: auto;'>{json.dumps(payload.data, indent=2)}</pre>" if payload.data else ""}
            </div>
            <div style="background: #1e293b; color: #94a3b8; padding: 15px; border-radius: 0 0 8px 8px; font-size: 12px;">
                <p style="margin: 0;">MYCA - Mycosoft Autonomous Cognitive Agent</p>
                <p style="margin: 5px 0 0 0;">{payload.timestamp}</p>
            </div>
        </div>
        """
        return html

    async def _send_webhook(self, payload: NotificationPayload) -> Dict[str, Any]:
        """Send to n8n webhook for processing."""
        try:
            client = await self._get_client()
            
            response = await client.post(
                f"{N8N_WEBHOOK_URL}/webhook/myca/admin-notification",
                json=asdict(payload),
            )
            
            if response.status_code == 200:
                return {"status": "sent"}
            else:
                return {"status": "error", "code": response.status_code}
                
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _send_push(self, payload: NotificationPayload) -> Dict[str, Any]:
        """Send push notification (future: mobile app integration)."""
        # TODO: Integrate with Firebase Cloud Messaging or similar
        return {"status": "not_implemented", "reason": "Push notifications coming soon"}

    async def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get notification history."""
        return [asdict(n) for n in self._notification_history[-limit:]]

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
_service: Optional[AdminNotificationService] = None


def get_admin_notification_service() -> AdminNotificationService:
    """Get the global admin notification service."""
    global _service
    if _service is None:
        _service = AdminNotificationService()
    return _service


async def notify_morgan(
    title: str,
    message: str,
    type: str = "info",
    agent: str = "MYCA",
    priority: str = "normal",
    **kwargs
) -> Dict[str, Any]:
    """Convenience function to notify Morgan."""
    service = get_admin_notification_service()
    return await service.notify(
        title=title,
        message=message,
        type=type,
        agent=agent,
        priority=priority,
        **kwargs
    )
