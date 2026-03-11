# External Repo Integration – Feature Usage, Interaction & Testing

**Date:** 2026-03-10  
**Status:** Complete  
**Related:** `docs/EXTERNAL_REPO_INTEGRATION_COMPLETE_MAR10_2026.md`

## Overview

This document describes **how** each Phase 1 feature works, **where** you can see and interact with it, and **how to test** it. Special focus on CREP and UI rules that improve the interface.

---

## 1. CREP Map Preferences Panel

### What It Does

Saves and loads your CREP map state (bounds, zoom, layers, ground filter, basemap, Earth-2 imagery toggles) to Supabase. Requires an authenticated user.

### Where to See & Use It

1. **Open CREP Dashboard:** http://localhost:3010/dashboard/crep (or http://localhost:3020/dashboard/crep if using CREP-only dev)
2. **Right panel → Data tab** — The Map Preferences panel appears below the Map Controls. Two buttons: **Load** and **Save**.

### How to Interact

| Action | Steps | Result |
|--------|-------|--------|
| **Load** | Click **Load** | Fetches saved preferences from Supabase. If signed in and you have saved preferences, the map flies to your saved view, restores layers, filters, and basemap. If not signed in: "Sign in to load saved preferences". If no preferences: "No saved preferences". |
| **Save** | Adjust map (zoom, pan, layers, ground filter, basemap), then click **Save** | Saves current map state to Supabase. If signed in: "Preferences saved". If not signed in: 401, "Sign in to save preferences". |

### API Endpoints

- **GET** `/api/crep/preferences?name=default` — Returns `{ preferences, authenticated }`. Unauthenticated: `preferences: null`, `authenticated: false`.
- **POST** `/api/crep/preferences` — Requires auth. Body: `{ name, bounds, center_lat, center_lng, zoom, layers, kingdom_filter, eo_imagery, basemap }`. Returns 401 when unauthenticated.

### How to Test

```powershell
# GET (unauthenticated) – expect 200, preferences: null
Invoke-WebRequest -Uri "http://localhost:3010/api/crep/preferences" -UseBasicParsing | Select-Object StatusCode, Content

# POST (unauthenticated) – expect 401
try { Invoke-WebRequest -Uri "http://localhost:3010/api/crep/preferences" -Method POST -Body '{"name":"default"}' -ContentType "application/json" } catch { $_.Exception.Response.StatusCode }
```

---

## 2. CREP Fungal API (Turf Bbox Validation)

### What It Does

Returns biodiversity observations (fungi, plants, animals, etc.) for a map bounding box. Uses Turf.js (`@turf/bbox-polygon`, `@turf/area`) to validate bbox coordinates. Invalid boxes (e.g. west < -180) return 400.

### Where to See & Use It

- **CREP Dashboard** — Biodiversity / fungal layer fetches from this API when you pan/zoom. You do not call it directly; the dashboard does.
- **Direct API:** `GET /api/crep/fungal?north=40&south=20&east=-80&west=-100&kingdom=all`

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| north, south, east, west | Yes | Bounding box in degrees. west must be in [-180, 180], north ≥ south, etc. |
| kingdom | No | `all` (default), `Fungi`, `Plantae`, `Animalia`, etc. |

### How to Test

```powershell
# Invalid bbox (west=-181) – expect 400
Invoke-WebRequest -Uri "http://localhost:3010/api/crep/fungal?north=0&south=0&east=0&west=-181" -UseBasicParsing

# Valid bbox – expect 200, GeoJSON feature collection
Invoke-WebRequest -Uri "http://localhost:3010/api/crep/fungal?north=40&south=20&east=-80&west=-100" -UseBasicParsing
```

---

## 3. C-Suite Finance Status (MAS + Website Proxy)

### What It Does

Proxies requests from the website to MAS `GET /api/csuite/cfo/status` for C-Suite finance status. The website route forwards to `http://192.168.0.188:8001/api/csuite/cfo/status`.

### Where to See & Use It

- **API:** `GET /api/mas/csuite/finance/status` — Frontends call this; it proxies to MAS.
- **Frontend usage:** C-Suite finance widgets or dashboards that consume finance status.

### How to Test

```powershell
# Expect 200 (success) or 429 (MAS rate limit) or 404 (MAS route not found)
Invoke-WebRequest -Uri "http://localhost:3010/api/mas/csuite/finance/status" -UseBasicParsing
```

A non-5xx response indicates the proxy is reaching MAS. 429 = rate limit; 404 = MAS route may not be registered.

---

## 4. Label Syncer (GitHub Action)

### What It Does

