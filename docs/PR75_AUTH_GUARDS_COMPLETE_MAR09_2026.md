# PR #75 Auth Guards Complete

**Date:** March 9, 2026  
**Status:** Complete  
**Related:** PR #75, `docs/PR75_IMPLEMENTATION_PLAN_MAR09_2026.md`

---

## Summary

Security remediation for PR #75: Guardian, Avani, and Identity APIs now require scoped API key authentication on all mutating endpoints.

---

## Changes Delivered

### 1. Guardian API (`mycosoft_mas/core/routers/guardian_api.py`)

- **POST `/emergency-halt`** — Requires `require_api_key_scoped("guardian:admin")`
- **POST `/operational-mode`** — Requires `require_api_key_scoped("guardian:admin")`; `requester` set from API key `user_id`
- **POST `/sentry/activate`** — Requires `require_api_key_scoped("guardian:admin")`
- **POST `/sentry/deactivate`** — Requires `require_api_key_scoped("guardian:admin")`
- Read-only endpoints (`GET /status`, `/boot-statement`, etc.) remain unauthenticated for dashboard display

### 2. Avani Router (`mycosoft_mas/core/routers/avani_router.py`)

- **POST `/season/update`** — Requires `require_api_key_scoped("avani:update")`
- **Removed** `is_root` from `SeasonUpdateRequest` — Root authority now derived from API key scope `avani:root`
- Callers with `avani:root` can perform Root-gated seasonal transitions; others cannot

### 3. Identity API (`mycosoft_mas/core/routers/identity_api.py`)

- **POST `/earliest-fragment`** — Requires `require_api_key_scoped("identity:write")`
- **POST `/preferences`** — Requires `require_api_key_scoped("identity:write")`
- **POST `/moral-assessments`** — Requires `require_api_key_scoped("identity:write")`
- **POST `/continuity-events`** — Requires `require_api_key_scoped("identity:write")`; `authorized_by` set from auth, not request body
- **POST `/creator-bond`** — Requires `require_api_key_scoped("identity:write")`
- Read-only endpoints remain unauthenticated (or use existing auth where applicable)

### 4. Identity Migration Script (`scripts/run_identity_migration.py`)

- Loads `.credentials.local` in addition to `.env`
- If `MINDEX_DATABASE_URL` not set, builds from `MINDEX_DB_PASSWORD` or `VM_PASSWORD`:
  - `postgresql://mindex:{password}@192.168.0.189:5432/mindex`
- Run: `python scripts/run_identity_migration.py` from MAS repo root

---

## API Key Scopes Required

| Scope | Used By | Purpose |
|-------|---------|---------|
| `guardian:admin` | Guardian API | Emergency halt, operational mode, sentry toggle |
| `avani:update` | Avani router | Season updates |
| `avani:root` | Avani router | Root-gated seasonal transitions |
| `identity:write` | Identity API | All identity write endpoints |

---

## Migration Status

- **Script:** `scripts/run_identity_migration.py` — Ready
- **Migration SQL:** `migrations/025_identity_system.sql` — Creates `identity` schema and tables
- **Execution:** Requires `MINDEX_DATABASE_URL` or `MINDEX_DB_PASSWORD` in `.env` / `.credentials.local`
- **Note:** `VM_PASSWORD` may differ from MINDEX Postgres password; set `MINDEX_DB_PASSWORD` explicitly for MINDEX DB access

---

## Verification

1. **Guardian:** Call POST endpoints without `X-API-Key` (or wrong scope) → 401/403
2. **Avani:** Call POST `/season/update` without `avani:update` scope → 401/403
3. **Identity:** Call POST endpoints without `identity:write` scope → 401/403

---

## Related Documents

- `docs/PR75_IMPLEMENTATION_PLAN_MAR09_2026.md` — Full PR75 plan, frontend, marketing
- `docs/MICAH_GUARDIAN_ARCHITECTURE_MAR09_2026.md` — Guardian design
- `docs/AVANI_MICAH_CONSTITUTION_MAR09_2026.md` — Avani governance
- `docs/RECIPROCAL_TURING_PROTOCOL_MAR09_2026.md` — Identity API
