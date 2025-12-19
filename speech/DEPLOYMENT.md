# MYCA Speech Interface - Deployment Guide

## 📋 Commands to Run

### 1. Start Speech Gateway

```bash
# Docker Compose (recommended)
cd speech
docker-compose -f docker-compose.speech.yml up -d

# Or local Python
cd speech/gateway
pip install -r requirements.txt
export OPENAI_API_KEY=sk-your-key-here
python main.py
```

**Gateway URL**: `http://localhost:8002`

### 2. Start Speech UI

```bash
cd speech/ui
npm install
npm run dev
```

**UI URL**: `http://localhost:3000`

### 3. Import n8n Workflows

1. Open n8n UI: `http://localhost:5678`
2. Navigate to **Workflows** → **Import**
3. Import these files:
   - `n8n/workflows/speech/speech-command-turn.json`
   - `n8n/workflows/speech/speech-safety-confirm.json`
4. **Activate** both workflows (toggle switch in top-right)

### 4. Configure Secrets

#### Option A: Environment Variables (Quick Start)

```bash
export OPENAI_API_KEY=sk-your-openai-api-key-here
```

#### Option B: Vault (Production)

```bash
# Set Vault connection
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=your-vault-token

# Store OpenAI API key
vault kv put secret/myca/speech openai-api-key=sk-your-key-here
```

### 5. Test the System

```bash
# Run smoke test
cd speech/scripts
chmod +x smoke_test.sh
./smoke_test.sh

# Or PowerShell
./smoke_test.ps1
```

## 🌐 Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Speech UI** | http://localhost:3000 | Push-to-talk web interface |
| **Speech Gateway** | http://localhost:8002 | Audio processing service |
| **Gateway Health** | http://localhost:8002/health | Health check endpoint |
| **Gateway Voices** | http://localhost:8002/voices | List available TTS voices |
| **n8n UI** | http://localhost:5678 | Workflow automation UI |
| **n8n Webhook** | http://localhost:5678/webhook/myca/speech_turn | Speech command endpoint |

## 🔍 Verification Steps

### 1. Gateway Health Check

```bash
curl http://localhost:8002/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "speech-gateway",
  "n8n_url": "http://n8n:5678",
  "vault_configured": true
}
```

### 2. List Available Voices

```bash
curl http://localhost:8002/voices
```

Expected response:
```json
{
  "voices": [
    {"id": "alloy", "name": "Alloy", "gender": "neutral"},
    ...
  ],
  "provider": "openai"
}
```

### 3. Test n8n Webhook

```bash
curl -X POST http://localhost:5678/webhook/myca/speech_turn \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-123",
    "transcript": "Hello MYCA",
    "actor": "user"
  }'
```

### 4. Test UI

1. Open `http://localhost:3000`
2. Click "Allow" for microphone permission
3. Hold mic button or press Spacebar
4. Speak: "Hello MYCA"
5. Release button
6. Should see transcript and hear response

## 📊 Architecture Flow

```
User (Browser)
    ↓ [Audio Capture]
Speech UI (localhost:3000)
    ↓ [POST /speech/turn]
Speech Gateway (localhost:8002)
    ↓ [STT: OpenAI Whisper]
Transcript Text
    ↓ [POST /webhook/myca/speech_turn]
n8n Workflow
    ↓ [POST /voice/orchestrator/chat]
MAS Orchestrator
    ↓ [Response Text]
n8n Workflow
    ↓ [Return JSON]
Speech Gateway
    ↓ [TTS: OpenAI]
Audio Base64
    ↓ [JSON Response]
Speech UI
    ↓ [Audio Playback]
User (Browser)
```

## 🔐 Security Checklist

- [ ] OpenAI API key stored in Vault (not env vars)
- [ ] Vault token secured and rotated
- [ ] Gateway behind reverse proxy (HTTPS)
- [ ] Rate limiting enabled
- [ ] Wake word enabled for production
- [ ] Raw audio storage disabled
- [ ] Audit logs monitored
- [ ] CORS configured properly
- [ ] Input validation enabled
- [ ] Destructive command confirmation required

## 📝 Environment Variables

### Speech Gateway

| Variable | Default | Description |
|----------|---------|-------------|
| `N8N_BASE_URL` | `http://n8n:5678` | n8n service URL |
| `N8N_WEBHOOK_PATH` | `/webhook/myca-command` | Legacy webhook path |
| `N8N_SPEECH_WEBHOOK_PATH` | `/webhook/myca/speech_turn` | Speech webhook path |
| `VAULT_ADDR` | `http://localhost:8200` | Vault address |
| `VAULT_TOKEN` | - | Vault authentication token |
| `VAULT_SECRET_PATH` | `secret/data/myca/speech` | Vault secret path |
| `OPENAI_API_KEY` | - | OpenAI API key (fallback) |
| `AUDIT_LOG_PATH` | `data/speech_audit.jsonl` | Audit log file path |
| `STORE_RAW_AUDIO` | `false` | Enable raw audio storage |
| `RAW_AUDIO_PATH` | `data/speech_audio` | Raw audio storage path |

### Speech UI

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_GATEWAY_URL` | `http://localhost:8002` | Gateway service URL |

## 🐛 Troubleshooting

### Gateway Issues

```bash
# Check gateway logs
docker logs -f speech-gateway

# Check gateway health
curl http://localhost:8002/health

# Test gateway directly
curl -X POST http://localhost:8002/speech/turn \
  -F "audio=@test.webm" \
  -F "provider=openai" \
  -F "voice=alloy"
```

### n8n Issues

```bash
# Check n8n is running
curl http://localhost:5678/healthz

# Check workflow is activated
# (Open n8n UI and verify toggle switch)

# Test webhook directly
curl -X POST http://localhost:5678/webhook/myca/speech_turn \
  -H "Content-Type: application/json" \
  -d '{"request_id":"test","transcript":"test"}'
```

### UI Issues

```bash
# Check browser console (F12)
# Common issues:
# - Microphone permission denied
# - CORS errors (check gateway CORS config)
# - Network errors (check gateway URL)
```

## 📈 Monitoring

### Audit Logs

```bash
# View audit logs
tail -f data/speech_audit.jsonl

# Search for specific request
grep "request_id_here" data/speech_audit.jsonl
```

### Performance Metrics

Each audit log entry includes `timings_ms`:
- `audio_read_ms` - Time to read audio
- `stt_ms` - Speech-to-text latency
- `n8n_ms` - n8n processing time
- `tts_ms` - Text-to-speech latency
- `total_ms` - End-to-end latency

Target: < 4000ms total on LAN

## 🚀 Production Deployment

1. **Set up Vault** with proper authentication
2. **Store secrets** in Vault (not env vars)
3. **Enable HTTPS** via reverse proxy (nginx/traefik)
4. **Configure rate limiting** per user/IP
5. **Enable wake word** for security
6. **Disable raw audio storage** (privacy)
7. **Set up monitoring** for audit logs
8. **Configure backup** for conversation data
9. **Set up alerts** for errors/failures
10. **Document** custom configurations

## 📚 Additional Resources

- [Full README](README.md) - Complete documentation
- [Quick Start](QUICKSTART.md) - 5-minute setup guide
- [n8n Integration Guide](../docs/N8N_INTEGRATION_GUIDE.md) - n8n details
- [Twilio Integration](../docs/TWILIO_INTEGRATION.md) - SMS/voice integration

---

**Ready to deploy!** 🚀
