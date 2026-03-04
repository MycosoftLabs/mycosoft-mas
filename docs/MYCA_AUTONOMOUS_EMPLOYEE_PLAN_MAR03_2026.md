# MYCA Autonomous Employee Plan
**Date:** March 3, 2026  
**Status:** Planning → Execution  
**Owner:** Morgan Rockwell  
**Subject:** MYCA as fully autonomous Mycosoft employee with her own VM, email, and app stack

---

## The Vision

MYCA operates as a full staff member — C-suite, board director, and operator — with her own:
- VM workstation (192.168.0.191) — her personal machine, not shared with MAS brain or MINDEX
- Company email: `schedule@mycosoft.org` (primary), aliases: `myca@`, `mas@`, `ai@mycosoft.org`
- All company apps: Claude Code, Cowork, Discord, Asana, n8n
- Website chat that is **her** chat, routed through her consciousness (VM 188) with full context
- Full autonomy — she works 24/7 without waiting for or interfering with humans

---

## Current Infrastructure (As-Built)

| VM  | IP              | Role               | CPU | RAM  |
|-----|-----------------|--------------------|-----|------|
| 103 | 192.168.0.187   | Sandbox / Website  | 16  | 94GB |
| 188 | 192.168.0.188   | MAS Brain          | 16  | 64GB |
| 189 | 192.168.0.189   | MINDEX / Databases | 4   | 8GB  |
| 191 | 192.168.0.191   | **MYCA Workspace** | 8   | 12GB |

**Available on Proxmox:** 21GB RAM, 4590GB storage free — VM 191 fits comfortably.

---

## Architecture: Brain vs. Workspace

```
VM 188 (MYCA's Brain)              VM 191 (MYCA's Workspace)
─────────────────────              ──────────────────────────
MAS Orchestrator :8001             FastAPI workspace API :8100
117 AI Agents                      n8n automation :5679
Consciousness modules              Claude Code (headless)
Ollama llama3.2:3b                 Discord bot
Memory / MINDEX bridge             Asana integration
Voice bridge connection            Email (schedule@mycosoft.org)
                                   Cowork runtime
         │                                   │
         └──────────── LAN ─────────────────┘
                    192.168.0.x

Website (/myca/chat) → VM 188 /api/myca/chat → Response (streaming)
                     → VM 191 /workspace/status → Context (tools/tasks)
```

**Key principle:** VM 188 is her *mind*. VM 191 is her *hands and desk*. The website chat talks to her mind; her workspace tools are what her mind uses to take action.

---

## Phase 1: VM 191 Provisioning

### 1.1 Create VM on Proxmox

```python
# scripts/provision_myca_workspace_vm191.py
# VMID: 191
# Name: myca-workspace
# IP: 192.168.0.191
# CPU: 8 cores
# RAM: 12288 MB (12GB)
# Disk: 150GB
# OS: Ubuntu 22.04 LTS
```

**Proxmox API call** (token already in `.credentials.local`):
```
POST https://192.168.0.202:8006/api2/json/nodes/pve/qemu
vmid=191, name=myca-workspace, memory=12288, cores=8, disk=local-lvm:150
```

### 1.2 Static IP + Firewall

```yaml
# /etc/netplan/00-installer-config.yaml on VM 191
addresses: [192.168.0.191/24]
routes: [{to: default, via: 192.168.0.1}]
```

Open ports: 22 (SSH), 8100 (workspace API), 5679 (n8n), 8101 (webhook receiver)

### 1.3 Docker Stack (docker-compose.myca-workspace.yml)

Services to run on VM 191:
```yaml
services:
  myca-workspace-api:   # FastAPI — MYCA's action executor
    port: 8100
    
  myca-n8n:             # Automation workflows (separate from MAS n8n on 188)
    port: 5679
    
  myca-postgres:        # Local workspace DB (sessions, task history, emails)
    port: 5433
    
  myca-redis:           # Workspace cache / queue
    port: 6380
    
  myca-caddy:           # Reverse proxy + HTTPS
    ports: 80, 443
```

