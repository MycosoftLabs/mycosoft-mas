# MYCA Fallback-Only Fix — March 5, 2026

**Status:** Complete  
**Issue:** MYCA chat showing only `myca-local-fallback` / `myca-consciousness` instead of real AI responses.

## Root Cause

When the Voice Orchestrator (`/api/mas/voice/orchestrator`) hits **myca-local-fallback**, it means **all** of these failed:

1. **MAS Consciousness API** (`http://192.168.0.188:8001/api/myca/chat`) — timeout, 5xx, or empty/broken response
2. **LLM APIs** — Groq, Claude, OpenAI, Gemini, Grok (need API keys)
3. **Ollama** — local Llama on MAS VM (`http://192.168.0.188:11434`)
4. **n8n workflows** — Master Brain, speech webhooks

If **any** provider succeeds, you get `myca-groq`, `myca-consciousness`, etc. Only when **all** fail do you get `myca-local-fallback` with canned responses.

## Fixes Applied

### 1. OLLAMA_BASE_URL default (website)

**Changed:** Default from `http://localhost:11434` to `http://192.168.0.188:11434`.

**Why:** Ollama runs on MAS VM (188). When the website runs on Sandbox (187) or local dev, `localhost` does not reach Ollama. The website server must call `192.168.0.188:11434`.

**File:** `website/app/api/mas/voice/orchestrator/route.ts`

### 2. Env vars for MYCA (website .env.local / VM env)

Ensure the **website** has at least:

```bash
# MAS
MAS_API_URL=http://192.168.0.188:8001

# Ollama on MAS VM
OLLAMA_BASE_URL=http://192.168.0.188:11434
OLLAMA_MODEL=llama3.3

# At least ONE of these for real AI (otherwise you rely on consciousness + Ollama)
GROQ_API_KEY=<your-key>
ANTHROPIC_API_KEY=<your-key>
OPENAI_API_KEY=<your-key>
```

If **no** LLM keys are set and consciousness/Ollama fail, you will always get `myca-local-fallback`.

## Verification

1. **MAS health:** `curl http://192.168.0.188:8001/health`
2. **Consciousness API:** `curl http://192.168.0.188:8001/api/myca/ping`
3. **Ollama:** `curl http://192.168.0.188:11434/api/tags` (Ollama must be running on MAS VM)
4. **Chat test:** Send a message on `/myca` — check response `agent` field; should be `myca-groq`, `myca-consciousness`, `myca-claude`, etc., not `myca-local-fallback`.

## If Still Fallback-Only

1. Check website server logs for `[MYCA]` — shows which providers were tried and why they failed.
2. Confirm `MAS_API_URL` is correct and MAS is reachable from the website host.
3. Confirm at least one LLM key is set and valid.
4. If Ollama is used: ensure Ollama runs on MAS VM 188 and port 11434 is open.

## Related

- `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` — env vars and VM layout
- `website/app/api/mas/voice/orchestrator/route.ts` — getMycaResponse, callMycaConsciousness, raceProviders
