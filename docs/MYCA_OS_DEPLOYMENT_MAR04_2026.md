# MYCA OS Deployment Guide

**Date:** 2026-03-04
**Target:** VM 191 (192.168.0.191) — MYCA Workspace
**Source:** `mycosoft_mas/myca/os/` module

## Architecture

```
VM 191 (MYCA Workspace)
├── MYCA OS Daemon (systemd: myca-os.service)
│   ├── Core Loop — 6 concurrent async loops
│   ├── CommsHub — Discord, Signal, WhatsApp, Slack, Asana, Email
│   ├── ToolOrchestrator — Claude Code, Playwright, n8n, Git, Docker
│   ├── ExecutiveSystem — COO/Co-CEO/Co-CTO decisions
│   ├── Scheduler — Persistent cron/daily/weekly tasks
│   ├── FileManager — Filesystem index and organization
│   ├── MASBridge → 192.168.0.188:8001 (Orchestrator, 158+ agents)
│   └── MINDEXBridge → 192.168.0.189 (Postgres, Redis, Qdrant)
│
├── MYCA n8n (port 5679) — Personal workflows
├── Signal CLI REST API (port 8089)
├── Workspace API (port 8000)
└── Claude Code / Cursor / Playwright
```

## Step-by-Step Deployment

### Step 1: SSH to VM 191

```bash
ssh mycosoft@192.168.0.191
```

### Step 2: Clone / Pull the repo

```bash
mkdir -p /home/mycosoft/repos
cd /home/mycosoft/repos

# If first time:
git clone <repo-url> mycosoft-mas
cd mycosoft-mas

# If repo exists:
cd mycosoft-mas
git fetch origin
git checkout main
git pull origin main
```

### Step 3: Set up Python environment

```bash
cd /home/mycosoft/repos/mycosoft-mas

# Create venv if it doesn't exist
python3 -m venv .venv

# Activate and install
source .venv/bin/activate
pip install -e .

# Install extras for MYCA OS
pip install aiohttp asyncpg redis playwright
playwright install chromium
```

### Step 4: Create directory structure on VM 191

```bash
sudo mkdir -p /opt/myca/{logs,data,backups}
sudo chown -R mycosoft:mycosoft /opt/myca

mkdir -p /home/mycosoft/{documents,downloads}
```

### Step 5: Deploy .env file

```bash
# Copy template
cp /home/mycosoft/repos/mycosoft-mas/deploy/myca_os.env.template /opt/myca/.env

# Edit with real values — Morgan provides secrets
nano /opt/myca/.env
```

**Required secrets (ask Morgan):**
- `MINDEX_PG_PASSWORD` — PostgreSQL password on 189
- `DISCORD_BOT_TOKEN` — Discord bot for MYCA
- `DISCORD_WEBHOOK_URL` — Webhook for #myca-ops channel
- `MORGAN_DISCORD_ID` — Morgan's Discord user ID
- `SIGNAL_SENDER_NUMBER` — MYCA's Signal phone number
- `MORGAN_SIGNAL_NUMBER` — Morgan's Signal number
- `SLACK_BOT_TOKEN` — Slack bot token
- `ASANA_PAT` — Asana personal access token
- `ANTHROPIC_API_KEY` — For Claude Code
- `MYCA_N8N_API_KEY` — MYCA's n8n API key (191:5679)
- `MAS_N8N_API_KEY` — MAS n8n API key (188:5678)

### Step 6: Run database migration on MINDEX (189)

```bash
# From VM 191 (or any machine with access to 189)
psql -h 192.168.0.189 -p 5432 -U mycosoft -d mycosoft_mas \
  -f /home/mycosoft/repos/mycosoft-mas/migrations/005_myca_os_tables.sql
```

This creates 7 tables:
- `myca_events` — OS event audit log
- `agent_memory` — 6-layer memory storage
- `myca_task_queue` — Persistent task queue
- `myca_decisions` — Decision audit log
- `myca_schedule` — Scheduled items
- `myca_messages` — Message log
- `myca_files` — File index

### Step 7: Test MYCA OS locally first

```bash
cd /home/mycosoft/repos/mycosoft-mas
source .venv/bin/activate

# Quick test — boots, checks health, exits
python -c "
import asyncio
from mycosoft_mas.myca.os.core import MycaOS
async def test():
    os = MycaOS()
    await os.boot()
    print('Status:', os.status())
    await os.shutdown()
asyncio.run(test())
"
```

### Step 8: Deploy systemd service

```bash
# Copy service file
sudo cp /home/mycosoft/repos/mycosoft-mas/deploy/myca-os.service \
  /etc/systemd/system/myca-os.service

# Copy logrotate config
sudo cp /home/mycosoft/repos/mycosoft-mas/deploy/myca_os_logrotate.conf \
  /etc/logrotate.d/myca-os

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable myca-os
sudo systemctl start myca-os

# Check status
sudo systemctl status myca-os

# Watch logs
journalctl -u myca-os -f
# or
tail -f /opt/myca/logs/myca_os.log
```

