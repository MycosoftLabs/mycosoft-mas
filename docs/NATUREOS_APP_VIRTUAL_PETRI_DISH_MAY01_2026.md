# NatureOS App — Virtual Petri Dish — May 1, 2026

## What it is

**Virtual Petri Dish** is the culture-growth simulator workspace with optional **MyceliumSeg** validation when the segmentation API is configured—no fabricated colony metrics.

## Why it's in NatureOS

Petri-scale simulation is a **daily lab metaphor**; elevating it to a top-level App removes ambiguity with generic “tools” naming.

## Current capabilities (shipped)

- Route: `/natureos/virtual-petri-dish` (from `/natureos/tools/petri-dish`).
- Embeds `PetriDishEmbed` / validation panel reads `MYCELIUMSEG_API_URL` / `NEXT_PUBLIC_MYCELIUMSEG_API_URL`.

## Data sources

- **MINDEX:** validation datasets via panel configuration.
- **MyceliumSeg API:** optional service (typical port 8010) when deployed.

## Roadmap

1. Server-side probe endpoint for segmentation health (optional) to drive hub “pending” badges without mock counts.
2. Stronger link-out from **Biology Simulator** landing.

## Related apps

- **Biology Simulator**, **Fungi Compute**, **Tools hub** (AI Analysis category).

## File locations

- `WEBSITE/website/app/natureos/virtual-petri-dish/page.tsx`
- `WEBSITE/website/components/natureos/tools/petri-dish-embed.tsx`
- `WEBSITE/website/components/scientific/myceliumseg-validation-panel.tsx`

## Replaces / supersedes

- **`/natureos/tools/petri-dish`**, **`/natureos/petri-sim`** (redirects).
