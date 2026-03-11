# Voice v9 Deployment and Runtime (Mar 2, 2026)

**Date:** March 2, 2026  
**Status:** Complete  
**Related Plan:** myca-voice-v9; `VOICE_V9_BASELINE_AUDIT_MAR02_2026.md`, `TEST_VOICE_LOCAL_FIX_MAR10_2026.md`, `VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`

## Overview

This document specifies the local and production runtime topology, environment variable contracts, and rollout stages for the MYCA Voice Suite v9 architecture. It enables the same v9 API contracts to target local or remote inference without code changes.

---

## 1. Runtime Modes

| Mode | Use Case | Moshi/Bridge Location | MAS Location | Website Location |
|------|----------|------------------------|--------------|------------------|
| **dev** | Local development, hot reload | Localhost (8998/8999) | VM 188:8001 | Localhost 3010 |
| **production** | Live sandbox/production | GPU node 190 or VM 187/188 | VM 188:8001 | VM 187:3000 |

---

## 2. Dev Mode (Local Voice Setup)

### 2.1 Topology

```
Browser (test-voice @ localhost:3010)
  ├── WebSocket v9: ws://192.168.0.188:8001/ws/voice/v9   (direct to MAS)
  ├── REST v9:      /api/test-voice/mas/voice-v9/*        (Next.js → MAS 188:8001)
  ├── Bridge WS:    ws://localhost:8999                   (PersonaPlex Bridge)
  └── TTS:          edge-tts (Bridge)                     (Moshi 0x02 not supported; see TTS_FALLBACK_PERSONAPLEX_MAR11_2026.md)
```

### 2.2 Startup Order (Dev)

1. **MAS Orchestrator** – VM 188:8001 (always on via systemd)
2. **Moshi** – `python scripts/start_voice_system.py` (external terminal)
3. **PersonaPlex Bridge** – Started with Moshi (8999)
4. **Website dev server** – `npm run dev:next-only` (external terminal, port 3010)

### 2.3 Env Contracts (Website `.env.local`)

| Variable | Value | Purpose |
|----------|-------|---------|
| `MAS_API_URL` | `http://192.168.0.188:8001` | MAS REST API base |
| `NEXT_PUBLIC_MAS_API_URL` | `http://192.168.0.188:8001` | MAS URL for browser (v9 WS, proxy) |
| `NEXT_PUBLIC_USE_LOCAL_GPU` | `true` | Use localhost for Bridge/Moshi (8998/8999) |
| `USE_LOCAL_VOICE` | `true` or `1` | Server-side local voice routing |
| `MINDEX_API_URL` | `http://192.168.0.189:8000` | MINDEX API (MAS Brain context) |
| `NEXT_PUBLIC_BASE_URL` | `http://localhost:3010` | Dev site URL for callbacks |

### 2.4 Verification (Dev)

```powershell
# 1. Start Moshi + Bridge (external terminal)
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/start_voice_system.py

# 2. Ensure MAS is up
Invoke-RestMethod -Uri "http://192.168.0.188:8001/health"

# 3. Start website dev server (external terminal)
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev:next-only

# 4. Open test-voice with v9 diagnostics
# http://localhost:3010/test-voice
# Toggle "v9 Diagnostics" ON; create session; verify WebSocket + REST
```

---

## 3. Production Mode

### 3.1 Topology

```
Browser (test-voice @ sandbox.mycosoft.com)
  ├── WebSocket v9: wss://.../ws/voice/v9  (via Cloudflare → MAS 188:8001)
  ├── REST v9:      /api/test-voice/mas/voice-v9/*  (Next.js → MAS 188:8001)
  ├── Bridge WS:    wss://gpu-node... or ws://192.168.0.190:8999
  └── Moshi TTS:    GPU node 190:8998 (or colocated)
```

### 3.2 Startup Order (Production)

1. **MAS Orchestrator** – VM 188:8001 (systemd `mas-orchestrator`)
2. **Moshi + Bridge** – GPU node 190 (or Sandbox 187 if colocated)
3. **Website container** – VM 187:3000 (Docker)
4. **Cloudflare** – Cache purge after deploy

### 3.3 Env Contracts (Production)

