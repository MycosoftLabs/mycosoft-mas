# MYCA Test Voice Complete – February 11, 2026

## Summary

Test voice now uses the **MYCA Brain** for responses instead of raw Moshi ("I'm Moshi"). The full flow is:

```
User speaks → Web Speech API (transcript) → Bridge WebSocket (user_transcript) 
→ MAS Brain → response text → Moshi TTS (0x02+text) → speaker
```

## Changes Made

### 1. Frontend (`WEBSITE/website/app/test-voice/page.tsx`)

When Web Speech API produces a final transcript:
- Sends `{ type: "user_transcript", text }` over the bridge WebSocket
- Continues to call `cloneTextToMAS()` for memory/tools

### 2. Bridge (`mycosoft-mas/services/personaplex-local/personaplex_bridge_nvidia.py`)

- **user_transcript**: Any JSON with `text` already triggers `clone_to_mas_memory(s, "user", text)` → `process_with_mas_brain()`
- **MYCA_BRAIN_ENABLED** (default `true`): Does **not** forward user audio bytes to Moshi, so Moshi does not generate its own reply. Moshi only receives `0x02 + MAS response` for TTS.

## How to Test

1. **Start GPU services** (Moshi 8998, Bridge 8999):
   ```bash
   python scripts/_start_voice_system.py
   # or: start Moshi + bridge manually
   ```

2. **Start website dev server** on port 3010:
   ```bash
   cd WEBSITE/website && npm run dev:next-only
   ```

3. **Open** http://localhost:3010/test-voice

4. **Connect** (Moshi + Bridge must be online)

5. **Speak** (e.g. "What is your name?")  
   - Expected: MYCA’s reply from MAS Brain ("I am MYCA from Mycosoft")  
   - Old behavior: "I'm Moshi" from Moshi

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `MYCA_BRAIN_ENABLED` | `true` | Use MAS Brain; do not send user audio to Moshi |
| `NEXT_PUBLIC_PERSONAPLEX_BRIDGE_WS_URL` | `ws://localhost:8999` | Bridge WebSocket for test-voice |
| `MOSHI_HOST`, `MOSHI_PORT` | localhost:8998 | Moshi server |

## Files Touched

| File | Change |
|------|--------|
| `WEBSITE/website/app/test-voice/page.tsx` | Send `user_transcript` to bridge WebSocket when transcript is final |
| `mycosoft-mas/services/personaplex-local/personaplex_bridge_nvidia.py` | Skip forwarding user audio to Moshi when MYCA_BRAIN_ENABLED |
