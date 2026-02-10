# MYCA Chat Deployment - February 10, 2026

## Overview

MYCA (Mycosoft Autonomous Cognitive Agent) chat is now fully operational across all environments. This document covers the deployment configuration and how to maintain it.

## Status

| Environment | URL | Status |
|-------------|-----|--------|
| Local Dev | http://localhost:3010/api/mas/chat | Working |
| Sandbox | http://192.168.0.187:3000/api/mas/chat | Working |
| Production | https://mycosoft.com (via Cloudflare) | Working |

## Architecture

```
User Chat Request
       │
       ▼
Website API (/api/mas/chat)
       │
       ├─► n8n Workflow (if available)
       │
       ├─► Anthropic Claude (primary, needs credits)
       │
       ├─► OpenAI GPT-4 
       │
       ├─► Groq (Llama 3.3 - currently active)
       │
       ├─► Google Gemini
       │
       └─► xAI Grok
```

MYCA falls through providers until one responds successfully.

## Required API Keys

The following keys must be configured in the website container:

| Key | Provider | Notes |
|-----|----------|-------|
| `ANTHROPIC_API_KEY` | Anthropic | Claude models (needs credits) |
| `OPENAI_API_KEY` | OpenAI | GPT-4 models |
| `GROQ_API_KEY` | Groq | Llama 3.3 (fast, free tier) |
| `GOOGLE_AI_API_KEY` | Google | Gemini models |
| `XAI_API_KEY` | xAI | Grok models |

**SECURITY**: Never commit API keys to git. Keys are stored in:
- Local: `website/.env.local` (gitignored)
- Sandbox: Docker container environment variables

## Deployment Process

### Local Development

1. Edit `website/.env.local` with API keys
2. Restart dev server: `npm run dev:next-only`
3. Test: POST to `http://localhost:3010/api/mas/chat`

### Sandbox Deployment

The Sandbox container must be started with API keys as environment variables:

```bash
docker run -d --name mycosoft-website -p 3000:3000 \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  -e ANTHROPIC_API_KEY="..." \
  -e OPENAI_API_KEY="..." \
  -e GROQ_API_KEY="..." \
  -e GOOGLE_AI_API_KEY="..." \
  -e XAI_API_KEY="..." \
  -e MAS_API_URL="http://192.168.0.188:8001" \
  -e N8N_URL="http://192.168.0.188:5678" \
  --restart unless-stopped \
  mycosoft-always-on-mycosoft-website:latest
```

### After Deployment

Always purge Cloudflare cache:
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache" \
  -H "Authorization: Bearer API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

## Testing MYCA

```powershell
$body = @{
    message = "Hello MYCA, who are you?"
    context = @{ source = "test" }
    session_id = "test-session"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://192.168.0.187:3000/api/mas/chat" `
  -Method POST -Body $body -ContentType "application/json"
```

Expected response should have `provider: "groq"` (or another working provider).

## MAS Integration

MYCA chat also queries the MAS orchestrator for live status:
- Agent count from `http://192.168.0.188:8001/agents/registry/`
- n8n status from `http://192.168.0.188:5678/healthz`
- Metabase status from `http://192.168.0.188:3000/api/health`

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "fallback" provider | No API keys configured | Add keys to container env |
| "credit balance too low" | Anthropic has no credits | Add credits or rely on other providers |
| Empty response | n8n workflow not configured | Falls through to direct LLM calls |
| 500 error | Container crashed or API error | Check container logs |

## Related Files

- Chat API: `website/app/api/mas/chat/route.ts`
- Environment: `website/.env.local` (gitignored)
- MAS Orchestrator: `mycosoft_mas/core/myca_main.py`

## Security Notes

1. API keys are NEVER committed to git
2. `.env.local` is in `.gitignore`
3. Sandbox keys are passed via `-e` flags to Docker (not stored in files on VM)
4. Rotate keys periodically
5. Monitor API usage to detect leaks
