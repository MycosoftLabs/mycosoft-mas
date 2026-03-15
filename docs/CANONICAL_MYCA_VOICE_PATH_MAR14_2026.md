# Canonical MYCA Realtime Voice Path — Mar 14, 2026

**Status:** Locked  
**Related:** Nemotron MYCA Rollout plan, PersonaPlex bridge, Brain API, test-voice page

## Single authoritative path

The **only** low-latency realtime MYCA voice path is:

```
Browser (mic) → PersonaPlex Bridge → MAS Brain API → response (text/stream)
```

- **PersonaPlex Bridge** (`services/personaplex-local/personaplex_bridge_nvidia.py`) is the single entry for full-duplex voice. It sends user speech to MAS and receives MYCA responses.
- **MAS Brain API** (`POST /voice/brain/chat` and `POST /voice/brain/stream`) is the single backend contract for MYCA’s memory-aware, tool-capable responses. Implemented in `mycosoft_mas/core/routers/brain_api.py`.

All other voice or “MYCA response” entry points must **adapt to this contract** (i.e. call the same MAS Brain API) and must not implement a competing path to another LLM or workflow.

## Backend contract (MAS Brain)

- **Endpoint:** `POST {MAS_ORCHESTRATOR_URL}/voice/brain/chat`
- **Request body (BrainChatRequest):**
  - `message` (required): user message
  - `session_id` (optional): voice/chat session ID
  - `conversation_id` (optional): conversation thread ID
  - `user_id` (required): user identifier
  - `history` (optional): list of `{role, content}` for conversation history
  - `provider` (optional): `"auto"` | `"gemini"` | `"claude"` | `"openai"`
  - `include_memory_context` (optional): include recalled memories (default true)
- **Response (BrainChatResponse):** `response`, `provider`, `session_id`, `conversation_id`, `memory_context`, `actions_taken`, `timestamp`

Callers (bridge, website orchestrator, or any future client) must use this contract so that memory, tools, and model routing stay consistent.

## Who uses this path

| Consumer | Role | How it uses the path |
|----------|------|----------------------|
| **PersonaPlex Bridge** | Primary realtime voice | POSTs to `/voice/brain/chat` with message, session_id, conversation_id, user_id, context (source: personaplex_voice). Full-duplex controls (barge-in, VAD) live in the bridge/session layer. |
| **Website voice orchestrator** | Adapter for non-WebSocket voice | `app/api/mas/voice/orchestrator/route.ts` uses the **same** MAS Brain endpoint as Phase 1. No separate “consciousness” or LLM path for voice; it proxies to `/voice/brain/chat`. Fallbacks (e.g. consciousness API or frontier LLMs) only when Brain is unavailable. |
| **test-voice page** | Frontend | Connects to PersonaPlex Bridge (WebSocket) or uses orchestrator; both ultimately go through Bridge → Brain or Orchestrator → Brain. |

## Full-duplex semantics

- **Barge-in, interrupt, VAD, streaming:** Handled in the **bridge and session layer** (`duplex_session.py`, bridge WebSocket), not in the website orchestrator.
- The Brain API is request/response (or stream); the bridge turns that into full-duplex by managing session state, cancellation, and TTS/ASR.

## Out of scope for this path

- **Chat UI (non-voice):** May use `/api/myca/chat` or other MAS routes; those are not the canonical **voice** path and may be refactored later to also call the Brain for consistency.
- **n8n Master Brain / Speech workflows:** Not part of the canonical realtime voice path; they are separate automation entry points.

## References

- Plan: Nemotron 3 Integration for MYCA and AVANI (canon-voice-path todo)
- Bridge: `services/personaplex-local/personaplex_bridge_nvidia.py` — `query_mas_brain()`, `MYCA_BRAIN_URL`
- Brain API: `mycosoft_mas/core/routers/brain_api.py` — `BrainChatRequest`, `POST /chat`
- Orchestrator: `WEBSITE/website/app/api/mas/voice/orchestrator/route.ts` — `callMasBrain()`, `getMycaResponse()`
- Duplex session: `mycosoft_mas/consciousness/duplex_session.py`
