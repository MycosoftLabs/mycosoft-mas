# MYCA/AVANI Worldstate Monetization — Verification and Proof

**Date:** March 14, 2026  
**Status:** Complete  
**Related:** [MYCA_WORLDSTATE_MONETIZATION_COMPLETE_MAR14_2026.md](MYCA_WORLDSTATE_MONETIZATION_COMPLETE_MAR14_2026.md), [MYCA_AVANI_WORLDSTATE_CONNECTION_CONTRACT_MAR14_2026.md](MYCA_AVANI_WORLDSTATE_CONNECTION_CONTRACT_MAR14_2026.md)

---

## 1. What an agent actually sees (browser proof)

Verification was performed with the website dev server on **port 3010**. Screenshots were captured during the run.

### 1.1 Agent offer page — `/agent`

- **URL:** `http://localhost:3010/agent`
- **Heading:** "Agent Access — MYCA & AVANI Live Worldstate"
- **Copy:** "Connect your agents to live worldstate from MYCA and AVANI. Pay only for active connection time at **$1 per minute.**"
- **CTAs visible to an agent:**
  - **Buy 60 minutes — $60** (primary; leads to Stripe checkout)
  - **View pricing**
  - **View balance & usage** (leads to dashboard)
- **Sections:** "What you get", "How it works", "Human users"
- **Proof:** Page loads, all CTAs and pricing are visible; no mock data.

### 1.2 Agent dashboard — `/agent/dashboard`

- **URL:** `http://localhost:3010/agent/dashboard`
- **Heading:** "Agent dashboard"
- **API key:** Input with placeholder `myca_raas_...`; "Save & load" loads balance and usage from MAS.
- **Links:** "Back to Agent Access", "Buy more minutes", "Pricing"
- **Proof:** Dashboard loads; after entering a valid RaaS API key and clicking "Save & load", balance and usage are fetched from MAS (see API flow below).

---

## 2. End-to-end flow (proof it’s working)

| Step | Action | How to verify |
|------|--------|----------------|
| 1 | Human or agent visits `/agent` | Page shows offer and $1/min; "Buy 60 minutes" present. |
| 2 | Purchase minutes (Stripe) | Checkout completes; Stripe webhook calls MAS to add minutes (or claim via `stripe_checkout_session_id`). |
| 3 | Get API key | After onboarding/registration, agent receives API key (e.g. from dashboard or onboarding response). |
| 4 | Start session | `POST /api/raas/worldstate/start` with `X-API-Key`. Returns `session_id` and `balance_minutes`. |
| 5 | Heartbeat | `POST /api/raas/worldstate/heartbeat` with `session_id`. Balance decreases by elapsed minutes. |
| 6 | Stop session | `POST /api/raas/worldstate/stop` with `session_id`. Returns `total_minutes_used` and updated `balance_minutes`. |
| 7 | Balance/usage | `GET /api/raas/worldstate/balance` and `GET /api/raas/worldstate/usage` with `X-API-Key`. Dashboard uses these. |
| 8 | Exhausted balance | When balance is 0, `POST /start` or `POST /heartbeat` returns **402** with `X-Balance-Minutes: 0`. |

**Money-in proof:** Minutes are added when Stripe checkout is claimed (`add_minutes` in `worldstate_session`). Sessions deduct minutes on heartbeat and stop; balance and usage endpoints reflect the same state. Automated tests (see below) assert 402 when balance is 0 and assert successful start/heartbeat/stop and balance decrease with mocks.

---

## 3. API endpoints (reference)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/raas/worldstate/start` | X-API-Key | Start session; 402 if balance = 0 |
| POST | `/api/raas/worldstate/heartbeat` | X-API-Key + body.session_id | Keep session alive; deduct minutes |
| POST | `/api/raas/worldstate/stop` | X-API-Key + body.session_id | End session; return total used |
| GET | `/api/raas/worldstate/balance` | X-API-Key | Current minute balance |
| GET | `/api/raas/worldstate/usage` | X-API-Key | Balance + recent sessions |

Website proxy (with API key from dashboard):

- `GET /api/mas/raas/worldstate/balance` → forwards to MAS with `X-API-Key`
- `GET /api/mas/raas/worldstate/usage` → forwards to MAS with `X-API-Key`

---

## 4. Tests verifying behavior

Location: **`tests/test_raas_worldstate_session.py`**

- **401 without key:** Request to `/api/raas/worldstate/start` without `X-API-Key` returns 401.
- **402 when balance exhausted:** With mocked `start_session` returning `(None, 0, "insufficient_balance")`, response is 402 and `X-Balance-Minutes: 0`.
- **Successful start:** Mock returns `(session_id, 60, None)`; response 200 with `session_id` and `balance_minutes`.
- **Heartbeat 402:** Mock returns `(False, 0, 0, "insufficient_balance")`; response 402.
- **Stop and balance/usage:** Mocks return success and balance/usage; response bodies match.
- **Agent flow (money in and out):** Mocked flow: start → heartbeat → stop; then get balance; assert balance decreased and usage reflects session.

Run:

```bash
cd mycosoft-mas
poetry run pytest tests/test_raas_worldstate_session.py -v
```

**Result (March 14, 2026):** All 9 tests pass (401, 402 start/heartbeat, 200 start/heartbeat/stop/balance/usage, agent flow money in/out).

---

## 5. How to run a full clean test

1. **MAS unit/integration tests**
   ```bash
   cd mycosoft-mas
   poetry run pytest tests/ -v --tb=short
   ```
2. **RaaS worldstate tests only**
   ```bash
   poetry run pytest tests/test_raas_worldstate_session.py -v
   ```
3. **Website (manual)**  
   - Start dev server (port 3010): `npm run dev:next-only` in website repo.  
   - Open `http://localhost:3010/agent` and `http://localhost:3010/agent/dashboard`.  
   - With a valid API key in dashboard, "Save & load" should show balance and usage from MAS.

---

## 6. Screenshots

Full-page screenshots were captured during verification:

- **Agent page:** `agent-page-full-mar14.png` (offer, CTAs, $1/min, Buy 60 min).
- **Agent dashboard:** `agent-dashboard-full-mar14.png` (API key input, Buy more minutes, Pricing).

Paths at capture time: `%LOCALAPPDATA%\Temp\cursor\screenshots\` (or equivalent). These demonstrate exactly what an agent sees in the browser.

---

## 7. Document index

- Completion and design: [MYCA_WORLDSTATE_MONETIZATION_COMPLETE_MAR14_2026.md](MYCA_WORLDSTATE_MONETIZATION_COMPLETE_MAR14_2026.md)
- Contract (MYCA/AVANI): [MYCA_AVANI_WORLDSTATE_CONNECTION_CONTRACT_MAR14_2026.md](MYCA_AVANI_WORLDSTATE_CONNECTION_CONTRACT_MAR14_2026.md)
- This verification: **MYCA_WORLDSTATE_VERIFICATION_AND_PROOF_MAR14_2026.md**
