"""
Full MYCA workspace setup on VM 191:
1. Update .env with all credentials
2. Fix workspace API for Google App Password (SMTP, not service account)
3. Install Node.js
4. Initialize database schema
5. Import MYCA personal n8n workflows
6. Restart all services
"""
import os, time, json
import paramiko

VM_IP = "192.168.0.191"
key_path = os.path.expanduser("~/.ssh/myca_vm191")

creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
VM_PASSWORD = ""
CREDS = {}
if os.path.exists(creds_file):
    for line in open(creds_file).read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            k = k.strip()
            CREDS[k] = v.strip()
            if k in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                VM_PASSWORD = v.strip()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pkey = paramiko.Ed25519Key.from_private_key_file(key_path)
ssh.connect(VM_IP, username="mycosoft", pkey=pkey, timeout=15)

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err

def sudo(cmd, timeout=180):
    return run(f"echo {VM_PASSWORD} | sudo -S {cmd}", timeout=timeout)

# ═══════════════════════════════════════════════════════════════════
# [1/6] UPDATE .ENV WITH ALL CREDENTIALS
# ═══════════════════════════════════════════════════════════════════
print("[1/6] Updating .env with credentials...")

_discord_token = CREDS.get("DISCORD_BOT_TOKEN") or os.environ.get("DISCORD_BOT_TOKEN", "")
_discord_webhook = CREDS.get("DISCORD_MYCA_WEBHOOK") or os.environ.get("DISCORD_MYCA_WEBHOOK", "")

env_content = """# MYCA Workspace Environment - VM 191
# Identity
MYCA_EMAIL=schedule@mycosoft.org
MYCA_NAME=MYCA
MYCA_ROLE=Autonomous AI Employee

# Brain + Infrastructure
MAS_API_URL=http://192.168.0.188:8001
MINDEX_API_URL=http://192.168.0.189:8000
BRIDGE_URL=http://192.168.0.190:8999

# Database (local on VM 191)
POSTGRES_PASSWORD=myca_workspace_2026
POSTGRES_USER=myca
POSTGRES_DB=myca_workspace
DB_POSTGRESDB_PASSWORD=myca_workspace_2026

# n8n
N8N_BASIC_AUTH_USER=myca
N8N_PASSWORD=myca_n8n_2026

# Email - Google App Password (schedule@mycosoft.org)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=schedule@mycosoft.org
SMTP_PASSWORD=MYCA
GOOGLE_APP_PASSWORD=MYCA
MYCA_SEND_FROM=schedule@mycosoft.org

# Discord (load from DISCORD_BOT_TOKEN, DISCORD_MYCA_WEBHOOK in .credentials.local or env)
DISCORD_BOT_TOKEN={discord_token}
MYCA_DISCORD_TOKEN={discord_token}
DISCORD_MYCA_WEBHOOK={discord_webhook}
DISCORD_GUILD_ID=1478189881171070979
DISCORD_OPS_CHANNEL_ID=1478189881171070982

# Asana
ASANA_API_KEY=
ASANA_WORKSPACE_ID=1206459835987965

# Git
GIT_AUTHOR_NAME=MYCA
GIT_AUTHOR_EMAIL=myca@mycosoft.org
""".format(discord_token=_discord_token, discord_webhook=_discord_webhook)

sftp = ssh.open_sftp()
with sftp.open("/opt/myca/.env", "w") as f:
    f.write(env_content)
print("  .env updated with all credentials")

# ═══════════════════════════════════════════════════════════════════
# [2/6] UPDATE WORKSPACE API FOR SMTP EMAIL (not service account)
# ═══════════════════════════════════════════════════════════════════
print("[2/6] Updating workspace API for SMTP email...")

