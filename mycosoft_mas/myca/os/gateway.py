"""
MYCA Gateway — HTTP/WebSocket control plane at port 8100.

Single entry point for all clients: website, CLI, Discord, n8n, MCP.
Serves health, status, tasks, message injection, shell execution, and real-time logs.

Date: 2026-03-05
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Set

from aiohttp import web

logger = logging.getLogger("myca.os.gateway")

GATEWAY_PORT = int(os.getenv("MYCA_GATEWAY_PORT", "8100"))
GATEWAY_HOST = os.getenv("MYCA_GATEWAY_HOST", "0.0.0.0")

# In-memory log buffer for /logs (last N lines)
LOG_BUFFER: list[str] = []
LOG_BUFFER_MAX = 500
WS_CLIENTS: Set[web.WebSocketResponse] = set()


def log_to_buffer(msg: str):
    """Append a log line to the buffer for /logs endpoint and WS broadcast."""
    LOG_BUFFER.append(msg)
    if len(LOG_BUFFER) > LOG_BUFFER_MAX:
        LOG_BUFFER.pop(0)
    # Broadcast to WS clients
    for ws in list(WS_CLIENTS):
        if not ws.closed:
            try:
                asyncio.create_task(ws.send_str(json.dumps({"type": "log", "line": msg})))
            except Exception:
                WS_CLIENTS.discard(ws)


def broadcast_skill_progress(skill_id: str, message: str, percent: Optional[float] = None):
    """Broadcast skill progress to WebSocket clients for real-time UI updates."""
    payload = {"type": "skill_progress", "skill_id": skill_id, "message": message}
    if percent is not None:
        payload["percent"] = percent
    for ws in list(WS_CLIENTS):
        if not ws.closed:
            try:
                asyncio.create_task(ws.send_str(json.dumps(payload)))
            except Exception:
                WS_CLIENTS.discard(ws)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_gateway_api_key() -> str:
    for env_name in ("MYCA_GATEWAY_API_KEY", "MYCA_API_KEY", "MYCA_WORKSPACE_API_KEY"):
        value = (os.getenv(env_name) or "").strip()
        if value:
            return value
    return ""


def _get_bearer_token(request: web.Request) -> str:
    auth = request.headers.get("Authorization", "").strip()
    if not auth.lower().startswith("bearer "):
        return ""
    return auth[7:].strip()


def _get_request_api_key(request: web.Request) -> str:
    return (
        request.headers.get("X-MYCA-API-Key", "").strip()
        or request.headers.get("X-API-Key", "").strip()
        or _get_bearer_token(request)
    )


def _is_trusted_remote(request: web.Request) -> bool:
    trusted = {
        "127.0.0.1",
        "::1",
        "localhost",
        "192.168.0.191",
        "192.168.0.188",
    }
    configured = os.getenv("MYCA_TRUSTED_IPS", "").strip()
    if configured:
        trusted.update(ip.strip() for ip in configured.split(",") if ip.strip())
    remote = (request.remote or "").strip()
    return remote in trusted


def _is_authorized_request(request: web.Request) -> bool:
    expected = _get_gateway_api_key()
    provided = _get_request_api_key(request)
    if expected and provided:
        return hmac.compare_digest(expected, provided)
    return _is_trusted_remote(request)


def _auth_error() -> web.Response:
    return web.json_response(
        {"error": "unauthorized", "message": "Valid MYCA gateway credentials required."},
        status=401,
    )


def _feature_disabled_error(feature: str) -> web.Response:
    return web.json_response(
        {"error": "disabled", "message": f"{feature} is disabled by runtime policy."},
        status=403,
    )


async def handle_channels(request: web.Request) -> web.Response:
    """GET /channels — Per-channel connectivity status (Slack, Asana, Signal, Discord, WhatsApp)."""
    try:
        from mycosoft_mas.myca.os.channels_health import get_all_channel_status

        data = await get_all_channel_status()
        return web.json_response(data)
    except Exception as e:
        return web.json_response({"channels": {}, "error": str(e)})


async def handle_health(request: web.Request) -> web.Response:
    """GET /health — Health check for load balancers and monitoring. Includes channel status."""
    identity = os.getenv("SMTP_USER", os.getenv("MYCA_IDENTITY", "schedule@mycosoft.org"))
    vm = os.getenv("MYCA_VM", "192.168.0.191")
    base_payload = {
        "identity": identity,
        "vm": vm,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    os_ref = request.app.get("myca_os")
    if not os_ref:
        # Return basic health + channel status even when OS not attached (e.g. during boot)
        try:
            from mycosoft_mas.myca.os.channels_health import get_all_channel_status

            channel_data = await get_all_channel_status()
            services = {
                ch: (data.get("connected", False) or data.get("status") == "connected")
                for ch, data in (channel_data.get("channels") or {}).items()
            }
        except Exception:
            services = {}
        connected = sum(1 for v in services.values() if v)
        return web.json_response(
            {
                **base_payload,
                "status": "healthy" if connected > 0 else "no_os",
                "healthy": connected > 0,
                "services": services,
            }
        )
    try:
        health = await os_ref._check_health()
        payload = {
            **base_payload,
            "status": "ok",
            "healthy": health.get("healthy", True),
            "cycle": health.get("cycle", 0),
            "issues": health.get("issues", []),
        }
        # Include channel connectivity (Slack, Asana, Discord, Signal, WhatsApp)
        try:
            from mycosoft_mas.myca.os.channels_health import get_all_channel_status

            channel_data = await get_all_channel_status()
            payload["services"] = {
                ch: (data.get("connected", False) or data.get("status") == "connected")
                for ch, data in (channel_data.get("channels") or {}).items()
            }
        except Exception:
            payload["services"] = {}
        return web.json_response(payload)
    except Exception as e:
        return web.json_response(
            {
                **base_payload,
                "status": "error",
                "healthy": False,
                "error": str(e),
            }
        )


async def handle_status(request: web.Request) -> web.Response:
    """GET /status — Full daemon status."""
    if not _is_authorized_request(request):
        return _auth_error()
    os_ref = request.app.get("myca_os")
    if not os_ref:
        return web.json_response({"error": "MYCA OS not attached"})
    return web.json_response(os_ref.status())


async def handle_tasks_get(request: web.Request) -> web.Response:
    """GET /tasks — Current task queue."""
    if not _is_authorized_request(request):
        return _auth_error()
    os_ref = request.app.get("myca_os")
    if not os_ref:
        return web.json_response({"tasks": [], "error": "no_os"})
    executive = os_ref.executive
    tasks = [
        {
            "title": t.title,
            "priority": t.priority.value,
            "status": t.status,
            "type": t.task_type,
            "source": t.source,
        }
        for t in executive._task_queue
    ]
    return web.json_response({"tasks": tasks, "count": len(tasks)})


async def handle_tasks_post(request: web.Request) -> web.Response:
    """POST /tasks — Submit a new task."""
    if not _is_authorized_request(request):
        return _auth_error()
    os_ref = request.app.get("myca_os")
    if not os_ref:
        return web.json_response({"error": "MYCA OS not attached"}, status=503)
    try:
        body = await request.json()
    except Exception:
        body = {}
    title = body.get("title", "Untitled task")
    description = body.get("description", "")
    priority = body.get("priority", "medium")
    task_type = body.get("type", body.get("task_type", "general"))
    source = body.get("source", "api")
    assigned_to = body.get("assigned_to")

    executive = os_ref.executive
    task = executive.add_task(
        title=title,
        description=description,
        priority=priority,
        task_type=task_type,
        source=source,
        assigned_to=assigned_to,
    )
    return web.json_response(
        {
            "status": "added",
            "task_id": getattr(task, "id", None),
            "title": task.title,
        }
    )


async def handle_message_post(request: web.Request) -> web.Response:
    """POST /message — Send a message to MYCA (she processes it like Morgan)."""
    if not _is_authorized_request(request):
        return _auth_error()
    os_ref = request.app.get("myca_os")
    if not os_ref:
        return web.json_response({"error": "MYCA OS not attached"}, status=503)
    try:
        body = await request.json()
    except Exception:
        body = {}
    content = body.get("content", body.get("message", ""))
    if not content:
        return web.json_response({"error": "content required"}, status=400)

    msg = {
        "source": body.get("source", "api"),
        "sender": body.get("sender", "api"),
        "sender_id": body.get("sender_id"),
        "content": content,
        "is_morgan": body.get("is_morgan", False),
    }
    asyncio.create_task(os_ref._handle_message(msg))
    return web.json_response({"status": "accepted", "content": content[:100]})


async def handle_shell_post(request: web.Request) -> web.Response:
    """POST /shell — Execute a shell command (MYCA runs it)."""
    if not _is_authorized_request(request):
        return _auth_error()
    if not _env_flag("MYCA_ENABLE_SHELL_API", default=False):
        return _feature_disabled_error("Shell API")
    os_ref = request.app.get("myca_os")
    if not os_ref:
        return web.json_response({"error": "MYCA OS not attached"}, status=503)
    try:
        body = await request.json()
    except Exception:
        body = {}
    command = body.get("command", body.get("cmd", ""))
    if not command:
        return web.json_response({"error": "command required"}, status=400)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        return web.json_response(
            {
                "status": "completed",
                "returncode": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        )
    except asyncio.TimeoutError:
        return web.json_response({"status": "timeout", "error": "Command timed out"}, status=408)
    except Exception as e:
        return web.json_response({"status": "failed", "error": str(e)}, status=500)


async def handle_logs(request: web.Request) -> web.Response:
    """GET /logs — Tail last N log lines."""
    if not _is_authorized_request(request):
        return _auth_error()
    n = int(request.query.get("n", "100"))
    n = min(n, LOG_BUFFER_MAX)
    lines = LOG_BUFFER[-n:] if LOG_BUFFER else []
    return web.json_response({"logs": lines, "count": len(lines)})


async def handle_sessions(request: web.Request) -> web.Response:
    """GET /sessions — Active conversation sessions (placeholder)."""
    if not _is_authorized_request(request):
        return _auth_error()
    return web.json_response({"sessions": []})


async def handle_skills(request: web.Request) -> web.Response:
    """GET /skills — List available skills."""
    if not _is_authorized_request(request):
        return _auth_error()
    try:
        from mycosoft_mas.myca.os.skills_manager import list_skills

        skills = list_skills()
        return web.json_response({"skills": skills})
    except Exception as e:
        return web.json_response({"skills": [], "error": str(e)})


async def handle_skills_run(request: web.Request) -> web.Response:
    """POST /skills/run — Run a skill by ID."""
    if not _is_authorized_request(request):
        return _auth_error()
    os_ref = request.app.get("myca_os")
    try:
        body = await request.json()
    except Exception:
        body = {}
    skill_id = body.get("skill_id", body.get("skill", ""))
    args = body.get("args", body)
    if not skill_id:
        return web.json_response({"error": "skill_id required"}, status=400)
    try:
        from mycosoft_mas.myca.os.skills_manager import run_skill

        result = await run_skill(skill_id, args, os_ref)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"status": "failed", "error": str(e)}, status=500)


async def handle_skills_install(request: web.Request) -> web.Response:
    """POST /skills/install — Install a skill from a git repository."""
    if not _is_authorized_request(request):
        return _auth_error()
    if not _env_flag("MYCA_ENABLE_SKILL_INSTALL", default=False):
        return _feature_disabled_error("Skill install API")
    try:
        body = await request.json()
    except Exception:
        body = {}
    url = body.get("url", body.get("repo", ""))
    branch = body.get("branch", "main")
    if not url:
        return web.json_response({"error": "url or repo required"}, status=400)
    try:
        from mycosoft_mas.myca.os.skills_manager import install_skill_from_git

        skill_id = install_skill_from_git(url, branch=branch)
        return web.json_response({"status": "installed", "skill_id": skill_id})
    except Exception as e:
        return web.json_response({"status": "failed", "error": str(e)}, status=500)


# Valid webhook sources and their default task type/priority mapping
WEBHOOK_SOURCE_CONFIG = {
    "asana": {"task_type": "asana", "default_priority": "high"},
    "github": {"task_type": "github", "default_priority": "high"},
    "calendar": {"task_type": "calendar", "default_priority": "medium"},
    "n8n": {"task_type": "automation", "default_priority": "medium"},
    "csuite": {"task_type": "finance", "default_priority": "high"},
    "finance": {"task_type": "finance", "default_priority": "high"},
    "custom": {"task_type": "general", "default_priority": "medium"},
}


def _verify_webhook_hmac(body: bytes, signature_header: Optional[str], secret: str) -> bool:
    """Verify HMAC-SHA256 signature. Supports X-Hub-Signature-256 (sha256=hex) and X-Webhook-Signature (hex)."""
    if not secret or not signature_header:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    if signature_header.startswith("sha256="):
        received = signature_header[7:].strip().lower()
    else:
        received = signature_header.strip().lower()
    return hmac.compare_digest(expected, received)


async def handle_webhooks(request: web.Request) -> web.Response:
    """POST /webhooks/{source} — Receive webhook from Asana, GitHub, Calendar, n8n, or custom."""
    source = request.match_info.get("source", "custom").lower()
    if source not in WEBHOOK_SOURCE_CONFIG:
        return web.json_response(
            {"error": f"unknown source. valid: {list(WEBHOOK_SOURCE_CONFIG)}"},
            status=400,
        )

    os_ref = request.app.get("myca_os")
    if not os_ref:
        return web.json_response({"error": "MYCA OS not attached"}, status=503)

    body = await request.read()
    secret = os.getenv("WEBHOOK_SECRET", "").strip()
    sig_header = request.headers.get("X-Hub-Signature-256") or request.headers.get(
        "X-Webhook-Signature"
    )

    if secret:
        if not _verify_webhook_hmac(body, sig_header, secret):
            logger.warning("Webhook HMAC verification failed for source=%s", source)
            return web.json_response({"error": "invalid signature"}, status=401)
    else:
        return web.json_response(
            {"error": "WEBHOOK_SECRET not configured; webhooks disabled"},
            status=503,
        )

    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError:
        payload = {}

    cfg = WEBHOOK_SOURCE_CONFIG[source]
    title = payload.get("title") or payload.get("name") or f"Webhook from {source}"
    description = payload.get("description") or payload.get("body") or json.dumps(payload)[:2000]
    priority = payload.get("priority") or cfg["default_priority"]
    task_type = payload.get("task_type") or cfg["task_type"]

    executive = os_ref.executive
    task = executive.add_task(
        title=str(title),
        description=str(description),
        priority=str(priority),
        task_type=str(task_type),
        source=source,
    )
    return web.json_response(
        {
            "status": "accepted",
            "source": source,
            "task_id": getattr(task, "db_id", None),
            "title": task.title,
        }
    )


STANDUP_PROMPT_TEMPLATE = """**Daily Standup** (11 AM)

