# MYCA Query (NatureOS)

**Component**: NatureOS-compatible MYCA query routing  
**Status**: Implemented

## Location

- `WEBSITE/website/app/api/myca/query/route.ts`
- NatureOS: `website-integration/api/myca-query.ts` (when present)

## Behavior

- When on mycosoft.com or localhost: uses `/api/myca/query` (website MAS proxy)
- When on Azure NatureOS: uses Azure MYCA endpoint
- Proxies to `MAS_API_URL/api/myca/chat`

## Request

- `message`, `session_id`, `conversation_id`, `user_id`, `context`
