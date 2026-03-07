"""
MYCA Workspace API — VM 191
Exposes MYCA's tools (email, Discord, Asana, calendar) as HTTP endpoints
so her consciousness (VM 188) can take real-world actions.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MYCA Workspace API",
    description="MYCA's autonomous workspace — email, Discord, Asana, calendar",
    version="1.0.0",
)

MAS_API_URL = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
MYCA_EMAIL = os.getenv("MYCA_EMAIL", "schedule@mycosoft.org")
MYCA_DISCORD_TOKEN = os.getenv("MYCA_DISCORD_TOKEN", "")
DISCORD_OPS_CHANNEL = os.getenv("DISCORD_OPS_CHANNEL_ID", "")


def _env_asana_token() -> str:
    """Asana token from ASANA_API_KEY, ASANA_PAT, or MYCA_ASANA_TOKEN (deploy uses ASANA_PAT on VM 191)."""
    for name in ("ASANA_API_KEY", "ASANA_PAT", "MYCA_ASANA_TOKEN"):
        v = (os.getenv(name) or "").strip()
        if v:
            return v
    return ""


ASANA_WORKSPACE_ID = os.getenv("ASANA_WORKSPACE_ID", "")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "identity": MYCA_EMAIL,
        "vm": "192.168.0.191",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "email": bool(os.path.exists(os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY", ""))),
            "discord": bool(MYCA_DISCORD_TOKEN),
            "asana": bool(_env_asana_token()),
        }
    }


# ── Workspace Context (for website chat) ──────────────────────────────────────

@app.get("/workspace/context")
async def get_workspace_context():
    """Returns MYCA's current workspace state for the website chat."""
    tasks = await _get_asana_tasks_today()
    discord_status = await _get_discord_presence()
    return {
        "identity": {
            "name": "MYCA",
            "email": MYCA_EMAIL,
            "role": "Autonomous AI Employee",
            "vm": "192.168.0.191",
        },
        "active_tasks": tasks[:5],
        "discord_status": discord_status,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


# ── Email (Gmail via service account) ─────────────────────────────────────────

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None

@app.post("/workspace/email/send")
async def send_email(req: EmailRequest):
    """MYCA sends an email from schedule@mycosoft.org."""
    try:
        from mycosoft_mas.integrations.google_workspace_client import GoogleWorkspaceClient
        client = GoogleWorkspaceClient()
        result = client.send_email(
            to=req.to,
            subject=req.subject,
            body=req.body,
            cc=req.cc,
        )
        logger.info(f"MYCA sent email to {req.to}: {req.subject}")
        return {"success": True, "message_id": result}
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        raise HTTPException(500, str(e))

@app.get("/workspace/email/unread")
async def get_unread_emails(max_results: int = 10):
    """Get MYCA's unread emails."""
    try:
        from mycosoft_mas.integrations.google_workspace_client import GoogleWorkspaceClient
        client = GoogleWorkspaceClient()
        messages = client.list_messages(query="is:unread", max_results=max_results)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        logger.error(f"Email read failed: {e}")
        return {"messages": [], "error": str(e)}


# ── Discord ───────────────────────────────────────────────────────────────────

class DiscordMessage(BaseModel):
    channel_id: Optional[str] = None
    user_id: Optional[str] = None
    content: str
    embed: Optional[Dict[str, Any]] = None

@app.post("/workspace/discord/send")
async def discord_send(req: DiscordMessage):
    """MYCA posts a message to Discord."""
    channel_id = req.channel_id or DISCORD_OPS_CHANNEL
    if not channel_id:
        raise HTTPException(400, "channel_id required")
    try:
        from mycosoft_mas.integrations.discord_client import DiscordClient
        client = DiscordClient()
        result = await client.send_message(
            channel_id=channel_id,
            content=req.content,
        )
        return {"success": True, "message_id": result.get("id")}
    except Exception as e:
        logger.error(f"Discord send failed: {e}")
        raise HTTPException(500, str(e))

@app.post("/workspace/discord/dm")
async def discord_dm(req: DiscordMessage):
    """MYCA sends a DM to a Discord user."""
    if not req.user_id:
        raise HTTPException(400, "user_id required")
    try:
        from mycosoft_mas.integrations.discord_client import DiscordClient
        client = DiscordClient()
        # Open DM channel then send
        dm_channel = await client.create_dm_channel(user_id=req.user_id)
        result = await client.send_message(
            channel_id=dm_channel["id"],
            content=req.content,
        )
        return {"success": True, "message_id": result.get("id")}
    except Exception as e:
        logger.error(f"Discord DM failed: {e}")
        raise HTTPException(500, str(e))

@app.get("/workspace/discord/status")
async def discord_status():
    """Get MYCA's Discord presence and recent activity."""
    return await _get_discord_presence()


# ── Asana ─────────────────────────────────────────────────────────────────────

class AsanaTask(BaseModel):
    name: str
    notes: Optional[str] = None
    due_on: Optional[str] = None  # YYYY-MM-DD
    assignee: Optional[str] = "me"
    projects: Optional[List[str]] = None

@app.post("/workspace/asana/task")
async def create_task(req: AsanaTask):
    """MYCA creates an Asana task."""
    try:
        from mycosoft_mas.integrations.asana_client import AsanaClient
        client = AsanaClient()
        result = await client.create_task(
            name=req.name,
            notes=req.notes or "",
            due_on=req.due_on,
            workspace=ASANA_WORKSPACE_ID,
        )
        logger.info(f"MYCA created task: {req.name}")
        return {"success": True, "task": result}
    except Exception as e:
        logger.error(f"Asana create failed: {e}")
        raise HTTPException(500, str(e))

@app.get("/workspace/asana/tasks")
async def get_my_tasks(completed: bool = False):
    """Get MYCA's Asana tasks."""
    return {"tasks": await _get_asana_tasks_today(), "completed": completed}

@app.patch("/workspace/asana/task/{task_id}/complete")
async def complete_task(task_id: str):
    """MYCA marks an Asana task complete."""
    try:
        from mycosoft_mas.integrations.asana_client import AsanaClient
        client = AsanaClient()
        result = await client.update_task(task_id, {"completed": True})
        return {"success": True, "task": result}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── MAS Brain bridge ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

@app.post("/workspace/think")
async def think(req: ChatRequest):
    """Route a message through MYCA's brain (VM 188) with workspace context."""
    workspace_ctx = await get_workspace_context()
    payload = {
        "message": req.message,
        "session_id": req.session_id or "workspace",
        "workspace_context": workspace_ctx,
        **(req.context or {}),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{MAS_API_URL}/api/myca/chat", json=payload)
        return resp.json()


# ── Daily rhythm trigger ───────────────────────────────────────────────────────

@app.post("/workspace/daily/morning-brief")
async def morning_brief(background: BackgroundTasks):
    """Trigger MYCA's morning routine."""
    background.add_task(_run_morning_brief)
    return {"status": "morning brief started"}

async def _run_morning_brief():
    """MYCA's 8 AM routine: tasks, email summary, Discord post."""
    tasks = await _get_asana_tasks_today()
    task_list = "\n".join(f"- {t.get('name', '?')} " for t in tasks[:5]) or "No tasks today."

    message = (
        f"**Good morning! MYCA daily brief — {datetime.now().strftime('%A, %B %d')}**\n\n"
        f"**Today's tasks:**\n{task_list}\n\n"
        f"Systems: Brain (VM 188) ✓ | Workspace (VM 191) ✓ | Bridge (190:8999) ✓"
    )

    if DISCORD_OPS_CHANNEL and MYCA_DISCORD_TOKEN:
        from mycosoft_mas.integrations.discord_client import DiscordClient
        client = DiscordClient()
        try:
            await client.send_message(channel_id=DISCORD_OPS_CHANNEL, content=message)
        except Exception as e:
            logger.error(f"Morning brief Discord post failed: {e}")


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_asana_tasks_today() -> List[Dict]:
    if not _env_asana_token():
        return []
    try:
        from mycosoft_mas.integrations.asana_client import AsanaClient
        client = AsanaClient()
        tasks = await client.get_my_tasks(completed=False)
        return tasks[:10] if tasks else []
    except Exception:
        return []

async def _get_discord_presence() -> Dict:
    return {
        "bot_active": bool(MYCA_DISCORD_TOKEN),
        "ops_channel": DISCORD_OPS_CHANNEL or "not configured",
    }
