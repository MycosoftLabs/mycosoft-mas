# MYCA Memory-Brain Integration - February 5, 2026

## Overview

This document describes the integration of MYCA's memory system with the brain (LLM response generation) for PersonaPlex voice interactions. The goal is to ensure MYCA's responses are informed by and contribute to the memory system.

## Architecture

### Components Created/Modified

1. **`mycosoft_mas/llm/memory_brain.py`** (NEW)
   - `MYCAMemoryBrain` class - Memory-aware wrapper around FrontierLLMRouter
   - `MemoryAwareContext` dataclass - Extended context with memory fields
   - `get_memory_brain()` - Singleton factory function

2. **`mycosoft_mas/core/routers/brain_api.py`** (NEW)
   - REST API endpoints for the memory-integrated brain
   - `POST /voice/brain/chat` - Non-streaming response
   - `POST /voice/brain/stream` - SSE streaming response
   - `GET /voice/brain/status` - Brain health and status
   - `GET /voice/brain/context/{user_id}` - Get memory context
   - `POST /voice/brain/event` - Record significant events

3. **`mycosoft_mas/core/routers/voice_orchestrator_api.py`** (MODIFIED)
   - Added memory brain as fallback after n8n workflows
   - Updated `_generate_response()` to use memory brain
   - Fallback chain: n8n workflow -> Memory Brain -> Local responses

### Data Flow

`
User speaks -> PersonaPlex/Moshi -> Bridge -> MAS Voice Orchestrator
                                                       |
                                                       v
                                            1. Try n8n workflow
                                                       |
                                            2. Try Memory Brain
                                               - Load user profile
                                               - Recall semantic memories
                                               - Get recent episodes
                                               - Inject context into prompt
                                               - Route to Gemini/Claude/GPT-4
                                               - Store conversation turn
                                               - Learn user facts
                                                       |
                                            3. Fallback to local responses
                                                       |
                                                       v
                                               Response -> Bridge -> Moshi TTS
`

## Memory Integration Features

### Pre-Response Memory Loading

When MYCA receives a message, the Memory Brain:

1. **Loads User Profile** - Preferences, name, last interaction time
2. **Recalls Semantic Memories** - Relevant facts via vector similarity search
3. **Gets Recent Episodes** - Significant events in recent history
4. **Gets Voice Context** - Previous voice session summaries and topics

### Memory-Enhanced Prompt

The loaded memory is formatted and injected into the LLM context:

`
=== USER PREFERENCES ===
- communication_style: casual
- topics_of_interest: mycology, AI

=== RELEVANT MEMORIES ===
- User prefers detailed technical explanations
- Previous discussion about MINDEX database

=== RECENT EVENTS ===
- Successfully deployed PersonaPlex v8.0.0
- Voice session with 15 turns completed
`

### Post-Response Memory Storage

After generating a response, the Memory Brain:

1. **Stores Conversation Turn** - Both user message and assistant response
2. **Learns User Facts** - Extracts preferences, name, workplace from user input
3. **Records Significant Events** - Tool executions, agent invocations

## API Endpoints

### Brain Chat (Non-Streaming)

`ash
POST /voice/brain/chat
Content-Type: application/json

{
  "message": "Tell me about MINDEX",
  "session_id": "optional-session-id",
  "conversation_id": "optional-conv-id",
  "user_id": "morgan",
  "provider": "auto"
}
`

Response:
`json
{
  "response": "MINDEX is our fungal knowledge graph...",
  "provider": "gemini",
  "session_id": "xxx",
  "conversation_id": "yyy",
  "memory_context": {
    "memories": [...],
    "episodes": [...],
    "profile": {...}
  }
}
`

### Brain Stream (SSE)

`ash
POST /voice/brain/stream
`

Returns Server-Sent Events with token streaming.

### Brain Status

`ash
GET /voice/brain/status
`

Returns health, provider availability, and memory stats.

## Configuration

### Environment Variables

- `GEMINI_API_KEY` - Google Gemini API key (recommended)
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key
- `N8N_WEBHOOK_URL` - n8n webhook base URL

### Memory Settings

In `MYCAMemoryBrain`:
- `max_recalled_memories = 5` - Max semantic memories to load
- `max_recent_episodes = 3` - Max recent episodes to include
- `memory_relevance_threshold = 0.5` - Minimum similarity score

## Testing

### Health Check

`ash
curl http://192.168.0.188:8001/voice/brain/health
`

### Test Chat

`ash
curl -X POST http://192.168.0.188:8001/voice/brain/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Who are you?", "user_id": "morgan"}'
`

### Memory Context

`ash
curl http://192.168.0.188:8001/voice/brain/context/morgan?query=mycology
`

## Integration with PersonaPlex Bridge

The PersonaPlex Bridge (`personaplex_bridge_nvidia.py`) can now:

1. Call `POST /voice/brain/chat` for memory-aware responses
2. Receive responses that incorporate user preferences and history
3. Contribute to memory through conversation turn persistence

## Fallback Chain

The voice orchestrator now has a three-tier fallback:

1. **n8n Workflow** - `myca-brain-v2` workflow (if configured)
2. **Memory Brain** - Gemini/Claude/GPT-4 with memory context
3. **Local Responses** - Pattern-matched MYCA identity responses

This ensures MYCA always responds, even if external services are unavailable.

## Memory Layer Usage

| Layer | Storage | Purpose |
|-------|---------|---------|
| Ephemeral | In-memory | Current turn context |
| Session | Redis | Active conversation |
| Working | Redis | Multi-session tasks |
| Semantic | Qdrant | Long-term facts |
| Episodic | PostgreSQL | Significant events |
| System | Redis | MYCA configuration |

## Next Steps

1. [ ] Add voice tone/emotion detection for context
2. [ ] Implement conversation summarization at session end
3. [x] Add memory search UI in dashboard - See [MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md](./MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md)
4. [ ] Integrate with n8n for memory-based workflow triggers
5. [ ] Add memory pruning for old/irrelevant content

## Files Modified

- `mycosoft_mas/llm/memory_brain.py` - NEW
- `mycosoft_mas/core/routers/brain_api.py` - NEW
- `mycosoft_mas/core/routers/voice_orchestrator_api.py` - MODIFIED
- `mycosoft_mas/core/myca_main.py` - Already includes brain_router

## Version

- Memory Brain: 1.0.0
- Voice Orchestrator: 2.1.0-memory-brain
- PersonaPlex Bridge: 8.0.0

---

*MYCA Memory-Brain Integration - February 5, 2026*
*Mycosoft Multi-Agent System*
