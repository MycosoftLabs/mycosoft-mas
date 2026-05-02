# NatureOS App — Growth Analytics — May 1, 2026

## What it is

**Growth Analytics** is the NatureOS workspace for growth curves and biological analytics tied to real telemetry/datasets where integrated—no fabricated series.

## Why it's in NatureOS

Growth metrics are how labs close the loop between devices, experiments, and publication-ready charts; it belongs in the fixed App list.

## Current capabilities (shipped)

- Route: `/natureos/growth-analytics` (from `/natureos/tools/growth-analytics`).

## Data sources

- **MINDEX / device APIs** as wired by the existing page implementation.
- **MAS** optional aggregation endpoints when configured.

## Roadmap

1. **`GROWTH_ANALYTICS_AGENTIC_PLAN_MAY01_2026.md`** — agent-driven interpretation of uploaded runs.
2. Explicit dataset picker sourced from MINDEX only.

## Related apps

- **Virtual Petri Dish**, **Devices / telemetry**, **Fungi Compute**.

## File locations

- `WEBSITE/website/app/natureos/growth-analytics/page.tsx`

## Replaces / supersedes

- **`/natureos/tools/growth-analytics`** (301 redirect).
