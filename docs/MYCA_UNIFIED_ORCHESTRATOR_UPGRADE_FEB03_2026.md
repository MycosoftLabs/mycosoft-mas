# MYCA Unified Orchestrator Upgrade Plan

**Date:** February 3, 2026  
**Goal:** Ensure there is ONE unified MYCA running on the MAS VM with full identity awareness, workflow access, memory integration, and PersonaPlex voice capabilities.

---

## Current State Analysis

### Problem Summary

1. **MYCA doesn't know her identity** - When asked "What is your name?", she responds like a generic support agent instead of saying "I'm MYCA"
2. **No LLM being called with MYCA's prompt** - The n8n workflows just route, no AI with personality
3. **MAS VM may have stale code** - Not synced with latest local changes
4. **Multiple potential MYCA instances** - Confusion between local dev and VM orchestrator

### Architecture Overview

```
                    ┌─────────────────────────────────────────────────────────┐
                    │           Local Development (RTX 5090)                   │
                    │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
                    │  │ PersonaPlex  │ │  Bridge      │ │  Website Dev     │ │
                    │  │ Moshi 8998   │ │  8999        │ │  3010            │ │
                    │  └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘ │
                    └─────────┼────────────────┼──────────────────┼───────────┘
                              │                │                  │
                              │                │                  │
                    ┌─────────▼────────────────▼──────────────────▼───────────┐
                    │              MAS VM (192.168.0.188)                       │
                    │  ┌──────────────────────────────────────────────────────┐│
                    │  │              MYCA Orchestrator 8001                  ││
                    │  │  - Voice Orchestrator API                            ││
                    │  │  - Prompt Manager (MYCA Identity)                    ││
                    │  │  - Memory API (5 scopes)                             ││
                    │  └──────────────────────┬───────────────────────────────┘│
                    │                         │                                │
                    │  ┌──────────────────────▼───────────────────────────────┐│
                    │  │               n8n Workflows 5678                      ││
                    │  │  - myca/voice → Gemini AI with MYCA prompt           ││
                    │  │  - myca/system → Infrastructure control               ││
                    │  │  - myca/agents → Agent routing                        ││
                    │  └──────────────────────────────────────────────────────┘│
                    │  ┌────────────────┐                                      │
                    │  │ Redis 6379    │                                       │
                    │  └────────────────┘                                      │
                    └──────────────────────────────────────────────────────────┘
```

### Files Modified Today (Already Done)

| File | Change |
|------|--------|
| `n8n/workflows/myca_voice_brain.json` | NEW - MYCA voice workflow with Gemini LLM integration |
| `config/myca_personaplex_prompt_1000.txt` | NEW - Condensed 792-char identity prompt for voice |
| `mycosoft_mas/core/myca_main.py` | UPDATED - Uses `myca/voice` webhook, identity-aware fallbacks |
| `mycosoft_mas/core/routers/voice_orchestrator_api.py` | UPDATED - Identity-aware local responses |

---

## Phase 1: Prepare Code

### 1.1 Verify Local Changes

Before deploying, ensure all local changes are committed:

```bash
# Check status
git status

# Stage new/modified files
git add n8n/workflows/myca_voice_brain.json
git add config/myca_personaplex_prompt_1000.txt
git add mycosoft_mas/core/myca_main.py
git add mycosoft_mas/core/routers/voice_orchestrator_api.py
git add docs/MYCA_UNIFIED_ORCHESTRATOR_UPGRADE_FEB03_2026.md

# Commit
git commit -m "feat(myca): Add identity-aware voice brain and fallback responses

- Created myca_voice_brain.json workflow with Gemini LLM and MYCA system prompt
- Added condensed 792-char identity prompt for Moshi voice personality
- Updated myca_main.py to use myca/voice webhook and identity-aware fallbacks
- Updated voice_orchestrator_api.py with MYCA identity in all responses
- MYCA now knows her name and role when asked"

# Push to GitHub
git push origin main
```

### 1.2 Clean Up Temp Files

Remove the helper scripts created during this session:

```powershell
Remove-Item _update_myca_main.py -ErrorAction SilentlyContinue
Remove-Item _update_voice_orch.py -ErrorAction SilentlyContinue
```

---

## Phase 2: Deploy to MAS VM (192.168.0.188)

### 2.1 SSH to MAS VM and Pull Latest Code

```bash
ssh mycosoft@192.168.0.188

# Navigate to MAS directory
cd /opt/mycosoft/mas

# Backup current code
cp -r mycosoft_mas mycosoft_mas_backup_$(date +%Y%m%d)

# Pull latest code
git fetch origin
git reset --hard origin/main
```

