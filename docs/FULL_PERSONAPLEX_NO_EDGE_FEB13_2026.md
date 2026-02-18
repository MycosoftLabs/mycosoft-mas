# Full PersonaPlex — No Edge, Moshi Only (Feb 13, 2026)

## Policy

Voice is **100% PersonaPlex / Moshi**. There is no edge-tts, no Aria, and no other TTS fallback.  
Flow: **User mic → Moshi STT → MAS Brain → response text → Moshi TTS → speaker.**

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
- **TTS**: Bridge sends response text to Moshi with `\x02` + utf-8 text; Moshi streams TTS audio (kind=1) and text (kind=2) back; Bridge forwards to browser.

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

- **Bridge**: `services/personaplex-local/personaplex_bridge_nvidia.py` v8.2.0  
  - MAS response → frontend (text) + `session.moshi_ws.send_bytes(b"\x02" + response_text.encode("utf-8"))` for TTS.  
  - No edge_tts or other TTS path.
- **Consciousness pipeline**: `docs/CONSCIOUSNESS_PIPELINE_ARCHITECTURE_FEB12_2026.md`  
- **GPU node**: `docs/GPU_NODE_INTEGRATION_FEB13_2026.md`, `docs/GPU_NODE_RUNBOOK_FEB13_2026.md`

## Test-voice

1. Start Moshi on the 5090 inference host on port 8998.  
2. On gpu01 bridge host, set `MOSHI_HOST` to the 5090 host LAN IP and `MOSHI_PORT=8998`.  
3. Start PersonaPlex Bridge on gpu01 port 8999.  
4. Open http://localhost:3010/test-voice and use voice; audio in/out is full PersonaPlex (Moshi only).
