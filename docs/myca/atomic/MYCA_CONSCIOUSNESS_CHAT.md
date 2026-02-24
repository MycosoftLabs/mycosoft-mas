# MYCA Consciousness Chat API

**Component**: MAS API for MYCA chat (consciousness-backed)  
**Status**: Implemented

## Location

- mycosoft_mas/core/routers/consciousness_api.py
- Prefix: /api/myca

## Endpoints

- POST /api/myca/chat - Chat with MYCA consciousness
- GET /api/myca/status - Consciousness status
- POST /api/myca/awaken - Wake consciousness

## Request (ChatRequest)

message, session_id, user_id, context, stream

## Response (ChatResponse)

message, session_id, emotional_state, thoughts_processed, timestamp

## Website Proxy

app/api/myca/query/route.ts proxies to MAS /api/myca/chat. Uses MAS_API_URL from env.
