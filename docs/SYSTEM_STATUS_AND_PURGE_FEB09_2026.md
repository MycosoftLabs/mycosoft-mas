# System Status, Purge, and GitHub Path – Feb 9, 2026

Single reference for: (1) what has been done across the system, (2) what can be done next, (3) Cloudflare purge and where credentials live (including “agents cat”), (4) GitHub-as-source-of-truth path for MAS and website, (5) rule to always check latest docs so agents stay aligned.

---

## 1. Always Use Latest Docs

**Rule:** Before starting any new plan, task, or implementation, read the latest docs (e.g. last 72 hours) and key registries so status is current and agents don’t conflict.

- **Master index:** `docs/MASTER_DOCUMENT_INDEX.md`
- **System registry:** `docs/SYSTEM_REGISTRY_FEB04_2026.md`
- **API catalog:** `docs/API_CATALOG_FEB04_2026.md`
- **Recent docs:** List `docs/*.md` by date (latest first) and read newest first.
- **This doc:** Current system status, purge, and GitHub path.

---

## 2. What Has Been Done

### CREP / Earth2 / Physics (real data only)

- **Website (CREP Earth2):** All Earth2 API routes use real upstream → cached-real → explicit error/503 only (no synthetic data). Client (`lib/earth2/client.ts`) no longer returns default synthetic status/models; strict availability and errors.
- **Website build:** Fixed invalid fetch URLs and BOM in `use-biocompute.ts`, `use-autonomous.ts`, and autonomous experiments API routes; build succeeds.
- **Website deploy:** Deploy script `deploy_sandbox_rebuild_FEB09_2026.py` runs on Sandbox VM 187: git fetch/reset, Docker build, container restart with NAS mount, then Cloudflare purge. Container healthy; site returns HTTP 200.

### MAS

- **PhysicsNeMo / Earth2:** MAS has earth2 and physicsnemo routers; `physicsnemo_api.py` proxies to `PHYSICSNEMO_API_URL`. Code is in place.
- **MAS on GitHub:** Push from local MAS to `origin/main` has previously failed (HTTP 500 / remote hung up). Until push succeeds, VM 188 cannot “pull from GitHub” for MAS; deploy from GitHub path is blocked for MAS.

### Cloudflare purge

- **Scripts:** `_cloudflare_cache.py` implements `purge_everything()`; used by `deploy_sandbox_rebuild_FEB09_2026.py`, `_rebuild_sandbox.py`, `_check_build_and_start.py`, `_wait_restart.py`, `_wait_and_restart.py`, `_deploy_homepage_search.py`.
- **Config:** Purge reads `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID` from environment. As of Feb 9, 2026, `_cloudflare_cache.py` also loads `.env.local` and `.env` from the website repo root (script directory and cwd), so credentials in website `.env.local` are used when running deploy/purge from the website repo.
- **“Agents cat”:** You reported putting Cloudflare API and ID in “agents cat.” That can mean:
  - **Website `.env.local`:** Add `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID` there; purge will use them when deploy scripts run from the website repo.
  - **Cursor/agent config:** If credentials are stored in a Cursor agent category or another config agents read, ensure that when those agents run the deploy script they either run it from the website repo (so `.env.local` is loaded) or that the same vars are exported in the environment before calling the script.
- **Manual purge:** Dashboard: Cloudflare → mycosoft.com → Caching → Purge Everything. Or curl with token/zone ID (see `C:\Users\admin2\.cursor\skills\cloudflare-cache-purge\SKILL.md`).

### VMs and services

- **187 (Sandbox):** Website container rebuilt and running with NAS mount; health 200.
- **188 (MAS):** Orchestrator running; earlier automation report had purge succeeding when env was set.
- **189 (MINDEX):** Data stack and API healthy; do not run Claude Code on 189 (AVX/Bun issue).

---

## 3. What Can Be Done Next

| Area | Action |
|------|--------|
| **Cloudflare purge** | Ensure `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID` are in website `.env.local` (or in the env when deploy runs), then run deploy script or call `purge_everything()` from website repo so purge runs after every website deploy. |
| **MAS on GitHub** | Retry `git push origin main` from mycosoft-mas (or fix remote/SSH/network). Once pushed, all MAS deploys should follow: pull from GitHub on VM 188, then rebuild/restart MAS container. |
| **MAS deploy VM 188** | After MAS is on GitHub: on 188, `git fetch origin && git reset --hard origin/main`, then rebuild/restart MAS (e.g. `_rebuild_mas_container.py` or equivalent). |
| **CREP end-to-end** | After purge (and optionally MAS deploy): verify sandbox CREP (Earth2 status, layers, errors). If 187→188 is down, fix network so sandbox can reach MAS. |
| **Docs** | Keep MASTER_DOCUMENT_INDEX and this status doc updated when major changes ship; all agents should read latest docs before starting work. |

---

## 4. GitHub Path (Source of Truth)

- **Website:** Changes are committed and pushed to GitHub (e.g. MycosoftLabs/website). Deploy: on VM 187 pull from `origin/main`, rebuild Docker image, restart container, then purge Cloudflare. No deploy from local-only branches; follow GitHub path.
- **MAS:** Intended flow is the same: push to GitHub (MycosoftLabs/mycosoft-mas), then on VM 188 pull from `origin/main` and rebuild/restart. Currently blocked by push failures; once unblocked, all MAS deploys should follow this path.
- **Other repos:** Same principle: push first, then deploy from GitHub on the relevant VM.

---

## 5. Quick Reference

| Item | Where / How |
|------|-------------|
| Purge credentials | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ZONE_ID` in website `.env.local` or in env when running deploy from website repo; or in “agents cat” env used by the script. |
| Purge helper | `WEBSITE/website/_cloudflare_cache.py` – loads .env then calls Cloudflare API. |
| Deploy website | Push to GitHub → on 187 pull, build, run container with NAS mount → purge. |
| Deploy MAS | Push to GitHub → on 188 pull, rebuild/restart MAS container. |
| Latest status | Read `docs/MASTER_DOCUMENT_INDEX.md` and newest dated docs first. |

---

## 6. Related Docs

| Topic | Doc |
|-------|-----|
| Full automation report | `docs/FULL_PLATFORM_AUTOMATION_EXECUTION_REPORT_FEB09_2026.md` |
| Status and next steps | `docs/STATUS_AND_NEXT_STEPS_FEB09_2026.md` |
| PhysicsNeMo integration | `docs/PHYSICSNEMO_INTEGRATION_FEB09_2026.md` |
| Master document index | `docs/MASTER_DOCUMENT_INDEX.md` |
| Cloudflare purge skill | `C:\Users\admin2\.cursor\skills\cloudflare-cache-purge\SKILL.md` |
| Dev/deploy pipeline | `docs/DEV_TO_SANDBOX_PIPELINE_FEB06_2026.md` |
