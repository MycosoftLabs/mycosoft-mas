# MYCA Search AI Stream

**Component**: Website API route for streaming search AI  
**Status**: Implemented

## Location

- WEBSITE/website/app/api/search/ai/stream/route.ts

## Behavior

- Proxies to MAS POST /voice/brain/stream
- Passes session_id, conversation_id, context
- SSE response for streaming tokens
- Records intention after stream completes

## Request Body

message, session_id, conversation_id, user_id, context

## Usage

AIWidget uses stream when available for real-time display.