### 2.2 Rebuild and Restart MAS Orchestrator

```bash
# Stop current container
docker stop myca-orchestrator

# Rebuild with no cache
docker build -t myca-orchestrator:latest --no-cache -f Dockerfile .

# Restart
docker compose up -d myca-orchestrator

# Verify health
curl http://localhost:8001/health
```

### 2.3 Install Missing Dependencies

```bash
# If running locally or in container
pip install python-jose
```

---

## Phase 3: Configure n8n with MYCA Voice Brain

### 3.1 Import New Workflow

**Option 1: Via n8n UI**
1. Go to http://192.168.0.188:5678
2. Login with morgan@mycosoft.org / REDACTED_VM_SSH_PASSWORD
3. Click "Add Workflow" → "Import from File"
4. Select: `n8n/workflows/myca_voice_brain.json`
5. Click "Save" then "Activate"

**Option 2: Via n8n API**
```bash
curl -X POST http://192.168.0.188:5678/api/v1/workflows \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -d @n8n/workflows/myca_voice_brain.json
```

### 3.2 Configure Google AI Studio Credentials

In n8n:
1. Go to **Settings > Credentials**
2. Click "Add Credential"
3. Search for "Google AI" or "Gemini"
4. Select "Google AI (Gemini) API"
5. Enter your API key from https://aistudio.google.com/apikey
6. Save as "Google AI Studio"
7. The myca_voice_brain workflow should now use this credential

### 3.3 Verify Workflow is Active

```bash
# Check workflow status
curl http://192.168.0.188:5678/webhook/myca/voice -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "What is your name?"}'

# Expected: Response with "I'm MYCA" in response_text
```

---

## Phase 4: Memory Integration

### 4.1 Memory Scopes (Already Implemented)

| Scope | Storage | TTL | Use Case |
|-------|---------|-----|----------|
| conversation | Redis | Session | Current voice session context |
| user | MINDEX + Qdrant | Permanent | User preferences, history |
| agent | Redis | 24h | Agent-specific working memory |
| system | MINDEX | Permanent | System configuration |
| ephemeral | Memory | Request | Single request context |

### 4.2 Verify Redis Connection

```bash
# Test Redis on MAS VM
docker exec -it mas-redis redis-cli PING
# Expected: PONG

# Check memory API
curl http://192.168.0.188:8001/api/memory/list?scope=conversation
```

---

## Phase 5: Update PersonaPlex Bridge

### 5.1 For Local Development

The bridge is configured to call the website orchestrator:
```python
MAS_ORCHESTRATOR_URL = "http://localhost:3010/api/mas"
MAS_VOICE_ENDPOINT = "/voice/orchestrator"
```

### 5.2 For Production (MAS VM)

Update to call MAS VM directly:
```python
MAS_ORCHESTRATOR_URL = "http://192.168.0.188:8001"
MAS_VOICE_ENDPOINT = "/voice/orchestrator/chat"
```

### 5.3 MYCA Identity Prompt

The bridge loads MYCA's persona from the PromptManager. Files:
- Full prompt (10k chars): `config/myca_personaplex_prompt.txt`
- Condensed (792 chars): `config/myca_personaplex_prompt_1000.txt`

---

## Phase 6: Test Voice Identity

### 6.1 Start All Services (Local Testing)

**Terminal 1: Start PersonaPlex**
```powershell
cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python start_personaplex.py
```

**Terminal 2: Start MAS (optional, for local testing)**
```powershell
cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python -m uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8001
```

**Terminal 3: Start Website**
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev
```

### 6.2 Test Identity Responses via API

```bash
# Test local
curl -X POST http://localhost:8001/voice/orchestrator/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is your name?"}'

# Expected response should include "I'm MYCA" or "My name is MYCA"
```

### 6.3 Test Voice Conversation

1. Go to http://localhost:3010/test-voice
2. Click "Start MYCA Voice Session"
3. Allow microphone access
4. Ask: "What is your name?"
5. **Expected:** MYCA should respond: "I'm MYCA - My Companion AI..."

---

## Phase 7: Unified MYCA Architecture

### 7.1 Single Brain Rule

There should be **ONE MYCA** running on the MAS VM (192.168.0.188):

```
┌──────────────────────────────────────────────────────────────┐
│                      MYCA (Single Brain)                      │
│                     192.168.0.188:8001                        │
├──────────────────────────────────────────────────────────────┤
│  PromptManager    │  Memory API   │  Voice Orchestrator      │
│  (Identity)       │  (5 Scopes)   │  (Single Entry Point)    │
├──────────────────────────────────────────────────────────────┤
│                     n8n Workflows                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐               │
│  │myca/voice  │ │myca/system │ │myca/agents │               │
│  │(LLM+Prompt)│ │(Infra)     │ │(Routing)   │               │
│  └────────────┘ └────────────┘ └────────────┘               │
├──────────────────────────────────────────────────────────────┤
│                     Agent Pool (227 agents)                   │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 All Requests Route to MYCA

