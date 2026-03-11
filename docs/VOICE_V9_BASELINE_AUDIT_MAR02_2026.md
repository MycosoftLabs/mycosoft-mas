# Voice v9 Baseline Audit (Mar 2, 2026)

**Date:** March 2, 2026  
**Status:** Complete  
**Related Plan:** myca-voice-v9; `FULL_PERSONAPLEX_NO_EDGE_FEB13_2026.md`, `TEST_VOICE_LOCAL_FIX_MAR10_2026.md`

## Overview

This document maps the current live voice path end-to-end, identifies duplication and divergence risks, and establishes the authoritative v9 migration baseline for the MYCA Voice Suite v9 plan.

---

## 1. Live Voice Path (Current Implementation)

### 1.1 End-to-End Flow

```
User speaks
    ↓
Browser SpeechRecognition (test-voice page)
    ↓
Transcript produced
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PARALLEL PATHS (duplication risk)                                    │
├─────────────────────────────────────────────────────────────────────┤
│ Path A: Page → Bridge WebSocket                                      │
│   ws.send({ type: "user_transcript", text })                         │
│   → Bridge receives JSON with "text"                                 │
│   → clone_to_mas_memory() → process_with_mas_brain()                 │
│   → POST MAS /voice/brain/chat                                       │
│   → Brain response → Moshi TTS (0x02+text) + frontend mas_event      │
├─────────────────────────────────────────────────────────────────────┤
│ Path B: Page → cloneTextToMAS()                                      │
│   POST /api/test-voice/mas/orchestrator-chat                         │
│   → MAS /voice/orchestrator/chat                                     │
│   → Memory writes, tool calls, agent invocations, injection queue    │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Inventory

| Component | Path | Port | Role |
|-----------|------|------|------|
| **test-voice page** | `WEBSITE/website/app/test-voice/page.tsx` | — | Browser UI; SpeechRecognition STT; WebSocket to Bridge; cloneTextToMAS to orchestrator |
| **PersonaPlex Bridge** | `MAS/services/personaplex-local/personaplex_bridge_nvidia.py` | 8999 | WebSocket bridge; receives user_transcript JSON; clone_to_mas_memory → process_with_mas_brain; sends to Moshi TTS |
| **Moshi** | `scripts/start_voice_system.py` / Moshi server | 8998 | TTS only (in current MYCA Brain mode); receives 0x02+text for synthesis |
| **MAS Brain API** | `mycosoft_mas/core/routers/brain_api.py` | 8001 | `POST /voice/brain/chat`; memory-integrated brain; tool pipeline |
| **MAS Voice Orchestrator** | `mycosoft_mas/core/routers/voice_orchestrator_api.py` | 8001 | `POST /voice/orchestrator/chat`; tool usage, memory, agents, n8n |

### 1.3 Website API Routes (test-voice)

| Route | Proxies To | Purpose |
|-------|------------|---------|
| `/api/test-voice/diagnostics` | Bridge health + Moshi port | Diagnostics with TCP fallback |
| `/api/test-voice/bridge/health` | `http://localhost:8999/health` | Bridge health |
| `/api/test-voice/bridge/session` | Bridge session proxy | Session lifecycle |
| `/api/test-voice/mas/orchestrator-chat` | MAS `POST /voice/orchestrator/chat` | cloneTextToMAS target |
| `/api/test-voice/mas/myca-status` | MAS status | MYCA status |
| `/api/test-voice/mas/memory-health` | MAS memory | Memory health |
| `/api/test-voice/mas/voice-session/create` | MAS voice session | Session creation |
| `/api/test-voice/mas/voice-session/[sessionId]/end` | MAS end session | End session |

### 1.4 STT Source: Browser vs Moshi

- **Intended architecture** (per `FULL_PERSONAPLEX_NO_EDGE_FEB13_2026.md`): Moshi STT → MAS Brain → Moshi TTS.
- **Actual implementation**: Browser `SpeechRecognition` produces transcript; user text is sent via `user_transcript` JSON to the Bridge. Moshi is used for TTS only in MYCA Brain mode.
- Bridge does **not** send user audio to Moshi when in MYCA Brain mode; transcript comes from the page.

---

## 2. Duplication and Divergence Risks

### 2.1 Duplicate MAS Calls

For each user turn, both paths hit MAS:

1. **Bridge** → `clone_to_mas_memory()` → `process_with_mas_brain()` → `POST /voice/brain/chat`
2. **Page** → `cloneTextToMAS()` → `POST /api/test-voice/mas/orchestrator-chat` → `POST /voice/orchestrator/chat`

**Risks:**
- Duplicate memory writes for the same user message
- Divergent conversation state (Brain vs Orchestrator each maintain their own context)
- Tool calls may fire from both paths
- Persona bleed if assistant speech sources are ambiguous

### 2.2 cloneTextToMAS vs Bridge Responsibility

