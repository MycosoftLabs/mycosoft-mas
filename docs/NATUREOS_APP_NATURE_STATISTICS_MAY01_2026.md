# NatureOS App — Nature Statistics — May 1, 2026

## What it is

The **Nature Statistics** app is the primary workspace for species-level and aggregate biological statistics on mycosoft.com NatureOS—taxonomy-aware views, observation-backed metrics, and links into MINDEX-backed explorers.

## Why it's in NatureOS

Platform users need a **single entry** for “how much nature data do we have, where, and for which taxa?” aligned with MINDEX and CREP-aligned observation pipelines—not buried under legacy `/species` naming.

## Current capabilities (shipped)

- Route: `/natureos/nature-statistics` (redirect from `/natureos/species`).
- Renders existing Nature Statistics view/components migrated with the route rename.

## Data sources

- **MINDEX:** taxon, observations, stats routers via website `/api/mindex/*` proxies.
- **MAS:** optional orchestration for derived metrics where wired.

## Roadmap (next milestones)

1. Surface freshness/lag indicators per dataset with honest empty states.
2. Tie prominent KPIs to documented ETL job schedules in MINDEX.

## Related apps

- **Ancestry Database** — drill-down taxonomy and species detail.
- **Earth Simulator** — spatial context for observations.

## File locations

- `WEBSITE/website/app/natureos/nature-statistics/page.tsx`
- Sidebar: `WEBSITE/website/components/dashboard/nav.tsx`

## Replaces / supersedes

- Public path **`/natureos/species`** (301 redirect).
