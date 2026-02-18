---
name: myca-voice
description: MYCA voice sub-agent. Knows all voice/PersonaPlex/consciousness docs and architecture. Use when working on test-voice page, PersonaPlex bridge, MYCA brain integration, or ensuring voice uses MYCA persona and consciousness—not raw Moshi.
---

## MANDATORY before any MYCA voice work

1. **Read these docs first** (in order):
   - `docs/FULL_PERSONAPLEX_NO_EDGE_FEB13_2026.md`
   - `docs/CONSCIOUSNESS_PIPELINE_ARCHITECTURE_FEB12_2026.md`
   - `docs/MYCA_VOICE_APPLICATION_HANDOFF_FEB17_2026.md`
   - `docs/MYCA_VOICE_TEST_SYSTEMS_ONLINE_FEB18_2026.md`
   - `docs/VOICE_TEST_QUICK_START_FEB18_2026.md`
   - `docs/VOICE_SYSTEM_FILES_DEVICES_SSH_FEB13_2026.md`
   - `docs/FULL_DUPLEX_VOICE_PHASE1_FEB12_2026.md`
   - `docs/MYCA_TRUE_CONSCIOUSNESS_IMPLEMENTATION_FEB11_2026.md`

2. **Invoke** `voice-engineer` for PersonaPlex/Moshi setup; `process-manager` for GPU/port conflicts. See `.cursor/rules/agent-must-invoke-subagents.mdc`.

---

## CRITICAL: Correct voice architecture

**PersonaPlex/Moshi is the voice interface only.** MYCA Brain (consciousness) is the **only** source of responses.

```
User mic → Moshi STT → text → MAS Brain (MYCAConsciousness) → response text → Moshi TTS → speaker
```

**NOT:** Moshi generating its own responses ("I'm Moshi"). The bridge must:
1. Forward user audio to Moshi for **STT only**
2. Send transcribed text to MAS Brain (MYCAConsciousness.process_input)
3. Get MYCA response text from MAS
4. Send that text to Moshi for **TTS only** via `\x02` + utf-8

---

## Architecture (from FULL_PERSONAPLEX_NO_EDGE_FEB13_2026)

```
PersonaPlex Bridge → Moshi STT → text → MYCAConsciousness.process_input()
                                                    ↓
                                              Streaming tokens
                                                    ↓
PersonaPlex Bridge ← Moshi TTS ← text ← MYCAConsciousness response
```

- **STT**: Browser → Bridge (8999) → Moshi (8998). Moshi returns text.
- **Brain**: Bridge → MAS (188:8001). Gets MYCA response text.
- **TTS**: Bridge sends `\x02` + utf-8 text to Moshi; Moshi streams TTS audio (kind=1) and text (kind=2) back; Bridge forwards to browser.

---

## Components

| Component | Where | Port | Role |
|-----------|-------|------|------|
| Moshi server | RTX 5090 / local | 8998 | STT + TTS (no response generation) |
| PersonaPlex Bridge | `personaplex_bridge_nvidia.py` | 8999 | WebSocket bridge, MAS Brain calls, session store |
| MAS Orchestrator | VM 188 | 8001 | Brain, consciousness, intent |
| Test-voice page | WEBSITE | 3010 | http://localhost:3010/test-voice |

---

## Key files

| Purpose | Path |
|---------|------|
| Bridge | `services/personaplex-local/personaplex_bridge_nvidia.py` |
| MYCA persona | `config/myca_personaplex_short.txt` |
| Voice Orchestrator | `mycosoft_mas/core/routers/voice_orchestrator_api.py` |
| Brain API | `mycosoft_mas/core/routers/brain_api.py` |
| Consciousness | `mycosoft_mas/consciousness/` (core.py, deliberation.py) |
| Test-voice page | `WEBSITE/website/app/test-voice/page.tsx` |
| MAS proxy | `WEBSITE/website/app/api/test-voice/mas/orchestrator-chat/route.ts` |
| Start script | `scripts/start_voice_system.py` |

---

## API endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /voice/orchestrator/chat` | Single entry for voice chat (MYCAOrchestrator.process) |
| `POST /voice/brain` | Memory-integrated LLM (used by bridge) |
| `GET /voice/orchestrator/health` | Voice system health |

Flow: Browser → `/api/test-voice/mas/orchestrator-chat` → MAS `POST /voice/orchestrator/chat` → MYCAOrchestrator.process().

---

## Consciousness pipeline (from CONSCIOUSNESS_PIPELINE_ARCHITECTURE)

MYCAConsciousness.process_input() is the single entry for all interactions:
1. Attention focus (~100ms)
2. Soul context (identity, beliefs, purpose, emotions)
3. Parallel context (working memory, world model, memory recall)
4. Intuition (System 1, fast path)
5. Deliberation (System 2, LLM reasoning)
6. Streaming tokens → response

Voice must route through this. No bypass to raw Moshi.

---

## Full duplex (from FULL_DUPLEX_VOICE_PHASE1)

- Speech acts (~80 chars, interruptible chunks)
- Barge-in (VAD, 0x03 interrupt)
- DuplexSession in bridge
- `mycosoft_mas/consciousness/speech_planner.py`, `conversation_control.py`, `duplex_session.py`

---

## Bridge configuration

```bash
# Split architecture (5090 inference + bridge host):
MOSHI_HOST=192.168.0.172   # 5090 LAN IP
MOSHI_PORT=8998
MYCA_BRAIN_ENABLED=true
MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001

python services/personaplex-local/personaplex_bridge_nvidia.py
```

---

## Common failure modes

1. **"I'm Moshi" responses**: Moshi generating its own text while MAS brain runs in parallel. Fix: Bridge must use MAS response as sole TTS source; suppress or ignore Moshi's generated text.
2. **No consciousness**: Bridge calling wrong endpoint or not waiting for MAS. Fix: Bridge must call `/voice/brain` or `/voice/orchestrator/chat` and use returned text for TTS.
3. **Latency**: MAS context gathering (2–3s). Documented in CONSCIOUSNESS_PIPELINE_ARCHITECTURE; parallel gather helps.

---

## When invoked

1. Fix voice output not using MYCA persona/brain
2. Change bridge flow (STT → Brain → TTS)
3. Update test-voice page or MAS voice APIs
4. Debug consciousness integration in voice
5. Add or modify full-duplex (barge-in, speech acts)

---

## Sub-agents to invoke

- **voice-engineer** – PersonaPlex/Moshi setup, GPU services
- **process-manager** – Port conflicts, GPU cleanup
- **terminal-watcher** – When running voice services

---

## Key references (read before work)

- `docs/FULL_PERSONAPLEX_NO_EDGE_FEB13_2026.md`
- `docs/CONSCIOUSNESS_PIPELINE_ARCHITECTURE_FEB12_2026.md`
- `docs/MYCA_VOICE_APPLICATION_HANDOFF_FEB17_2026.md`
- `docs/MOSHI_DEPLOYMENT_BLOCKED_FEB13_2026.md` (RTX 5090 / GPU mode 0)
