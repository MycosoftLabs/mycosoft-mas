# Codex Handoff — Backend Security Audit (June 9, 2026)

**Date:** June 9, 2026
**Full report:** `docs/SECURITY_AUDIT_ALL_SYSTEMS_JUN09_2026.md` (MAS repo)
**Context:** Companion to website PR #186. Backend repos were swept for the same issue classes.

---

## Top criticals (backend)

| # | Repo | Finding | File |
|---|------|---------|------|
| 1 | MAS | `POST /api/deploy/trigger` + `/autonomous-fix` unauthenticated — runs deploy subprocesses on VM 188 | `mycosoft_mas/core/routers/deploy_api.py` |
| 2 | MAS | `POST /{device_id}/firmware/flash` unauthenticated | `mycosoft_mas/core/routers/firmware_flash_api.py` |
| 3 | MINDEX | `require_api_key` fails open when `API_KEYS` env empty — whole API unauthenticated on misdeploy | `mindex_api/dependencies.py` |
| 4 | MAS | Revoked password literal as env default in tracked script | `scripts/recreate_mas_container.py:25` |
| 5 | MAS | MycoBrain 8003 service auth is a silent no-op fallback | `services/mycobrain/mycobrain_service_standalone.py:22-28` |

---

## Critical insight for PR 186

PR 186 gated the **website proxies** to `mas/orchestrator/action` and `autonomous/experiments`. The **direct LAN path to 188:8001 is still open** — MAS has no auth middleware. The website fixes are correct; the backend fix (shared `MAS_INTERNAL_TOKEN` dependency) must ship too or the gate can be walked around.

---

## What is backend-only (do NOT fix from website repo)

- All MAS router auth (deploy, firmware-flash, agent-runner, autonomous, coding)
- MINDEX fail-closed auth
- MycoBrain 8003 fail-closed auth
- platform-infra compose port binds
- Hardcoded-credential cleanup in MAS/MINDEX scripts

## What is website-adjacent (coordinate)

- When `MAS_INTERNAL_TOKEN` ships on MAS, the website BFF routes that call 188:8001 must send `X-MAS-Internal-Token` (server-side env, never `NEXT_PUBLIC_*`).
- The `DEVICE_INGEST_TOKEN` pattern from PR 186 is the template for MycoBrain/MAS device ingest.

## What NOT to do

- Do not merge PR 186 changes into backend repos directly — different stacks.
- Do not put any token values in code or docs — env only (`.credentials.local`, VM `.env`).
- Do not "fix" MINDEX `text(f...)` SQL by rewriting routers — verified not injectable (internal table allowlists); convention cleanup only.

---

## Status

- This pass is **report-only**. No fixes applied, nothing committed/pushed, no deploys.
- Remediation order and Morgan-required actions (rotations, history scrub) are in the full report.