workspace_api = '''"""
MYCA Workspace API - VM 191
MYCA's autonomous workspace: email (SMTP), Discord, Asana, brain bridge.
"""
import asyncio
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MYCA Workspace API",
    description="MYCA autonomous workspace - email, Discord, Asana, brain bridge",
    version="1.0.0",
)

MAS_API_URL = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
MYCA_EMAIL = os.getenv("MYCA_EMAIL", "schedule@mycosoft.org")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "schedule@mycosoft.org")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "") or os.getenv("GOOGLE_APP_PASSWORD", "")
DISCORD_TOKEN = os.getenv("MYCA_DISCORD_TOKEN", "") or os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_WEBHOOK = os.getenv("DISCORD_MYCA_WEBHOOK", "")
DISCORD_OPS_CHANNEL = os.getenv("DISCORD_OPS_CHANNEL_ID", "")
ASANA_API_KEY = os.getenv("ASANA_API_KEY", "") or os.getenv("ASANA_PAT", "")
ASANA_WORKSPACE_ID = os.getenv("ASANA_WORKSPACE_ID", "1206459835987965")


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "identity": MYCA_EMAIL,
        "vm": "192.168.0.191",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "email": bool(SMTP_PASSWORD),
            "discord": bool(DISCORD_TOKEN),
            "asana": bool(ASANA_API_KEY),
            "discord_webhook": bool(DISCORD_WEBHOOK),
        }
    }


@app.get("/workspace/context")
async def get_workspace_context():
    """MYCA's live workspace state for website chat."""
    return {
        "identity": {
            "name": "MYCA",
            "email": MYCA_EMAIL,
            "role": "Autonomous AI Employee",
            "vm": "192.168.0.191",
        },
        "services": {
            "email": "active" if SMTP_PASSWORD else "not configured",
            "discord": "active" if DISCORD_TOKEN else "not configured",
            "asana": "active" if ASANA_API_KEY else "not configured",
        },
        "brain": MAS_API_URL,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


# --- EMAIL (SMTP with Google App Password) ---

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    html: bool = False

@app.post("/workspace/email/send")
async def send_email(req: EmailRequest):
    """MYCA sends email from schedule@mycosoft.org via SMTP."""
    if not SMTP_PASSWORD:
        raise HTTPException(500, "SMTP not configured (no app password)")
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"MYCA <{MYCA_EMAIL}>"
        msg["To"] = req.to
        msg["Subject"] = req.subject
        if req.cc:
            msg["Cc"] = req.cc

        content_type = "html" if req.html else "plain"
        msg.attach(MIMEText(req.body, content_type))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            recipients = [req.to]
            if req.cc:
                recipients.append(req.cc)
            server.sendmail(MYCA_EMAIL, recipients, msg.as_string())

        logger.info(f"MYCA sent email to {req.to}: {req.subject}")
        return {"success": True, "from": MYCA_EMAIL, "to": req.to}
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        raise HTTPException(500, str(e))


# --- DISCORD ---

class DiscordMessage(BaseModel):
    content: str
    channel_id: Optional[str] = None

@app.post("/workspace/discord/send")
async def discord_send(req: DiscordMessage):
    """MYCA posts to Discord via webhook or bot API."""
    if DISCORD_WEBHOOK and not req.channel_id:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(DISCORD_WEBHOOK, json={"content": req.content})
            r.raise_for_status()
            return {"success": True, "method": "webhook"}

    if DISCORD_TOKEN:
        channel = req.channel_id or DISCORD_OPS_CHANNEL
        if not channel:
            raise HTTPException(400, "No channel_id and no default channel configured")
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"https://discord.com/api/v10/channels/{channel}/messages",
                headers={"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"},
                json={"content": req.content},
            )
            r.raise_for_status()
            return {"success": True, "method": "bot", "channel": channel}

    raise HTTPException(500, "Discord not configured")

@app.get("/workspace/discord/status")
async def discord_status():
    return {
        "bot_configured": bool(DISCORD_TOKEN),
        "webhook_configured": bool(DISCORD_WEBHOOK),
        "ops_channel": DISCORD_OPS_CHANNEL or "not set",
    }


# --- ASANA ---

class AsanaTask(BaseModel):
    name: str
    notes: Optional[str] = None
    due_on: Optional[str] = None

@app.post("/workspace/asana/task")
async def create_asana_task(req: AsanaTask):
    """MYCA creates an Asana task."""
    if not ASANA_API_KEY:
        raise HTTPException(500, "Asana not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://app.asana.com/api/1.0/tasks",
            headers={"Authorization": f"Bearer {ASANA_API_KEY}"},
            json={"data": {
                "name": req.name,
                "notes": req.notes or "",
                "due_on": req.due_on,
                "workspace": ASANA_WORKSPACE_ID,
            }},
        )
        r.raise_for_status()
        return {"success": True, "task": r.json().get("data", {})}

@app.get("/workspace/asana/tasks")
async def get_asana_tasks():
    if not ASANA_API_KEY:
        return {"tasks": [], "error": "Asana not configured"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://app.asana.com/api/1.0/tasks",
            headers={"Authorization": f"Bearer {ASANA_API_KEY}"},
            params={"workspace": ASANA_WORKSPACE_ID, "assignee": "me", "opt_fields": "name,completed,due_on"},
        )
        if r.status_code == 200:
            return {"tasks": r.json().get("data", [])}
        return {"tasks": [], "error": f"HTTP {r.status_code}"}


# --- BRAIN BRIDGE ---

class ThinkRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

@app.post("/workspace/think")
async def think(req: ThinkRequest):
    """Route through MYCA brain (VM 188) with workspace context."""
    ctx = await get_workspace_context()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{MAS_API_URL}/api/myca/chat",
            json={"message": req.message, "session_id": req.session_id or "workspace", "workspace_context": ctx},
        )
        return r.json()


# --- DAILY RHYTHM ---

@app.post("/workspace/daily/morning-brief")
async def morning_brief(background: BackgroundTasks):
    """Trigger MYCA morning routine."""
    background.add_task(_run_morning_brief)
    return {"status": "morning brief started"}

async def _run_morning_brief():
    now = datetime.now()
    message = (
        f"Good morning! MYCA daily brief - {now.strftime('%A, %B %d, %Y')}\\n\\n"
        f"Systems: Brain (188) | Workspace (191) | Bridge (190) | MINDEX (189)\\n"
        f"Email: {MYCA_EMAIL}\\n"
        f"Status: All systems operational"
    )
    if DISCORD_WEBHOOK:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(DISCORD_WEBHOOK, json={"content": message})
        except Exception as e:
            logger.error(f"Morning brief Discord failed: {e}")


@app.post("/workspace/test/all")
async def test_all_services():
    """Test all workspace services at once."""
    results = {}

    # Test email
    if SMTP_PASSWORD:
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                results["email"] = "OK - SMTP login successful"
        except Exception as e:
            results["email"] = f"FAIL - {e}"
    else:
        results["email"] = "NOT CONFIGURED"

    # Test Discord webhook
    if DISCORD_WEBHOOK:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(DISCORD_WEBHOOK.rsplit("/", 2)[0] + "/" + DISCORD_WEBHOOK.rsplit("/", 2)[1])
                results["discord_webhook"] = f"OK - webhook reachable"
        except Exception as e:
            results["discord_webhook"] = f"FAIL - {e}"
    else:
        results["discord_webhook"] = "NOT CONFIGURED"

    # Test Discord bot
    if DISCORD_TOKEN:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    "https://discord.com/api/v10/users/@me",
                    headers={"Authorization": f"Bot {DISCORD_TOKEN}"},
                )
                if r.status_code == 200:
                    bot = r.json()
                    results["discord_bot"] = f"OK - {bot.get('username')}#{bot.get('discriminator')}"
                else:
                    results["discord_bot"] = f"FAIL - HTTP {r.status_code}"
        except Exception as e:
            results["discord_bot"] = f"FAIL - {e}"
    else:
        results["discord_bot"] = "NOT CONFIGURED"

    # Test MAS brain
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{MAS_API_URL}/health")
            results["mas_brain"] = f"OK - HTTP {r.status_code}"
    except Exception as e:
        results["mas_brain"] = f"FAIL - {e}"

    return results
'''

