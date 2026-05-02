# NatureOS App — Earth Simulator — May 1, 2026

## What it is

The **Earth Simulator** provides CREP-aligned environmental visualization (layers, events, earth intelligence hooks) as a first-class NatureOS App—not nested only under Tools or Infrastructure sidebars.

## Why it's in NatureOS

Earth/environment context is **foundational** for defense, lab, and field workflows; it must appear in the canonical App order and **once** (duplicate Infrastructure entry removed).

## Current capabilities (shipped)

- Route: `/natureos/earth-simulator` (embed moved from `/natureos/tools/earth-simulator`).
- Redirects preserve bookmarks and external links.

## Data sources

- **CREP / tile / weather** integrations as configured on the website (env-driven).
- **MINDEX** worldview/earth endpoints where proxied.
- **Earth-2 Legion** when `EARTH2_API_URL` and related env point to live services.

## Roadmap

1. Document per-layer data contracts in MINDEX (`worldview_*`) with explicit “no data” UX.
2. Align legend/styling with **Aerosol** dust/weather overlays where shared.

## Related apps

- **Aerosol** (dust/weather-adjacent layers).
- **CREP dashboard** (public defense surface).

## File locations

- `WEBSITE/website/app/natureos/earth-simulator/page.tsx`
- Embed components under `WEBSITE/website/components/natureos/tools/earth-simulator-embed.tsx` (or successor)

## Replaces / supersedes

- **`/natureos/tools/earth-simulator`** (301 redirect).
