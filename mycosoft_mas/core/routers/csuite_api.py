"""
C-Suite Executive Assistant API Router

Heartbeat, reporting, escalation, and bounded-autonomy integration for
the four OpenClaw executive assistants (CEO, CFO, CTO, COO) on Proxmox 202.

Assistants report to MAS (188) and are visible to MYCA (191) via MAS.
State persists in Redis; escalations forward to MAS notifications (Morgan)
and are stored for Morgan visibility and MYCA task queues.

Created: March 7, 2026
"""

import json
import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("CSUITE")

router = APIRouter(prefix="/api/csuite", tags=["csuite"])

# Redis keys for C-Suite
_CSUITE_REDIS_KEY = "csuite:assistants"
_CFO_REPORT_HISTORY_KEY = "csuite:cfo:report_history"
_CFO_DIRECTIVES_KEY = "csuite:cfo:directives"
_CFO_AGENT_REPORTS_KEY = "csuite:cfo:agent_reports"
_CTO_REPORT_HISTORY_KEY = "csuite:cto:report_history"
_CTO_TASKS_KEY = "csuite:cto:tasks"  # Hash: task_id -> JSON
_CSUITE_ESCALATIONS_KEY = "csuite:escalations"  # List: escalation entries for Morgan visibility
_REDIS_TTL_SEC = 60 * 60 * 24 * 7  # 7 days
_MAX_HISTORY_ITEMS = 50

# In-memory registry (synced with Redis; fallback when Redis unavailable)
_assistant_registry: Dict[str, Dict[str, Any]] = {}
_heartbeat_ttl_seconds = int(os.getenv("CSUITE_HEARTBEAT_TTL", "120"))
_stale_task_threshold_seconds = int(os.getenv("CSUITE_STALE_TASK_SEC", "3600"))  # 1 hour
_redis_available: Optional[bool] = None


def _get_redis() -> Optional[redis.Redis]:
    """Return Redis client or None if unavailable."""
    global _redis_available
    if _redis_available is False:
        return None
    url = os.getenv("REDIS_URL") or os.getenv("MINDEX_REDIS_URL", "redis://192.168.0.189:6379")
    try:
        r = redis.from_url(url, socket_connect_timeout=3, decode_responses=True)
        r.ping()
        _redis_available = True
        return r
    except Exception as e:
        logger.debug("C-Suite: Redis unavailable (%s), using in-memory registry", e)
        _redis_available = False
        return None


def _load_registry() -> Dict[str, Dict[str, Any]]:
    """Load assistant registry from Redis into memory."""
    r = _get_redis()
    if r is None:
        return dict(_assistant_registry)
    try:
        data = r.get(_CSUITE_REDIS_KEY)
        if data:
            _assistant_registry.clear()
            _assistant_registry.update(json.loads(data))
        return dict(_assistant_registry)
    except Exception as e:
        logger.warning("C-Suite: Redis load failed: %s", e)
        return dict(_assistant_registry)


def _save_registry() -> None:
    """Persist assistant registry to Redis."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(_CSUITE_REDIS_KEY, _REDIS_TTL_SEC, json.dumps(_assistant_registry, default=str))
    except Exception as e:
        logger.warning("C-Suite: Redis save failed: %s", e)


def _push_history(key: str, item: Dict[str, Any]) -> None:
    """Append item to Redis list and trim to max size."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.lpush(key, json.dumps(item, default=str))
        r.ltrim(key, 0, _MAX_HISTORY_ITEMS - 1)
        r.expire(key, _REDIS_TTL_SEC)
    except Exception as e:
        logger.warning("C-Suite: Redis push to %s failed: %s", key, e)


def _get_history(key: str) -> List[Dict[str, Any]]:
    """Retrieve list from Redis, deserializing JSON items."""
    r = _get_redis()
    if r is None:
        return []
    try:
        raw = r.lrange(key, 0, _MAX_HISTORY_ITEMS - 1) or []
        out = []
        for s in raw:
            try:
                out.append(json.loads(s))
            except json.JSONDecodeError:
                pass
        return out
    except Exception as e:
        logger.warning("C-Suite: Redis get %s failed: %s", key, e)
        return []


def _get_cto_tasks() -> Dict[str, Dict[str, Any]]:
    """Return all CTO tasks from Redis hash."""
    r = _get_redis()
    if r is None:
        return {}
    try:
        data = r.hgetall(_CTO_TASKS_KEY) or {}
        out = {}
        for k, v in data.items():
            if v:
                try:
                    out[k] = json.loads(v)
                except json.JSONDecodeError:
                    pass
        return out
    except Exception as e:
        logger.warning("C-Suite: Redis get CTO tasks failed: %s", e)
        return {}


