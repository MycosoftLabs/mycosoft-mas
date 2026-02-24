# MYCA Demo Connection Fixes – Feb 17, 2026

## Summary

Several fixes were made so MYCA works correctly in the Live Demo when the MAS backend is unreachable or returns a different response format.

## Root Causes

1. **Consciousness API response mismatch** – MAS Consciousness API returns `{ message: "..." }` but the orchestrator expected `reply` or `response`, so it ignored valid responses.
2. **Very long timeouts** – 30s timeout for consciousness when MAS is unreachable delayed fallback to LLM providers.
3. **Generic error handling** – Connection issues produced unclear error messages in the UI.

## Changes

### 1. Orchestrator – consciousness response parsing (`website/app/api/mas/voice/orchestrator/route.ts`)

- Read `data.message` as well as `data.reply` and `data.response`:
  ```ts
  const text = data.message ?? data.reply ?? data.response ?? null
  ```
- Set `routed_to` in the response for the activity panel.
- Reduced consciousness timeout from 30s to 10s when MAS is unreachable.

### 2. MYCA context – error handling (`website/contexts/myca-context.tsx`)

- Parse JSON error responses from the API.
- Show clearer errors:
  - Network: “MYCA can't reach the API backend. If you're on localhost, ensure MAS (192.168.0.188) is reachable…”
  - Missing API keys: “MYCA's AI backends need API keys…”
  - Other: include the server error message (truncated).

## Diagnostic Checks

### MAS reachable from dev machine

```powershell
Invoke-WebRequest -Uri "http://192.168.0.188:8001/health" -UseBasicParsing -TimeoutSec 5
```

- If this times out, the dev PC is not on the same network as MAS (192.168.0.188). The orchestrator will then fall back to Claude, OpenAI, Groq, etc.

### Orchestrator (Next.js API)

```powershell
# GET (health)
Invoke-WebRequest -Uri "http://localhost:3010/api/mas/voice/orchestrator" -Method GET -UseBasicParsing

# POST (chat)
$body = '{"message":"Hello"}'
Invoke-RestMethod -Uri "http://localhost:3010/api/mas/voice/orchestrator" -Method POST -ContentType "application/json" -Body $body -TimeoutSec 30
```

### On Sandbox (VM 187)

The website container on Sandbox calls MAS at 192.168.0.188 on the LAN, so MAS should be reachable. Chat should work there if LLM keys are configured in the deployed environment.

### Topology WebSocket

The activity panel connects to `ws://192.168.0.188:8001/ws/topology`. This is a direct browser → MAS connection. If the user is not on the LAN (e.g. visiting sandbox.mycosoft.com remotely), that WebSocket will not connect because 192.168.0.188 is a private IP.

## Next Steps If Demo Still Fails

1. **Confirm dev server** – `npm run dev:next-only` in the website repo; check for errors in the terminal.
2. **Confirm LLM keys** – `.env.local` should define `ANTHROPIC_API_KEY` (or other LLM keys) for fallback when MAS is down.
3. **Watch Next.js logs** – On each chat request you should see `[Orchestrator] Request from web: "..."` and `[MYCA] Provider: ...`.
4. **Ensure MAS is up** – On the same LAN, verify `http://192.168.0.188:8001/health` returns 200.
