# Speech Duplex Migration — Backend-Owned ASR/TTS Preserving Full Duplex

**Date:** March 14, 2026  
**Status:** Definition (implementation reference for Nemotron MYCA/AVANI integration)  
**Related:** `nemotron_myca_rollout_8469ab79.plan.md` §5, PersonaPlex bridge, `duplex_session.py`, `test-voice` page

---

## 1. Current State

- **PersonaPlex Bridge** (`services/personaplex-local/personaplex_bridge_nvidia.py`): Canonical realtime path is Browser → Bridge → MAS Brain. Bridge connects to **Moshi** (STT + TTS) on GPU node (e.g. 192.168.0.190:8998). User mic → Moshi STT → MAS Brain → response text → Moshi TTS → speaker. Barge-in is implemented via VAD and a stop signal to Moshi (close/reopen or interrupt byte).
- **TTS fallback** (`tts_fallback.py`): When Moshi does not support text→TTS (kind 0x02), **edge-tts** is used (browser/cloud); output is converted to Opus and sent to the client. This path is **not** interruptible in the same way as Moshi; it is batch synthesis.
- **DuplexSession** (`consciousness/duplex_session.py`): Holds ConversationController, SpeechPlanner, VAD, barge-in cooldown, and cancellation. Full-duplex behavior (listen while speaking, barge-in) lives in the bridge/session layer.
- **test-voice** (`website/app/test-voice/page.tsx`): Client for MYCA voice; expects WebSocket protocol with Opus and control messages. Parity for latency, barge-in, and session continuity is the gate for retiring legacy paths.

---

## 2. Goal

Define the migration from **Moshi- and browser-dependent** speech (STT/TTS) to **backend-owned, interruptible** ASR/TTS while **preserving PersonaPlex full duplex**: same barge-in semantics, VAD, session continuity, and single canonical path (bridge → MAS brain).

---

## 3. Backend-Owned ASR/TTS — Contract

### 3.1 Semantics

- **ASR (Speech-to-Text):** A backend service that accepts **streaming audio** (e.g. WebSocket or chunked HTTP) and returns **streaming or incremental transcripts**. It must support **cancel/interrupt**: when the client or bridge sends an interrupt (e.g. user started speaking), the service stops returning results for the current utterance and can optionally flush or start a new utterance.
- **TTS (Text-to-Speech):** A backend service that accepts **text** (or streaming text) and returns **streaming audio** (e.g. Opus chunks at 24 kHz mono, 20 ms frames to match current client). It must support **interrupt**: when the client or bridge sends a stop signal (barge-in), the service **stops generating and streaming** immediately and does not continue to send buffered audio for the current response.

### 3.2 Interruptible Streaming Requirements

| Requirement | ASR | TTS |
|-------------|-----|-----|
| Input | Streaming audio (e.g. WebSocket binary) | Text or streaming text |
| Output | Streaming/incremental transcript | Streaming audio (Opus or PCM→Opus) |
| Cancel/Interrupt | API or message to cancel current utterance | API or message to stop current synthesis and flush |
| Latency | Low enough for real-time turn-taking (e.g. &lt; 300 ms first token) | First audio chunk as soon as possible; chunked to allow interrupt between chunks |
| Session | Optional session id for context (e.g. speaker adaptation) | Optional voice/session id |

### 3.3 Where Backend Services Run

- **Preferred:** GPU node (192.168.0.190) for low-latency ASR/TTS, colocated with PersonaPlex bridge when the bridge runs there, or same network as the bridge so that bridge ↔ ASR/TTS latency is minimal.
- **Alternative:** MAS VM (188) or a dedicated speech VM if GPU is not required for the chosen models (e.g. smaller Nemotron speech models or cloud-backed ASR/TTS with streaming).

---

## 4. Three-Phase Migration

### Phase 1 — Nemotron brain, keep Moshi speech (current)

