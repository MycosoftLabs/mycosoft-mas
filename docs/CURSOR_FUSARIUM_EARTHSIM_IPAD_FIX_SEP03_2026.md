# Cursor Fusarium Earth Simulator / iPad fix — Sep 03, 2026

**Date:** September 3, 2026  
**Status:** Website code ready on `fix/fusarium-earthsim-ipad-sep03` (worktree). Public cutover is CI/CD blue-green after merge to `main`.  
**Classification:** UNCLASSIFIED  
**Authority:** Morgan Rockcoons (CEO / CTO / COO / SAO). RJ Ricasata is CFO, not COO.  
**CUI:** None. No fabricated tracks. Loopback **8212** is not the public fix.

**Related:** `CURSOR_FUSARIUM_TWINS_HOST_PUBLIC_MOUNT_SEP02_2026.md` (PR 293/294), `CURSOR_FUSARIUM_OWNER_AUTH_LIVE_SEP02_2026.md`

## Live inspection (anonymous)

Inspected `https://mycosoft.com` before editing. Owner password was **not** completed: `MYCOSOFT_DEFAULT_PASSWORD` from the gitignored vault is not the live Supabase owner password (same finding as Sep 02). Browser MCP was unavailable. No password was logged or written.

| URL | HTTP | Notes |
|---|---|---|
| `/fusarium` | 307 | → `/fusarium/login?redirectTo=%2Ffusarium` |
| `/fusarium/login` | 200 | Site `app/layout` + marketing Header present (`sticky top-0 z-[200]`) |
| `/fusarium/earth-simulator` | 307 | → login with `redirectTo=/fusarium/earth-simulator` (route exists) |
| `/fusarium/aerosol` | 307 | → login with that path (route exists) |
| `/fusarium/gcs` | 307 | → login (route exists) |
| `/fusarium/crep` | 307 | → login (route exists) |
| `/natureos/earth-simulator` | 200 | Working civilian globe (Morgan’s comparison target) |
| `/natureos/aerosol` | 200 | Working |
| `/api/fusarium/operator/state` | 401 | Honest withhold — not LIVE |
| `/api/health` | 200 | Public origin up |

Live HTML MapLibre guard on the public image still matches only:

`/(natureos/earth-simulator|natureos/crep|dashboard/crep)(/|$)`

It does **not** include `/fusarium/earth-simulator`.

## Root cause (verified in source, not assumed)

Public Fusarium is website Next twins-host (`/fusarium/...`), not a `basePath` / WASM 404 and not 8212.

1. **Site Header overlay (iPad / tablet).** `AppShellProviders` always rendered `<Header />` (`z-[200]`) except Psathyrella / Launchpad. Operator chrome + `100dvh` globe sat under that bar. Tablet sidebar was `z-index: 6`. Content looked “not loaded.”
2. **Earth Sim path checks were NatureOS-only.** Staged boot, event DOM caps, MapLibre guard, overlay skip, SW skip used `/natureos/earth-simulator` only. Fusarium globe ran as the full CREP dashboard under dual chrome → blank / OOM.
3. **App workspace padding.** `isAppRoute` missed siblings; classification notice could steal height from the globe.
4. **Layout 401/MFA `redirectTo`.** Dashboard layout could bounce to `/fusarium` instead of the requested app. Middleware already preserved the path; layout now reads `x-mycosoft-pathname`.
5. **NatureOS zoom lag.** Shared `getEarthSimulatorEventDomCap` could keep climbing at city zoom. Tightened to a plateau (max 280). Did not replace the globe implementation.

## What changed (website worktree only)

Dirty local `WEBSITE/website` (`fix/launchpad-ingest-bearer-alias`) was **not** reset. Edits are in `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-earthsim-ipad-fix`. Fusarium repo was **not** edited. Claude-owned classification / operator CSS implementation files were not rewritten except the website-owned `fusarium-operator.css` chrome (z-index, dvh, tablet, 44px targets).

| File | Change |
|---|---|
| `lib/auth/fusarium-paths.ts` | New client-safe path helpers (no `next/server`) |
| `lib/auth/fusarium-owner-gate.ts` | Re-exports those helpers |
| `components/providers/AppShellProviders.tsx` | Full-bleed on operator paths using **real** `pathname` (no Header flash after hydrate) |
| `components/fusarium/fusarium-layout-client.tsx` | `html/body.fusarium-operator`; app routes include earth-simulator, aerosol, crep, gcs |
| `app/fusarium/fusarium-operator.css` | `100dvh` lock, safe-area, tablet ≤1180px, sidebar z-40 / scrim z-30, 44px touch |
| `app/fusarium/(dashboard)/layout.tsx` | MFA/401 `redirectTo` from `x-mycosoft-pathname` |
| `middleware.ts` | Sets `x-mycosoft-pathname` |
| `lib/crep/earth-simulator-boot.ts` | `isEarthSimulatorPathname` / `isGlobeCrepPathname`; event cap 160–280 |
| `lib/crep/production-first-load.ts` | Uses shared helper |
| `app/dashboard/crep/CREPDashboardClient.tsx` | Earth Sim / globe / SW skip via helper |
| `app/layout.tsx` | MapLibre guard includes `fusarium/earth-simulator` |
| `components/ui/map.tsx`, CREP overlays, `lib/ground-station/context.tsx`, `components/dashboard/top-nav.tsx` | Same path helper |
| `__tests__/lib/crep/earth-simulator-boot.test.ts` | Path + cap tests |
| `__tests__/lib/auth/fusarium-paths.test.ts` | Full-bleed vs public login/launchpad |

## Routes to verify after cutover

Owner session required (`morgan@mycosoft.org`). This lane could not click past login.

| Route | Expect |
|---|---|
| `/fusarium/earth-simulator` | Same CREP globe composition as NatureOS; staged boot; no site Header |
| `/fusarium/aerosol` | Aerosol workbench loads, or honest empty — never a fake globe |
| `/fusarium/gcs`, `/fusarium/crep` | Full-bleed workspace, no marketing nav overlay |
| `/fusarium/login`, `/fusarium/launchpad` | Marketing Header **kept** |
| `/natureos/earth-simulator` | Still 200; zoom should stay flatter (event DOM cap) |

## Tablet viewports

Checked in CSS / layout (browser MCP down; post-login click-through not done):

| Viewport | Intent |
|---|---|
| 768px | Hamburger; sidebar drawer z-40; workspace full width; no horizontal overflow |
| 1024px | Same tablet query (`max-width: 1180px`) |
| ~820×1180 | iPad; site Header must not paint; `min-h-dvh` / `100dvh`; touch ≥44px |

## Tests

- `tsx` asserts on path helpers + event cap: **pass**
- Jest in this worktree failed to boot (`clearMocksOnScope`) when junctioned to the dirty tree’s `node_modules` — not used as a pass signal

## Remaining blockers

1. **Owner session not completed** — cannot prove live Earth Sim / Aerosol paint until Morgan signs in.
2. **Browser MCP unavailable** — no tablet screenshot pass in this lane.
3. **BFF honesty** — `/api/fusarium/operator/state` stays 401 anonymous; unbound runtime stays **RUNTIME UNREACHABLE**. That is not a globe 404.
4. **NatureOS zoom** — event-marker DOM is capped. High-res tile / WebGL memory can still hitch; globe implementation was not rewritten.
5. **Public image** still has the old MapLibre guard until this branch is blue-green cut over.

## Deploy rule

One deploy owner. Do not stop the live primary. Candidate HTTP **200** before cutover. NAS mount required: `/opt/mycosoft/media/website/assets:/app/public/assets:ro`. Do not treat 8212 as the public origin.
