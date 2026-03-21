"""
Omnichannel API Router - MYCA Autonomous Omnichannel System.

Unified send/receive/verify/status for all platform connectors (Slack, Discord,
WhatsApp, Signal, Email, Asana). Used by n8n ingestion and response workflows.

Endpoints:
  POST /api/omnichannel/send        - Route message to correct platform
  POST /api/omnichannel/receive     - n8n webhook intake for normalized messages
  POST /api/omnichannel/forward     - Forward normalized payload to n8n intent orchestrator
  POST /api/omnichannel/verify-sender - Verify sender authorization
  GET  /api/omnichannel/status      - Connector health across all platforms

Created: Mar 2, 2026
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/omnichannel", tags=["omnichannel"])


def _env_any(*names: str) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class OmnichannelSendRequest(BaseModel):
    """Request to send a message to a platform."""

    platform: str = Field(..., description="slack|discord|whatsapp|signal|email|asana")
    channel_id: Optional[str] = Field(None, description="Channel ID for slack/discord")
    recipient: Optional[str] = Field(
        None, description="Phone for whatsapp/signal, email for email, task_gid for asana"
    )
    thread_id: Optional[str] = Field(None, description="Thread ID for slack/discord")
    text: str = Field(..., description="Message text")
    subject: Optional[str] = Field(None, description="Email subject when platform=email")
    attachments: Optional[List[str]] = Field(None, description="Attachment URLs")


class OmnichannelReceiveRequest(BaseModel):
    """Normalized message from ingestion workflow."""

    platform_source: str = Field(..., description="slack|discord|whatsapp|signal|email|asana")
    channel_id: Optional[str] = None
    sender_id: str = Field(..., description="Platform-specific sender ID")
    sender_email: Optional[str] = None
    message_text: str = Field(...)
    attachments: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[str] = None
    thread_id: Optional[str] = None


class VerifySenderRequest(BaseModel):
    """Request to verify sender authorization."""

    platform: str = Field(...)
    sender_id: str = Field(...)


class VerifySenderResponse(BaseModel):
    """Response from sender verification."""

    authorized: bool
    role: str = "none"
    email: str = ""


# ---------------------------------------------------------------------------
# Lazy client initialization (avoid import cycles, optional deps)
# ---------------------------------------------------------------------------


def _get_slack_client():
    from mycosoft_mas.integrations.slack_client import SlackClient

    token = _env_any("MYCA_SLACK_BOT_TOKEN", "SLACK_BOT_TOKEN", "SLACK_OAUTH_TOKEN")
    return SlackClient({"token": token})


def _get_discord_client():
    from mycosoft_mas.integrations.discord_client import DiscordClient

    return DiscordClient()


def _get_whatsapp_client():
    from mycosoft_mas.integrations.whatsapp_client import WhatsAppClient

    return WhatsAppClient()


def _get_signal_client():
    from mycosoft_mas.integrations.signal_client import SignalClient

    return SignalClient()


def _get_google_client():
    try:
        from mycosoft_mas.integrations.google_workspace_client import GoogleWorkspaceClient

        return GoogleWorkspaceClient()
    except ImportError:
        return None


def _get_asana_client():
    from mycosoft_mas.integrations.asana_client import AsanaClient

    return AsanaClient({"api_key": _env_any("ASANA_API_KEY", "ASANA_PAT", "MYCA_ASANA_TOKEN")})


def _get_platform_access():
    from mycosoft_mas.security.platform_access import PlatformAccessControl

    return PlatformAccessControl()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/send")
async def omnichannel_send(req: OmnichannelSendRequest) -> Dict[str, Any]:
    """Route message to the correct platform connector."""
    platform = req.platform.lower()
    text = req.text or ""

    if platform == "slack":
        ch = req.channel_id or req.recipient
        if not ch:
            raise HTTPException(400, "channel_id or recipient required for slack")
        client = _get_slack_client()
        result = await client.post_message(ch, text, thread_ts=req.thread_id)
        return {"success": result is not None, "platform": "slack", "result": result}

    if platform == "discord":
        ch = req.channel_id or req.recipient
        if not ch:
            raise HTTPException(400, "channel_id or recipient required for discord")
        client = _get_discord_client()
        result = await client.send_message(ch, text, thread_id=req.thread_id)
        return {"success": result is not None, "platform": "discord", "result": result}

    if platform == "whatsapp":
        rec = req.recipient
        if not rec:
            raise HTTPException(400, "recipient (phone) required for whatsapp")
        client = _get_whatsapp_client()
        result = await client.send_message(rec, text)
        return {"success": result is not None, "platform": "whatsapp", "result": result}

    if platform == "signal":
        rec = req.recipient
        if not rec:
            raise HTTPException(400, "recipient (phone) required for signal")
        client = _get_signal_client()
        result = await client.send_message(rec, text, attachments=req.attachments)
        return {"success": result is not None, "platform": "signal", "result": result}

    if platform == "email":
        rec = req.recipient
        if not rec:
            raise HTTPException(400, "recipient (email) required for email")
        gw = _get_google_client()
        if not gw:
            raise HTTPException(503, "Google Workspace client not available")
        subject = req.subject or "Message from MYCA"
        result = await gw.send_email(rec, subject, text, html=True)
        return {"success": bool(result), "platform": "email", "result": result}

    if platform == "asana":
        task_gid = req.recipient or req.channel_id
        if not task_gid:
            raise HTTPException(400, "recipient (task_gid) required for asana")
        client = _get_asana_client()
        result = await client.add_comment(task_gid, text)
        return {"success": result is not None, "platform": "asana", "result": result}

    raise HTTPException(400, f"Unsupported platform: {platform}")


class OmnichannelForwardRequest(BaseModel):
    """Forward normalized payload to n8n intent orchestrator."""

    platform_source: str = Field(...)
    channel_id: Optional[str] = None
    sender_id: str = Field(...)
    sender_email: Optional[str] = None
    message_text: str = Field(...)
    attachments: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[str] = None
    thread_id: Optional[str] = None
    sender_role: Optional[str] = None
    sender_email_resolved: Optional[str] = None


@router.post("/forward")
async def omnichannel_forward(req: OmnichannelForwardRequest) -> Dict[str, Any]:
    """Forward normalized payload to n8n intent orchestrator webhook."""
    base = os.getenv("N8N_WEBHOOK_BASE") or os.getenv("N8N_BASE_URL", "http://192.168.0.191:5678")
    url = f"{base.rstrip('/')}/webhook/myca/intent/orchestrator"
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=req.model_dump(exclude_none=True))
            r.raise_for_status()
            return {"success": True, "forwarded_to": url, "response": r.json()}
    except Exception as e:
        logger.warning("Forward to n8n failed: %s", e)
        raise HTTPException(503, f"Could not forward to intent orchestrator: {e}")


@router.post("/receive")
async def omnichannel_receive(req: OmnichannelReceiveRequest) -> Dict[str, Any]:
    """n8n webhook intake for normalized messages. Validates and acknowledges."""
    # Validate platform
    allowed = {"slack", "discord", "whatsapp", "signal", "email", "asana"}
    if req.platform_source.lower() not in allowed:
        raise HTTPException(400, f"Invalid platform_source: {req.platform_source}")
    # Acknowledge - actual orchestration is done by n8n workflows
    return {
        "success": True,
        "message": "Received",
        "platform_source": req.platform_source,
        "sender_id": req.sender_id,
    }


@router.post("/verify-sender", response_model=VerifySenderResponse)
async def verify_sender(req: VerifySenderRequest) -> VerifySenderResponse:
    """Verify sender is authorized. Called by n8n ingestion workflow."""
    pac = _get_platform_access()
    level = await pac.verify_sender(req.platform.lower(), req.sender_id)
    return VerifySenderResponse(
        authorized=level.authorized,
        role=level.role or "none",
        email=level.email or "",
    )


@router.get("/status")
async def omnichannel_status() -> Dict[str, Any]:
    """Connector health across all platforms."""
    status: Dict[str, Any] = {}

    # Slack
    try:
        _get_slack_client()
        tok = _env_any("MYCA_SLACK_BOT_TOKEN", "SLACK_BOT_TOKEN", "SLACK_OAUTH_TOKEN")
        status["slack"] = {"configured": bool(tok), "healthy": bool(tok)}
    except Exception as e:
        status["slack"] = {"configured": False, "healthy": False, "error": str(e)}

    # Discord
    try:
        _get_discord_client()
        tok = _env_any("MYCA_DISCORD_TOKEN", "DISCORD_BOT_TOKEN")
        status["discord"] = {"configured": bool(tok), "healthy": bool(tok)}
    except Exception as e:
        status["discord"] = {"configured": False, "healthy": False, "error": str(e)}

    # WhatsApp (Evolution API)
    try:
        wc = _get_whatsapp_client()
        ok = await wc.health_check()
        status["whatsapp"] = {"configured": True, "healthy": ok}
    except Exception as e:
        status["whatsapp"] = {"configured": False, "healthy": False, "error": str(e)}

    # Signal (signal-cli REST)
    try:
        sig = _get_signal_client()
        ok = await sig.health_check()
        status["signal"] = {"configured": bool(sig.number), "healthy": ok}
    except Exception as e:
        status["signal"] = {"configured": False, "healthy": False, "error": str(e)}

    # Email (Google Workspace)
    try:
        gw = _get_google_client()
        status["email"] = {"configured": gw is not None, "healthy": gw is not None}
    except Exception as e:
        status["email"] = {"configured": False, "healthy": False, "error": str(e)}

    # Asana
    try:
        _get_asana_client()
        tok = _env_any("ASANA_API_KEY", "ASANA_PAT", "MYCA_ASANA_TOKEN")
        status["asana"] = {"configured": bool(tok), "healthy": bool(tok)}
    except Exception as e:
        status["asana"] = {"configured": False, "healthy": False, "error": str(e)}

    return {"connectors": status}