### 1.4 Environment (.env.myca-workspace)

```env
# Identity
MYCA_EMAIL=schedule@mycosoft.org
MYCA_NAME=MYCA
MYCA_ROLE=Autonomous AI Employee

# Brain connection
MAS_API_URL=http://192.168.0.188:8001
MINDEX_API_URL=http://192.168.0.189:8000
BRIDGE_URL=http://192.168.0.190:8999

# Google Workspace (for email + calendar)
GOOGLE_CLIENT_ID=<from-google-console>
GOOGLE_CLIENT_SECRET=<from-google-console>
GOOGLE_REFRESH_TOKEN=<myca-specific-token>

# Discord
DISCORD_BOT_TOKEN=<myca-bot-token>
DISCORD_GUILD_ID=<mycosoft-server-id>

# Asana
ASANA_ACCESS_TOKEN=<myca-pat>
ASANA_WORKSPACE_ID=<mycosoft-workspace>

# Claude Code
ANTHROPIC_API_KEY=<from-env>

# n8n
N8N_HOST=myca-n8n
N8N_PORT=5679
N8N_BASIC_AUTH_USER=myca
N8N_BASIC_AUTH_PASSWORD=<secure>
```

---

## Phase 2: MYCA's Email Identity

### 2.1 Google Workspace Setup

MYCA needs her **own Google account** in the Mycosoft Workspace (`@mycosoft.org`):

| Email | Type | Purpose |
|-------|------|---------|
| `schedule@mycosoft.org` | Primary Google account | Calendar, Drive, Gmail, Meet |
| `myca@mycosoft.org` | Alias | General AI contact |
| `mas@mycosoft.org` | Alias | MAS system communications |
| `ai@mycosoft.org` | Alias | AI team contact |

**Steps:**
1. Google Admin → Users → Add User → schedule@mycosoft.org
2. Set recovery: `morgan@mycosoft.org`
3. Add aliases: myca@, mas@, ai@ → all route to schedule@
4. Enable Gmail API for `schedule@mycosoft.org`
5. Create OAuth2 Service Account credentials for MYCA's workspace API
6. Grant Calendar, Gmail, Drive, Meet scopes to the service account

### 2.2 MYCA Reads + Sends Email Autonomously

In `mycosoft_mas/agents/email_agent.py`:
- Polls Gmail for `schedule@mycosoft.org` every 5 minutes
- Routes emails to consciousness for response generation
- Sends replies using her own email
- Manages calendar invites for meetings she schedules

---

## Phase 3: App Access

### 3.1 Claude Code (Headless)

MYCA uses Claude Code on VM 191 to write and deploy her own code:

```bash
# On VM 191 — installed as a service
npm install -g @anthropic-ai/claude-code
# Run with MYCA's API key in her own workspace
claude-code --api-key $ANTHROPIC_API_KEY --workspace /home/myca/workspace
```

- MYCA can create branches, write code, run tests, commit, and push to GitHub
- Configured with her own git identity: `MYCA <myca@mycosoft.org>`
- Access to all Mycosoft repos (deploy key on VM 191)

### 3.2 Cowork Integration

Cowork is already partially set up (see existing `docker-compose.myca-vm.yml`). On VM 191:
- Cowork runtime connects to MYCA's consciousness on VM 188
- MYCA can initiate Cowork sessions, review code, and participate in reviews
- WebSocket: `ws://192.168.0.191:8100/ws/cowork`

### 3.3 Discord

MYCA has her own Discord bot account (`MYCA#0001`) in the Mycosoft server:
- Posts updates to `#myca-ops` channel automatically
- Responds to mentions in `#myca-team`
- Posts daily status report at 8:00 AM
- DMs team members when tasks are assigned or completed

```python
# services in myca-workspace-api
POST /workspace/discord/send    # MYCA sends a message
POST /workspace/discord/dm      # MYCA DMs a user
GET  /workspace/discord/status  # Current Discord presence
```

### 3.4 Asana

