# MYCA Speech Interface

Complete push-to-talk voice interface for MYCA with n8n integration.

## Architecture

```
Browser (UI) → Speech Gateway → STT (OpenAI) → n8n → MAS Orchestrator → TTS (OpenAI) → Browser
```

## Components

### 1. Speech UI (`speech/ui/`)
- React + Vite web application
- Push-to-talk (mouse hold or Spacebar)
- Real-time mic level indicator
- Conversation transcript
- Settings panel (voice selection, wake word, etc.)

### 2. Speech Gateway (`speech/gateway/`)
- FastAPI service handling audio pipeline
- STT via OpenAI Whisper
- TTS via OpenAI text-to-speech
- Vault integration for secrets (falls back to env vars)
- Rate limiting and audit logging
- Safety checks for destructive commands

### 3. n8n Workflows (`n8n/workflows/speech/`)
- `speech-command-turn.json` - Main command processing
- `speech-safety-confirm.json` - Confirmation flow for destructive actions

## Prerequisites

1. **n8n running** on port 5678 (via docker-compose)
2. **OpenAI API Key** (in Vault or `OPENAI_API_KEY` env var)
3. **Vault** (optional, falls back to env vars)

## Quick Start

### 1. Start Speech Gateway

```bash
# Option A: Docker Compose (recommended)
docker-compose -f speech/docker-compose.speech.yml up -d

# Option B: Local Python
cd speech/gateway
pip install -r requirements.txt
python main.py
```

Gateway runs on `http://localhost:8002`

### 2. Start Speech UI

```bash
cd speech/ui
npm install
npm run dev
```

UI runs on `http://localhost:3000`

### 3. Import n8n Workflows

1. Open n8n UI: `http://localhost:5678`
2. Go to **Workflows** → **Import**
3. Import:
   - `n8n/workflows/speech/speech-command-turn.json`
   - `n8n/workflows/speech/speech-safety-confirm.json`
4. Activate both workflows

### 4. Configure Secrets

#### Option A: Vault (Recommended)

```bash
# Set Vault address and token
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=your-token

# Store OpenAI API key
vault kv put secret/myca/speech openai-api-key=sk-...
```

#### Option B: Environment Variables

```bash
export OPENAI_API_KEY=sk-...
```

## Usage

1. **Open UI**: Navigate to `http://localhost:3000`
2. **Grant microphone permission** when prompted
3. **Hold button or press Spacebar** to talk
4. **Release** to send audio
5. **View transcript** and hear MYCA's response

## Settings

- **Voice Enabled**: Toggle TTS audio playback
- **Voice Selection**: Choose from available OpenAI voices (alloy, echo, nova, etc.)
- **Store Raw Audio**: Save audio files for debugging (default: off)
- **Wake Word**: Require "Myca" prefix (default: off)
- **Provider**: OpenAI (browser fallback coming soon)

## Safety Features

### Destructive Command Detection

Commands containing keywords like "delete", "destroy", "wipe", etc. trigger confirmation:

1. Gateway detects destructive command
2. Returns confirmation request
3. User must say: `"Confirm action request_id <id>"`
4. Confirmation processed via `/speech/confirm` endpoint

### Wake Word

If enabled, transcript must start with "Myca" to be processed.

## API Endpoints

### Gateway Endpoints

- `GET /health` - Health check
- `GET /voices` - List available TTS voices
- `POST /speech/turn` - Process speech turn (multipart audio)
- `POST /speech/confirm` - Confirm destructive action

### n8n Webhooks

- `POST /webhook/myca/speech_turn` - Speech command processing
- `POST /webhook/myca/speech_confirm` - Confirmation handling

## Testing

### Smoke Test

```bash
cd speech/scripts
chmod +x smoke_test.sh
./smoke_test.sh
```

### Manual Test

```bash
# Test with audio file
curl -X POST http://localhost:8002/speech/turn \
  -F "audio=@test_audio.webm" \
  -F "provider=openai" \
  -F "voice=alloy"
```

## Audit Logging

All speech turns are logged to:
- **Gateway**: `data/speech_audit.jsonl` (JSONL format)
- **n8n**: Data Table `myca-speech-audit`
- **Postgres**: Table `myca_conversation` (if configured)

Each log entry includes:
- `request_id` (UUID)
- `transcript` (user input)
- `myca_text` (response)
- `timings_ms` (performance metrics)
- `timestamp`
- `is_destructive` (safety flag)

## Troubleshooting

### "OpenAI API key not found"
- Check Vault: `vault kv get secret/myca/speech`
- Or set: `export OPENAI_API_KEY=sk-...`
- Restart gateway

### "n8n webhook failed"
- Verify n8n is running: `curl http://localhost:5678/healthz`
- Check workflow is activated
- Verify webhook path matches: `/webhook/myca-command`

### "No transcript generated"
- Check audio format (webm/opus preferred)
- Verify OpenAI API key is valid
- Check gateway logs: `docker logs speech-gateway`

### "Mic not working"
- Grant browser microphone permission
- Check browser console for errors
- Try different browser (Chrome recommended)

## Development

### Gateway Development

```bash
cd speech/gateway
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```

### UI Development

```bash
cd speech/ui
npm install
npm run dev
```

## Production Deployment

1. **Set up Vault** with proper authentication
2. **Configure secrets** in Vault (not env vars)
3. **Enable HTTPS** for gateway and UI
4. **Set up monitoring** for audit logs
5. **Configure rate limiting** per user/IP
6. **Enable wake word** for security
7. **Disable raw audio storage** (privacy)

## Security Notes

- **Never commit** `.env.local` or secrets
- **Use Vault** for production secrets
- **Rate limit** gateway endpoints
- **Validate** all user inputs
- **Audit log** all interactions
- **Require wake word** in production

## Performance

- **STT latency**: ~1-2s (OpenAI Whisper)
- **n8n processing**: ~0.5-1s
- **TTS latency**: ~1-2s (OpenAI TTS)
- **Total**: ~2-5s end-to-end (on LAN)

## Next Steps

- [ ] Browser fallback (Web Speech API)
- [ ] Conversation context memory
- [ ] Multi-language support
- [ ] Voice activity detection (VAD)
- [ ] Streaming STT/TTS
- [ ] Custom wake words
- [ ] User authentication
- [ ] Conversation export

## Support

For issues or questions:
1. Check logs: `docker logs speech-gateway`
2. Review audit logs: `data/speech_audit.jsonl`
3. Test endpoints: `speech/scripts/smoke_test.sh`
