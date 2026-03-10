# CREP iNaturalist → MINDEX ETL and Local-First Design

**Date**: March 9, 2026
**Status**: Design
**Related**: CREP Dashboard, MINDEX, `/api/crep/fungal`, Level of Detail (LOD)

---

## Overview

This document specifies the architecture for:
1. **iNaturalist → MINDEX ETL** – Bulk and continuous import of iNaturalist observations into MINDEX
2. **Clone-on-first-display** – When CREP shows data from iNaturalist API, immediately clone it into MINDEX; subsequent requests use local MINDEX
3. **Level of Detail (LOD)** – Zoom-based rendering: region clusters → area clusters → individual markers
4. **Local-first propagation** – CREP always prefers MINDEX; external APIs only for discovery and backfill

---

## Current State

### Data Flow (As Implemented)

- **CREP `/api/crep/fungal`**: MINDEX primary, iNaturalist/GBIF fallback when MINDEX is empty
- **MINDEX `obs.observation`**: Table `obs.observation` with `source`, `source_id`, `taxon_id`, `latitude`, `longitude`, `media`, `metadata`
- **No clone-on-display**: When fallback returns iNaturalist data, it is **not** written back to MINDEX
- **No LOD**: All markers at same resolution regardless of zoom

### Gap

- iNaturalist data shown on the map is **not** persisted to MINDEX
- No bulk iNaturalist ETL job populates MINDEX
- Map circles for life forms may not open detail widgets (separate fix in progress)
- No zoom-based LOD; all observations rendered individually even at low zoom

---

## Target Architecture

### 1. iNaturalist → MINDEX ETL (Bulk + Scheduled)

| Component | Location | Purpose |
|-----------|----------|---------|
| ETL job | MINDEX `mindex_etl/jobs/` or MAS script | Fetch iNaturalist observations by region/taxon; transform to MINDEX `obs.observation` format; upsert by `source_id` |
| Schedule | Cron / n8n | Run daily or on demand for priority regions (e.g. FUNGAL_HOTSPOT_REGIONS) |
| Schema | `obs.observation` | `source='inat'`, `source_id=<iNaturalist observation id>` |

**Field mapping** (iNaturalist → MINDEX):

- `id` → `source_id` (store as string, e.g. `"12345678"`)
- `taxon.id` → `taxon_id` (link to MINDEX taxa or create)
- `geojson.coordinates` → `latitude`, `longitude`
- `observed_on` / `created_at` → `observed_at`
- `user.login` → `observer`
- `quality_grade` → `metadata.quality_grade`
- `photos[0].url` → `media`
- `place_guess` → `metadata.place_guess`
- `uri` → `metadata.uri` (for "View on iNaturalist" link)

### 2. Clone-on-First-Display

**Trigger**: When `/api/crep/fungal` returns observations from iNaturalist (or GBIF) because MINDEX had none or insufficient data for the requested bounds.

**Action**:
1. For each observation returned from iNaturalist/GBIF, check if `source_id` exists in MINDEX
2. If not, POST to MINDEX `obs.observation` (or a dedicated clone endpoint) to persist
3. Fire-and-forget async clone; do not block the response
4. On next request (or refresh), MINDEX will have the data → serve from MINDEX

**Implementation options**:
- **Option A**: Website API route calls MINDEX `POST /api/mindex/observations/clone` with batch of external observations
- **Option B**: MINDEX has an internal "clone from external" endpoint; CREP passes `?clone=true` and MINDEX performs the clone after responding
- **Option C**: Background job triggered by CREP; enqueue observation IDs to clone; worker writes to MINDEX

**Recommendation**: Option A – `/api/crep/fungal` after returning iNaturalist/GBIF data, calls MINDEX clone endpoint in background (fire-and-forget).

### 3. Level of Detail (LOD)

| Zoom Level | Behavior | Data Source |
|------------|----------|-------------|
| Low (e.g. &lt; 8) | Show clusters by region; count per cluster | MINDEX aggregated or bbox counts |
| Medium (8–12) | Clusters by grid cell; summary counts | MINDEX bbox query with clustering |
| High (&gt; 12) | Individual markers; click opens detail widget | MINDEX bbox query; full observation data |

**LOD checks**:
- CREP must not dismiss popup when user clicks a deck.gl entity (fixed via `lastEntityPickTimeRef` + map click handler)
- Entity click must pass full `entity.properties` (FungalObservation) to selection so widget has data
- Clusters must be clickable to zoom in or show cluster summary

### 4. Local-First Routing

**Priority**:
1. MINDEX (local) – always query first
2. iNaturalist/GBIF – only when MINDEX returns empty for the requested bbox/kingdom
3. On external fallback: clone results to MINDEX (async)
4. Next refresh: MINDEX has data → local propagation

**Check**: Before falling back, verify MINDEX with bbox filter. If MINDEX has data, use it. If not, fetch external, return to user, then clone.

---

## Implementation Checklist

- [ ] **MINDEX**: Add `POST /api/mindex/observations/clone` (or equivalent) to accept batch of observations from iNaturalist/GBIF, upsert by `source`+`source_id`
- [ ] **MINDEX ETL**: Create `inaturalist_observations_sync` job to fetch by region/taxon and upsert to `obs.observation`
- [ ] **CREP API**: After returning iNaturalist/GBIF data, call MINDEX clone endpoint in background
- [ ] **CREP Map**: Implement LOD – clustering at low zoom, individual markers at high zoom
- [ ] **CREP Map**: Ensure all life-form circles (fungal, plant, animal, etc.) open detail widget on click (entity.properties + no dismiss on entity pick)
- [ ] **Documentation**: Update CREP data flow docs to reflect clone-on-display and local-first

---

## Related Documents

- `docs/DEVICE_UI_VERIFICATION_COMPLETE_MAR07_2026.md` – CREP/Device UI verification
- MINDEX `mindex_api/routers/observations.py` – Current observations API
- WEBSITE `app/api/crep/fungal/route.ts` – CREP fungal/life data API (MINDEX primary, iNaturalist fallback)
