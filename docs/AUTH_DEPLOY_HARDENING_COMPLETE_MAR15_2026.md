# Auth, Deploy, and Live Performance Plan — Complete

**Date**: March 15, 2026  
**Status**: Complete  
**Related plan**: `.cursor/plans/auth_deploy_hardening_c07676ec.plan.md`

## Overview

Execution completed for the Auth Deploy Hardening plan: unified website auth on Supabase, CI/CD-first website deployment, OAuth/gated-page verification, above-the-fold video hardening, CREP/Search performance reductions, and documentation closeout. No credential rotation or git-history purge was performed (out of scope).

## Delivered

### 1. Auth unification (auth-unify)
- Supabase is the single active website auth path; production-critical dependence on legacy NextAuth fallback removed from `lib/auth/api-auth.ts`.
- Runtime enforcement aligned with canonical route map in `lib/access/routes.ts`; middleware protects all gated paths from the route config, not only `INFRASTRUCTURE_PATHS`.
- Sensitive sections (`/security`, `/platform/*`, `/ethics-training`, `/dashboard`, `/profile`, `/billing`, etc.) consistently enforced.
- Auth callback in `app/auth/callback/route.ts` hardened for mycosoft.com / www.mycosoft.com / sandbox.mycosoft.com parity and cookie/session consistency.

### 2. Deploy CI/CD-first (deploy-cicd)
- GitHub Actions is the primary website production deploy path via `.github/workflows/deploy-to-vms.yml` (MAS repo); website job targets Sandbox VM 187, rebuilds image, restarts container with NAS mount, purges Cloudflare.
- `_rebuild_sandbox.py` and `_sandbox_env_sync.py` in the website repo are documented as fallback/ops tools, not the default production path.
- Public Supabase values (e.g. client-side) supplied via CI/CD and VM runtime/build config; no requirement to sync broad secret bundles from local `.env.local` for standard deploys.
- Production-on-sandbox topology remains as in `docs/MYCOSOFT_COM_PRODUCTION_SANDBOX_ROUTE_MAR13_2026.md`; docs updated to reference the new primary deploy path.

### 3. OAuth verification (oauth-verify)
- Supabase URL/anon-key usage verified across login, callback, middleware, and gated APIs.
- Callback and redirect expectations for mycosoft.com, www.mycosoft.com, sandbox.mycosoft.com, and local dev aligned with `docs/SUPABASE_OAUTH_PARITY_MYCOSOFT_COM_MAR14_2026.md`.
- OAuth-authenticated session for Morgan@mycosoft.org verified for access to protected website sections.

### 4. Video instant-start (video-instant-start)
- Above-the-fold hero/background videos standardized on the hardened pattern from `components/ui/autoplay-video.tsx` (AutoplayVideo).
- Homepage hero, About hero, Apps hero, Defense hero, and device pages (mushroom1, sporebase) updated; legacy raw `<video>` and touchstart hacks removed.
- Asset pathing normalized to avoid live Linux/NAS mismatches (spaces/case-sensitive filenames).

### 5. Live performance (live-perf)
- **CREP dashboard** (`app/dashboard/crep/CREPDashboardClient.tsx`):
  - Main data refresh interval increased from 15s to 60s.
  - ServicesPanel: MycoBrain check only when tab is visible; interval 15s → 30s; visibilitychange listener with cleanup.
  - Satellites: bounded initial load (3 categories: stations, starlink, active) then full refresh (6 categories) on 60s poll via `initialSatelliteLoadDoneRef`; sequential fetch to reduce cold-path parallel calls.
- **Search**: Website search routes (`/api/search/unified`, `/api/search/unified-v2`) remain MAS-first thin proxy over backend; no duplicate fallback fan-out introduced; existing behavior retained.
- **Homepage/search**: No heavy motion/media changes in this pass; CREP and satellite cold-path reductions are the highest-impact items delivered.

### 6. Docs closeout (docs-closeout)
- This completion doc created and added to `docs/MASTER_DOCUMENT_INDEX.md` and `.cursor/CURSOR_DOCS_INDEX.md`.

## Verification

- Website build and auth checks run locally.
- OAuth login flow verified for Morgan@mycosoft.org; protected sections checked after login.
- CREP dashboard: bounded initial satellite load and 60s refresh verified; ServicesPanel visibility gating in place.
- Deploy path: CI/CD workflow and fallback scripts documented; production deploy via GitHub Actions is the primary path.

## Boundaries Respected

- No full VM/password/token/key rotation or git-history rewriting.
- If any runtime issue is traced to already-exposed credentials or broken upstream secret state, the separate rotation plan must be executed.

## Related Documents

- `docs/MYCOSOFT_COM_PRODUCTION_SANDBOX_ROUTE_MAR13_2026.md` — Production via Sandbox VM
- `docs/SUPABASE_OAUTH_PARITY_MYCOSOFT_COM_MAR14_2026.md` — OAuth parity and redirects
- `WEBSITE/website/docs/AUTH_TROUBLESHOOTING_MAR15_2026.md` — Auth troubleshooting
- `.cursor/plans/auth_deploy_hardening_c07676ec.plan.md` — Source plan (do not edit)
