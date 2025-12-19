# MYCA Speech Interface - Quick Start

## 🚀 Get Started in 5 Minutes

### Prerequisites Check

```bash
# Check n8n is running
curl http://localhost:5678/healthz

# Check OpenAI API key is set
echo $OPENAI_API_KEY  # or check Vault
```

### Step 1: Start Speech Gateway

**Option A: Docker (Recommended)**
```bash
cd speech
docker-compose -f docker-compose.speech.yml up -d
```

**Option B: Local Python**
```bash
cd speech/gateway
pip install -r requirements.txt
export OPENAI_API_KEY=sk-your-key-here
python main.py
```

Gateway runs on: `http://localhost:8002`

### Step 2: Start Speech UI

```bash
cd speech/ui
npm install
npm run dev
```

UI runs on: `http://localhost:3000`

### Step 3: Import n8n Workflows

1. Open n8n: `http://localhost:5678`
2. **Workflows** → **Import**
3. Import these files:
   - `n8n/workflows/speech/speech-command-turn.json`
   - `n8n/workflows/speech/speech-safety-confirm.json`
4. **Activate** both workflows (toggle switch)

### Step 4: Test It!

1. Open `http://localhost:3000` in browser
2. **Allow microphone** access
3. **Hold button** or press **Spacebar** to talk
4. **Release** to send
5. **Hear MYCA respond** 🎤

## ✅ Verification

### Test Gateway
```bash
# Health check
curl http://localhost:8002/health

# List voices
curl http://localhost:8002/voices
```

### Test UI
- Open `http://localhost:3000`
- Click mic button - should see "Recording..."
- Speak - mic level bar should move
- Release - should see "Processing..." then response

### Test n8n Integration
```bash
# Send test request to n8n webhook
curl -X POST http://localhost:5678/webhook/myca/speech_turn \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-123",
    "transcript": "Hello MYCA",
    "actor": "user"
  }'
```

## 🔧 Configuration

### Set OpenAI API Key

**Option A: Environment Variable**
```bash
export OPENAI_API_KEY=sk-your-key-here
```

**Option B: Vault**
```bash
vault kv put secret/myca/speech openai-api-key=sk-your-key-here
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=your-token
```

### Configure Gateway

Edit `speech/docker-compose.speech.yml` or set env vars:
- `N8N_BASE_URL` - n8n URL (default: `http://n8n:5678`)
- `OPENAI_API_KEY` - OpenAI API key
- `VAULT_ADDR` - Vault address (optional)
- `STORE_RAW_AUDIO` - Save audio files (default: `false`)

## 🐛 Troubleshooting

### "Gateway not reachable"
- Check gateway is running: `docker ps | grep speech-gateway`
- Check logs: `docker logs speech-gateway`
- Verify port 8002 is not in use

### "OpenAI API key not found"
- Set `OPENAI_API_KEY` env var
- Or configure Vault (see above)
- Restart gateway

### "n8n webhook failed"
- Verify n8n is running: `curl http://localhost:5678/healthz`
- Check workflow is **activated** (toggle switch)
- Verify webhook path: `/webhook/myca/speech_turn`

### "Mic not working"
- Grant browser microphone permission
- Check browser console (F12) for errors
- Try Chrome browser (best compatibility)

### "No transcript"
- Check audio format (webm/opus preferred)
- Verify OpenAI API key is valid
- Check gateway logs for STT errors

## 📝 Next Steps

- Read full [README.md](README.md) for details
- Run smoke test: `speech/scripts/smoke_test.sh`
- Configure wake word for security
- Set up audit logging monitoring
- Enable conversation memory

## 🎯 Commands Summary

```bash
# Start gateway
docker-compose -f speech/docker-compose.speech.yml up -d

# Start UI
cd speech/ui && npm run dev

# Test gateway
curl http://localhost:8002/health

# View logs
docker logs -f speech-gateway
```

## 🌐 URLs

- **UI**: http://localhost:3000
- **Gateway**: http://localhost:8002
- **n8n**: http://localhost:5678
- **Gateway Health**: http://localhost:8002/health
- **Gateway Voices**: http://localhost:8002/voices

---

**Ready to talk to MYCA!** 🎤✨