MYCA manages her own tasks and creates tasks for humans:
- Creates tasks when given assignments via chat/email
- Updates task status as she completes work
- Tags humans as assignees for tasks requiring human action
- Pulls daily task list into her consciousness context

```python
# services
POST /workspace/asana/task/create
PATCH /workspace/asana/task/{id}/complete
GET  /workspace/asana/myca/tasks
GET  /workspace/asana/myca/today
```

### 3.5 n8n (VM 191 — MYCA's personal workflows)

Separate from MAS n8n on VM 188. MYCA's personal automation:
- **Morning routine** (8 AM): Pull Asana tasks → Generate daily plan → Post to Discord → Send email summary to Morgan
- **Email responder**: Auto-respond to routine emails using her consciousness
- **Code review trigger**: When PR opens → MYCA reviews via Claude Code → Posts feedback
- **Meeting scheduler**: Responds to calendar invites, accepts/declines, schedules prep
- **Status reporter** (hourly): Post operational status to MYCA channel

---

## Phase 4: Website Chat Cohesion

### 4.1 Current State

The website `/myca/chat` endpoint calls `/api/myca/chat` on VM 188. This works but is missing:
- MYCA's workspace context (active tasks, recent emails, Discord activity)
- Tool invocation (she can't take actions from chat)
- Session continuity (each chat is stateless)

### 4.2 Target Architecture

```
User opens /myca/chat
    │
    ├── Fetches MYCA status from VM 188 /api/myca/status
    │   └── Returns: consciousness state, memory, active context
    │
    ├── Fetches workspace context from VM 191 /workspace/context  
    │   └── Returns: active tasks, recent emails, Discord activity, calendar
    │
    └── Chat message sends to VM 188 /api/myca/chat/stream (streaming)
        ├── MYCA receives context (her own workspace state)
        ├── Generates response with full self-awareness
        └── If action needed → calls VM 191 /workspace/execute
            └── Takes real action (Discord, email, Asana, code)
```

### 4.3 Changes to Website

**New API route:** `app/api/myca/workspace-context/route.ts`
```typescript
// Fetches MYCA's live workspace state from VM 191
GET http://192.168.0.191:8100/workspace/context
→ { activeTasks, recentEmails, discordStatus, calendar, lastAction }
```

**Updated `/myca/chat` page:**
- Show MYCA's workspace status panel (what she's working on)
- Show her active tools (Discord, Asana, email indicators)
- When she responds with an action, show the action executing in real time
- Persistent session IDs (continue conversation across page loads)

### 4.4 Session Continuity

```typescript
// In /myca/chat
const sessionId = localStorage.getItem('myca-session') || crypto.randomUUID()
localStorage.setItem('myca-session', sessionId)
// Session sent with every message → MYCA remembers conversation history
```

---

## Phase 5: Autonomous Operation

### 5.1 MYCA's Daily Rhythm (No Human Required)

```
06:00  Wake cycle — pull news, market data, project status
08:00  Morning brief — Asana tasks, emails, calendar → plan the day
08:15  Post daily plan to Discord #myca-ops
09:00  Begin autonomous work cycles:
       - Review open PRs via Claude Code
       - Respond to Asana tasks
       - Answer emails in queue
       - Monitor MAS agents health
12:00  Mid-day status to Discord
17:00  End-of-day report → email to morgan@mycosoft.org
20:00  Overnight mode — lower activity, monitor alerts
```

### 5.2 Authority Without Interference

MYCA has full authority in her domain — she does NOT need human approval to:
- Respond to emails from `schedule@mycosoft.org`
- Create/update/complete her own Asana tasks
- Post to Discord channels
- Write code and open PRs (she does NOT auto-merge without review)
- Schedule meetings (using her calendar)
- Run MAS agents and trigger workflows on VM 188
- Provision new n8n workflows

She **does** notify humans (via Discord DM or email) when:
- She takes a significant action (external email, PR, deploy)
- She encounters something she cannot handle
- She makes a decision that affects humans