def _set_cto_task(task_id: str, task: Dict[str, Any]) -> None:
    """Store a CTO task in Redis hash."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.hset(_CTO_TASKS_KEY, task_id, json.dumps(task, default=str))
        r.expire(_CTO_TASKS_KEY, 86400 * 14)  # 14 days
    except Exception as e:
        logger.warning("C-Suite: Redis set CTO task failed: %s", e)


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


class FinanceDirectiveBody(BaseModel):
    """Finance directive from Meridian (CFO) to steer finance agents."""
    source: str = Field(default="Meridian", description="Meridian | CFO | Perplexity")
    directive: str = Field(..., description="Directive text or instruction")
    priority: str = Field(default="normal", description="low | normal | high | urgent")
    target_agent: Optional[str] = Field(default=None, description="Optional specific agent ID")
    extra: Dict[str, Any] = Field(default_factory=dict)


class AgentReportBody(BaseModel):
    """Report from a finance agent back to CFO."""
    agent_id: str = Field(..., description="Finance agent ID")
    report_type: str = Field(..., description="task_completion | status | escalation")
    summary: str = Field(..., description="Brief summary")
    details: Optional[Dict[str, Any]] = Field(default=None)
    task_id: Optional[str] = Field(default=None)


class ForgeTaskCreate(BaseModel):
    """CTO task posted by MYCA/Morgan for Forge."""
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description or instructions")
    priority: str = Field(default="normal", description="low | normal | high | urgent")
    source: str = Field(default="MYCA", description="MYCA | Morgan | CEO")
    extra: Dict[str, Any] = Field(default_factory=dict)


class ForgeTaskAck(BaseModel):
    """Forge acknowledges or completes a task."""
    status: str = Field(..., description="in_progress | complete | failed")
    summary: Optional[str] = Field(default=None, description="Completion summary")
    details: Optional[Dict[str, Any]] = Field(default=None)


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
    _save_registry()
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
    report_entry = {
        "role": body.role,
        "assistant_name": body.assistant_name,
        "type": body.report_type,
        "summary": body.summary,
        "details": body.details,
        "task_id": body.task_id,
        "escalated": body.escalated,
        "at": now.isoformat(),
    }
    _assistant_registry[aid]["last_report"] = report_entry
    _save_registry()

    # Persist to role-specific report history
    if body.role.upper() == "CTO":
        _push_history(_CTO_REPORT_HISTORY_KEY, report_entry)
    elif body.role.upper() == "CFO":
        _push_history(_CFO_REPORT_HISTORY_KEY, report_entry)

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
    esc_entry = {
        "role": body.role,
        "assistant_name": body.assistant_name,
        "subject": body.subject,
        "context": body.context,
        "options": body.options,
        "urgency": body.urgency,
        "at": now.isoformat(),
        "assistant_id": aid,
    }
    _assistant_registry[aid]["last_escalation"] = esc_entry
    _save_registry()

    # Persist escalation for Morgan visibility and MYCA task queues
    _push_history(_CSUITE_ESCALATIONS_KEY, esc_entry)

    # Forward to MAS notifications (Morgan) — email, webhook, SMS per priority
    try:
        from mycosoft_mas.services.admin_notifications import notify_morgan
        msg = f"{body.subject}\n\n{body.context}"
        if body.options:
            msg += "\n\nOptions: " + "; ".join(body.options)
        await notify_morgan(
            title=f"C-Suite Escalation: {body.role} ({body.assistant_name})",
            message=msg,
            type="warning" if body.urgency in ("high", "urgent") else "info",
            agent=body.assistant_name,
            priority=body.urgency,
            data={"subject": body.subject, "options": body.options, "role": body.role},
            requires_action=True,
        )
    except Exception as e:
        logger.warning("C-Suite: escalation notify_morgan failed: %s", e)

    return {"status": "ok", "assistant_id": aid, "escalation_received": True, "urgency": body.urgency}


@router.get("/assistants")
async def list_assistants(
    role: Optional[str] = Query(None, description="Filter by role: CEO, CFO, CTO, COO"),
    status: Optional[str] = Query(None, description="Filter by status: healthy, stale, offline"),
) -> Dict[str, Any]:
    """List registered C-Suite assistants (for MYCA dashboard, MAS UI)."""
    _load_registry()
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


@router.post("/finance-directive")
async def csuite_finance_directive(body: FinanceDirectiveBody) -> Dict[str, Any]:
    """Receive finance directive from Meridian (CFO) to steer finance agents."""
    now = datetime.now(timezone.utc)
    entry = {
        "source": body.source,
        "directive": body.directive,
        "priority": body.priority,
        "target_agent": body.target_agent,
        "extra": body.extra,
        "at": now.isoformat(),
    }
    _push_history(_CFO_DIRECTIVES_KEY, entry)
    logger.info(f"C-Suite finance directive [{body.priority}]: {body.source} — {body.directive[:80]}...")
    return {"status": "ok", "directive_received": True, "at": now.isoformat()}


@router.post("/agent-report")
async def csuite_agent_report(body: AgentReportBody) -> Dict[str, Any]:
    """Receive report from a finance agent back to CFO."""
    now = datetime.now(timezone.utc)
    entry = {
        "agent_id": body.agent_id,
        "report_type": body.report_type,
        "summary": body.summary,
        "details": body.details,
        "task_id": body.task_id,
        "at": now.isoformat(),
    }
    _push_history(_CFO_AGENT_REPORTS_KEY, entry)
    logger.info(f"C-Suite agent report: {body.agent_id} [{body.report_type}] — {body.summary[:80]}...")
    return {"status": "ok", "report_received": True, "at": now.isoformat()}


@router.get("/cfo/dashboard")
async def cfo_dashboard() -> Dict[str, Any]:
    """CFO dashboard: report history, directives, agent reports, stale tasks for Meridian oversight."""
    report_history = _get_history(_CFO_REPORT_HISTORY_KEY)
    directives = _get_history(_CFO_DIRECTIVES_KEY)
    agent_reports = _get_history(_CFO_AGENT_REPORTS_KEY)

    # Stale tasks: finance tasks with last update older than threshold
    stale_tasks: List[Dict[str, Any]] = []
    try:
        from mycosoft_mas.finance.discovery import list_finance_tasks
        tasks = await list_finance_tasks()
        now = datetime.now(timezone.utc)
        for t in tasks:
            at_str = t.get("at")
            if at_str:
                try:
                    dt = datetime.fromisoformat(at_str.replace("Z", "+00:00"))
                    age = (now - dt).total_seconds()
                    if age > _stale_task_threshold_seconds:
                        t_copy = dict(t)
                        t_copy["stale_seconds"] = int(age)
                        stale_tasks.append(t_copy)
                except Exception:
                    pass
    except Exception as e:
        logger.warning("C-Suite: stale task check failed: %s", e)

    return {
        "report_history": report_history,
        "directives": directives,
        "agent_reports": agent_reports,
        "stale_tasks": stale_tasks,
        "stale_threshold_seconds": _stale_task_threshold_seconds,
    }


@router.get("/cfo/status")
async def cfo_status() -> Dict[str, Any]:
    """CFO finance status for website/MYCA: health, counts, last activity.
    Used by finance plugin and C-suite dashboards."""
    report_history = _get_history(_CFO_REPORT_HISTORY_KEY)
    directives = _get_history(_CFO_DIRECTIVES_KEY)
    agent_reports = _get_history(_CFO_AGENT_REPORTS_KEY)
    _load_registry()
    cfo = _assistant_registry.get("csuite-cfo") or {}
    last_hb = cfo.get("last_heartbeat")
    status = "healthy"
    if last_hb:
        try:
            dt = datetime.fromisoformat(last_hb.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - dt).total_seconds()
            status = "stale" if age > _heartbeat_ttl_seconds else "healthy"
        except Exception:
            status = "unknown"
    else:
        status = "offline"

    return {
        "status": status,
        "role": "CFO",
        "assistant_name": cfo.get("assistant_name", "Meridian"),
        "reports_count": len(report_history),
        "directives_count": len(directives),
        "agent_reports_count": len(agent_reports),
        "last_heartbeat": last_hb,
        "last_report": cfo.get("last_report"),
    }


@router.get("/cfo/summary")
async def cfo_summary() -> Dict[str, Any]:
    """MYCA-visible CFO summary: aggregate counts and recent activity."""
    report_history = _get_history(_CFO_REPORT_HISTORY_KEY)
    directives = _get_history(_CFO_DIRECTIVES_KEY)
    agent_reports = _get_history(_CFO_AGENT_REPORTS_KEY)
    recent_reports = report_history[:5] if report_history else []
    recent_directives = directives[:3] if directives else []
    return {
        "reports_count": len(report_history),
        "directives_count": len(directives),
        "agent_reports_count": len(agent_reports),
        "recent_reports": recent_reports,
        "recent_directives": recent_directives,
    }


# --- Forge (CTO) endpoints ---


@router.post("/forge/task")
async def forge_create_task(body: ForgeTaskCreate) -> Dict[str, Any]:
    """Create a CTO task for Forge (from MYCA/Morgan)."""
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    task = {
        "id": task_id,
        "status": "pending",
        "title": body.title,
        "description": body.description,
        "priority": body.priority,
        "source": body.source,
        "extra": body.extra,
        "created_at": now.isoformat(),
        "acked_at": None,
        "summary": None,
        "details": None,
    }
    _set_cto_task(task_id, task)
    logger.info(f"C-Suite Forge task created: {task_id} — {body.title[:60]}...")
    return {"status": "ok", "task_id": task_id, "task": task}


@router.get("/forge/tasks")
async def forge_list_tasks(
    status: Optional[str] = Query(None, description="Filter: pending | in_progress | complete | failed"),
) -> Dict[str, Any]:
    """List CTO tasks for Forge to fetch."""
    tasks_map = _get_cto_tasks()
    tasks = list(tasks_map.values())
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    return {"tasks": tasks, "count": len(tasks)}


@router.post("/forge/tasks/{task_id}/ack")
async def forge_ack_task(task_id: str, body: ForgeTaskAck) -> Dict[str, Any]:
    """Forge acknowledges or completes a task."""
    tasks_map = _get_cto_tasks()
    if task_id not in tasks_map:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks_map[task_id]
    task["status"] = body.status
    task["summary"] = body.summary
    task["details"] = body.details
    task["acked_at"] = datetime.now(timezone.utc).isoformat()
    _set_cto_task(task_id, task)
    logger.info(f"C-Suite Forge task {task_id} acked: {body.status}")
    return {"status": "ok", "task_id": task_id, "task": task}


@router.get("/forge/dashboard")
async def forge_dashboard() -> Dict[str, Any]:
    """Forge dashboard: report history, pending tasks, assistant status, stale-work visibility."""
    _load_registry()
    report_history = _get_history(_CTO_REPORT_HISTORY_KEY)
    tasks_map = _get_cto_tasks()
    tasks = list(tasks_map.values())
    pending = [t for t in tasks if t.get("status") in ("pending", "in_progress")]
    assistant = _assistant_registry.get("csuite-cto") or {}

    # Stale work: tasks pending/in_progress older than threshold
    now = datetime.now(timezone.utc)
    stale_tasks: List[Dict[str, Any]] = []
    for t in pending:
        at_str = t.get("created_at") or t.get("acked_at")
        if at_str:
            try:
                dt = datetime.fromisoformat(at_str.replace("Z", "+00:00"))
                age = (now - dt).total_seconds()
                if age > _stale_task_threshold_seconds:
                    t_copy = dict(t)
                    t_copy["stale_seconds"] = int(age)
                    stale_tasks.append(t_copy)
            except Exception:
                pass

    return {
        "report_history": report_history[:20],
        "tasks": tasks,
        "pending_count": len(pending),
        "stale_tasks": stale_tasks,
        "assistant": assistant,
        "stale_threshold_seconds": _stale_task_threshold_seconds,
    }


@router.get("/forge/summary")
async def forge_summary() -> Dict[str, Any]:
    """MYCA-visible CTO summary: aggregate counts and recent activity for Morgan oversight."""
    _load_registry()
    report_history = _get_history(_CTO_REPORT_HISTORY_KEY)
    tasks_map = _get_cto_tasks()
    tasks = list(tasks_map.values())
    pending = [t for t in tasks if t.get("status") in ("pending", "in_progress")]
    escalations = _get_history(_CSUITE_ESCALATIONS_KEY)
    assistant = _assistant_registry.get("csuite-cto") or {}

    # Stale task count
    now = datetime.now(timezone.utc)
    stale_count = 0
    for t in pending:
        at_str = t.get("created_at") or t.get("acked_at")
        if at_str:
            try:
                dt = datetime.fromisoformat(at_str.replace("Z", "+00:00"))
                if (now - dt).total_seconds() > _stale_task_threshold_seconds:
                    stale_count += 1
            except Exception:
                pass

    return {
        "reports_count": len(report_history),
        "tasks_count": len(tasks),
        "pending_count": len(pending),
        "stale_tasks_count": stale_count,
        "escalations_count": len(escalations),
        "recent_reports": report_history[:5] if report_history else [],
        "recent_escalations": escalations[:5] if escalations else [],
        "assistant_status": assistant.get("status", "unknown"),
        "last_heartbeat": assistant.get("last_heartbeat"),
    }


@router.get("/escalations")
async def list_escalations(
    role: Optional[str] = Query(None, description="Filter by role"),
    limit: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    """List C-Suite escalations for Morgan oversight and MYCA task visibility."""
    escalations = _get_history(_CSUITE_ESCALATIONS_KEY)
    if role:
        escalations = [e for e in escalations if e.get("role", "").upper() == role.upper()]
    return {"escalations": escalations[:limit], "count": len(escalations[:limit])}


@router.get("/health")
async def csuite_health() -> Dict[str, str]:
    """Health check for C-Suite API."""
    return {"status": "healthy", "service": "csuite-api"}
