# MYCA Platform Status and Gaps -- Consolidated Report

**Date:** March 5, 2026  
**Status:** Living document  
**Purpose:** Single source of truth for what's done, what's not, and what's needed

---

## Executive Summary

The MYCA platform is **partially operational**. Core infrastructure (MAS, MINDEX, Website, n8n) is working. **MYCA OS is deployed and running on VM 191** (verified 2026-03-05 via `scripts/deploy_myca_191_full.py`). Health at `http://192.168.0.191:8100/health` — email, Discord, discord_webhook services enabled; Asana pending PAT. Two major plans are complete (MYCA Full Autonomous Bot, Ethics Training System). Several integrations and channel connections require user-provided credentials.

---

## 1. What's Done

### 1.1 Infrastructure and Services

| Component | Status | Notes |
|-----------|--------|-------|
| MAS Orchestrator (VM 188:8001) | WORKING | Postgres to MINDEX fixed; Redis healthy |
| MINDEX (VM 189) | WORKING | API 8000, Postgres, Redis, Qdrant all up |
| Website (VM 187:3000) | WORKING | Sandbox live |
| n8n (MAS VM 188:5678) | WORKING | Workflow automation |
| **MYCA OS (VM 191:8100)** | **WORKING** | Deployed 2026-03-05; email, Discord, discord_webhook up |
| MYCA OS code (13 modules) | COMPLETE | All modules written in `mycosoft_mas/myca/os/` |
| Integration clients | COMPLETE | 75+ clients; Full Platform Integration done |
| Agent modules | COMPLETE | 173 agents across 24 categories |

### 1.2 Plans Completed

| Plan | Status | Reference |
|------|--------|-----------|
| MYCA Full Autonomous Bot | All 7 phases complete | `.cursor/plans/myca_full_autonomous_bot_1791d64e.plan.md` |
| Ethics Training System | All tasks complete | `.cursor/plans/ethics_training_system_383ddd76.plan.md` |
| Full Platform Integration | Complete | `docs/FULL_PLATFORM_INTEGRATION_MAR04_2026.md` |

### 1.3 MYCA Full Autonomous Bot (7 Phases)

- **Phase 1:** executive.py wired to Claude API; SOUL.md + MEMORY.md context
- **Phase 2:** discord_gateway.py with discord.py bot
- **Phase 3:** slack_gateway.py with slack_bolt Socket Mode
- **Phase 4:** IMAP polling for schedule@mycosoft.org Gmail
- **Phase 5:** Asana task comment polling and response
- **Phase 6:** Playwright real browser automation (login, forms, screenshots)
- **Phase 7:** n8n workflow execution via webhooks

### 1.4 Ethics Training System

- Sandbox session manager, training engine, grading engine
- 11 API endpoints under `/api/ethics/training/*`
- Website at `/ethics-training/*` (dashboard, sandbox, analytics)
- Michelle user, access control
- 6 starter YAML scenarios
- Observer MYCA integration

### 1.5 Fixes Applied (Recent)

1. **MAS Postgres:** Wrong MINDEX_DB_PASSWORD; fixed via `.env` + `--env-file` on container
2. **Ollama:** Not bound to 0.0.0.0; fixed on MAS 188
3. **mycosoft-ssh MCP:** Fixed; usable from Claude Code, Cursor, Cowork

---

## 2. What's Not Done / Blockers

### 2.1 VM 191 (MYCA) — MYCA OS Deployed and Running

| Item | Status |
|------|--------|
| SSH password auth | **FIXED** (verified 2026-03-05; hostname `myca-workspace`) |
| **MYCA OS daemon (191:8100)** | **RUNNING** (deployed 2026-03-05 via `scripts/deploy_myca_191_full.py`) |
| MYCA FastAPI (191:8000) | DOWN — optional; not part of current deploy |
| MYCA n8n (191:5679) | DOWN — optional; not part of current deploy |

**Deploy script:** `python scripts/deploy_myca_191_full.py` — clones repo, sets up venv (Python 3.11), deploys .env, systemd service, starts MYCA OS. Logs: `/opt/myca/logs/myca_os.log`. Attach: `ssh mycosoft@192.168.0.191 -t 'tmux attach -t myca-os'`.

### 2.2 MYCA Channel Connections