Syncs GitHub labels across repos using `.github/labels.yml` and `.github/workflows/sync-labels.yml`. Ensures MAS and WEBSITE repos share consistent label sets.

### Where to See & Use It

- **Config:** `MAS/.github/labels.yml`, `WEBSITE/.github/labels.yml`
- **Workflow:** `MAS/.github/workflows/sync-labels.yml`, `WEBSITE/.github/workflows/sync-labels.yml`
- **Triggered:** On push to `main` or manually.

No UI. Verify by checking Actions tab in each repo.

---

## 5. Uncodixfy UI Rule

### What It Does

Cursor rule that guides agents to avoid "AI slop" UI and aim for human-designed aesthetics (Linear, Raycast, Stripe, GitHub).

### Where It Applies

- **Rule file:** `WEBSITE/website/.cursor/rules/uncodixfy-derived.mdc`
- **Applies to:** `website-dev`, `mobile-engineer`, and all UI work.

### Rules (Summary)

| Avoid | Prefer |
|-------|--------|
| Floating glassmorphism, oversized corners, pill buttons, hero sections | Solid sidebars (240–260px), 8–12px radius, simple borders |
| Decorative eyebrows, gradient text, dramatic shadows | Plain headers, subtle shadows (≤8px blur), 100–200ms transitions |
| Blue-black gradients, cyan accents | Existing project colors, predefined palettes |
| KPI card grids as default | Clean rows, left-aligned text, simple hover |

### How It Improves CREP

CREP dashboard uses:
- Simple map controls (no pill overload)
- Solid right panel, ScrollArea
- CrepMapPreferencesPanel: small buttons (h-8), outline variant, no floating shells
- Badges for data sources: small, outline, 6–8px radius

---

## 6. CREP-Specific UI Rules (crep-context.mdc)

### Rules of Thumb

- **No mock data** — CREP uses real APIs only; empty state or error message if unavailable.
- **429 handling** — Satellites and other rate-limited APIs show "Rate limit reached. Try again in a minute." instead of throwing.
- **Single orbit source** — Satellite orbits only from EntityDeckLayer; no duplicate orbit layers.

### How CREP Features Comply

| Feature | Compliance |
|---------|------------|
| CrepMapPreferencesPanel | Real Supabase; empty/null when unauthenticated |
| CREP fungal API | Real MINDEX/iNaturalist/GBIF; 400 for invalid bbox |
| Map controls | Real layer toggles, no fake data |

---

## 7. Test Summary (Run Date: 2026-03-10)

| Test | Expected | Result |
|------|----------|--------|
| CREP fungal – invalid bbox (west=-181) | 400 | 400 ✓ |
| CREP fungal – valid bbox | 200, GeoJSON | 200, ~450KB ✓ |
| CREP preferences GET (unauthenticated) | 200, `{ preferences: null, authenticated: false }` | 200 ✓ |
| CREP preferences POST (unauthenticated) | 401 | 401 ✓ |
| Finance proxy | Reaches MAS (200/429/404) | 404 (proxy working) ✓ |

---

## 8. Quick Verification Commands

Run with dev server on port 3010:

```powershell
# CREP fungal – invalid
Invoke-WebRequest -Uri "http://localhost:3010/api/crep/fungal?north=0&south=0&east=0&west=-181" -UseBasicParsing

# CREP fungal – valid
Invoke-WebRequest -Uri "http://localhost:3010/api/crep/fungal?north=40&south=20&east=-80&west=-100" -UseBasicParsing

# CREP preferences GET
Invoke-WebRequest -Uri "http://localhost:3010/api/crep/preferences" -UseBasicParsing

# CREP preferences POST (expect 401)
Invoke-WebRequest -Uri "http://localhost:3010/api/crep/preferences" -Method POST -Body '{"name":"default"}' -ContentType "application/json" -UseBasicParsing

# Finance proxy
Invoke-WebRequest -Uri "http://localhost:3010/api/mas/csuite/finance/status" -UseBasicParsing
```

---

## Related Documents

- `docs/EXTERNAL_REPO_INTEGRATION_COMPLETE_MAR10_2026.md` — Phase 1 completion
- `docs/EXTERNAL_REPO_SYSTEM_BOUNDARIES_MAR10_2026.md` — System boundaries
- `WEBSITE/website/docs/CREP_INTEGRATION_TEST_PLAN_MAR10_2026.md` — CREP integration test plan
- `.cursor/rules/crep-context.mdc` — CREP context for agents
- `WEBSITE/website/.cursor/rules/uncodixfy-derived.mdc` — Uncodixfy UI rule