Morgan, Garret, RJ, Beto — please share:
1. What you did yesterday
2. What you're doing today
3. Any blockers

Reply in this thread. MYCA will summarize and flag overdue items."""


async def handle_beto_onboarding_get(request: web.Request) -> web.Response:
    """GET /beto-onboarding — Beto onboarding checklist with completion status."""
    if not _is_authorized_request(request):
        return _auth_error()
    try:
        from pathlib import Path

        import yaml

        cfg_path = Path(__file__).resolve().parents[3] / "config" / "beto_onboarding_checklist.yaml"
        if not cfg_path.exists():
            return web.json_response({"items": [], "error": "checklist config not found"})
        cfg = yaml.safe_load(cfg_path.read_text())
        items = cfg.get("checklist", [])
    except Exception as e:
        return web.json_response({"items": [], "error": str(e)})

    # Get completion from mindex_bridge (working memory or pg)
    completed_map = {}
    os_ref = request.app.get("myca_os")
    if os_ref:
        bridge = getattr(os_ref, "mindex_bridge", None)
        if bridge and getattr(bridge, "_pg_pool", None) and bridge._pg_pool:
            try:
                async with bridge._pg_pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT checklist_id, completed_at, notes FROM myca_beto_onboarding WHERE completed_at IS NOT NULL"
                    )
                    completed_map = {
                        r["checklist_id"]: {
                            "completed_at": (
                                r["completed_at"].isoformat() if r["completed_at"] else None
                            ),
                            "notes": r["notes"],
                        }
                        for r in rows
                    }
            except Exception:
                pass
        elif bridge and hasattr(bridge, "recall"):
            try:
                data = await bridge.recall("working:beto_onboarding")
                if data and isinstance(data, dict):
                    completed_map = data
            except Exception:
                pass

    result = []
    for item in items:
        cid = item.get("id", "")
        comp = completed_map.get(cid, {})
        result.append(
            {
                "id": cid,
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "completed": cid in completed_map and comp.get("completed_at"),
                "completed_at": comp.get("completed_at"),
                "notes": comp.get("notes"),
            }
        )
    return web.json_response({"items": result})


async def handle_beto_onboarding_complete(request: web.Request) -> web.Response:
    """POST /beto-onboarding/{id}/complete — Mark Beto onboarding item complete."""
    if not _is_authorized_request(request):
        return _auth_error()
    item_id = request.match_info.get("id", "").strip()
    if not item_id:
        return web.json_response({"error": "id required"}, status=400)
    try:
        body = await request.json()
    except Exception:
        body = {}
    notes = body.get("notes", "")

    os_ref = request.app.get("myca_os")
    if not os_ref:
        return web.json_response({"error": "MYCA OS not attached"}, status=503)
    bridge = getattr(os_ref, "mindex_bridge", None)
    if not bridge:
        return web.json_response({"error": "mindex_bridge not available"}, status=503)

    if getattr(bridge, "_pg_pool", None) and bridge._pg_pool:
        try:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            async with bridge._pg_pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO myca_beto_onboarding (checklist_id, completed_at, notes, updated_at)
                       VALUES ($1, $2, $3, $4)
                       ON CONFLICT (checklist_id) DO UPDATE SET completed_at = $2, notes = $3, updated_at = $4""",
                    item_id,
                    now,
                    notes or None,
                    now,
                )
            return web.json_response({"status": "completed", "id": item_id})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    return web.json_response(
        {"error": "PostgreSQL storage required for Beto onboarding"}, status=503
    )


