# n8n Integration Guide for MYCA MAS

## Overview

This guide covers how to integrate n8n with the Mycosoft Multi-Agent System (MAS) for workflow automation, including voice pipelines, Zapier MCP integration, and comprehensive agent orchestration.

## n8n Instance Configuration

### Access
- **Web UI**: http://localhost:5678
- **Basic Auth**: Username `admin`, Password `myca2024` (change via env vars)
- **API Access**: Use the instance API key for programmatic access

### API Key
Create an API key in the n8n UI: `Settings → n8n API → Create an API Key`.

**Usage in HTTP requests**:
```bash
curl -X GET http://localhost:5678/api/v1/workflows \
  -H "X-N8N-API-KEY: <your-api-key>"
```

## Available Workflows

### 1. MYCA Text Chat (`text-chat-workflow.json`)
Simple text-based chat with Ollama LLM.

**Webhook endpoint**: `POST http://localhost:5678/webhook/chat`

**Request body**:
```json
{
  "message": "Hello MYCA, what's the status?"
}
```

### 2. MYCA Voice Chat (`voice-chat-workflow.json`)
End-to-end voice pipeline: STT → LLM → TTS.

**Webhook endpoint**: `POST http://localhost:5678/webhook/voice-chat`

**Request**: Multipart form data with `audio` field (webm/ogg file)

**Response**: Audio file (MP3)

### 3. Comprehensive MAS Integration (`comprehensive-mas-workflow.json`)
Full-featured workflow demonstrating:
- MAS agent listing
- Orchestrator chat with context
- n8n Data Table logging
- Feedback loop integration
- Zapier MCP integration ready

**Webhook endpoint**: `POST http://localhost:5678/webhook/myca-command`

**Request body**:
```json
{
  "command": "list agents",
  "context": "optional metadata"
}
```

## MAS Orchestrator Endpoints (for n8n HTTP Request nodes)

All endpoints accessible via docker network at `http://mas-orchestrator:8000`

### Voice Endpoints

#### Chat (Text-based)
```
POST /voice/orchestrator/chat
Content-Type: application/json

{
  "message": "What can you do?",
  "conversation_id": "optional-uuid",
  "want_audio": false
}
```

**Response**:
```json
{
  "conversation_id": "uuid",
  "response_text": "I can help you...",
  "audio_base64": "...",  // if want_audio=true
  "audio_mime": "audio/mpeg"
}
```

#### Speech-to-Speech
```
POST /voice/orchestrator/speech
Content-Type: multipart/form-data

file: <audio file>
conversation_id: optional-uuid
```

**Response**:
```json
{
  "conversation_id": "uuid",
  "transcript": "user said...",
  "response_text": "MYCA replied...",
  "audio_base64": "base64-encoded-audio",
  "audio_mime": "audio/mpeg"
}
```

### Feedback Endpoints

#### Submit Feedback
```
POST /voice/feedback
Content-Type: application/json

{
  "conversation_id": "uuid",
  "agent_name": "Orchestrator",
  "transcript": "user message",
  "response_text": "agent response",
  "rating": 5,  // 1-5
  "success": true,
  "notes": "optional feedback notes"
}
```

#### Get Recent Feedback
```
GET /voice/feedback/recent?limit=25
```

#### Get Feedback Summary
```
GET /voice/feedback/summary
```

**Response**:
```json
{
  "total": 42,
  "avg_rating": 4.2,
  "avg_success": 0.95
}
```

### Agent Endpoints

#### List Agents
```
GET /agents
```

#### List Voice-Ready Agents
```
GET /voice/agents
```

## Zapier MCP Integration

### MCP Server URL
```
https://mcp.zapier.com/api/mcp/s/MmM5MmJkNDgtMDI5MC00ZGZhLWFlOGItYzM1MDQ4YTNkOWU0OmY5OWI4ZGYxLTAxNTgtNGZmOC05MDRkLTZlMmQzMzNlM2ViOQ==/mcp
```

### Using Zapier MCP in n8n

1. Add an **HTTP Request** node to your workflow
2. Configure:
   - **Method**: POST
   - **URL**: The Zapier MCP server URL above
   - **Authentication**: None (auth embedded in URL)
   - **Headers**: `Content-Type: application/json`
3. **Body** (JSON):
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "zapier_action_name",
    "arguments": {
      "your_param": "value"
    }
  },
  "id": "unique-request-id"
}
```

### Common Zapier Actions via MCP
- **Send Email**: Gmail, Outlook, etc.
- **Create Task**: Todoist, Asana, Trello, etc.
- **Post Message**: Slack, Discord, Teams, etc.
- **Update Spreadsheet**: Google Sheets, Airtable, etc.
- **Calendar Events**: Google Calendar, Outlook Calendar, etc.

## Advanced n8n Workflow Patterns

### 1. Voice → Agent Router → Feedback Loop

```
Webhook (voice upload)
  ↓
STT (Whisper)
  ↓
Route by Intent (IF node: contains "financial", "corporate", "marketing")
  ↓ (branch per agent)
POST /agents/{agent_id}/... (agent-specific endpoint)
  ↓