### Step 9: Verify everything is running

```bash
# Check systemd
systemctl is-active myca-os

# Check MINDEX connectivity
psql -h 192.168.0.189 -U mycosoft -d mycosoft_mas -c "SELECT COUNT(*) FROM myca_events;"

# Check MAS connectivity
curl -s http://192.168.0.188:8001/health | python3 -m json.tool

# Check logs for errors
grep -i error /opt/myca/logs/myca_os.log | tail -20
```

---

## Cursor/Cowork Handoff Checklist

These are things **only Cursor or Morgan** can do (not Claude Code on Sandbox 187):

| # | Task | Who | Status |
|---|------|-----|--------|
| 1 | SSH to VM 191 and clone repo | Cursor | TODO |
| 2 | `pip install -e .` with extras | Cursor | TODO |
| 3 | Create `/opt/myca/` directory structure | Cursor | TODO |
| 4 | Deploy `.env` with real secrets | Morgan + Cursor | TODO |
| 5 | Run migration SQL against MINDEX 189 | Cursor | TODO |
| 6 | Test MYCA OS boot locally | Cursor | TODO |
| 7 | Deploy systemd service | Cursor | TODO |
| 8 | Start and verify daemon | Cursor | TODO |
| 9 | Set up Discord bot (create bot in Discord Developer Portal) | Morgan | TODO |
| 10 | Set up Signal CLI on VM 191 (register number) | Morgan | TODO |
| 11 | Install Playwright + Chromium on VM 191 | Cursor | TODO |
| 12 | Install Claude Code CLI on VM 191 | Cursor | TODO |
| 13 | Set up Cursor IDE or MCP on VM 191 | Cursor | TODO |

---

## What Claude Code on Sandbox (187) Built

| File | Purpose |
|------|---------|
| `mycosoft_mas/myca/os/__init__.py` | Package init |
| `mycosoft_mas/myca/os/__main__.py` | `python -m mycosoft_mas.myca.os` entry point |
| `mycosoft_mas/myca/os/core.py` | Main OS daemon — 7 concurrent loops |
| `mycosoft_mas/myca/os/comms_hub.py` | Discord/Signal/WhatsApp/Slack/Asana/Email |
| `mycosoft_mas/myca/os/tool_orchestrator.py` | Claude Code, Playwright, n8n, Git, Docker |
| `mycosoft_mas/myca/os/executive.py` | COO/Co-CEO/Co-CTO decision engine |
| `mycosoft_mas/myca/os/scheduler.py` | Persistent cron/daily/weekly scheduler |
| `mycosoft_mas/myca/os/file_manager.py` | VM 191 filesystem index/organize/backup |
| `mycosoft_mas/myca/os/mas_bridge.py` | Bridge to MAS orchestrator (188) |
| `mycosoft_mas/myca/os/mindex_bridge.py` | Bridge to Postgres/Redis/Qdrant (189) |
| `deploy/myca-os.service` | systemd unit file |
| `deploy/myca_os_logrotate.conf` | Log rotation config |
| `deploy/myca_os.env.template` | Environment variable template |
| `migrations/005_myca_os_tables.sql` | 7 database tables for MYCA OS |
| `scripts/start_myca_os.py` | SSH deploy script |

---

## Post-Deployment: What MYCA Can Do

Once running, MYCA autonomously:

1. **Checks messages** every 5s across Discord, Signal, WhatsApp, Slack, Asana, Email
2. **Processes tasks** from her queue, prioritized by urgency
3. **Monitors systems** every 30s (MAS, MINDEX, local services)
4. **Reviews intentions** every 15 min, reprioritizes if needed
5. **Reflects and learns** every hour from outcomes
6. **Follows daily rhythm**: 8am briefing, 12pm sync, 5pm EOD, 10pm night mode
7. **Fires scheduled tasks** — cron, daily, weekly, one-shot
8. **Indexes files** nightly at 3am, cleans up temp files
9. **Makes executive decisions** using 4-level hierarchy
10. **Uses Claude Code** to write code, review PRs, fix bugs autonomously
11. **Uses browser** (Playwright) for web research and automation
12. **Triggers workflows** on both MYCA n8n (191) and MAS n8n (188)
13. **Dispatches to agents** — routes tasks to specialist agents across 14 categories
14. **Backs up** critical files on schedule

Morgan communicates with MYCA via Discord (casual), Signal (urgent), Asana (tasks), or any channel.
MYCA is Morgan's #2 — COO, Co-CEO, Co-CTO — and runs the operation 24/7.