async def handle_investor_draft(request: web.Request) -> web.Response:
    """POST /investor-draft — Generate investor update draft (called by n8n quarterly)."""
    if not _is_authorized_request(request):
        return _auth_error()
    body = {}
    ct = request.headers.get("Content-Type", "")
    if "application/json" in ct:
        try:
            body = await request.json() or {}
        except Exception:
            pass
    else:
        try:
            form = await request.post()
            body = dict(form) if form else {}
        except Exception:
            pass
    from datetime import datetime, timezone
    from pathlib import Path

    def _get(v):
        x = body.get(v, "")
        return x[0] if isinstance(x, (list, tuple)) else (x or "")

    period = _get("period")
    if not period:
        now = datetime.now()
        q = (now.month - 1) // 3 + 1
        period = f"{now.year}-Q{q}"
    template_name = _get("template") or "investor_update"
    tpl_path = Path(__file__).resolve().parents[3] / "templates" / f"{template_name}.md"
    if not tpl_path.exists():
        return web.json_response({"error": f"template {template_name} not found"}, status=404)
    content = tpl_path.read_text()
    content = content.replace("[YYYY-MM-DD]", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    content = content.replace("[Quarter/Period]", str(period))
    # TODO: Fetch metrics from MINDEX when /api/mindex/metrics available
    return web.json_response({"draft": content, "period": period})


async def handle_standup_prompt(request: web.Request) -> web.Response:
    """POST /standup-prompt — Post daily standup prompt to Discord/Slack (called by n8n at 11 AM Mon-Fri)."""
    if not _is_authorized_request(request):
        return _auth_error()
    os_ref = request.app.get("myca_os")
    if not os_ref:
        return web.json_response({"error": "MYCA OS not attached"}, status=503)
    try:
        comms = getattr(os_ref, "comms", None)
        if not comms:
            return web.json_response({"error": "comms hub not available"}, status=503)
        from mycosoft_mas.myca.os.comms_hub import Channel

        await comms.broadcast(STANDUP_PROMPT_TEMPLATE, channels=[Channel.DISCORD, Channel.SLACK])
        return web.json_response({"status": "sent", "channels": ["discord", "slack"]})
    except Exception as e:
        logger.exception("Standup prompt failed")
        return web.json_response({"status": "error", "error": str(e)}, status=500)


async def handle_ws(request: web.Request) -> web.WebSocketResponse:
    """WebSocket /ws — Real-time log streaming and task updates."""
    if not _is_authorized_request(request):
        raise web.HTTPUnauthorized(text="Valid MYCA gateway credentials required.")
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    WS_CLIENTS.add(ws)
    try:
        await ws.send_str(
            json.dumps(
                {
                    "type": "connected",
                    "message": "Connected to MYCA Gateway",
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )
        )
        async for _ in ws:
            pass
    except Exception:
        pass
    finally:
        WS_CLIENTS.discard(ws)
    return ws


def create_app(os_ref=None) -> web.Application:
    """Create the aiohttp application."""
    app = web.Application()
    app["myca_os"] = os_ref

    # Use explicit route names to avoid aiohttp resource reuse that can cause
    # "method POST is already registered" when dynamic paths overlap.
    app.router.add_get("/channels", handle_channels, name="channels")
    app.router.add_get("/health", handle_health, name="health")
    app.router.add_get("/status", handle_status, name="status")
    app.router.add_get("/tasks", handle_tasks_get, name="tasks")
    app.router.add_post("/tasks", handle_tasks_post, name="tasks")
    app.router.add_post("/message", handle_message_post, name="message")
    app.router.add_post("/shell", handle_shell_post, name="shell")
    app.router.add_get("/logs", handle_logs, name="logs")
    app.router.add_get("/sessions", handle_sessions, name="sessions")
    app.router.add_get("/ws", handle_ws, name="ws")
    app.router.add_get("/skills", handle_skills, name="skills")
    app.router.add_post("/skills/run", handle_skills_run, name="skills_run")
    app.router.add_post("/skills/install", handle_skills_install, name="skills_install")
    app.router.add_post("/standup-prompt", handle_standup_prompt, name="standup_prompt")
    app.router.add_post("/investor-draft", handle_investor_draft, name="investor_draft")
    app.router.add_get("/beto-onboarding", handle_beto_onboarding_get, name="beto_onboarding_get")
    app.router.add_post(
        "/beto-onboarding/{id}/complete",
        handle_beto_onboarding_complete,
        name="beto_onboarding_complete",
    )
    app.router.add_post(r"/webhooks/{source}", handle_webhooks, name="webhooks")

    return app


async def run_gateway(os_ref, port: int = GATEWAY_PORT, host: str = GATEWAY_HOST):
    """Run the gateway server. Blocks until shutdown."""
    app = create_app(os_ref)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("MYCA Gateway listening on http://%s:%s", host, port)
    return runner
