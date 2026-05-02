# NatureOS App — Fungi Compute — May 1, 2026

## What it is

**Fungi Compute** is the NatureOS workspace for fungal bio-compute: protocols, FCI-adjacent tooling links, and integration surfaces that connect lab compute narratives to MINDEX and device telemetry where configured.

## Why it's in NatureOS

Fungi-first compute is a **core Mycosoft differentiator**; it belongs in the fixed App list so operators find it without hunting the Tools section.

## Current capabilities (shipped)

- Route: `/natureos/fungi-compute` (existing implementation retained).

## Data sources

- **MINDEX:** genetics, compounds, observation contexts as exposed by existing page/API proxies.
- **Devices:** MycoBrain / registry when pages link to device flows.

## Roadmap

1. Explicit health banners when MINDEX/device backends are unreachable (no fake metrics).
2. Cross-links from **Compound Analyser** and **Biology Simulator** landing.

## Related apps

- **Compound Analyser**, **Virtual Petri Dish**, **Growth Analytics**.

## File locations

- `WEBSITE/website/app/natureos/fungi-compute/` (existing pages)

## Replaces / supersedes

- None (ordering/navigation only in this reorg).
