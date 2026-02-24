# MYCA Brain API

**Component**: Memory-integrated brain for chat and streaming  
**Status**: Implemented

## Location

- `mycosoft_mas/core/routers/brain_api.py`
- Prefix: `/voice/brain`

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/voice/brain/chat` | POST | Non-streaming brain response |
| `/voice/brain/stream` | POST | Streaming (SSE) brain response |
| `/voice/brain/status` | GET | Brain status and providers |
| `/voice/brain/context` | GET | Memory context for user/conversation |

## Request (BrainChatRequest)

- `message`, `session_id`, `conversation_id`, `user_id`, `history`, `provider`, `include_memory_context`

## Provider Routing

- `auto`, `gemini`, `claude`, `openai`

## Website Usage

- `app/api/search/ai/route.ts` and `app/api/search/ai/stream/route.ts` proxy to MAS
