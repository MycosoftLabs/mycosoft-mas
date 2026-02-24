# MYCA Sync API

**Component**: Conversation save/restore, MAS sync  
**Status**: Implemented

## Location

- `WEBSITE/website/app/api/myca/sync/route.ts`
- `WEBSITE/website/app/api/myca/conversations/route.ts` (if present)
- `contexts/myca-context.tsx` – restoreFromMAS, syncToMAS

## Endpoints

- `POST /api/myca/sync` – Save conversation to MAS
- `GET /api/myca/conversations` – List/load conversations

## Storage

- localStorage: `myca_messages:{userId}`, `myca_conversation_id:{userId}`
- MAS: via `/api/myca/sync` backend
