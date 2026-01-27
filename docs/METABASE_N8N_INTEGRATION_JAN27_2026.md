# Metabase + n8n Integration for MYCA - January 27, 2026

## Overview

This document describes the full integration of **Metabase** (business intelligence) and **n8n** (workflow automation) into the MYCA Multi-Agent System.

## Deployed Components

### 1. Metabase - Business Intelligence
- **URL**: http://192.168.0.188:3000
- **Container**: `myca-metabase`
- **Database**: PostgreSQL (`myca-metabase-db`)
- **Purpose**: Natural language queries, database analytics, dashboard visualization
- **Login**: morgan@mycosoft.org / Mushroom1!

### 2. n8n - Workflow Engine
- **URL**: http://192.168.0.188:5678
- **Container**: `myca-n8n`
- **Purpose**: Voice workflows, chat processing, automation
- **Login**: admin / Mushroom1!

### 3. PostgreSQL (Metabase Internal)
- **Container**: `myca-metabase-db`
- **Database**: metabase
- **User**: metabase
- **Password**: MetabasePass123!

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MYCA Topology Dashboard                      │
│                    (localhost:3010 / sandbox)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      /api/mas/chat                               │
│  • Tries n8n workflow first                                      │
│  • Falls back to direct LLM (Claude → GPT-4o → Groq → Gemini)   │
│  • Returns integration status                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│    n8n      │  │  Metabase   │  │    MAS      │
│   :5678     │  │   :3000     │  │   :8001     │
│  Workflows  │  │  Analytics  │  │ Orchestrator│
└─────────────┘  └─────────────┘  └─────────────┘
```

## API Endpoints

### Website API Routes

#### `/api/mas/chat` (POST)
Main MYCA chat endpoint with integrated backend status.

**Request:**
```json
{
  "message": "What's the system status?",
  "session_id": "session-123",
  "context": { "source": "topology-dashboard" }
}
```

**Response:**
```json
{
  "response": "All systems operational...",
  "agent": "myca-orchestrator",
  "provider": "gpt-4o",
  "session_id": "session-123",
  "timestamp": "2026-01-27T02:12:00Z",
  "integrations": {
    "mas": { "agents": 16, "health": "online" },
    "n8n": { "healthy": true },
    "metabase": { "healthy": true }
  }
}
```

#### `/api/metabase` (GET/POST)
Metabase integration for database queries.

**GET** - Check status:
```
GET /api/metabase
GET /api/metabase?action=databases
GET /api/metabase?action=questions
```

**POST** - Execute queries:
```json
{
  "action": "query",
  "query": "SELECT COUNT(*) FROM species",
  "databaseId": 1
}
```

```json
{
  "action": "natural",
  "naturalQuery": "How many species do we have?"
}
```

#### `/api/n8n` (GET/POST)
n8n workflow integration.

**GET** - Check status:
```
GET /api/n8n
GET /api/n8n?action=workflows
```

**POST** - Trigger workflows:
```json
{
  "action": "myca-chat",
  "data": {
    "message": "Hello MYCA",
    "session_id": "session-123"
  }
}
```

```json
{
  "action": "myca-voice",
  "data": {
    "text": "Hello, this is MYCA",
    "voice_action": "tts"
  }
}
```

## n8n Workflows

### MYCA Chat Workflow
- **Webhook**: `/webhook/myca-chat`
- **Purpose**: Process chat messages through n8n with full workflow capabilities
- **Path**: `scripts/n8n_workflows/myca_chat_workflow.json`

### MYCA Voice Workflow
- **Webhook**: `/webhook/myca-voice`
- **Purpose**: Text-to-Speech (ElevenLabs) and Speech-to-Text (OpenAI Whisper)
- **Path**: `scripts/n8n_workflows/myca_voice_workflow.json`

## Importing n8n Workflows

1. Open n8n at http://192.168.0.188:5678
2. Login with admin / Mushroom1!
3. Go to Workflows → Import from File
4. Select workflow JSON files from `scripts/n8n_workflows/`
5. Configure credentials (OpenAI, ElevenLabs)
6. Activate workflows

## Environment Variables

Add to `.env.local`:

```env
# Metabase + n8n Integration
METABASE_URL=http://192.168.0.188:3000
METABASE_USERNAME=morgan@mycosoft.org
METABASE_PASSWORD=Mushroom1!
N8N_URL=http://192.168.0.188:5678
N8N_USERNAME=admin
N8N_PASSWORD=Mushroom1!

# ElevenLabs Voice (for n8n workflows)
ELEVENLABS_API_KEY=your_key_here
MYCA_VOICE_ID=aEO01A4wXwd1O8GPgGlF
```

## Container Management

### Start Services
```bash
cd /home/mycosoft/myca-integrations
docker compose up -d
```

### Stop Services
```bash
docker compose down
```

### View Logs
```bash
docker logs myca-metabase --tail 100
docker logs myca-n8n --tail 100
```

### Restart Services
```bash
docker compose restart metabase
docker compose restart n8n
```

## Testing

### Test Metabase
```bash
curl http://192.168.0.188:3000/api/health
# Expected: {"status":"ok"}
```

### Test n8n
```bash
curl http://192.168.0.188:5678/healthz
# Expected: 200 OK
```

### Test Chat Integration
```powershell
$body = @{
    message = "What integrations are connected?"
    session_id = "test-session"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3010/api/mas/chat" -Method POST -Body $body -ContentType "application/json"
```

## Files Created

### Website (`C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\`)
- `app/api/metabase/route.ts` - Metabase API integration
- `app/api/n8n/route.ts` - n8n workflow API integration
- `app/api/mas/chat/route.ts` - Updated with integration status

### MAS (`C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\`)
- `scripts/deploy_metabase_n8n.py` - Deployment script
- `scripts/check_vm_for_metabase.py` - Status check script
- `scripts/n8n_workflows/myca_chat_workflow.json` - Chat workflow
- `scripts/n8n_workflows/myca_voice_workflow.json` - Voice workflow

### MAS VM (`/home/mycosoft/myca-integrations/`)
- `docker-compose.yml` - Container definitions

## Next Steps

1. **Configure Metabase Databases**: Connect MINDEX, PostgreSQL databases to Metabase
2. **Import n8n Workflows**: Load chat and voice workflows into n8n
3. **Add ElevenLabs API Key**: Enable voice synthesis in n8n
4. **Create Dashboards**: Build Metabase dashboards for agent metrics
5. **Expand Workflows**: Add more n8n workflows for specific agent tasks

## Troubleshooting

### Metabase not responding
```bash
# Check if container is running
docker ps | grep metabase

# View logs
docker logs myca-metabase --tail 50

# Restart
docker restart myca-metabase
```

### n8n webhooks not working
1. Ensure workflow is activated (toggle on)
2. Check webhook URL is correct
3. Verify credentials are configured
4. Check n8n logs for errors

### Chat not using n8n
- n8n workflow may not be configured
- Falls back to direct LLM (this is expected behavior)
- Check `provider` field in response

## Status Summary

| Component | Status | URL | Notes |
|-----------|--------|-----|-------|
| Metabase | ✅ Healthy | :3000 | Business intelligence |
| n8n | ✅ Healthy | :5678 | Workflow engine |
| MAS Orchestrator | ✅ Online | :8001 | 16 agents |
| Redis | ✅ Online | :6379 | Message broker |

---

*Document created: January 27, 2026*
*Last updated: January 27, 2026*
