# MYCA AVANI Route Contract Validation — MAR31 2026

Date: 2026-03-31  
Status: Implemented for Corporate-first Nemotron rollout

## Scope

Validate user-facing AVANI request/response behavior while Corporate routing is switched to Nemotron-first with Ollama fallback.

## Website Route Changes Applied

- Updated `WEBSITE/website/app/api/myca/route.ts` to remove all mock responses and random confidence values.
- Route now proxies live MYCA requests to MAS (`/api/myca/chat`, `/api/myca/status`) using `MAS_API_URL`.
- Preserved backward-compatible response fields for existing AVANI callers:
  - `answer`
  - `confidence`
  - `sources`
  - `suggestedQuestions`
  - `fallback`
  - `timestamp`

## Contract Parity Checks

Use these checks during wave promotions:

1. **Status path parity**
   - Website: `GET /api/myca?action=context`
   - MAS source: `GET /api/myca/status`
   - Expected: response includes conscious state and processing counters.

2. **Chat envelope parity**
   - Website: `POST /api/myca` with `question`
   - MAS source: `POST /api/myca/chat`
   - Expected: website response still returns `answer` even when MAS returns `message` or `response`.

3. **Streaming parity**
   - Website: `POST /api/myca/consciousness/chat`
   - MAS source: `POST /api/myca/chat` (SSE enabled)
   - Expected: `text/event-stream` forwarding is preserved and no schema drift in chunk events.

4. **Fallback visibility**
   - Expected: fallback state is explicit in payload (`fallback=true`) and routing telemetry appears in MAS response internals.

## Validation Commands

```powershell
# 1) Status/context
Invoke-RestMethod -Uri "http://localhost:3010/api/myca?action=context" -Method GET

# 2) AVANI chat envelope
Invoke-RestMethod -Uri "http://localhost:3010/api/myca" -Method POST -ContentType "application/json" -Body (@{
  question = "Confirm MYCA operational status"
  session_id = "avani-contract-test"
} | ConvertTo-Json)

# 3) MAS smoke matrix (provider/mode telemetry)
poetry run python scripts/llm/run_nemotron_smoke_matrix.py
```

## Gate Outcome for Corporate Wave

- Contract-breaking mock behavior removed from AVANI-facing `api/myca` route.
- Corporate wave can stay active with:
  - `MYCA_BACKEND_MODE_CORPORATE=nemotron`
  - global fallback still enabled via hybrid mode.