| Channel | Status | Blocker |
|---------|--------|---------|
| MYCA ↔ Claude Code / Cursor / GPT | CAN CONNECT | MYCA OS running on 191 |
| MYCA ↔ Discord | **UP** (per health) | Deployed |
| MYCA ↔ Discord webhook | **UP** | Deployed |
| MYCA ↔ Email (IMAP) | **UP** | Gmail app password set |
| MYCA ↔ Slack | Code done; needs xapp- token | User must provide |
| MYCA ↔ Signal | Code done | Configure signal-cli on 191 |
| MYCA ↔ Asana | Code done; needs PAT | User must provide if missing |

### 2.3 Other Gaps

| Item | Status |
|------|--------|
| CREP collectors on MAS | Degraded; not running (non-critical) |
| Proxmox API (105:8006) | Unreachable (firewall or down) |

---

## 3. User Inputs Needed

| Item | Purpose | Where to get |
|------|---------|--------------|
| Slack App Token (xapp-...) | Socket Mode for slack_gateway.py | api.slack.com > App > Socket Mode > Enable > generate |
| Discord Message Content Intent | Bot must read message text | discord.com/developers > Bot > enable "Message Content Intent" |
| Asana PAT | Task/comment API access | Asana > My Profile > Apps > Personal Access Token |
| Signal numbers | signal-cli-rest-api | Configure in signal-cli on VM 191 |
| WhatsApp API | WhatsApp Business API | Meta Developer (if using WhatsApp) |

---

## 4. VM Layout

| VM | IP | Role | Key Ports |
|----|-----|------|-----------|
| Sandbox | 192.168.0.187 | Website Docker | 3000 |
| MAS | 192.168.0.188 | Orchestrator, n8n, Ollama | 8001, 5678, 11434 |
| MINDEX | 192.168.0.189 | Postgres, Redis, Qdrant, MINDEX API | 5432, 6379, 6333, 8000 |
| GPU | 192.168.0.190 | GPU workloads | TBD |
| MYCA | 192.168.0.191 | MYCA OS, FastAPI, n8n personal | 8000, 5679, 6080 (noVNC) |

---

## 5. Next Steps (Prioritized)

1. ~~**Deploy MYCA OS**~~ — **DONE** (2026-03-05; script: `scripts/deploy_myca_191_full.py`)
2. **Configure env vars** on VM 191 — SLACK_APP_TOKEN, Asana PAT if needed
3. **Connect remaining channels** — Slack (xapp- token), Asana (PAT), Signal
4. **Run MINDEX migration** (optional) — set `MINDEX_PG_PASSWORD` in env to enable 005_myca_os_tables
5. **Enable CREP collectors** on MAS (optional, non-critical)

---

## 6. Key Documents

| Document | Purpose |
|----------|---------|
| `docs/MYCA_PIPELINE_STATUS_MAR05_2026.md` | Full diagnostic; layer-by-layer status |
| `docs/MYCA_OS_DEPLOYMENT_MAR04_2026.md` | MYCA OS deployment steps |
| `docs/MYCA_SELF_PROVISIONING_PLAYBOOK_MAR04_2026.md` | MYCA self-provisioning on VM 191 |
| `docs/MYCOSOFT_SSH_MCP_MAR03_2026.md` | SSH MCP setup for Claude/Cursor/Cowork |
| `docs/FULL_PLATFORM_INTEGRATION_MAR04_2026.md` | 80+ external integrations |
| `docs/MYCA_ETHICS_TRAINING_SYSTEM_MAR04_2026.md` | Ethics training system |
| `docs/MASTER_DOCUMENT_INDEX.md` | Master doc index |

---

## 7. Health Check Commands

```powershell
# Sandbox website
Invoke-WebRequest -Uri "http://192.168.0.187:3000" -UseBasicParsing -TimeoutSec 5

# MAS health (use /health not /)
Invoke-WebRequest -Uri "http://192.168.0.188:8001/health" -UseBasicParsing -TimeoutSec 10

# MINDEX health
Invoke-WebRequest -Uri "http://192.168.0.189:8000/health" -UseBasicParsing -TimeoutSec 5

# MYCA OS health (VM 191)
Invoke-RestMethod -Uri "http://192.168.0.191:8100/health" -TimeoutSec 10
```

**Note:** MAS and MINDEX may time out from dev machine if not on same LAN. Use SSH tunnel or run from a VM if needed.

---

## 8. Document History

| Date | Change |
|------|--------|
| 2026-03-05 | Initial consolidated status and gaps report |
| 2026-03-05 | MYCA OS deployed on VM 191 via deploy_myca_191_full.py; health verified at :8100 |