| Variable | Value | Purpose |
|----------|-------|---------|
| `MAS_API_URL` | `http://192.168.0.188:8001` | MAS REST (internal) |
| `NEXT_PUBLIC_MAS_API_URL` | `https://api.mycosoft.com` or MAS public URL | MAS for browser |
| `NEXT_PUBLIC_USE_LOCAL_GPU` | `false` or unset | Use remote Bridge/Moshi |
| `BRIDGE_URL` | `http://192.168.0.190:8999` | PersonaPlex Bridge (internal) |
| `MOSHI_URL` | `http://192.168.0.190:8998` | Moshi STT/TTS (internal) |
| `MINDEX_API_URL` | `http://192.168.0.189:8000` | MINDEX API |

### 3.4 GPU Node (190) Assignment

When voice inference is moved to the GPU node:

- Moshi: 192.168.0.190:8998
- PersonaPlex Bridge: 192.168.0.190:8999
- Same startup: `python scripts/start_voice_system.py` (or systemd on 190)

---

## 4. v9 API Endpoints (MAS)

Voice v9 is colocated with MAS. No separate v9 service.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/voice/v9/sessions` | POST | Create session |
| `/api/voice/v9/sessions/{id}/end` | POST | End session |
| `/api/voice/v9/sessions/{id}/transcripts` | GET | List transcripts |
| `/api/voice/v9/sessions/{id}/events` | GET | List speechworthy events |
| `/api/voice/v9/sessions/{id}/latency` | GET | Latency traces |
| `/api/voice/v9/sessions/{id}/persona` | GET | Persona lock state |
| `/api/voice/v9/sessions/{id}/barge-in` | POST | Request barge-in |
| `/api/voice/v9/sessions/{id}/persona/apply` | POST | Apply persona to text |
| `/api/voice/v9/ingest-event` | POST | Ingest raw event |
| `/ws/voice/v9` | WebSocket | Unified v9 session stream |

---

## 5. Website Proxy (REST Only)

The website proxies v9 REST through Next.js to avoid CORS and centralize auth:

- **Route:** `/api/test-voice/mas/voice-v9/*`
- **Target:** `{MAS_API_URL}/api/voice/v9/*`
- **WebSocket:** Browser connects directly to `ws://{MAS_WS}/ws/voice/v9` (no proxy)

---

## 6. Rollout Stages

| Stage | Scope | What Changes |
|-------|-------|--------------|
| **0** | Current | Legacy Bridge + test-voice; browser STT; duplicate MAS paths |
| **1** | Dev | v9 toggle ON; `useVoiceV9Session` + v9 components; Bridge/Moshi local (8998/8999) |
| **2** | Dev | v9 session rail replaces legacy center column when v9 ON; single MAS path |
| **3** | Production | Deploy v9 to Sandbox; Bridge/Moshi on GPU node 190 |
| **4** | Production | Deprecate legacy Bridge path; v9 as default |

---

## 7. Responsibility Split

| Component | Responsibility |
|-----------|----------------|
| **Moshi** | STT/TTS speech infra only; no identity or reasoning |
| **PersonaPlex Bridge** | WebSocket bridge; receives transcript JSON; calls MAS Brain; sends to Moshi TTS |
| **conversation_cortex** | Low-latency conversational layer (v9); cognitive routing |
| **MAS v9 services** | Session lifecycle, event rail, persona lock, interrupt manager, truth mirror |
| **MAS Brain** | Memory, tools, agents; invoked by Bridge and v9 MAS bridge |

---

## 8. Key Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Bridge/Moshi unreachable in prod | Health checks with TCP fallback; document GPU node startup |
| v9 and legacy paths diverge | Keep v9 toggle; migrate fully before removing legacy |
| WebSocket CORS/firewall | Use same origin or Cloudflare WS upgrade for prod |
| Env var drift | This doc as source of truth; validate in health endpoint |

---

## 9. Related Docs

- `docs/VOICE_V9_BASELINE_AUDIT_MAR02_2026.md` – Live path, v9 baseline
- `docs/VOICE_V9_DUPLEX_PERSONA_COMPLETE_MAR02_2026.md` – InterruptManager, PersonaLockService
- `docs/TEST_VOICE_LOCAL_FIX_MAR10_2026.md` – Local Bridge/Moshi, TCP fallback
- `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md` – VM layout, MAS/MINDEX URLs
- `.cursor/rules/run-servers-externally.mdc` – Never run dev server in Cursor
