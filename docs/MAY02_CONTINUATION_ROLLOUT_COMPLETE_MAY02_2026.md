# MAY02 Continuation & Operationalization Rollout — Complete (May 02, 2026)

**Date:** May 02, 2026  
**Status:** Complete (P0–P2 operationalization + P3 hygiene / queue closure)  
**Related:** `.cursor/plans/may02_continuation_rollout_02414f10.plan.md` (source plan — not edited)

## Summary

| Track | Outcome |
|-------|---------|
| **P0 lazy-registry** | `LazyCREPDashboard` repointed; broken lazy exports removed; `npm run build` unblocked (completed in prior thread). |
| **P0 MINDEX 189** | Inventory + All-Life migration applied; API restarted (prior thread). |
| **P0 MAS 188** | Heartbeat summary routes + missing routers pushed; orchestrator restarted (prior thread). |
| **P0 n8n 188** | All-Life workflow imported via `docker exec` when sync-both rate-limited (prior thread). |
| **P1 Sandbox 187** | Website blue/green rebuild from `main` (prior thread). **Cloudflare:** `scripts/cloudflare_purge_zone_from_mas_env.py` now loads creds from MAS **or** `WEBSITE/website/.credentials.local` — run after each prod deploy. |
| **P1 Petri v2** | Rust `petri_engine` **borrow-check fixes** (`chemistry.rs`, `world.rs`) so release Docker build succeeds (`fix(petri_engine)` on `main`). Added `services/petri_engine/Dockerfile`, `scripts/myceliumseg/Dockerfile`, `GET /health` on seg API, `scripts/deploy_petri_v2_stack_vm187.py` (health curls use `curl -sS` + `|| true` so `pipefail` does not false-fail the script). **`docs/PETRI_DISH_V2_RUNBOOK_MAY02_2026.md`**. **`scripts/set_petri_engine_env_mas188.py`** appends `PETRI_ENGINE_V2_URL` to **`/home/mycosoft/mycosoft/mas/.env`** (matches `deploy/mas-orchestrator.service` `EnvironmentFile`) and restarts `mas-orchestrator`. Verified **`GET /api/simulation/petri/v2/health`** → `petri_engine_service` ok. |
| **P2 Verification** | **`scripts/natureos_bff_route_inventory.py`** added; reports **64** `route.ts` handlers under `app/api/natureos`. Petri: **187:8050** + **188** proxy health OK from LAN. Full UI/matrix: `docs/NATUREOS_STAGING_MATRIX_MAY02_2026.md` + Petri runbook + MYCA Alive docs (prior thread). |
| **P3 May01 shells** | No full implementations in this rollout (multi-sprint). Queue: **`docs/P3_MAY01_IMPLEMENTATION_QUEUE_MAY02_2026.md`**; footers added to all six MAY01 plan shells. |
| **P3 waypoints** | Supabase migration shipped: `WEBSITE/website/supabase/migrations/20260502_natureos_crep_waypoints.sql` (RLS). **localStorage → table** UI migration remains a follow-up. |
| **P3 entitlements** | Draft contract: **`docs/CREP_AGENT_KEY_SCOPE_CONTRACT_DRAFT_MAY02_2026.md`** — implementation pending key store design. |
| **P3 CREP chat audit** | **Single** `MYCAChatWidget` usage in `CREPDashboardClient` (grep — no duplicate mount found). |
| **P3 sitemap** | **`app/sitemap.ts`** already includes `/natureos` and `/natureos/earth-simulator`. |
| **P3 MYCA phase docs** | Optional per-phase `_COMPLETE` splits **not** produced (rolled into existing MYCA Alive completion docs). |
| **P3 dashboard voice hook** | Removed unused **`hooks/useDashboardVoice.ts`** and barrel exports from **`hooks/index.ts`**. |
| **P3 docker import guards** | **`mycosoft_mas/runtime/agent_pool.py`**: optional `docker` SDK — pool disables cleanly when package missing (local dev). |
| **P3 doc indexes** | This doc + P3 queue + agent contract + runbook; manifest refresh via `python scripts/build_docs_manifest.py`. |

## Verify

1. **Cloudflare:** `python scripts/cloudflare_purge_zone_from_mas_env.py` → success JSON.  
2. **Petri (after deploy script):** `curl http://192.168.0.187:8050/health` and `curl http://192.168.0.188:8001/api/simulation/petri/v2/health` (with `PETRI_ENGINE_V2_URL` set).  
3. **Website BFF:** `curl -s http://localhost:3010/api/simulation/petri/v2/health` (dev) proxies MAS.  
4. **BFF count:** `python scripts/natureos_bff_route_inventory.py` → 64 files.  
5. **Supabase:** apply `20260502_natureos_crep_waypoints.sql` in target project; enable Realtime on `crep_waypoints` if required.

## Lessons learned

- Credential loaders must accept **website** `.credentials.local` when MAS repo copy is absent (Cloudflare purge).  
- **Petri** deploy requires fresh **git on 187** (`petri_engine` not present on stale clones).  
- P3 “plan shells” should be closed with an explicit **queue doc** rather than implying code shipped.  
- **MAS orchestrator env:** Prefer appending vars to **`EnvironmentFile`** (`~/mycosoft/mas/.env`) over interactive sudo; use **`sudo -S` without a PTY** if restart must be automated (avoids password echo in captured streams).  
- If any VM credential appeared in local assistant or terminal logs, **rotate** per `no-hardcoded-secrets` / incident policy.

## Follow-ups

- **MAS .env:** If `PETRI_ENGINE_V2_URL` must change, edit `/home/mycosoft/mycosoft/mas/.env` on **188** or re-run **`scripts/set_petri_engine_env_mas188.py`**.  
- **Sandbox 187 git:** Some paths under `~/mycosoft/mas` may be root-owned — `sudo chown -R mycosoft:mycosoft /home/mycosoft/mycosoft/mas` restores clean `git reset --hard` (optional).  
- Implement **agent key scope** per draft contract.  
- **localStorage** waypoint migration to Supabase client.  
- Execute **`P3_MAY01_IMPLEMENTATION_QUEUE_MAY02_2026.md`** in separate threads.
