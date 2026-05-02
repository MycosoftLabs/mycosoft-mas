# NatureOS App — Aerosol — May 1, 2026

## What it is

**Aerosol** is a thin v1 dashboard for six airborne-layer themes—pollen, spores, dust, virus, chemicals, radiation—with **real BFF proxies** to MINDEX (and honest empty states for feeds not yet wired).

## Why it's in NatureOS

Airborne environmental risk sits between **Earth Simulator** and health/defense narratives; it replaces the misleading “spore tracker only” framing while leaving deep epidemiology/radiation feeds to a follow-on plan.

## Current capabilities (shipped)

- Route: `/natureos/aerosol`.
- BFF: `GET` handlers under `/api/natureos/aerosol/{pollen,spores,dust,virus,chemicals,radiation}`.

## Data sources

- **MINDEX:** observations (spores), emissions (chemicals), worldview/pollen where implemented in BFF; virus/radiation return explicit pending metadata until feeds exist.
- **CREP/weather:** dust alignment documented to mirror Earth Simulator patterns.

## Roadmap

1. **`AEROSOL_VIRUS_RADIATION_FEEDS_PLAN_MAY01_2026.md`** — public health + radiation ingestion.
2. Shared map component parity with CREP Earth layers.

## Related apps

- **Earth Simulator**, **Nature Statistics**, **CREP**.

## File locations

- `WEBSITE/website/app/natureos/aerosol/page.tsx`
- `WEBSITE/website/components/natureos/apps/aerosol/aerosol-dashboard.tsx`
- `WEBSITE/website/app/api/natureos/aerosol/*/route.ts`

## Replaces / supersedes

- **`/natureos/tools/spore-tracker`** as primary IA entry (301 redirect).
