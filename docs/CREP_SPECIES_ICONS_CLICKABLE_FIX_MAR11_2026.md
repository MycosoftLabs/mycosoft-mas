# CREP Species Icons Clickable Fix — Mar 11, 2026

**Status:** Complete  
**Related:** Species icons (fungi, plants, birds, insects, etc.) were not clickable; species widget popup did not appear.

## Root Cause

1. **deck.gl MapboxOverlay blocking pointer events** — With MapboxOverlay added as a MapLibre control, the deck canvas/overlay was intercepting clicks before they reached MapLibre DOM markers. Markers use `.maplibregl-marker-container`, which needed a higher z-index to sit above the overlay.
2. **Button semantics** — FungalMarker button lacked `type="button"`, which can cause unintended form submission behavior.
3. **Coordinate parsing** — `formatObs` in the bounds-based fetch did not handle `geometry.coordinates` [lng, lat] from APIs that use GeoJSON format.

## Changes Made

### 1. CREPDashboardClient.tsx

- **Marker container z-index and pointer-events**
  - Added CSS for `.crep-map-container .maplibregl-marker-container`:
    - `z-index: 1000 !important` — Ensures markers render above deck.gl overlay
    - `pointer-events: auto !important` — Ensures markers receive clicks
  - Added `.crep-map-container .maplibregl-marker` with `pointer-events: auto !important` for the marker elements.

- **formatObs coordinate parsing**
  - Parse `latitude`/`longitude` or `lat`/`lng`.
  - Fall back to `geometry.coordinates` [lng, lat] when lat/lng fields are missing (GeoJSON-style API responses).

### 2. fungal-marker.tsx

- Added `type="button"` to the clickable button to avoid form submission and ensure consistent click handling.

## Verification

1. Open http://localhost:3010/dashboard/crep
2. Enable the "Nature Observations" (Fungi) layer in the layers panel
3. Pan/zoom to an area with observations (e.g., San Diego, Pacific Northwest)
4. Click a species icon (mushroom, plant, bird, insect, etc.)
5. Confirm the species widget popup appears next to the icon

## Files Modified

- `website/app/dashboard/crep/CREPDashboardClient.tsx` — CSS and `formatObs` updates
- `website/components/crep/markers/fungal-marker.tsx` — `type="button"` on the marker button

## References

- deck.gl MapboxOverlay: https://deck.gl/docs/api-reference/mapbox/mapbox-overlay
- Stack Overflow: Markers not working when deck.gl layers added — use MapboxOverlay as overlay child of map (already in place)
