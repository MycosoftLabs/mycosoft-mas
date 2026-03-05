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

import aiohttp
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


async def handle_health(request: web.Request) -> web.Response:
    """GET /health — Health check for load balancers and monitoring."""
    os_ref = request.app.get("myca_os")
    if not os_ref:
        return web.json_response({"status": "no_os", "healthy": False})
    try:
        health = await os_ref._check_health()
        return web.json_response({
            "status": "ok",
            "healthy": health.get("healthy", True),
            "cycle": health.get("cycle", 0),
            "issues": health.get("issues", []),
        })
    except Exception as e:
        return web.json_response({"status": "error", "healthy": False, "error": str(e)})


async def handle_status(request: web.Request) -> web.Response:
    """GET /status — Full daemon status."""
    os_ref = request.app.get("myca_os")
    if not os_ref:
        return web.json_response({"error": "MYCA OS not attached"})
    return web.json_response(os_ref.status())


async def handle_tasks_get(request: web.Request) -> web.Response:
    """GET /tasks — Current task queue."""
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

    executive = os_ref.executive
    task = executive.add_task(
        title=title,
        description=description,
        priority=priority,
        task_type=task_type,
        source=source,
    )
    return web.json_response({
        "status": "added",
        "task_id": getattr(task, "id", None),
        "title": task.title,
    })


async def handle_message_post(request: web.Request) -> web.Response:
    """POST /message — Send a message to MYCA (she processes it like Morgan)."""
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
        "content": content,
        "is_morgan": body.get("is_morgan", True),
    }
    asyncio.create_task(os_ref._handle_message(msg))
    return web.json_response({"status": "accepted", "content": content[:100]})


async def handle_shell_post(request: web.Request) -> web.Response:
    """POST /shell — Execute a shell command (MYCA runs it)."""
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
        return web.json_response({
            "status": "completed",
            "returncode": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        })
    except asyncio.TimeoutError:
        return web.json_response({"status": "timeout", "error": "Command timed out"}, status=408)
    except Exception as e:
        return web.json_response({"status": "failed", "error": str(e)}, status=500)


async def handle_logs(request: web.Request) -> web.Response:
    """GET /logs — Tail last N log lines."""
    n = int(request.query.get("n", "100"))
    n = min(n, LOG_BUFFER_MAX)
    lines = LOG_BUFFER[-n:] if LOG_BUFFER else []
    return web.json_response({"logs": lines, "count": len(lines)})


async def handle_sessions(request: web.Request) -> web.Response:
    """GET /sessions — Active conversation sessions (placeholder)."""
    return web.json_response({"sessions": []})


async def handle_skills(request: web.Request) -> web.Response:
    """GET /skills — List available skills."""
    try:
        from mycosoft_mas.myca.os.skills_manager import list_skills
        skills = list_skills()
        return web.json_response({"skills": skills})
    except Exception as e:
        return web.json_response({"skills": [], "error": str(e)})


async def handle_skills_run(request: web.Request) -> web.Response:
    """POST /skills/run — Run a skill by ID."""
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
    sig_header = request.headers.get("X-Hub-Signature-256") or request.headers.get("X-Webhook-Signature")

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
    return web.json_response({
        "status": "accepted",
        "source": source,
        "task_id": getattr(task, "db_id", None),
        "title": task.title,
    })


async def handle_ws(request: web.Request) -> web.WebSocketResponse:
    """WebSocket /ws — Real-time log streaming and task updates."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    WS_CLIENTS.add(ws)
    try:
        await ws.send_str(json.dumps({
            "type": "connected",
            "message": "Connected to MYCA Gateway",
            "ts": datetime.now(timezone.utc).isoformat(),
        }))
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

    app.router.add_get("/health", handle_health)
    app.router.add_get("/status", handle_status)
    app.router.add_get("/tasks", handle_tasks_get)
    app.router.add_post("/tasks", handle_tasks_post)
    app.router.add_post("/message", handle_message_post)
    app.router.add_post("/shell", handle_shell_post)
    app.router.add_get("/logs", handle_logs)
    app.router.add_get("/sessions", handle_sessions)
    app.router.add_get("/ws", handle_ws)
    app.router.add_get("/skills", handle_skills)
    app.router.add_post("/skills/run", handle_skills_run)
    app.router.add_post("/skills/install", handle_skills_install)
    app.router.add_post("/webhooks/{source}", handle_webhooks)

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
