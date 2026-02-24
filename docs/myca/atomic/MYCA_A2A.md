# MYCA A2A Gateway

**Component**: Agent-to-agent protocol gateway  
**Status**: Implemented

## Location

- `mycosoft_mas/core/routers/a2a_api.py`
- Website: `app/api/myca/a2a/agent-card/route.ts`, `app/api/myca/a2a/message/send/route.ts`

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/myca/a2a/agent-card` | Agent Card (skills, capabilities) |
| `POST /api/myca/a2a/message/send` | Send message to agent |

## Skills (Agent Card)

- `myca_search` – Execute search via SearchAgent
- `myca_nlq` – Route NLQ to SearchAgent/Metabase/MINDEX
- `orchestration`, `voice-chat`, `search`
