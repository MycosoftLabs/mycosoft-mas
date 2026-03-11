# Voice v9 Duplex and Persona Lock — Complete (Mar 2, 2026)

**Status:** Complete  
**Related plan:** myca-voice-v9 (Phase 4: Duplex and Interruptibility; Phase 3: Grounding and Persona Enforcement)

## Summary

Implemented the duplex interrupt manager and persona lock integration for the Voice v9 suite. MYCA stays responsive via barge-in and remains identity-safe through persona-locked text before TTS.

## Implemented

### InterruptManager

- **Path:** `mycosoft_mas/voice_v9/services/interrupt_manager.py`
- Wraps `DuplexSession` for v9 integration.
- Supports: barge-in, TTS pause/duck, interrupted draft preservation.
- Cached per session via `get_interrupt_manager(session_id)` / `release_interrupt_manager(session_id)`.
- `request_barge_in(user_input)` — manual trigger (e.g., when browser STT detects user speech).
- `on_audio(audio_chunk)` — VAD-based barge-in (returns True if triggered).
- `get_interrupt_state()` — returns `InterruptState` for API/UI.
- `set_tts_callbacks(send_tts, stop_tts)` — wires TTS for Moshi/PersonaPlex.
- Lifecycle: `voice_gateway.end_session()` calls `release_interrupt_manager()`.

### PersonaLockService

- **Path:** `mycosoft_mas/voice_v9/services/persona_lock_service.py`
- Validates and rewrites outgoing speech for MYCA identity.
- `apply(session_id, text)` → `PersonaLockResult` (locked text, was_rewritten, drift_detected, etc.).
- `get_state(session_id)` → `PersonaState` (rewrite_count, last_rewrite_reason, drift_detected).
- Regex-based persona bleed detection (e.g., "I'm an AI" → "I'm MYCA").
- Singleton via `get_persona_lock_service()`.

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/voice/v9/sessions/{session_id}/interrupt` | GET | Interrupt/duplex state |
| `/api/voice/v9/sessions/{session_id}/interrupt/barge-in` | POST | Trigger barge-in (body: `{ "user_input": "..." }`) |
| `/api/voice/v9/sessions/{session_id}/persona` | GET | Persona lock state |
| `/api/voice/v9/sessions/{session_id}/persona/apply` | POST | Apply persona lock to text (body: `{ "text": "..." }`) |

### WebSocket Messages

| Client sends | Server responds |
|--------------|-----------------|
| `{ "type": "get_interrupt", "session_id": "..." }` | `{ "type": "interrupt_state", ... }` |
| `{ "type": "barge_in", "session_id": "...", "user_input": "..." }` | `{ "type": "barge_in_acked" }` |
| `{ "type": "get_persona", "session_id": "..." }` | `{ "type": "persona_state", ... }` |

## Integration Points

- **DuplexSession:** `create_duplex_session()` from `mycosoft_mas/consciousness/duplex_session.py` (lines 513–544).
- **VoiceGateway:** `end_session()` releases `InterruptManager` so no orphan managers.
- **test-voice UI:** Will consume interrupt/persona state via v9 WebSocket and REST in Phase 5.

## Verification

- REST: `GET http://localhost:8001/api/voice/v9/sessions/{session_id}/interrupt` (requires valid session).
- REST: `POST .../persona/apply` with `{ "text": "I'm an AI" }` → returns `was_rewritten: true` and rewritten text.
- WebSocket: Connect to `/ws/voice/v9`, create session, then send `get_interrupt` / `get_persona` / `barge_in`.

## Next Steps

- Phase 5: Refactor `test-voice` page into v9 diagnostics console (SessionHeader, AudioControls, LiveTranscriptPane, EventPane, MASPane, LatencyPane, PersonaPane, SyncPane).
- Wire persona lock into `conversation_cortex` response path and immediately before TTS in the full v9 pipeline.
