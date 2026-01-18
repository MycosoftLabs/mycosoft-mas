# MYCA MAS - Quick Start

Get MYCA MAS running locally in under 5 minutes.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- 8GB+ RAM allocated to Docker
- 20GB+ free disk space

## Steps

### 1. Get Your Environment Ready

Copy the environment template:

```bash
# Windows PowerShell
Copy-Item ENV_TEMPLATE.md .env

# Linux/Mac/Git Bash
cp ENV_TEMPLATE.md .env
```

### 2. Add Your LLM API Key

Edit `.env` and add ONE of these:

**Option A: OpenAI (easiest, remote)**
```env
OPENAI_API_KEY=sk-your-key-here
LLM_DEFAULT_PROVIDER=openai
```

**Option B: Google Gemini (remote)**
```env
GEMINI_API_KEY=your-key-here
LLM_DEFAULT_PROVIDER=gemini
```

**Option C: Local LLM (free, no API key needed)**
```env
LOCAL_LLM_ENABLED=true
LLM_DEFAULT_PROVIDER=openai_compatible
```

### 3. Start Everything

```bash
# If you installed Make:
make up

# Without Make (Windows PowerShell):
docker compose up -d

# For local LLM (Option C above):
docker compose --profile local-llm up -d
```

### 4. Wait ~60 seconds

First boot takes time while services initialize.

### 5. Verify It's Working

```bash
# With Make:
make health

# Without Make:
curl http://localhost:8001/health
curl http://localhost:8001/ready
```

You should see:
- `/health` returns `{"status":"ok",...}`
- `/ready` returns `{"status":"ready",...}`

## 🎉 You're Done!

Access your services:

- **Mycosoft Website**: http://localhost:3000
- **CREP Dashboard**: http://localhost:3000/dashboard/crep
- **NatureOS**: http://localhost:3000/natureos
- **Device Manager**: http://localhost:3000/natureos/devices
- **MAS API**: http://localhost:8001
- **Grafana**: http://localhost:3002 (admin/admin)
- **Prometheus**: http://localhost:9090
- **MYCA UniFi Dashboard**: http://localhost:3100

## If You Used Local LLM (Option C)

Pull a model:

```bash
# Pull Llama 3 8B (4GB RAM, fast)
docker compose exec ollama ollama pull llama3:8b-instruct

# Test it
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy" \
  -d '{"model": "llama-3-8b-instruct", "messages": [{"role":"user","content":"Hello"}]}'
```

## Common Commands

```bash
make logs          # View logs
make down          # Stop everything
make restart       # Restart
make status        # See what's running
```

## Next Steps

- **Full Guide**: See `docs/LOCAL_DEV.md`
- **LLM Config**: See `config/models.yaml`
- **Upgrade Details**: See `IMPLEMENTATION_SUMMARY.md`

## Troubleshooting

**Problem**: Services won't start  
**Solution**: `make logs` to see errors, `make restart` to retry

**Problem**: Port conflict (e.g., 8001 in use)  
**Solution**: Edit `docker-compose.yml` to change ports

**Problem**: `/ready` returns `not_ready`  
**Solution**: Wait 30 more seconds (Postgres/Qdrant take time)

**Problem**: LLM calls fail  
**Solution**: Check your API key in `.env`, restart with `make restart`

**More Help**: See `docs/LOCAL_DEV.md` → Troubleshooting section

---

That's it! You now have a fully functional local MAS with multi-model LLM support. 🚀