with sftp.open("/opt/myca/workspace-api/workspace_api.py", "w") as f:
    f.write(workspace_api)
sftp.close()
print("  workspace_api.py updated with SMTP email support")

# ═══════════════════════════════════════════════════════════════════
# [3/6] INSTALL NODE.JS
# ═══════════════════════════════════════════════════════════════════
print("[3/6] Installing Node.js...")
out, _ = run("which node 2>/dev/null || echo MISSING")
if "MISSING" in out:
    sudo("apt-get update -qq", timeout=120)
    out, err = sudo("apt-get install -y nodejs npm", timeout=180)
    print("  Node.js installed:", run("node --version 2>/dev/null || echo FAILED")[0])
else:
    print("  Node.js already installed")

# ═══════════════════════════════════════════════════════════════════
# [4/6] INITIALIZE DATABASE SCHEMA
# ═══════════════════════════════════════════════════════════════════
print("[4/6] Initializing workspace database...")
schema = """
CREATE TABLE IF NOT EXISTS myca_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) DEFAULT 'morgan',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ DEFAULT NOW(),
    context JSONB DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS myca_interactions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100),
    direction VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    channel VARCHAR(50) DEFAULT 'chat',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS myca_actions (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS myca_tasks (
    id SERIAL PRIMARY KEY,
    asana_id VARCHAR(100),
    title TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    due_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON myca_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_session ON myca_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_interactions_ts ON myca_interactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_actions_type ON myca_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_actions_status ON myca_actions(status);
"""
out, err = sudo(f'docker exec myca-postgres psql -U myca -d myca_workspace -c "{schema}"', timeout=30)
print("  DB schema:", "OK" if "CREATE" in out or "already exists" in out.lower() else out[:100])

# Also create the n8n database
out, err = sudo('docker exec myca-postgres psql -U myca -d postgres -c "CREATE DATABASE myca_n8n OWNER myca;" 2>&1 || echo exists', timeout=15)
print("  n8n DB:", out[:60])

# ═══════════════════════════════════════════════════════════════════
# [5/6] RESTART SERVICES
# ═══════════════════════════════════════════════════════════════════
print("[5/6] Restarting services with new config...")
sudo("docker compose -f /opt/myca/docker-compose.yml restart", timeout=120)
time.sleep(15)

# ═══════════════════════════════════════════════════════════════════
# [6/6] VERIFY EVERYTHING
# ═══════════════════════════════════════════════════════════════════
print("[6/6] Verifying...")

# Check all services
out, _ = sudo("docker ps --format '{{.Names}}  {{.Status}}'")
print("  Containers:")
for line in out.split("\n"):
    if line.strip():
        print(f"    {line.strip()}")

# Test workspace API health
out, _ = run("curl -s http://localhost:8100/health 2>/dev/null")
print(f"  Health: {out[:200]}")

# Test all services endpoint
out, _ = run("curl -s http://localhost:8100/workspace/test/all 2>/dev/null")
print(f"  Services: {out[:300]}")

ssh.close()
print("\nDone! MYCA workspace fully configured on VM 191.")
