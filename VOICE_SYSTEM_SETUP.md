# MYCA Voice System Setup Guide

## 🎤 Quick Start (Local Voice Chat)

**Access MYCA voice interface**: http://localhost:8090

- **Voice Mode**: Hold the mic button, speak, release → MYCA responds with voice
- **Text Mode**: Type and press Enter → MYCA responds (with optional TTS if voice mode enabled)
- **Feedback**: After each response, rate with 👍/👎 and optionally add notes

## 🔊 Voice System Architecture

```
Browser @ localhost:8090
  ↓ (nginx reverse proxy, same-origin)
/api/mas/voice/orchestrator/speech
  ↓
MAS Orchestrator Container (FastAPI)
  ├─→ Whisper STT (faster-whisper-server)
  ├─→ Ollama LLM (llama3.2:3b)
  └─→ ElevenLabs TTS (premium) OR OpenedAI Speech (local fallback)
  ↓
Response: { transcript, response_text, audio_base64 }
  ↓
Browser plays audio + shows transcript
  ↓
User rates response (👍/👎 + notes)
  ↓
POST /api/mas/voice/feedback
  ↓
SQLite persistence (data/voice_feedback.db)
  ↓
Orchestrator learns from feedback (avg rating in system prompt)
```

## 🚀 Running the Voice System

### Start all voice services:
```bash
docker-compose up -d mas-orchestrator whisper openedai-speech ollama n8n voice-ui
```

### Start with ElevenLabs premium voices:
```bash
# Add your ElevenLabs API key to .env.local
echo "ELEVENLABS_API_KEY=your_elevenlabs_key_here" >> .env.local

# Start with voice-premium profile
docker-compose --profile voice-premium up -d elevenlabs-proxy

# Restart voice-ui to use new TTS endpoint
docker-compose restart voice-ui
```

### Verify all services are healthy:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr /i "mas-orchestrator whisper openedai-speech voice-ui"

curl http://localhost:8001/health
curl http://localhost:8765/docs
curl http://localhost:5500/v1/models
curl http://localhost:8090/
```

## 🎙️ ElevenLabs Voice Selection

### Available Voice Mappings (OpenAI → ElevenLabs)
- **`alloy`** → Sarah (clear, conversational) - **RECOMMENDED FOR SCARLETT-STYLE VOICE**
- **`echo`** → Rachel (calm, professional)
- **`fable`** → Adam (deep, narrative)
- **`onyx`** → Arnold (authoritative)
- **`nova`** → Sarah (default)
- **`shimmer`** → Dorothy (warm, friendly)
- **`scarlett`** → Sarah (custom mapping for Scarlett Johansson style)

### Customize Voice Selection

1. **Get your preferred ElevenLabs voice ID**:
   - Visit https://elevenlabs.io/app/voice-library
   - Preview voices, pick your favorite
   - Copy the voice ID (e.g., `EXAVITQu4vr4xnSDxMaL`)

2. **Update the voice mapping**:

Edit `mycosoft_mas/services/elevenlabs_proxy.py`:

```python
VOICE_MAP = {
    "alloy": "YOUR_PREFERRED_VOICE_ID_HERE",
    "scarlett": "YOUR_SCARLETT_STYLE_VOICE_ID_HERE",
    # ... other mappings
}
```

3. **Rebuild the ElevenLabs proxy**:
```bash
docker-compose --profile voice-premium up -d --build elevenlabs-proxy
```

### Test ElevenLabs Voice
```bash
curl -X POST http://localhost:5501/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","voice":"scarlett","input":"Hello, I am MYCA"}' \
  -o test_elevenlabs.mp3

# Play the audio file to verify voice quality
```

## 📊 Feedback System

### How Feedback Improves MYCA

1. **User rates each response** (1-5 stars, success/failure, optional notes)
2. **Stored in SQLite** at `data/voice_feedback.db`
3. **Orchestrator system prompt** automatically includes feedback stats:
   - "Recent feedback: avg rating 4.2/5 across last 10 rated interactions"
4. **MYCA adjusts responses** based on what worked (implicit learning)

### Feedback API

**Submit feedback**:
```bash
curl -X POST http://localhost:8001/voice/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "uuid",
    "agent_name": "Orchestrator",
    "transcript": "what is the weather",
    "response_text": "I dont have access to weather APIs yet",
    "rating": 2,
    "success": false,
    "notes": "Need weather integration"
  }'
```

**View recent feedback**:
```bash
curl http://localhost:8001/voice/feedback/recent?limit=10
```

**View summary stats**:
```bash
curl http://localhost:8001/voice/feedback/summary
```

## 🔗 n8n Integration

### Access n8n
- **Web UI**: http://localhost:5678
- **Username**: `admin`
- **Password**: `myca2024`
- **API Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjZThjZmRmOS0xODYzLTQwOGUtYjBiNy0zYTI4NWFjNzRkZjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1OTkyNTM4LCJleHAiOjE3Njg1Mzk2MDB9._54u_k8z-JRsSpU5CHoM9W2Sj1Pc6pi0SNhDE7VW2Qo`

### Import Workflows