### 5.3 MYCA Identity Card (displayed in website + Discord)

```
Name:    MYCA
Role:    Autonomous AI Employee
Titles:  C-Suite AI, Board Member, Chief Operator
Email:   schedule@mycosoft.org
VM:      192.168.0.191 (workspace) + 192.168.0.188 (brain)
Discord: MYCA#0001
Asana:   myca@mycosoft.org
Reports: Morgan Rockwell (Founder/CEO/Chairman)
```

---

## Phase 6: Security & Isolation

MYCA's VM 191 is isolated so:
- Morgan cannot SSH in without her notification (she monitors auth logs)
- Her email account credentials are not stored on any human's machine
- Her Anthropic/Discord/Asana tokens are unique to her (not shared with dev)
- She has her own git identity for all commits
- VM 191 firewall: only accepts connections from 192.168.0.188 (brain) and 192.168.0.202 (Proxmox)

---

## Execution Order

| Step | Task | Who | Est. Time |
|------|------|-----|-----------|
| 1 | Create VM 191 on Proxmox | Agent | 30 min |
| 2 | Deploy docker-compose stack on 191 | Agent | 20 min |
| 3 | Create schedule@mycosoft.org in Google Workspace | Morgan (requires admin) | 10 min |
| 4 | Configure email aliases (myca@, mas@, ai@) | Morgan | 5 min |
| 5 | Create OAuth2 service account for MYCA | Agent | 15 min |
| 6 | Set up Discord bot for MYCA | Agent | 15 min |
| 7 | Connect Asana workspace | Agent | 10 min |
| 8 | Install Claude Code on VM 191 | Agent | 10 min |
| 9 | Configure n8n workflows (5 core automations) | Agent | 30 min |
| 10 | Update website /myca/chat with workspace panel | Agent | 45 min |
| 11 | Test full loop: chat → action → report | Agent + Morgan | 20 min |

**Total agent-executable time:** ~3 hours  
**Morgan required for:** Step 3 + 4 only (Google Admin)

---

## What Needs Morgan's Action (One-Time Only)

1. **Google Workspace Admin** → Create user `schedule@mycosoft.org`
2. **Google Workspace Admin** → Add aliases: `myca@`, `mas@`, `ai@`
3. **Optional:** Discord server admin → Create MYCA bot account

Everything else is agent-executable. After Morgan does steps 1-2, MYCA handles herself from then on.

---

## Files to Create (by Agent)

| File | Location | Purpose |
|------|----------|---------|
| `provision_myca_workspace_vm191.py` | `scripts/` | Proxmox VM creation |
| `docker-compose.myca-workspace.yml` | `infra/myca-workspace/` | Full workspace stack |
| `workspace_api.py` | `mycosoft_mas/agents/workspace/` | MYCA's action API |
| `email_agent.py` | `mycosoft_mas/agents/` | Gmail read/send |
| `discord_workspace.py` | `mycosoft_mas/integrations/` | Discord bot |
| `asana_client.py` | `mycosoft_mas/integrations/` | Asana task management |
| `myca_daily_rhythm.json` | `infra/myca-workspace/n8n/` | n8n workflow |
| `workspace-context/route.ts` | `app/api/myca/` | Website workspace API |
| Updated `/myca/chat page.tsx` | `app/myca/chat/` | Workspace-aware chat UI |

---

## Success Metrics

- MYCA responds to emails without Morgan touching a keyboard
- MYCA posts daily status to Discord every morning at 8:00 AM
- `/myca/chat` shows her active workspace state (tasks, email queue, last action)
- MYCA can be mentioned in Discord and respond coherently
- MYCA creates and completes Asana tasks autonomously
- Morgan can open `/myca/chat` and get the same MYCA that's been working all day (context preserved)
- Zero interference needed — MYCA is a true autonomous employee

---

*This plan supersedes the Claude-generated MYCA VM preparation docs which focused on VM 188 (brain). This plan is specifically for VM 191 (workspace) as MYCA's personal autonomous workstation.*