TTS (ElevenLabs/OpenedAI)
  ↓
Store Feedback
  ↓
Log to n8n Data Table
  ↓
Respond to Webhook
```

### 2. Scheduled Agent Status Check

```
Schedule Trigger (every 5 min)
  ↓
GET /agents (list all agents)
  ↓
For each agent:
  GET /agents/{agent_id} (check status)
  ↓
  IF status != "active":
    POST /agents/{agent_id}/restart
    ↓
    POST to Slack/Email (alert)
  ↓
Log to n8n Data Table
```

### 3. Zapier → MAS → Feedback

```
Webhook (from Zapier)
  ↓
Extract command/intent
  ↓
POST /voice/orchestrator/chat (with context)
  ↓
Parse response (check for "ROUTE: AgentName")
  ↓
IF routed to agent:
  POST /agents/{agent_id}/task
  ↓
Store feedback (success/failure)
  ↓
Send result back to Zapier (via Zapier MCP)
```

## n8n Data Table for Logging

### Create Data Table
1. Open n8n UI
2. Navigate to **Data** → **Data Tables**
3. Click **New Data Table**
4. Name: `myca-interactions`
5. Add columns:
   - `conversation_id` (String)
   - `user_message` (String)
   - `assistant_response` (String)
   - `timestamp` (String)
   - `source` (String)
   - `agent_name` (String, nullable)
   - `rating` (Number, nullable)
   - `success` (Boolean, nullable)

### Use in Workflows

Add a **Data Storage (n8n)** node:
- **Operation**: Insert
- **Data Store**: Select `myca-interactions`
- **Rows**: Map workflow data to table columns

## Voice System Architecture

```
User (Browser/App)
  ↓
voice-ui (Nginx proxy @ localhost:8090)
  ↓
/api/mas/voice/orchestrator/speech  →  MAS Orchestrator (container)
  ↓
Whisper STT (container) → Orchestrator Logic → ElevenLabs/OpenedAI TTS (container)
  ↓
Response (JSON with audio_base64)
  ↓
User plays audio + sees transcript
  ↓
Feedback UI (👍/👎 + notes)
  ↓
POST /api/mas/voice/feedback
  ↓
Stored in SQLite (data/voice_feedback.db)
  ↓
Orchestrator learns from avg rating (injected into system prompt)
```

## ElevenLabs Integration

### Setup
1. Get ElevenLabs API key from https://elevenlabs.io
2. Add to `.env.local`:
```bash
ELEVENLABS_API_KEY=your_key_here
```
3. Start ElevenLabs proxy service:
```bash
docker-compose --profile voice-premium up -d elevenlabs-proxy
```

### Voice Selection
The proxy maps OpenAI voice names to ElevenLabs voice IDs:
- `alloy` → Sarah (clear, conversational)
- `echo` → Rachel (calm, professional)
- `fable` → Adam (deep, narrative)
- `onyx` → Arnold (authoritative)
- `nova` → Sarah (default)
- `shimmer` → Dorothy (warm, friendly)
- **`scarlett`** → Sarah (can be customized to your preferred ElevenLabs voice ID)

### Customize Voices
Edit `mycosoft_mas/services/elevenlabs_proxy.py` and update the `VOICE_MAP` dictionary with your preferred ElevenLabs voice IDs.

## Best Practices

1. **Always use conversation_id** for multi-turn dialogues
2. **Store feedback** after every interaction to improve MYCA over time
3. **Use n8n Data Tables** for audit logs and analytics
4. **Set up error webhooks** to Slack/email for production monitoring
5. **Use Zapier MCP** to connect MYCA to 5000+ external services
6. **Rate limit** your workflows in n8n settings to avoid overwhelming MAS

## Troubleshooting

### Voice UI returns errors
- Check `docker logs mycosoft-mas-mas-orchestrator-1`
- Verify all voice services are healthy: `docker ps | findstr whisper ollama openedai-speech`
- Test endpoints directly:
  ```bash
  curl http://localhost:8001/health
  curl http://localhost:8765/docs
  curl http://localhost:5500/v1/models
  ```

### n8n webhook not responding
- Ensure workflow is **saved** and **activated** in n8n UI
- Check webhook URL in workflow settings
- Test with: `curl -X POST http://localhost:5678/webhook/myca-command -d '{"command":"test"}'`

### Feedback not showing in UI
- Check browser console for JavaScript errors
- Verify `/api/mas/voice/feedback` endpoint is reachable via voice-ui nginx proxy
- Test directly: `curl http://localhost:8090/api/mas/health`

## Next Steps

1. **Import comprehensive workflow**: Open n8n UI, import `n8n/workflows/comprehensive-mas-workflow.json`, save, and activate
2. **Configure Zapier**: Add Zapier MCP HTTP Request nodes for external integrations
3. **Customize ElevenLabs voices**: Get your preferred voice IDs and update `VOICE_MAP`
4. **Monitor feedback**: Query `/voice/feedback/summary` regularly to track MYCA performance
5. **Scale workers**: Increase `MAS_WORKER_COUNT` in docker-compose for higher concurrency
