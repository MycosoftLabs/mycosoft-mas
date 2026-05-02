# NatureOS Cloud-Style Reorganization — May 1, 2026

**Date:** May 1, 2026  
**Status:** Complete (implementation + docs)  
**Related:** Per-app docs `NATUREOS_APP_*_MAY01_2026.md`; website `next.config.js` redirects; `components/dashboard/nav.tsx` Apps order.

## Purpose

Reorganize the public NatureOS experience into a **fixed-order console** of ten first-class Apps (AWS/GCP-style IA), each documented, with canonical URLs, redirects from legacy paths, a **Tools hub** index, **Biology Simulator** landing (roadmap), and **Aerosol** thin v1 wired to real backends via website BFF routes.

## Ordered Apps (single source of truth: sidebar)

1. Nature Statistics → `/natureos/nature-statistics` (was `/natureos/species`)
2. Fungi Compute → `/natureos/fungi-compute`
3. Earth Simulator → `/natureos/earth-simulator` (was `/natureos/tools/earth-simulator`)
4. Virtual Petri Dish → `/natureos/virtual-petri-dish` (was `/natureos/tools/petri-dish`)
5. Biology Simulator → `/natureos/biology-simulator` (landing; was mushroom-sim route)
6. Compound Analyser → `/natureos/compound-analyser` (was `/natureos/tools/compound-sim`)
7. Aerosol → `/natureos/aerosol` (was `/natureos/tools/spore-tracker`)
8. Ancestry Database → `/natureos/ancestry` (was top-level `/ancestry`)
9. Growth Analytics → `/natureos/growth-analytics` (was `/natureos/tools/growth-analytics`)
10. Tools → `/natureos/tools` (hub index; legacy simulators remain under `/natureos/tools/*`)

## Redirect map (website)

Configured in `WEBSITE/website/next.config.js` (permanent redirects). Examples:

- `/natureos/species` → `/natureos/nature-statistics`
- `/natureos/tools/earth-simulator` → `/natureos/earth-simulator`
- `/natureos/tools/petri-dish`, `/natureos/petri-sim` → `/natureos/virtual-petri-dish`
- `/natureos/tools/mushroom-sim` → `/natureos/biology-simulator`
- `/natureos/tools/spore-tracker` → `/natureos/aerosol`
- `/natureos/tools/compound-sim` → `/natureos/compound-analyser`
- `/natureos/tools/growth-analytics` → `/natureos/growth-analytics`
- `/ancestry`, `/ancestry/:path*` → `/natureos/ancestry`, `/natureos/ancestry/:path*`
- Exact `/natureos/lab-tools` → `/natureos/tools` (deep lab-tools routes preserved where applicable)

## New surfaces

- **Biology Simulator:** `app/natureos/biology-simulator/page.tsx`, `components/natureos/apps/biology-simulator/biology-simulator-landing.tsx` — probes MINDEX modules server-side; links to existing simulators; no mock biosensor data.
- **Aerosol:** `app/natureos/aerosol/page.tsx`, `components/natureos/apps/aerosol/aerosol-dashboard.tsx`; BFF `app/api/natureos/aerosol/{pollen,spores,dust,virus,chemicals,radiation}/route.ts`.
- **Tools hub:** `app/natureos/tools/page.tsx`, `components/natureos/apps/tools-hub/tools-hub-index.tsx` — seven categories; only real hrefs; pending items labeled.

## Backends

- **MINDEX** (VM 189:8000): taxon, observations, stats, compounds, genetics, eagle, emissions, worldview layers, etc.
- **MAS** (VM 188:8001): orchestration, devices, harness, search.
- **CREP / Earth layers:** consumed via existing Earth Simulator and proxy patterns where applicable.
- **NatureOS .NET:** lab tools APIs where wired from website.

## Follow-up plans (out of scope for this reorg)

Shell docs dated May 1, 2026 in `docs/`:

- `BIOLOGY_SIMULATOR_UNREAL_INTEGRATION_PLAN_MAY01_2026.md`
- `COMPOUND_ANALYSER_CHEMPUTER_AGENT_PLAN_MAY01_2026.md`
- `ANCESTRY_ALL_SPECIES_EXPANSION_PLAN_MAY01_2026.md`
- `GROWTH_ANALYTICS_AGENTIC_PLAN_MAY01_2026.md`
- `AEROSOL_VIRUS_RADIATION_FEEDS_PLAN_MAY01_2026.md`
- `NATUREOS_TOOLS_HUB_DEEP_INTEGRATION_PLAN_MAY01_2026.md`

## Verification

- `npm run build` in website repo after route moves.
- Spot-check redirects and new pages on localhost:3010 / sandbox after deploy + Cloudflare purge.

## Supersedes

- For **NatureOS product IA** on the website, this doc supersedes narrative-only references in older completion docs; historic implementation detail remains in `docs/NATUREOS_FULL_PLATFORM_COMPLETE_FEB19_2026.md`.