- `cloneTextToMAS` provides: memory_stats, tool_calls, agents_invoked, injection queue (e.g. `inject_to_moshi`).
- Bridge's `process_with_mas_brain` provides: Brain response text, TTS output, mas_event to frontend.
- Both can trigger memory and tools; the page uses orchestrator for tool injection while the Bridge uses Brain for the primary reply.

---

## 3. Authoritative v9 Migration Baseline

### 3.1 Decision: Bridge + Brain as Single Voice Authority

**For the v9 migration**, the authoritative baseline is:

| Authority | Component | MAS Endpoint | Role |
|-----------|-----------|--------------|------|
| **Primary** | PersonaPlex Bridge | `POST /voice/brain/chat` | Single source for voice responses; memory, tools, and TTS flow through Brain |
| **Deprecate for voice** | Page `cloneTextToMAS` | `POST /voice/orchestrator/chat` | Remove or gate so it does NOT fire for transcript already flowing through Bridge |

**Rationale:**
- The Bridge is the natural convergence point: it receives user_transcript, calls MAS Brain, and drives TTS. Making it the single authority eliminates duplicate memory writes.
- The Brain API is memory-integrated and has tool pipeline; it is sufficient for voice turns.
- The Orchestrator is heavier (agents, n8n, full planning); for low-latency voice, Brain is preferred.

### 3.2 Baseline Codification

1. **Bridge** remains the sole component that invokes MAS for live voice responses.
2. **Page** should NOT call `cloneTextToMAS` when the transcript is sent to the Bridge via WebSocket. Either:
   - Remove `cloneTextToMAS` for voice turns entirely, OR
   - Add a flag (e.g. `transcript_sent_to_bridge`) so cloneTextToMAS is skipped when Bridge is handling the turn.
3. **STT**: Keep browser SpeechRecognition as the supported dev path for v9 Phase 0; plan Moshi STT restoration as a later phase once the single-rail is stable.

### 3.3 Observability Recommendations

Add explicit observability around:

- **Transcript origin**: Log whether transcript came from Browser STT or (future) Moshi STT.
- **MAS clone calls**: Log when Bridge invokes `/voice/brain/chat`; log when page invokes orchestrator-chat (and ideally reduce to zero for voice).
- **Bridge replies**: Trace latency from user_transcript received to mas_event sent.
- **TTS source**: Ensure all assistant speech flows from Brain response → Bridge → Moshi; no alternate TTS paths.

---

## 4. Health and Diagnostics Alignment

Per `TEST_VOICE_LOCAL_FIX_MAR10_2026.md`:
- With `NEXT_PUBLIC_USE_LOCAL_GPU=true`, Bridge/Moshi use localhost 8998/8999.
- Diagnostics use TCP fallback when HTTP health times out.
- Test-voice page uses `ws://localhost:8999` when local GPU is enabled.

**Reconciliation:** The v9 migration should preserve these local voice assumptions. The diagnostics routes under `app/api/test-voice/*` remain valid for v9 Phase 0.

---

## 5. Files to Reference for v9 Implementation

| Purpose | File |
|---------|------|
| test-voice page | `WEBSITE/website/app/test-voice/page.tsx` |
| PersonaPlex Bridge | `MAS/services/personaplex-local/personaplex_bridge_nvidia.py` |
| Brain API | `MAS/mycosoft_mas/core/routers/brain_api.py` |
| Voice Orchestrator | `MAS/mycosoft_mas/core/routers/voice_orchestrator_api.py` |
| Duplex/session | `MAS/mycosoft_mas/consciousness/duplex_session.py` |
| MDP contracts | `docs/MDP_PROTOCOL_CONTRACTS_MAR07_2026.md` |
| Mycorrhizae telemetry (future) | `docs/MYCORRHIZAE_MYCA_TELEMETRY_BRIDGE_MAR07_2026.md` |

---

## 6. Next Steps (Plan Phases)

- **Phase 0 (complete)**: This baseline audit.
- **Phase 1**: Add `voice_v9` backend package; implement v9 schemas, services, routers, WebSocket contracts.
- **Phase 2+**: Normalized event rail, duplex/persona, test-voice UI refactor, deployment topology.

## Related Documents

- [FULL_PERSONAPLEX_NO_EDGE_FEB13_2026.md](./FULL_PERSONAPLEX_NO_EDGE_FEB13_2026.md)
- [TEST_VOICE_LOCAL_FIX_MAR10_2026.md](./TEST_VOICE_LOCAL_FIX_MAR10_2026.md)
- [MDP_PROTOCOL_CONTRACTS_MAR07_2026.md](./MDP_PROTOCOL_CONTRACTS_MAR07_2026.md)
- [MYCA_FULL_SYSTEM_RUNTIME_PROMOTION_COMPLETE_MAR06_2026.md](./MYCA_FULL_SYSTEM_RUNTIME_PROMOTION_COMPLETE_MAR06_2026.md)
