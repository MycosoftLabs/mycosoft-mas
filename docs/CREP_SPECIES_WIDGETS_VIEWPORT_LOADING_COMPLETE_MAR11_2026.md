# CREP Species Widgets & Viewport Loading — Complete

**Date**: March 11, 2026
**Status**: Complete
**Related**: CREP dashboard, iNaturalist-style loading, fungal observations

## Overview

Fixed CREP species markers so they load from map viewport (iNaturalist-style) instead of being overwritten by a global fetch. FilterToggle layout stability improved.

## Root Cause

`fetchData()` ran on mount and every 15 seconds, requesting `/api/crep/fungal` **without map bounds**, then overwrote `fungalObservations` and replaced bounds-based data from the map effect.

## Changes Delivered

### 1. Bounds-only fungal data
- Removed fungal fetch from `fetchData()` in `CREPDashboardClient.tsx`
- Fungal data now comes **only** from the bounds effect; `fetchData()` no longer overwrites it

### 2. Bounds effect – AbortController
- Added `AbortController` in the bounds effect
- Cleanup calls `ctrl.abort()` and `clearTimeout(t)` when `mapBounds` changes or on unmount

### 3. FilterToggle layout
- `components/crep/map-controls.tsx`: `FilterToggle` updated with:
  - `min-w-[72px]`
  - `overflow-hidden`
  - `[contain:layout]`
  - `min-w-0 truncate` on the label span to avoid bounce when labels change (e.g. "Fungi" vs "Fungi (12)")

### 4. Data flow
- `mapBounds` from map `onLoad`, `moveend`, `zoomend`
- Debounced (400 ms) bounds effect fetches `/api/crep/fungal?north=&south=&east=&west=&nocache=true`
- `fungalObservations` → `visibleFungalObservations` (LOD, groundFilter, fungalSpeciesFilter) → deck entities → `EntityDeckLayer`

## Verification

1. **Fungal API**: `/api/crep/fungal` accepts bounds (`north`, `south`, `east`, `west`); returns observations (MINDEX → iNaturalist/GBIF fallback).
2. **CREP dashboard**: http://localhost:3010/dashboard/crep
3. **To see species markers**: Pan/zoom to a data-rich area (e.g. Oregon: lat 44–45, lng -123 to -122). At global zoom (zoom 2) the viewport may have no or few observations; zoom in to regional level.

## Files Modified

| File | Change |
|------|--------|
| `website/app/dashboard/crep/CREPDashboardClient.tsx` | Removed fungal from fetchData; bounds effect with AbortController |
| `website/components/crep/map-controls.tsx` | FilterToggle min-width, contain, truncate for stable layout |

## Known Behavior

- **Initial load (zoom 2, global)**: May show 0 observations — API uses viewport bounds; global view may have no MINDEX data in that bbox.
- **Zoom in to region**: Species dots appear as bounds effect refetches for the new viewport.

## Related Documents

- [CREP Integration Test Plan](../WEBSITE/website/docs/CREP_INTEGRATION_TEST_PLAN_MAR10_2026.md)
- [CREP iNaturalist MINDEX ETL](./CREP_INATURALIST_MINDEX_ETL_MAR09_2026.md)
