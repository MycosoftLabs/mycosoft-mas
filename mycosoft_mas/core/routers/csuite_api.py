"""
C-Suite Executive Assistant API Router

Heartbeat, reporting, escalation, and bounded-autonomy integration for
the four OpenClaw executive assistants (CEO, CFO, CTO, COO) on Proxmox 90.

Assistants report to MAS (188) and are visible to MYCA (191) via MAS.

Created: March 7, 2026
"""

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("CSUITE")

router = APIRouter(prefix="/api/csuite", tags=["csuite"])

# In-memory registry (TTL-based; Redis optional later)
_assistant_registry: Dict[str, Dict[str, Any]] = {}
_heartbeat_ttl_seconds = int(os.getenv("CSUITE_HEARTBEAT_TTL", "120"))


class CSuiteHeartbeat(BaseModel):
    """Heartbeat from an executive assistant VM."""
    role: str = Field(..., description="CEO | CFO | CTO | COO")
    assistant_name: str = Field(..., description="Atlas | Meridian | Forge | Nexus")
    ip: str = Field(..., description="VM IP (192.168.0.192-195)")
    status: str = Field(default="healthy", description="healthy | degraded | error")
    openclaw_version: Optional[str] = Field(default=None)
    primary_tool: Optional[str] = Field(default=None, description="MYCAOS | Perplexity | Cursor | Claude Cowork")
    extra: Dict[str, Any] = Field(default_factory=dict)


class CSuiteReport(BaseModel):
    """Task completion, executive summary, or operating report."""
    role: str = Field(..., description="CEO | CFO | CTO | COO")
    assistant_name: str = Field(...)
    report_type: str = Field(..., description="task_completion | executive_summary | operating_report")
    summary: str = Field(..., description="Brief summary")
    details: Optional[Dict[str, Any]] = Field(default=None)
    task_id: Optional[str] = Field(default=None)
    escalated: bool = Field(default=False, description="True if escalation to Morgan required")


class CSuiteEscalation(BaseModel):
    """Escalation request when assistant needs Morgan's decision."""
    role: str = Field(...)
    assistant_name: str = Field(...)
    subject: str = Field(..., description="Escalation subject")
    context: str = Field(..., description="What decision is needed")
    options: Optional[List[str]] = Field(default=None, description="Proposed options")
    urgency: str = Field(default="normal", description="low | normal | high | urgent")


def _assistant_id(role: str) -> str:
    return f"csuite-{role.lower()}"


@router.post("/heartbeat")
async def csuite_heartbeat(body: CSuiteHeartbeat) -> Dict[str, Any]:
    """Receive heartbeat from C-Suite executive assistant VM."""
    aid = _assistant_id(body.role)
    now = datetime.now(timezone.utc)
    _assistant_registry[aid] = {
        "role": body.role,
        "assistant_name": body.assistant_name,
        "ip": body.ip,
        "status": body.status,
        "openclaw_version": body.openclaw_version,
        "primary_tool": body.primary_tool or "",
        "last_heartbeat": now.isoformat(),
        "extra": body.extra,
    }
    logger.info(f"C-Suite heartbeat: {body.role} ({body.assistant_name}) @ {body.ip} — {body.status}")
    return {"status": "ok", "assistant_id": aid, "registered_at": now.isoformat()}


@router.post("/report")
async def csuite_report(body: CSuiteReport) -> Dict[str, Any]:
    """Receive task completion, executive summary, or operating report from assistant."""
    aid = _assistant_id(body.role)
    now = datetime.now(timezone.utc)
    logger.info(f"C-Suite report [{body.report_type}]: {body.role} — {body.summary[:80]}...")
    # Store last report per assistant (optional; could forward to MYCA/n8n)
    if aid not in _assistant_registry:
        _assistant_registry[aid] = {}
    _assistant_registry[aid]["last_report"] = {
        "type": body.report_type,
        "summary": body.summary,
        "details": body.details,
        "task_id": body.task_id,
        "escalated": body.escalated,
        "at": now.isoformat(),
    }
    if body.escalated:
        logger.warning(f"C-Suite escalation from {body.role}: {body.summary}")
    return {"status": "ok", "assistant_id": aid, "report_received": True}


@router.post("/escalate")
async def csuite_escalation(body: CSuiteEscalation) -> Dict[str, Any]:
    """Receive escalation request when assistant needs Morgan's decision."""
    aid = _assistant_id(body.role)
    now = datetime.now(timezone.utc)
    logger.warning(f"C-Suite escalation: {body.role} ({body.assistant_name}) — {body.subject} [{body.urgency}]")
    if aid not in _assistant_registry:
        _assistant_registry[aid] = {}
    _assistant_registry[aid]["last_escalation"] = {
        "subject": body.subject,
        "context": body.context,
        "options": body.options,
        "urgency": body.urgency,
        "at": now.isoformat(),
    }
    # TODO: Forward to MYCA task queue or Discord/Slack notification
    return {"status": "ok", "assistant_id": aid, "escalation_received": True, "urgency": body.urgency}


@router.get("/assistants")
async def list_assistants(
    role: Optional[str] = Query(None, description="Filter by role: CEO, CFO, CTO, COO"),
    status: Optional[str] = Query(None, description="Filter by status: healthy, stale, offline"),
) -> Dict[str, Any]:
    """List registered C-Suite assistants (for MYCA dashboard, MAS UI)."""
    now = datetime.now(timezone.utc)
    results = []
    for aid, data in _assistant_registry.items():
        r = data.get("role", "")
        if role and r.upper() != role.upper():
            continue
        last = data.get("last_heartbeat")
        is_stale = False
        if last:
            try:
                dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                age = (now - dt).total_seconds()
                is_stale = age > _heartbeat_ttl_seconds
            except Exception:
                is_stale = True
        effective_status = "stale" if is_stale else data.get("status", "unknown")
        if status and effective_status != status:
            continue
        results.append({
            "assistant_id": aid,
            "role": r,
            "assistant_name": data.get("assistant_name", ""),
            "ip": data.get("ip", ""),
            "status": effective_status,
            "primary_tool": data.get("primary_tool", ""),
            "last_heartbeat": last,
            "last_report": data.get("last_report"),
            "last_escalation": data.get("last_escalation"),
        })
    return {"assistants": results, "count": len(results)}


@router.get("/health")
async def csuite_health() -> Dict[str, str]:
    """Health check for C-Suite API."""
    return {"status": "healthy", "service": "csuite-api"}
