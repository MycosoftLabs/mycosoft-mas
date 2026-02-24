# MYCA Search AI Route

**Component**: Website API route for search AI  
**Status**: Implemented

## Location

- WEBSITE/website/app/api/search/ai/route.ts

## Behavior

- Model routing: fast, quality, reasoning
- Full search context forwarded to MAS
- Proxies to MAS_API_URL/api/myca/chat or voice/brain/chat
- Records intention via POST /api/myca/intention

## Request Body

query, session_id, conversation_id, user_id, context, model

## Response

message, nlqData, nlqActions, nlqSources, metadata

## Fallback Chain

1. MAS Consciousness/Brain
2. Local knowledge base if MAS unavailable
