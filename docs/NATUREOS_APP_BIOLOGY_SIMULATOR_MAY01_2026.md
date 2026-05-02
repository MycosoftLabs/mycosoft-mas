# NatureOS App — Biology Simulator — May 1, 2026

## What it is

The **Biology Simulator** is the **program landing**: vision and roadmap for simulating life across scales (viruses → organisms → tissues), with **real** links to existing Mycosoft simulators and **server-side probes** of MINDEX modules—not placeholder datasets.

## Why it's in NatureOS

Mushroom-only framing was too narrow; this App communicates the **full-life simulation** thesis while honestly staging Unreal/agentic depth for follow-on work.

## Current capabilities (shipped)

- Route: `/natureos/biology-simulator`.
- Landing lists modules when MINDEX health/genetics/compounds probes succeed; otherwise explains gaps.

## Data sources

- **MINDEX:** `/api/mindex/eagle/health/stats`, genetics and compounds list probes (via website server-side fetch to internal API routes).
- **Existing simulators:** Virtual Petri Dish, Compound Analyser, lifecycle/symbiosis tools (linked).

## Roadmap

1. **`BIOLOGY_SIMULATOR_UNREAL_INTEGRATION_PLAN_MAY01_2026.md`** — Unreal bridge spike.
2. Catalog all simulation entry points in one JSON-driven index (from live registry, not hardcoded demo arrays).

## Related apps

- **Virtual Petri Dish**, **Compound Analyser**, **Physics & Math tools**.

## File locations

- `WEBSITE/website/app/natureos/biology-simulator/page.tsx`
- `WEBSITE/website/components/natureos/apps/biology-simulator/biology-simulator-landing.tsx`

## Replaces / supersedes

- **`/natureos/tools/mushroom-sim`** redirect target for IA (mushroom sim UI may still exist under tools for compatibility).
