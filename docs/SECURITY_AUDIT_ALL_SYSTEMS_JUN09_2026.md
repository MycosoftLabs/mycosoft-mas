# Security Audit — All Backend Systems (June 9, 2026)

**Date:** June 9, 2026
**Trigger:** Website PR #186 (`security: fix critical RCE, privilege escalation, and unauthenticated infra routes`) — checked whether the same issue classes exist in MAS, MINDEX, MycoBrain, Mycorrhizae, NLM, platform-infra, NatureOS.
**Scope:** Read + report only. No code fixes in this pass. Website repo excluded (already covered by PR 186).
**Method:** ripgrep sweeps + source reads of every flagged file. No secret values reproduced below.

---

## Executive summary

The **most serious finding mirrors PR 186's core lesson**: PR 186 added auth to the *website's proxy* for `mas/orchestrator/action`, but **MAS itself (188:8001) has no authentication layer at all** — only CORS + rate-limit middleware. Anyone on the LAN (or via any SSRF/tunnel into it) can trigger deployments, start/stop agents, flash firmware, and drive autonomous experiments directly, bypassing every fix in PR 186.

MINDEX auth **fails open** when `API_KEYS` is unset, and both repos have **tracked files containing revoked credentials** (git-history exposure class, same as PR 186's baked Supabase keys).

| Repo | Critical | High | Medium | Low |
|------|----------|------|--------|-----|
| MAS | 3 | 4 | 2 | 1 |
| MINDEX | 1 | 1 | 1 | 1 |
| MycoBrain (svc in MAS repo) | 0 | 1 | 0 | 0 |
| MycoBrain (firmware repo) | 0 | 0 | 0 | 1 |
| Mycorrhizae | 0 | 0 | 0 | 1 |
| NLM | 0 | 0 | 0 | 0 |
| platform-infra | 0 | 0 | 2 | 0 |
| NatureOS | 0 | 0 | 0 | 0 |

---

## PR 186 class comparison matrix

| Class (from PR 186) | Website finding | Same issue in backend? | Where |
|---|---|---|---|
| **A. RCE / command injection** | shell `nslookup` with query param | **Partially.** No direct param→shell interpolation found in MAS routers (deploy uses `create_subprocess_exec` with fixed script paths). But unauthenticated deploy/flash endpoints achieve RCE-equivalent outcomes. | `deploy_api.py`, `firmware_flash_api.py` |
| **B. Privilege escalation / fail-open auth** | role from user-writable `user_metadata.role` | **Yes.** MINDEX `require_api_key` fails open when env empty; MycoBrain 8003 `verify_api_key` no-op fallback. | `mindex_api/dependencies.py:24`, `services/mycobrain/mycobrain_service_standalone.py:22-28` |
| **C. Unauthenticated infra routes** | docker, orchestrator proxy, experiments, cctv | **Yes — worse.** MAS 8001 has no auth middleware; deploy, agent runner, firmware flash, autonomous, coding control all open. | see MAS findings below |
| **D. Network exposure (0.0.0.0 binds)** | Ollama/Prometheus/Redis | **Yes.** platform-infra compose publishes Postgres/Redis/Qdrant/n8n without loopback binding. | `platform-infra/docker-compose.yml` |
| **E. Baked/hardcoded secrets** | Supabase keys + NEXTAUTH in Dockerfiles | **Yes.** Revoked passwords as defaults in tracked scripts (MAS + MINDEX); tracked MQTT creds env file. | `scripts/recreate_mas_container.py`, MINDEX `scripts/_*.py`, `_jetson_mqtt.env` |
| **F. PII / debris in git** | authorized-users GPS file + 45 debris files | **Partially.** No PII file found; MAS has ~200 untracked one-shot scripts (hygiene risk if ever staged), MINDEX has tracked one-shot deploy scripts that embed creds (covered in E). | MAS `scripts/_*.py` (untracked), MINDEX `scripts/_*.py` (tracked) |
| **G. SQL injection** | n/a (RLS issues instead) | **No confirmed injection.** `text(f"...")` usages build from internal table dictionaries, not request params. Flagged for convention cleanup. | MINDEX `earth.py`, `eagle.py`, `taxon.py`, `genetics.py`, `library.py` |

---

## MAS — `MAS/mycosoft-mas` (VM 188:8001)

### Critical

| # | Class | Finding | Location | Fix |
|---|---|---|---|---|
| M-1 | C | **`POST /api/deploy/trigger` and `POST /api/deploy/autonomous-fix` are unauthenticated** and run deploy subprocesses (git pull + rebuild scripts) on the VM. RCE-equivalent for anyone who can reach 188:8001. | `mycosoft_mas/core/routers/deploy_api.py:185-268` | Add an internal-token dependency (e.g. `X-MAS-Internal-Token`) on the router; verify against env. |
| M-2 | C | **`firmware_flash_api.py` `POST /{device_id}/firmware/flash` unauthenticated** — remote firmware flash of devices. | `mycosoft_mas/core/routers/firmware_flash_api.py:138` | Same internal-token dependency + device allowlist. |
| M-3 | E | **Revoked DB password `Diamond1!` hardcoded as default** in a tracked script (`os.environ.get("MINDEX_DB_PASSWORD", "Diamond1!")`). Violates no-hardcoded-secrets rule; value lives in git history. | `scripts/recreate_mas_container.py:25` | Remove default (`""`), rotate if not already rotated, consider history scrub batch. |

### High

| # | Class | Finding | Location | Fix |
|---|---|---|---|---|
| M-4 | C | **`agent_runner_api.py`** — `POST /start`, `/stop`, `/wisdom/compile`, `/notify` unauthenticated agent lifecycle control. | `mycosoft_mas/core/routers/agent_runner_api.py:22-128` | Internal-token dependency. |
| M-5 | C | **`autonomous_api.py`** — 13 unauthenticated mutating endpoints (experiments create/start/pause/abort/adapt, hypotheses, agenda). Website PR 186 gated the *proxy* to these; direct access remains open. | `mycosoft_mas/core/routers/autonomous_api.py:41-214` | Internal-token dependency (matches the website-side `requireCompanyAuth` now in place). |
| M-6 | C | **`coding_api.py`** — code-change request/approve/cancel/emergency-halt endpoints have service `Depends` but **no auth** (10 `Depends` refs are DI, not auth). | `mycosoft_mas/core/routers/coding_api.py:120-316` | Internal-token dependency; manual-approval endpoint especially. |
| M-7 | B | **MycoBrain service 8003 auth fails open**: `from auth import verify_api_key` falls back to a stub returning `"no-auth"` on ImportError — and the standalone service typically runs without that module, leaving `/devices/connect`, `/devices/{id}/command`, `/flash`, `/clear-locks` open. | `services/mycobrain/mycobrain_service_standalone.py:22-28, 682-1241` | Fail closed: if auth module missing and `MYCOBRAIN_API_KEY` set, require it; log loudly when running unauthenticated. |

### Medium

| # | Class | Finding | Location | Fix |
|---|---|---|---|---|
| M-8 | E | **`_jetson_mqtt.env` tracked in git with real MQTT username/password.** | `_jetson_mqtt.env` (repo root) | Untrack, gitignore, rotate MQTT cred. |
| M-9 | C | **No global auth middleware** on the FastAPI app — only CORS + `RateLimitMiddleware`. Every router is opt-in for auth and most opted out. | `mycosoft_mas/core/myca_main.py:775-784` | Introduce shared `require_internal_token` dependency and apply to all mutating infra routers (M-1..M-6 list). |

### Low

| # | Class | Finding | Location | Fix |
|---|---|---|---|---|
| M-10 | F | ~200 untracked one-shot `scripts/_*.py` + logs (`data/*.txt`, `.codex-*`). Several (`_emergency_auth_*`, `_fix_tunnel_token_*`) operate on credentials; risk is accidental `git add -A`. | `scripts/`, `data/` | Add explicit gitignore patterns (`scripts/_*.py` opt-in policy), purge stale ones. |

**Positive:** `redteam_api.py` requires Guardian approval on simulations; `network_diagnostics.py` and `deploy_api.py` use `create_subprocess_exec` (no shell) with fixed argv; no `shell=True` in any router; no paramiko `exec_command` with request-data interpolation found.

---

## MINDEX — `MINDEX/mindex` (VM 189:8000)

### Critical

| # | Class | Finding | Location | Fix |
|---|---|---|---|---|
| X-1 | B | **`require_api_key` fails open**: when `settings.api_keys` is empty, *all* routes that depend on it accept any request. A misdeployed env (missing `API_KEYS`) silently disables auth API-wide. | `mindex_api/dependencies.py:24-40` | Fail closed in production (`MINDEX_ENV=production` ⇒ refuse to start or 401 when no keys configured). Migrate remaining routers to DB-backed `auth.require_internal_token` as the docstring already instructs. |

### High

| # | Class | Finding | Location | Fix |
|---|---|---|---|---|
| X-2 | E | **Revoked DB password `mycosoft_mindex_2026` hardcoded in 5 tracked scripts** (deploy one-shots). Git history exposure of a (revoked) credential + pattern invites recurrence. | `scripts/_deploy_mindex_v2.py:50`, `scripts/_fix_mindex.py:66`, `scripts/_full_fix.py:67,82`, `scripts/_kill_and_restart.py:64`, `scripts/_restart_mindex_fixed.py:42` | Replace with `os.environ["MINDEX_DB_PASSWORD"]`, untrack or delete dead scripts. |

### Medium

| # | Class | Finding | Location | Fix |
|---|---|---|---|---|
| X-3 | B | `require_device_api_key` also returns the key un-checked when `API_KEYS` empty and no device-hash match path taken (same fail-open family as X-1). | `mindex_api/dependencies.py:43-83` | Same fail-closed policy. |

### Low

| # | Class | Finding | Location | Fix |
|---|---|---|---|---|
| X-4 | G | `text(f"...")` dynamic SQL in several routers. **Verified:** table names come from internal dicts/lists (e.g. `earth.py:82-87` iterates a hardcoded `tables` map), not request input — no injection path confirmed. Convention risk only. | `mindex_api/routers/earth.py:84`, `eagle.py:100`, `taxon.py:75`, `genetics.py:194`, `library.py:231`, `plasticity_router.py:601`, `gpu/cuvs_index.py`, `gpu/mica_bridge.py` | Keep identifiers from allowlists; add a comment/lint rule; parameterize everything else. |

**Positive:** No tracked `.env`/credentials files; `library.py` path traversal guard (`_resolve_blob_path`) is correct; SINE/library routers parameterize user input.

---

## MycoBrain firmware repo — `CODE/mycobrain`

| # | Class | Severity | Finding | Location |
|---|---|---|---|---|
| MB-1 | E | Low | SSH password handling is correct (`%MYCOBRAIN_JETSON_PASSWORD%` env var, documented as never written to disk). No hardcoded secrets found in `tools/python/` or `firmware/common/`. | `tools/python/auto_probe_all.py` |

The real MycoBrain risk is the **service** in the MAS repo (finding M-7 above), not the firmware repo.

---

## Mycorrhizae — `CODE/Mycorrhizae/mycorrhizae-protocol` (8002)

| # | Class | Severity | Finding | Location |
|---|---|---|---|---|
| MY-1 | B | Low | REST/SSE stream routes properly require `X-API-Key` with scopes via `KeyServiceManager`. WebSocket auth is **optional** (anonymous connect allowed, key only for scoped access) — acceptable if anonymous scope is read-limited; verify channel exposure. | `api/stream_router.py:36-43`, `api/websocket_router.py:42-59` |

---

## NLM — `CODE/MAS/NLM`

No hardcoded secrets, no shell execution from request data, no auth surface of its own (library/package). Clean in this pass. (Default `MINDEX_API_URL` port fixed in `nlm/client.py` commit `4a82868`, Jun 5.)

---

## platform-infra — `CODE/platform-infra`

| # | Class | Severity | Finding | Location | Fix |
|---|---|---|---|---|---|
| P-1 | D | Medium | Compose publishes infra ports without loopback binding (default 0.0.0.0): Postgres `5436:5432`, Redis `6381:6379`, Qdrant `6333:6333`, plus app ports. Same class PR 186 fixed for Ollama/Prometheus/Redis on the website stack. | `docker-compose.yml:49,63,306` | Bind to `127.0.0.1:` where only-local, or restrict at host firewall to 192.168.0.0/24. |
| P-2 | D | Medium | MYCA VM compose: n8n `5678:5678` with `N8N_HOST=0.0.0.0` default; FastAPI `8000:8000`; signal-cli `8089:8080`. LAN-exposed automation surfaces. | `docker-compose.myca-vm.yml:20,31,49,87` | Keep behind Caddy/auth or bind loopback + reverse proxy. |

---

## NatureOS — `CODE/NATUREOS/NatureOS` (lighter pass)

Connection strings (CosmosDB, ServiceBus, EventGrid) are read from configuration/environment, not hardcoded. No findings in this pass. Deeper review of `Controllers/` auth attributes recommended in a future pass.

---

## Prioritized remediation plan

### Agent-fixable now (code changes, no key rotation)

1. **MAS internal-token dependency** (fixes M-1, M-2, M-4, M-5, M-6, M-9): one shared `require_internal_token` (env `MAS_INTERNAL_TOKEN`, header `X-MAS-Internal-Token`, fail-closed in production) applied to deploy, firmware-flash, agent-runner, autonomous, coding routers. Update website BFF + n8n callers to send it.
2. **MINDEX fail-closed auth** (X-1, X-3): refuse unauthenticated requests when env is production, even if `API_KEYS` empty; continue migration to DB-backed `auth.require_internal_token`.
3. **MycoBrain 8003 fail-closed** (M-7): require `MYCOBRAIN_API_KEY` when set; remove silent no-auth fallback.
4. **Strip hardcoded passwords** (M-3, X-2): env-only, delete dead one-shot scripts.
5. **Untrack `_jetson_mqtt.env`** (M-8) + gitignore.
6. **Compose loopback binds** (P-1, P-2) where services are host-local.

### Needs Morgan / credentialed action

- Rotate MQTT credential from `_jetson_mqtt.env` (M-8).
- Confirm `Diamond1!`/`mycosoft_mindex_2026` rotations already done (per no-hardcoded-secrets rule they are revoked — verify nothing still accepts them).
- Decide on git-history scrub batch (both repos) — same procedure as the March 2026 incident.
- Set `MAS_INTERNAL_TOKEN` on VM 188 env + website/n8n configs after fix #1 ships.

### Coordination with website PR 186

- PR 186's `mas/orchestrator/action` and `autonomous/experiments` website gates are **necessary but not sufficient** — they only protect the public path. Fix #1 closes the direct-LAN path. Ship both.
- The website's `DEVICE_INGEST_TOKEN` pattern is a good template for MycoBrain 8003 and MAS device ingest routes.

---

## Verification commands used

```text
rg "shell=True|os.system|pickle.loads"  → no router/service hits (Moshi .eval() = model API, false positive)
rg "@router.(post|put|delete)" vs auth refs per router → table in MAS section
read mindex_api/dependencies.py        → fail-open confirmed
read mycobrain_service_standalone.py:14-40 → no-auth fallback confirmed
read deploy_api.py:84-268              → fixed-argv subprocess, unauthenticated trigger confirmed
rg revoked credential literals         → M-3, X-2 hits confirmed tracked via git ls-files
```

---

## Related docs

- Website PR 186: `SECURITY_AUDIT_2026-06-09.md`, `SECURITY_MORGAN_ACTION_STEPS.md`, `SECURITY_CURSOR_HANDOFF.md` (website repo / PR branch)
- Codex handoff for this audit: `docs/codex-handoffs/SECURITY_AUDIT_BACKEND_CODEX_HANDOFF_JUN09_2026.md`
- No-secrets rule: `.cursor/rules/no-hardcoded-secrets.mdc`