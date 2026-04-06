# Ethics Training Sandbox Scenarios Repair Complete APR01 2026

**Date:** Apr 01, 2026  
**Status:** Complete  
**Related Plan:** `C:\Users\admin2\.cursor\plans\ethics_sandbox_fix_a9b5ccb5.plan.md`  
**Plan Todo Linkage:** `repair-mas-chat-contract`, `fix-website-ethics-ui`, `automate-scenarios-and-tests`, `verify-router-supabase-runtime`, `document-ethics-sandbox-repair`

## Scope

Repair the ethics training sandbox and scenarios system so it is a real text-to-text tool (no mock/stub behavior in user flow), with explicit backend failures, stable localhost behavior, and test coverage for scenario execution and error contracts.

## Delivered

- Hardened MAS sandbox chat contract in `mycosoft_mas/ethics/sandbox_manager.py`:
  - blank message now rejected with structured `SandboxChatError` (`blank_message`, 400)
  - fallback-string provider failures now surfaced as structured service errors (`llm_provider_failure`, 503)
  - empty model response now surfaced as structured service errors (`empty_model_response`, 503)
  - assistant message is no longer persisted when response is empty/fallback
- Updated ethics API contract in `mycosoft_mas/core/routers/ethics_training_api.py`:
  - structured HTTP errors for chat path (`error`, `detail`, optional `meta`)
  - scenario run now raises structured HTTP errors (instead of silent `"completed": false` response blobs)
- Strengthened scenario run propagation in `mycosoft_mas/ethics/training_engine.py`:
  - added `error_code` in `ScenarioRunResult`
  - preserved origin of scenario failure (`session_not_found`, `scenario_not_found`, `llm_provider_failure`, etc.)
- Updated website proxy + UI error behavior:
  - `app/api/ethics-training/[[...path]]/route.ts` now uses `isEthicsTrainingAllowedEmail(...)`
  - `components/ethics-training/TrainingChat.tsx` now checks `res.ok`, parses API errors, and rejects empty replies
  - `components/ethics-training/ScenarioRunner.tsx` now displays actionable backend error text and scenario run summaries
  - `app/ethics-training/sandbox/[id]/page.tsx` now distinguishes unauthorized / missing / server-down states
  - `app/ethics-training/scenarios/page.tsx` now shows explicit scenario-load failures
  - added shared parser `lib/ethics-training/api-errors.ts`
- Fixed live localhost regression:
  - `lib/access/routes.ts` now exports `isEthicsTrainingAllowedEmail(...)`
  - ethics allowlist expanded to include both `@mycosoft.org` and `@mycosoft.com` for Morgan and Michelle

## Verification

### Automated tests

- MAS focused tests:
  - `poetry run pytest tests/ethics/test_sandbox_manager.py tests/ethics/test_ethics_training_api.py tests/ethics/test_training_engine.py -q`
  - Result: **7 passed**
- Website focused tests:
  - `npm test -- __tests__/lib/auth/origin.test.ts __tests__/lib/ethics-training/api-errors.test.ts --runInBand`
  - Result: **6 passed**

### Runtime checks

- Localhost dev server:
  - `http://localhost:3010` returns 200 after external start
- Supabase/local auth wiring checks (value presence only):
  - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_BASE_URL`, `NEXT_PUBLIC_SITE_URL` are all set in `.env.local`
- Backend selection check:
  - active MYCA core backend resolves to configured provider/model/base URL in local runtime
- Ethics scenarios proxy check:
  - unauthenticated request to `/api/ethics-training/scenarios` now returns expected auth response (`403 {"error":"Unauthorized"}`), not 500
- Login redirect behavior:
  - localhost scenarios page correctly routes to login with redirect target (`/login?redirectTo=%2Fethics-training%2Fscenarios`)

## Follow-up

- Authenticated end-to-end scenario-run + grading assertions should be executed with a valid Morgan/Michelle session cookie in browser automation for full production parity.
- If desired, add a browser E2E test that signs in and validates full scenario run JSON and grade rendering in UI.

## Lessons Learned

- Generic fallback strings at the LLM layer must not be treated as successful domain responses.
- Route-level auth helpers used by API proxies must be exported and covered by tests to prevent silent production 500s.
- Scenario APIs should communicate failures through HTTP status + structured body, not ambiguous successful-status envelopes.
