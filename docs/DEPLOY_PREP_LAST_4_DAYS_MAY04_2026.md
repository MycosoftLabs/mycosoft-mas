# Deployment prep — last ~4 days of work (May 04, 2026)

**Date:** May 04, 2026  
**Purpose:** One-hour deploy window — what is already on GitHub vs what must be committed, and the recommended order of operations.

## Snapshot (ran same day)

| Repo | Branch vs `origin/main` | Uncommitted work |
|------|-------------------------|------------------|
| **website** | **0 / 0** (synced with remote) | **~103** status lines — **~60 files** touched (~3.1k insert / ~3k delete). Large batch: search/fluid, APIs, security, devices, e2e, config. |
| **mycosoft-mas** | **0 / 0** | **~56** lines — **~16 files** (~589 insert). Routers, agents, registries, docs, infra examples. |
| **mindex** | **0 / 0** | **~24** lines — **9 files** + **untracked**: `migrations/0031_mindex_app_overhaul.sql`, `0037_meshtastic_mesh.sql`, `mindex_api/ledger/*`. |
| **mycobrain** | **0 / 0** | Clean (no pending changes in snapshot). |
| **NatureOS** | **0 / 0** | Clean. |
| **Mycorrhizae** | **0 / 0** | Clean. |

**Interpretation:** Recent **commits are already pushed** to `origin/main` for the repos checked. The **deploy risk** is **uncommitted local changes** (especially **website** and **MINDEX migrations**) that will **not** ship until you **commit, push, and then pull on VMs**.

## Highlights already in `git log` (last 4 days, pushed)

- **Website:** search/nav/shell fixes, fluid search debounce, CREP loader, CI lint+build, NatureOS MVP surfaces, voice timeouts, Docker `NEXT_PUBLIC_BASE_URL`, changelog merges, etc.
- **MAS:** Petri deploy path, n8n/MINDEX ingest stub, agent/heartbeat/ledger, Prometheus/MCP ops docs, credentials hygiene, etc.
- **MINDEX:** All-life ETL scaffolding, petri v2 migration, router refresh (committed).
- **Mycobrain / NatureOS / Mycorrhizae:** recent commits present; working trees were clean at check time.

## Before the 1-hour window (minimum)

1. **Decide scope** — Deploy **only** what is merged to `main` on GitHub, **or** include local WIP by cutting **one commit per repo** (or one PR) with a clear message.
2. **Website** — From repo root: `npm ci` (if needed) → **`npm run build`** (production). Fix failures **before** push. Do **not** run full GPU dev stack for this.
3. **MAS** — `poetry run pytest tests/ -q --tb=line` (or your agreed smoke subset) after Python changes.
4. **MINDEX** — If **`0031` / `0037`** (or other new SQL) must go live: apply on **189** per your migration process **before** or **with** API restart; confirm backup/snapshot if policy requires.
5. **Secrets** — No passwords in commits; `.credentials.local` / VM env only. Confirm **Cloudflare** purge tokens and **VM_PASSWORD** loaded for scripts.

## Recommended deploy order (typical)

1. **MINDEX (189)** — Pull → migrate (if any) → rebuild/restart **mindex-api** (see `deploy-mindex` skill / `_deploy_mindex.py`).
2. **MAS (188)** — Pull → restart **mas-orchestrator** (systemd) after Python/router changes.
3. **Website (187)** — Pull → **`docker build --no-cache`** → run container with **NAS mount** for `public/assets` (see deployment checklist) → **Cloudflare purge everything**.
4. **Smoke** — `https://sandbox.../health` or home + one critical app route; MAS `http://192.168.0.188:8001/health`, MINDEX `http://192.168.0.189:8000/health` (adjust if URLs differ).

## Scripts / references (MAS repo)

- Website sandbox: `WEBSITE/website/_rebuild_sandbox.py` / `_deploy_sandbox.py`; purge via `_cloudflare_cache.py` or MCP.
- MAS VM: `deploy-mas-service` skill / `_rebuild_mas_container.py` / SSH `systemctl restart mas-orchestrator`.
- MINDEX: `_deploy_mindex.py` from MINDEX repo or documented VM procedure.

## Explicit non-actions

- **Do not** run deprecated NAS destroyer scripts (e.g. `_sync_nas_push_from_windows.py` — removed by policy).
- **Do not** deploy **website** Docker without the **read-only NAS assets** mount documented for 187.

## Registries / docs (if this deploy changes APIs or agents)

After deploy, if anything **new** shipped: update **`docs/API_CATALOG_FEB04_2026.md`**, **`docs/SYSTEM_REGISTRY_FEB04_2026.md`**, and **`docs/MASTER_DOCUMENT_INDEX.md`** as usual.

---

**Next step for you:** In the hour before cutover, **commit + push** any intentional WIP in **website** and **mindex** (and **mas** if needed), then execute the VM sequence above. Re-run `git status` on each repo immediately before push to confirm nothing accidental is included.
