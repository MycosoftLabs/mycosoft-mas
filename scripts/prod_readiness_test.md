# Production Readiness Test (MYCA + Dashboard + n8n)

This document defines an **extensive pre-production test** to validate that the system will work when moving from local/dev into production.

## Scope

- **Dashboard** (`unifi-dashboard` Next.js)
- **MYCA chat + voice** (`/api/myca/chat`, `/api/myca/tts`, Talk to MYCA UI)
- **MAS backend** (orchestrator health + core APIs)
- **ElevenLabs Proxy** (TTS)
- **n8n** (workflow persistence + webhook health, if used in prod)
- **Persistence** (Docker volumes, DBs, credentials)
- **Security** (no secrets in repo, TLS, CORS, auth boundaries)

---

## A. Pre-flight checks (must pass)

- **Ports/URLs defined**
  - Dashboard URL (prod): `https://<dashboard-domain>`
  - MAS backend URL: `http(s)://<mas-domain-or-host>:<port>`
  - n8n URL: `http(s)://<n8n-domain>`
  - ElevenLabs proxy URL: `http(s)://<proxy-domain>`
- **Secrets NOT in git**
  - API keys are provided via environment/secret manager only.
- **Docker volumes persistent**
  - n8n data lives in a named volume (or mounted persistent disk).
  - DBs (Postgres/Redis/Qdrant/etc.) persist to volumes.
- **Time + timezone sanity**
  - Containers have consistent timezone/UTC; cron workflows run as expected.

---

## B. Automated smoke test (run on staging + before prod)

Run: `scripts/prod_smoke_test.ps1`

### What it verifies

- **Dashboard reachable** (HTTP 200)
- **Dashboard API health**
  - `GET /api/myca/chat` (or health endpoint if present)
  - `GET /api/myca/tts` (or health endpoint if present)
- **Chat**
  - `POST /api/myca/chat` returns JSON with a response and **MYCA identity** constraints.
- **TTS**
  - `POST /api/myca/tts` returns audio (`audio/mpeg` or `audio/wav`) and is non-empty.
- **MAS**
  - `GET /health` or configured health endpoint is OK.
- **n8n (optional but recommended)**
  - `GET /api/v1/workflows` with API key returns list
  - critical workflows present
  - webhook endpoint returns non-404 (if prod uses webhooks)

---

## C. Browser E2E tests (must pass on staging)

Run: `cd unifi-dashboard; npm run test:e2e`

### Tests included

- **Home loads**
- **Theme toggle works** (dark/light)
- **Talk to MYCA panel opens**
- **Identity constraint**
  - Ask “what is your name and how do you pronounce it?”
  - Response includes `MYCA` and `my-kah`

---

## D. Voice-specific manual test protocol (staging)

> Browser speech recognition requires real user permission; do this manually.

- **Mic permission UX**
  - Permission is requested once, not repeatedly.
  - If denied, UI shows clear fallback (type input still works).
- **No feedback loop**
  - Start listening → speak → MYCA responds
  - Confirm it does NOT immediately re-trigger from its own audio
    - If it does: enable echo cancellation/noise suppression in getUserMedia, and pause recognition while TTS plays.
- **Latency**
  - “Hello MYCA” → first token response within ~1–2s target (depends on model)
  - TTS starts within acceptable threshold
- **Correct voice**
  - ElevenLabs Arabella voice is used when proxy is up
  - Fallback is explicit if proxy is down (avoid silent failure)

---

## E. n8n productionization checklist (if n8n drives integrations)

- **Pin n8n version** (avoid surprise upgrades)
- **Set canonical webhook URL**
  - `WEBHOOK_URL=https://<n8n-domain>/`
  - `N8N_HOST=<n8n-domain>`
  - `N8N_PROTOCOL=https`
- **Encryption key set**
  - `N8N_ENCRYPTION_KEY` fixed and stored securely
- **Backups**
  - Daily export of workflows (JSON) to persistent storage
  - DB backups if using Postgres
- **Credentials**
  - Confirm all required credentials exist in the prod n8n instance
  - Remember: n8n Cloud typically doesn’t export credentials; plan accordingly.

---

## F. Release gate (definition of “ready”)

Production is “ready” only if:

- Smoke test passes on staging and prod
- E2E tests pass on staging
- Manual voice test passes on staging
- n8n workflows + credentials are backed up and persistent
- No secrets committed to git

