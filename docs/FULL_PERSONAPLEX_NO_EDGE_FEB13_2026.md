# Full PersonaPlex — No Edge, Moshi Only (Feb 13, 2026)

## Policy

**STT:** 100% PersonaPlex / Moshi.  
**TTS:** Moshi does **not** support `kind 0x02` (text injection). The Bridge uses **edge-tts** as a TTS fallback. See `TTS_FALLBACK_PERSONAPLEX_MAR11_2026.md`.  
Flow: **User mic → Moshi STT → MAS Brain → response text → edge-tts (Bridge) → speaker.**

## Architecture (aligned with CONSCIOUSNESS_PIPELINE_ARCHITECTURE)

```
PersonaPlex Bridge → Moshi STT → text → MYCAConsciousness.process_input()
                                                    ↓
                                              Streaming tokens
                                                    ↓
PersonaPlex Bridge ← Moshi TTS ← text ← MYCAConsciousness response
```

- **STT**: Browser sends audio to Bridge (8999); Bridge forwards to Moshi (MOSHI_HOST:8998). Moshi returns text.
- **Brain**: Bridge sends text to MAS Brain (188:8001); gets MYCA response text.
- **TTS**: Bridge uses **edge-tts** (Moshi ignores `\x02` text injection). Bridge synthesizes via edge-tts → Opus → forwards `0x01` packets to browser.

## Components

| Component | Where | Port | Role |
|-----------|-------|------|------|
| Moshi server | **Remote inference host (RTX 5090 machine)** | 8998 | Heavy STT + TTS (Moshika/NATF2) |
| PersonaPlex Bridge | **Logic host (gpu01 / 1080 Ti Ubuntu)** | 8999 | WebSocket bridge, MAS Brain, session store |
| MAS Orchestrator | VM 188 | 8001 | Brain/consciousness |
| Test-voice page | Website localhost | 3010 | http://localhost:3010/test-voice |

## Bridge configuration (GPU node)

To use split architecture (5090 inference + 1080 logic), run the bridge on gpu01 with:

```bash
# On gpu01 bridge process, set these values:
$env:MOSHI_HOST = "192.168.0.172"  # 5090 machine LAN IP
$env:MOSHI_PORT = "8998"
python services/personaplex-local/personaplex_bridge_nvidia.py

# Or in .env / .env.local in MAS repo (if bridge loads it):
MOSHI_HOST=192.168.0.172
MOSHI_PORT=8998
```

Default when unset: `MOSHI_HOST=localhost`, `MOSHI_PORT=8998`.

## Code reference

- **Bridge**: `services/personaplex-local/personaplex_bridge_nvidia.py`  
  - MAS response → frontend (text) + **edge-tts TTS fallback** (`tts_fallback.py`) — Moshi `0x02` does not work.  
  - Requires: edge-tts, opuslib, ffmpeg. See `TTS_FALLBACK_PERSONAPLEX_MAR11_2026.md`.
- **Consciousness pipeline**: `docs/CONSCIOUSNESS_PIPELINE_ARCHITECTURE_FEB12_2026.md`  
- **GPU node**: `docs/GPU_NODE_INTEGRATION_FEB13_2026.md`, `docs/GPU_NODE_RUNBOOK_FEB13_2026.md`

## Test-voice

1. Start Moshi on the 5090 inference host on port 8998.  
2. On gpu01 bridge host, set `MOSHI_HOST` to the 5090 host LAN IP and `MOSHI_PORT=8998`.  
3. Start PersonaPlex Bridge on gpu01 port 8999.  
4. Open http://localhost:3010/test-voice and use voice; audio in/out is full PersonaPlex (Moshi only).