- PersonaPlex Bridge → `/voice/orchestrator/chat`
- Website API → `/voice/orchestrator/chat`
- n8n Webhooks → Call back to orchestrator
- All responses go through the **same identity-aware response pipeline**

---

## Environment Variables

### On MAS VM (.env)

```bash
# n8n
N8N_URL=http://localhost:5678
N8N_WEBHOOK_URL=http://localhost:5678/webhook
N8N_VOICE_WEBHOOK=myca/voice
N8N_API_KEY=your-n8n-api-key

# Google AI Studio (for n8n Gemini node)
GOOGLE_AI_API_KEY=your-gemini-api-key

# Memory
REDIS_URL=redis://localhost:6379

# Voice
ELEVENLABS_API_KEY=your-elevenlabs-key
MYCA_VOICE_ID=aEO01A4wXwd1O8GPgGlF
```

---

## Verification Checklist

After deployment, verify each item:

- [ ] MAS VM code is latest (`git log -1` shows today's commit)
- [ ] myca-orchestrator container running (`docker ps | grep myca`)
- [ ] n8n has myca/voice workflow active (check n8n UI)
- [ ] Google AI Studio credentials configured in n8n
- [ ] Redis running and responding (`docker exec mas-redis redis-cli PING`)
- [ ] `curl /voice/orchestrator/chat` returns MYCA-identified response
- [ ] Voice test shows MYCA knows her name
- [ ] Memory API endpoints responding (`/api/memory/list`)
- [ ] PromptManager loads both prompts correctly

---

## Rollback Plan

If issues occur after deployment:

```bash
# On MAS VM
cd /opt/mycosoft/mas

# Restore backup
rm -rf mycosoft_mas
mv mycosoft_mas_backup_YYYYMMDD mycosoft_mas

# Rebuild
docker compose up -d --build myca-orchestrator

# Verify
curl http://localhost:8001/health
```

---

## Summary

This plan ensures:

1. **ONE MYCA** - Single orchestrator on MAS VM at 192.168.0.188:8001
2. **Identity Awareness** - MYCA knows who she is via PromptManager and fallback responses
3. **LLM Integration** - n8n workflow calls Google Gemini with MYCA's full system prompt
4. **Memory** - 5-scope namespaced memory system (conversation, user, agent, system, ephemeral)
5. **Voice** - PersonaPlex full-duplex with MYCA persona and RTF monitoring
6. **Fallbacks** - Identity-aware responses even when n8n is unavailable

---

## Execution Log

### Completed (February 3, 2026)

1. **Code Changes Committed:**
   - `myca_voice_brain.json` - n8n workflow with Gemini LLM
   - `myca_personaplex_prompt_1000.txt` - Condensed identity prompt
   - `myca_main.py` - Identity-aware fallback responses
   - `voice_orchestrator_api.py` - Identity-aware responses
   - `infrastructure_ops.py` - Graceful NAS handling
   - Import path fixes for container deployment

2. **Deployed to MAS VM (192.168.0.188):**
   - Pulled latest code from GitHub
   - Created startup script with dependency installation
   - Container running and healthy

3. **Verified MYCA Identity:**
   ```json
   {
     "agent_name": "MYCA",
     "response_text": "I'm MYCA - My Companion AI. I'm the orchestrator of Mycosoft's Multi-Agent System. I coordinate all the specialized agents here and help you interact with our infrastructure. What can I help you with?"
   }
   ```

### Remaining Manual Steps

1. **Import n8n Workflow:**
   - Go to http://192.168.0.188:5678
   - Login: morgan@mycosoft.org / REDACTED_VM_SSH_PASSWORD
   - Import: `n8n/workflows/myca_voice_brain.json`
   - Activate workflow

2. **Configure Google AI Studio:**
   - Add Gemini API key in n8n Settings > Credentials
   - Get key from https://aistudio.google.com/apikey

3. **Test Voice Integration:**
   - Start PersonaPlex: `python start_personaplex.py`
   - Test voice conversation

---

*Created: February 3, 2026*  
*Last Updated: February 3, 2026*  
*Status: DEPLOYED - MYCA Identity Verified*