- **Done in plan:** Canonical path is bridge → MAS brain; response generation is Nemotron-backed via unified LLM routing.
- **Speech:** No change. Keep **Moshi** for STT and TTS. Keep **edge-tts** as fallback when Moshi does not support text-injection.
- **Full duplex:** Preserved by existing bridge + DuplexSession (VAD, barge-in, stop Moshi TTS on interrupt).
- **Gate:** test-voice works with Nemotron brain and existing Moshi/edge-tts.

### Phase 2 — Backend-owned ASR/TTS with interruptible streaming

- **Introduce** backend ASR and TTS services that implement the contract above (streaming in/out, interrupt/cancel).
- **Bridge changes:**
  - Option A: Bridge sends mic audio to **backend ASR** instead of Moshi; receives streaming transcript; sends transcript to MAS brain; receives response text; sends text to **backend TTS**; streams audio to client. On barge-in: send interrupt to ASR and TTS; cancel in-flight TTS and clear pipeline.
  - Option B: Keep Moshi as one implementation of “backend ASR/TTS” (Moshi already runs on GPU node and is used by the bridge); add a **second** implementation (e.g. Nemotron speech or another model) behind the same **abstract** ASR/TTS interface so the bridge can swap without changing duplex logic.
- **DuplexSession / ConversationController:** Unchanged. Barge-in still triggers “stop playback” and “cancel current response”; the only change is that “stop playback” calls the new TTS service’s interrupt API and “cancel” may also notify ASR to reset.
- **Fallback:** If backend TTS is unavailable, keep edge-tts fallback but document that edge-tts path is **not** fully interruptible (best-effort stop after current chunk).
- **Gate:** test-voice demonstrates parity: latency, barge-in, and session continuity with backend ASR/TTS enabled.

### Phase 3 — Retire legacy paths

- **After** test-voice proves parity (latency, barge-in, session continuity) with backend-owned ASR/TTS:
  - Deprecate direct Moshi STT/TTS from the bridge (or keep as optional fallback if Moshi remains available).
  - Deprecate edge-tts fallback for production MYCA voice, or keep only for non-voice routes (e.g. accessibility TTS) where interrupt is not required.
- **Documentation:** Update voice docs and SYSTEM_REGISTRY to state that the canonical voice path uses backend ASR/TTS with interruptible streaming; list retired components.

---

## 5. What Must Be Preserved (Full Duplex)

- **Barge-in:** User can interrupt MYCA while she is speaking; current TTS stops, new user turn is processed.
- **VAD:** Voice activity detection so that “user started speaking” is detected and converted to an interrupt signal.
- **Session continuity:** ConversationController and DuplexSession state (e.g. turn-taking, cooldown) remain so that back-to-back turns and barge-in do not break the session.
- **Single canonical path:** Browser → PersonaPlex Bridge → MAS Brain (and Bridge → ASR/TTS as backend services). No second, competing voice path that bypasses the bridge or duplex logic.

---

## 6. Implementation Notes

- **Bridge:** Refactor so that “STT source” and “TTS sink” are **pluggable** (e.g. Moshi adapter vs Nemotron ASR/TTS adapter). Same DuplexSession and barge-in logic drive both.
- **Protocol:** Define a minimal **backend speech API** (e.g. WebSocket or HTTP with chunked upload/streaming download) so that any backend ASR/TTS service can be wired in if it implements interrupt and streaming.
- **Testing:** Add regression tests for barge-in (interrupt TTS mid-stream), latency (time to first transcript and first audio chunk), and session continuity (multiple turns and one barge-in).

---

## 7. Risks and Open Points

- **Nemotron speech availability:** Nemotron 3 may include ASR/TTS; confirm model names, APIs, and whether they support streaming and interrupt. If not, another backend model (e.g. NeMo, or a cloud ASR/TTS with streaming) must satisfy the contract.
- **edge-tts:** Truly “interruptible” TTS on the backend may require a different stack (e.g. streaming TTS that can be stopped per request); edge-tts is pull-based and not designed for mid-stream stop.
- **Latency:** Backend ASR/TTS must meet latency budgets so that full duplex still feels natural; measure on 190 (or target host) before committing Phase 2.

---

**Next:** Implement Phase 2 when backend ASR/TTS services are available; run test-voice parity checks; then execute Phase 3 and update registries/docs.
