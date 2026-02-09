# Voice System Fix - February 4, 2026

## Issues Resolved

### Issue 1: NoneType iteration error
**Problem:** When no `text_prompt` parameter was provided, `text_prompt_tokens` was set to `None`, causing iteration errors.

**Fix:** Changed to use an empty list `[]` instead of `None` (line 147).

### Issue 2: CUDA Graphs causing server hangs
**Problem:** With CUDA graphs enabled, the server would become unresponsive after 1-2 connections. The lock was never released because `step_system_prompts_async` would hang indefinitely.

**Fix:** Added timeout protection in `server.py`:
1. Lock acquisition timeout (5 seconds) - prevents new connections from waiting forever
2. System prompts timeout (25 seconds) - prevents CUDA graph hangs from blocking everything
3. Proper try/finally to ensure lock is always released

```python
# Lock with timeout
await asyncio.wait_for(self.lock.acquire(), timeout=5.0)

try:
    # System prompts with timeout
    await asyncio.wait_for(
        self.lm_gen.step_system_prompts_async(...),
        timeout=25.0
    )
finally:
    self.lock.release()
```

---

## System Status After Fix

| Component | Status | Details |
|-----------|--------|---------|
| Moshi Server (8998) | PASS | PersonaPlex AI on RTX 5090 |
| PersonaPlex Bridge (8999) | PASS | v7.0.0, Moshi available |
| MAS Orchestrator (8001) | PASS | v0.1.0 on VM 192.168.0.188 |
| Voice Chat Endpoint | PASS | MYCA responding correctly |
| Redis (6379) | PASS | Conversation memory store |
| Memory API | PASS | 8-scope memory system |
| Moshi WebSocket (direct) | PASS | Handshake OK |
| Bridge WebSocket | PASS | Full pipeline OK |
| GPU (RTX 5090) | OK | 22.7GB/32.6GB, 95% util |
| n8n Workflows (5678) | FAIL | Optional - not running |

**Result: 9/10 checks passed, all critical systems working.**

---

## How to Use

### Option 1: Native Moshi UI (Direct)
Open: http://localhost:8998

### Option 2: Test Voice Page (via Bridge)
1. Start website: `cd website && npm run dev`
2. Open: http://localhost:3010/test-voice

### Option 3: MAS Voice API (Text-only)
```bash
curl -X POST http://192.168.0.188:8001/voice/orchestrator/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is your name?"}'
```

---

## Services Running

| Service | PID | Memory |
|---------|-----|--------|
| Moshi Server | 181788 | 22.7GB GPU |
| PersonaPlex Bridge | 44100 | ~80MB |

---

## Files Modified

1. `personaplex-repo/moshi/moshi/server.py` - Fixed None text_prompt_tokens bug

## Diagnostic Scripts Created

1. `_diagnose_moshi.py` - Quick Moshi health check
2. `_check_all_systems.py` - Comprehensive 10-point system check
3. `_test_moshi_fix.py` - WebSocket fix verification
4. `_test_full_pipeline.py` - End-to-end pipeline test

---

## Maintenance Commands

```powershell
# Check all systems
python _check_all_systems.py

# Restart Moshi if stuck
taskkill /F /IM python.exe
python start_personaplex.py

# Start Bridge
python services/personaplex-local/personaplex_bridge_nvidia.py
```

---

*Document created: February 4, 2026*
*System Status: FULLY OPERATIONAL*
