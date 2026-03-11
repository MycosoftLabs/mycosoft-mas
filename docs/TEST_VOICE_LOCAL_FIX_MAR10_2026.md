# Test-Voice Local Voice Fix (Mar 10, 2026)

**Date:** March 10, 2026  
**Status:** Complete  
**Related:** test-voice page, PersonaPlex Bridge, Moshi, local GPU (RTX 5090)

## Summary

Fixed test-voice page (`http://localhost:3010/test-voice`) when using **local** Moshi + PersonaPlex Bridge (localhost:8998/8999) instead of the GPU node (192.168.0.190). Diagnostics were timing out on Bridge health, causing false OFFLINE reports.

## Root Causes

1. **Bridge /health blocking:** The PersonaPlex Bridge `/health` endpoint called `await get_voice_store()`, which on first call connects to VoiceSessionStore (Supabase/Postgres). That connect can block for several seconds or hang when DB is unreachable, causing health checks to timeout (5s).
2. **No TCP fallback:** When Bridge HTTP health timed out, diagnostics reported everything OFFLINE even when Bridge and Moshi ports (8999, 8998) were listening.

## Changes Made

### 1. PersonaPlex Bridge – Non-blocking Health (`personaplex_bridge_nvidia.py`)

- **Before:** `store = await get_voice_store()` – triggers DB connect on first call.
- **After:** `store = voice_store` – use cached global only; do not trigger connect in health.
- **Effect:** `/health` returns quickly; `voice_store_connected` reflects whether the store was already initialized during startup.

### 2. Diagnostics API – TCP Fallback (`website/app/api/test-voice/diagnostics/route.ts`)

- Enable `tcpFallback=true` for Bridge health check.
- When HTTP times out, try a raw TCP connect to the Bridge port (8999). If open, report Bridge as ONLINE.
- When Bridge used TCP fallback (no JSON), additionally probe Moshi port (8998) via TCP to infer Moshi status.
- **Effect:** When Bridge HTTP is slow but the port is open, diagnostics show Bridge and Moshi as reachable instead of OFFLINE.

### 3. Local Voice Routing (Previous Session)

- With `NEXT_PUBLIC_USE_LOCAL_GPU=true` or `USE_LOCAL_VOICE=true`, diagnostics, bridge session proxy, and bridge health proxy use `http://localhost:8999` instead of GPU node URLs.
- Test-voice page sets `bridgeWsBaseUrl = "ws://localhost:8999"` when local GPU is enabled.

## Configuration

| Env | Purpose |
|-----|---------|
| `NEXT_PUBLIC_USE_LOCAL_GPU=true` | Use localhost for Bridge/Moshi (test-voice, diagnostics) |
| `USE_LOCAL_VOICE=true` or `USE_LOCAL_VOICE=1` | Same; server-side routing |

## Verification

1. **Start Moshi + Bridge** (external terminal):
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
   python scripts/start_voice_system.py
   ```
2. **Ensure website .env.local** has `NEXT_PUBLIC_USE_LOCAL_GPU=true`.
3. **Open** http://localhost:3010/test-voice.
4. **Run diagnostics** – Bridge and Moshi should show ONLINE (or at least reachable via TCP if HTTP is slow).
5. **Start session** – WebSocket should connect to `ws://localhost:8999` and full-duplex voice should work with MAS, MINDEX, search, STATIC, latents.

## Full System Flow (Local GPU)

```
Browser (test-voice)
  → ws://localhost:8999 (PersonaPlex Bridge)
      → http://localhost:8998 (Moshi STT/TTS)
  → /api/test-voice/* (Next.js) → MAS 192.168.0.188:8001
  → MINDEX 192.168.0.189:8000, search, STATIC, latents
```

## Files Modified

- `mas/services/personaplex-local/personaplex_bridge_nvidia.py` – health uses cached voice_store
- `website/app/api/test-voice/diagnostics/route.ts` – TCP fallback for Bridge; Moshi port probe when Bridge uses TCP

## Related Docs

- `docs/VOICE_TEST_QUICK_START_FEB18_2026.md`
- `docs/MYCA_VOICE_TEST_SYSTEMS_ONLINE_FEB18_2026.md`
- `.cursor/rules/run-servers-externally.mdc`
