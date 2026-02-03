# Voice System Fix Report - February 2, 2026

## Executive Summary

PersonaPlex voice system was NOT working due to multiple configuration issues. This document details what was broken and what was fixed.

---

## Issues Found & Fixed

### Issue 1: PersonaPlex Bridge Not Running
**Status:** ✅ FIXED

**Problem:** The PersonaPlex Bridge (port 8999) was not running. This is the critical component that connects the Moshi voice server to MYCA/MAS.

**Fix:** Started the bridge manually:
```powershell
cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
$env:MAS_ORCHESTRATOR_URL = "http://192.168.0.188:8001"
python services/personaplex-local/personaplex_bridge_nvidia.py
```

---

### Issue 2: Moshi Detection Bug in Bridge
**Status:** ✅ FIXED

**Problem:** The bridge checked for "moshi" in the server response, but the page title is "PersonaPlex", so `moshi_available` was always `false`.

**Fix:** Updated `personaplex_bridge_nvidia.py`:
```python
# Before:
if resp.status_code == 200 and "moshi" in resp.text.lower():

# After:
if resp.status_code == 200 and ("moshi" in resp.text.lower() or "personaplex" in resp.text.lower()):
```

---

### Issue 3: Wrong WebSocket Port in Website
**Status:** ✅ FIXED

**Problem:** The website `voice-duplex` page was connecting to port 8997 instead of 8999.

**Fix:** Updated `WEBSITE/website/app/myca/voice-duplex/page.tsx`:
- Changed all occurrences of `:8997` to `:8999`

---

### Issue 4: WebSocket Path Missing Session ID
**Status:** ✅ FIXED

**Problem:** The website was connecting to `ws://localhost:8999/` but the bridge expects `ws://localhost:8999/ws/{session_id}`.

**Fix:** Updated `voice-duplex/page.tsx` to:
1. First call `POST http://localhost:8999/session` to create a session
2. Then connect to `ws://localhost:8999/ws/{session_id}`

---

### Issue 5: ElevenLabs Quota Exceeded
**Status:** ⚠️ KNOWN ISSUE (from previous session)

**Problem:** ElevenLabs API returns `quota_exceeded` - 0 credits remaining.

**Impact:** The MYCA-connected voice mode falls back to ElevenLabs for TTS, but with no credits, no audio plays.

**Workaround:** Use Native PersonaPlex (Moshi) directly at `http://localhost:8998` which runs locally and doesn't require ElevenLabs.

---

## Current System Status

| Component | Port | Status | Notes |
|-----------|------|--------|-------|
| **Moshi Server** | 8998 | ✅ RUNNING | PersonaPlex native voice (NATF2.pt) |
| **PersonaPlex Bridge** | 8999 | ✅ RUNNING | Connects Moshi to MYCA |
| **MAS Orchestrator** | 8001 | ✅ ONLINE | On VM 192.168.0.188 |
| **n8n** | 5678 | ✅ ONLINE | On VM 192.168.0.188 |
| **Website Dev** | 3010 | ✅ RUNNING | Next.js dev server |

### Verified Working

```powershell
# Bridge health check
Invoke-RestMethod http://localhost:8999/health
# Returns: moshi_available = true

# Moshi WebSocket test
# Successfully connects to ws://localhost:8998/api/chat
```

---

## How To Use PersonaPlex Voice

### Option 1: Native Moshi UI (RECOMMENDED - Works Now)

1. Open browser to: **http://localhost:8998**
2. Select voice: **NATURAL_F2** (MYCA voice)
3. Optionally enter MYCA persona in Text Prompt:
   ```
   You are MYCA (Mycosoft Autonomous Cognitive Agent), an AI assistant for Mycosoft. You are calm, confident, and concise.
   ```
4. Click **Connect**
5. **Grant microphone permission** when browser asks
6. Start speaking naturally

> **Important:** The browser MUST have microphone permission. If Connect doesn't work, check browser permissions.

### Option 2: MYCA Voice Duplex Page

1. Open: **http://localhost:3010/myca/voice-duplex**
2. Click **Start Session**
3. Grant microphone permission
4. Speak or type messages

> **Note:** This mode may fall back to ElevenLabs if PersonaPlex WebSocket has issues.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Browser (User)                              │
│  ┌─────────────┐                                                │
│  │ Microphone  │ → Audio Input                                  │
│  └─────────────┘                                                │
└───────────────────────────────────────────────────┬─────────────┘
                                                    │
           ┌────────────────────────────────────────┴──────────────┐
           │                                                        │
           ▼                                                        ▼
┌─────────────────────────┐                         ┌─────────────────────────┐
│  Native Moshi UI        │                         │  MYCA Voice Duplex      │
│  http://localhost:8998  │                         │  http://localhost:3010  │
│  ─────────────────────  │                         │  ───────────────────────│
│  • Full-duplex voice    │                         │  • Session management   │
│  • NATF2.pt voice       │                         │  • Fallback to ElevenLabs│
│  • ~40ms latency        │                         │  • Text chat option     │
│  • NOT MYCA-connected   │                         │  • MYCA-connected       │
└───────────┬─────────────┘                         └───────────┬─────────────┘
            │                                                    │
            │ WebSocket /api/chat                                │ HTTP/WebSocket
            ▼                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PersonaPlex Bridge (Port 8999)                            │
│  ┌──────────────────┐  ┌───────────────────┐  ┌───────────────────────────┐ │
│  │ Intent           │→ │ Confirmation      │→ │ MAS Routing               │ │
│  │ Classification   │  │ Gating            │  │ (for tool calls)          │ │
│  └──────────────────┘  └───────────────────┘  └─────────────┬─────────────┘ │
└─────────────────────────────────────────────────────────────┼───────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MAS Orchestrator (192.168.0.188:8001)                     │
│  Agents, n8n Workflows, Tool Execution                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Startup Commands

### Start All Voice Services

```powershell
# Terminal 1: Moshi Server (if not already running)
cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python start_personaplex.py

# Terminal 2: PersonaPlex Bridge
cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
$env:MAS_ORCHESTRATOR_URL = "http://192.168.0.188:8001"
python services/personaplex-local/personaplex_bridge_nvidia.py

# Terminal 3: Website (optional)
cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev
```

### Verify Services

```powershell
# Check Moshi (should return HTML)
curl http://localhost:8998

# Check Bridge health
Invoke-RestMethod http://localhost:8999/health

# Check MAS Orchestrator
Invoke-RestMethod http://192.168.0.188:8001/health
```

---

## Troubleshooting

### "Connect button not working" on localhost:8998
1. Check browser console (F12) for errors
2. Ensure microphone permission is granted
3. Try a different browser (Chrome/Edge recommended)
4. Check if port 8998 is accessible: `netstat -ano | findstr :8998`

### "No voice audio playing"
1. Check speaker/headphone volume
2. Verify audio output device is correct
3. For ElevenLabs mode: API quota may be exhausted
4. Use Native Moshi (localhost:8998) instead

### "WebSocket connection failed"
1. Check if bridge is running: `netstat -ano | findstr :8999`
2. Restart the bridge if needed
3. Check bridge logs for errors

---

## Files Modified

| File | Change |
|------|--------|
| `services/personaplex-local/personaplex_bridge_nvidia.py` | Fixed Moshi detection |
| `WEBSITE/website/app/myca/voice-duplex/page.tsx` | Fixed port 8997→8999, session creation |

---

*Report generated: February 2, 2026*
*PersonaPlex Voice: NATF2.pt (Natural Female 2)*
*Moshi Server: kyutai/moshiko-pytorch-bf16*