1. Open n8n UI (http://localhost:5678)
2. Navigate to **Workflows**
3. Click **Import from File**
4. Select one of:
   - `n8n/workflows/text-chat-workflow.json`
   - `n8n/workflows/voice-chat-workflow.json`
   - `n8n/workflows/comprehensive-mas-workflow.json` ← **RECOMMENDED**
5. Click **Save** then **Activate**

### Call n8n from External Apps

**Text chat**:
```bash
curl -X POST http://localhost:5678/webhook/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello MYCA"}'
```

**Voice chat** (audio file):
```bash
curl -X POST http://localhost:5678/webhook/voice-chat \
  -F "audio=@recording.webm"
```

**Comprehensive workflow**:
```bash
curl -X POST http://localhost:5678/webhook/myca-command \
  -H "Content-Type: application/json" \
  -d '{"command":"list agents"}'
```

## 🔌 Zapier MCP Integration

### MCP Server URL
```
https://mcp.zapier.com/api/mcp/s/MmM5MmJkNDgtMDI5MC00ZGZhLWFlOGItYzM1MDQ4YTNkOWU0OmY5OWI4ZGYxLTAxNTgtNGZmOC05MDRkLTZlMmQzMzNlM2ViOQ==/mcp
```

### Example: Send Slack Message via Zapier MCP

In n8n, add an **HTTP Request** node:
- **URL**: `https://mcp.zapier.com/api/mcp/s/MmM5MmJkNDgtMDI5MC00ZGZhLWFlOGItYzM1MDQ4YTNkOWU0OmY5OWI4ZGYxLTAxNTgtNGZmOC05MDRkLTZlMmQzMzNlM2ViOQ==/mcp`
- **Method**: POST
- **Body**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "slack_send_message",
    "arguments": {
      "channel": "#myca-logs",
      "text": "{{ $json.response }}"
    }
  },
  "id": "{{ $runIndex }}"
}
```

## ⚙️ Configuration

### Environment Variables

Add to `.env.local`:

```bash
# Voice System
VOICE_OLLAMA_MODEL=llama3.2:3b
VOICE_STT_CONCURRENCY=2
VOICE_LLM_CONCURRENCY=2
VOICE_TTS_CONCURRENCY=2
MAS_WORKER_COUNT=2

# ElevenLabs (Premium TTS)
ELEVENLABS_API_KEY=your_key_here

# n8n
N8N_USER=admin
N8N_PASSWORD=myca2024
N8N_ENCRYPTION_KEY=myca-encryption-key-change-me

# Whisper/TTS URLs (docker network)
WHISPER_URL=http://whisper:8000
TTS_URL=http://openedai-speech:8000
OLLAMA_URL=http://ollama:11434
```

## 📈 Performance Tuning

### Increase Concurrency
Edit `docker-compose.yml`, add under `mas-orchestrator` environment:
```yaml
- MAS_WORKER_COUNT=4
- VOICE_STT_CONCURRENCY=4
- VOICE_LLM_CONCURRENCY=4
- VOICE_TTS_CONCURRENCY=4
```

Restart:
```bash
docker-compose up -d mas-orchestrator
```

### Use Faster Whisper Model
Edit `docker-compose.yml`, update `whisper` service:
```yaml
environment:
  - WHISPER__MODEL=Systran/faster-whisper-small.en  # or medium.en, large-v2
```

Restart:
```bash
docker-compose up -d whisper
```

## 🧪 Testing

### End-to-End Voice Test

```bash
# 1. Generate test audio
curl -X POST http://localhost:5500/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","voice":"alloy","input":"hello this is a test"}' \
  -o test_audio.mp3

# 2. Send to MYCA speech endpoint
curl -X POST http://localhost:8001/voice/orchestrator/speech \
  -F "file=@test_audio.mp3" \
  | jq .

# Expected: transcript + response_text + audio_base64
```

### Test Feedback Loop

```bash
# Submit feedback
curl -X POST http://localhost:8001/voice/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test-1",
    "agent_name": "Orchestrator",
    "rating": 5,
    "success": true,
    "notes": "Perfect response!"
  }'

# View summary
curl http://localhost:8001/voice/feedback/summary

# Expected: {"total": N, "avg_rating": X, "avg_success": Y}
```

## 🎯 Use Cases

### 1. Voice Assistant
**"Hey MYCA, what's the status of my agents?"**
- Voice UI → STT → Orchestrator → GET /agents → TTS → Voice response

### 2. Task Automation via Voice
**"MYCA, create a board resolution for Q4 review"**
- Voice UI → STT → Orchestrator → ROUTE: CorporateOperationsAgent → TTS

### 3. External Trigger via n8n
**Zapier → n8n → MAS**
- Zapier detects email → n8n webhook → MAS chat → Slack notification

### 4. Scheduled Agent Health Check
**n8n Schedule** (every 5 min)
- GET /agents → check status → restart if needed → Slack alert

### 5. Voice Analytics
**n8n Schedule** (daily)
- GET /voice/feedback/summary → format report → email to admin

## 🛡️ Security Notes

- **All voice services** run on private `mas-network` Docker network
- **Only nginx proxy** (port 8090) and MAS orchestrator (port 8001) are exposed to host
- **No API keys** needed for local services (Whisper, Ollama, local TTS)
- **ElevenLabs API key** required only if you enable `voice-premium` profile
- **n8n API key** scoped to public API, expires 2026-01-15

## 📚 Additional Resources

- Full n8n integration docs: `docs/N8N_INTEGRATION_GUIDE.md`
- MAS agent docs: `docs/agents/`
- Zapier MCP: https://mcp.zapier.com
- ElevenLabs voices: https://elevenlabs.io/app/voice-library

---

**Need help?** Check container logs:
```bash
docker logs mycosoft-mas-mas-orchestrator-1 --tail 100
docker logs mycosoft-mas-whisper-1 --tail 50
docker logs mycosoft-mas-n8n-1 --tail 50
```
