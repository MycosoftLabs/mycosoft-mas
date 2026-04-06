# Website MYCA/MAS Proxy Route Inventory — MAR31 2026

Date: 2026-03-31  
Status: Active inventory for Nemotron migration waves

## Purpose

Route-level inventory for website proxy/API paths that can be impacted by Nemotron routing, fallback behavior, streaming contract changes, and latency shifts.

## MYCA Website API Surface (`app/api/myca/**`)

Primary routes:

- `app/api/myca/route.ts`
- `app/api/myca/query/route.ts`
- `app/api/myca/nlq/route.ts`
- `app/api/myca/intention/route.ts`
- `app/api/myca/brain/stream/route.ts`
- `app/api/myca/runs/route.ts`
- `app/api/myca/conversations/route.ts`

Consciousness routes:

- `app/api/myca/consciousness/chat/route.ts`
- `app/api/myca/consciousness/status/route.ts`
- `app/api/myca/consciousness/world/route.ts`
- `app/api/myca/consciousness/awaken/route.ts`
- `app/api/myca/consciousness/soul/route.ts`
- `app/api/myca/consciousness/emotions/route.ts`
- `app/api/myca/consciousness/identity/route.ts`

Grounding/activity/a2a:

- `app/api/myca/grounding/route.ts`
- `app/api/myca/grounding/status/route.ts`
- `app/api/myca/grounding/thoughts/route.ts`
- `app/api/myca/grounding/ep/[id]/route.ts`
- `app/api/myca/activity/route.ts`
- `app/api/myca/activity/stream/route.ts`
- `app/api/myca/a2a/agent-card/route.ts`
- `app/api/myca/a2a/message/send/route.ts`

Other integration routes:

- `app/api/myca/workflows/route.ts`
- `app/api/myca/world/route.ts`
- `app/api/myca/connectivity/route.ts`
- `app/api/myca/reflection/route.ts`
- `app/api/myca/training/route.ts`
- `app/api/myca/sync/route.ts`
- `app/api/myca/connection-proposal/route.ts`
- `app/api/myca/thoughts/route.ts`

## MAS Website API Surface (`app/api/mas/**`)

Core MAS proxy routes:

- `app/api/mas/chat/route.ts`
- `app/api/mas/brain/query/route.ts`
- `app/api/mas/memory/route.ts`
- `app/api/mas/agents/route.ts`
- `app/api/mas/agents/[id]/route.ts`
- `app/api/mas/health/route.ts`
- `app/api/mas/world/[[...path]]/route.ts`
- `app/api/mas/topology/route.ts`
- `app/api/mas/connections/route.ts`
- `app/api/mas/orchestrator/action/route.ts`

Voice-sensitive routes:

- `app/api/mas/voice/route.ts`
- `app/api/mas/voice/confirm/route.ts`
- `app/api/mas/voice/sessions/route.ts`
- `app/api/mas/voice/duplex/session/route.ts`
- `app/api/mas/voice/orchestrator/route.ts`

Registry/ops/finance/commerce:

- `app/api/mas/registry/apis/route.ts`
- `app/api/mas/registry/systems/route.ts`
- `app/api/mas/notifications/route.ts`
- `app/api/mas/csuite/finance/status/route.ts`
- `app/api/mas/documents/search/route.ts`
- `app/api/mas/commerce/quote/route.ts`
- `app/api/mas/commerce/checkout/route.ts`
- `app/api/mas/mycobrain/route.ts`
- `app/api/mas/raas/worldstate/balance/route.ts`
- `app/api/mas/raas/worldstate/usage/route.ts`
- `app/api/mas/myca2-psilo/start/route.ts`
- `app/api/mas/myca2-psilo/session/[sessionId]/route.ts`
- `app/api/mas/myca2-psilo/session/[sessionId]/edge/route.ts`
- `app/api/mas/myca2-psilo/session/[sessionId]/stop/route.ts`
- `app/api/mas/myca2-psilo/session/[sessionId]/kill/route.ts`

## Per-Route Nemotron Compatibility Checks

Apply this matrix to all routes above:

1. **Payload contract**
   - Inputs unchanged when backend switches (`question`/`message`, context fields, session IDs).

2. **Response contract**
   - Required fields preserved for UI consumers even if MAS returns variant envelopes.

3. **Streaming compatibility**
   - SSE headers and event framing preserved (`Content-Type: text/event-stream`).

4. **Latency budget**
   - Corporate/user-facing routes: p95 <= 4000 ms.
   - Background/admin routes: p95 <= 6000 ms.

5. **Fallback behavior**
   - Fallback activation visible in response metadata or observability logs.
   - No silent degradation to fake content.

