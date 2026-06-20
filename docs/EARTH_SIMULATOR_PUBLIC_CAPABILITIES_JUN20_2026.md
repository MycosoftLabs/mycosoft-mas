# Earth Simulator — Public Capabilities Reference

**Date:** June 20, 2026  
**Status:** Complete (P0–P2 fixes shipped)  
**Canonical route:** https://mycosoft.com/natureos/earth-simulator  
**Related plan:** Earth Simulator P0–P2 Fix Plan (website PR #222, branch `hotfix/env-safe-export-jun20-v2`)

---

## What it is

The **Earth Simulator** is Mycosoft's environmental intelligence overlay: a Mapbox/Cesium globe with live movers (aircraft, vessels, satellites), nature observations (iNaturalist + MINDEX), fungal atlas layers, infrastructure (PMTiles), weather/emergency overlays, and MYCA conversational control.

---

## Data stack and provenance

| Layer | Source | Website BFF | Notes |
|-------|--------|---------------|-------|
| Aircraft | OpenSky / FlightRadar24 via MAS OEI | `/api/oei/flightradar24` | LOD: visible at zoom ≥ 3.5 |
| Vessels | AISstream via MAS OEI | `/api/oei/aisstream` | Capped in unified bundle |
| Satellites | CelesTrak registry via MAS OEI | `/api/oei/satellites` | TLE stripped from unified payload |
| Fungal / nature | GBIF + iNat + MINDEX | `/api/crep/fungal`, MINDEX bbox | Observation cards show verified / needs ID |
| Infrastructure | Static PMTiles + viewport stats | `/api/crep/tiles/*`, `/api/crep/infra/viewport-stats` | Power plants & DCs use PMTiles (not 16 MB GeoJSON) |
| Earth-2 clouds | Earth-2 Legion 249 | `/api/earth2/health` | Auto-disables when offline |
| Entity stream | MAS WebSocket | `/api/stream/entities` (SSE BFF) | Requires MAS 188 up |
| MYCA chat | MAS orchestrator LLM | MYCA context + fast local map commands | `localOnly=false` on Earth Sim panel |
| Unified bundle | Aggregated CREP | `/api/crep/unified` | Default caps: 1500 aircraft, 2500 vessels, 1200 sats, 800 fungal, 500 events |

**VM layout:** Website Sandbox 187, MAS 188, MINDEX 189, Earth-2 GPU 249, Voice GPU 241.

---

## P0–P2 fixes delivered (Jun 20, 2026)

### P0 — Credibility blockers

1. **`/api/stream/entities`** — SSE BFF proxies `ws://MAS:8001/api/entities/stream` with graceful disconnect.
2. **`/api/crep/unified`** — Default caps, bbox support, 45s route cache, `?countsOnly=true`, record slimming (~520 KB vs ~3 MB).
3. **Live status bar** — CONNECTED / DEGRADED / OFFLINE for MAS, MINDEX, MycoBrain, Earth-2 (30s poll).
4. **Infra PMTiles** — `preferGeoJSON: false` for global power plants & data centers; `crep-sw.js` cache bumped to `crep-v6`.

### P1 — UX / science quality

5. **UTF-8** — Observation cards use Lucide `CheckCircle2` + plain "verified" text.
6. **Aircraft LOD hint** — "Zoom in for aircraft" when zoom < 3.5; Playwright asserts planes at z ≥ 4.
7. **Services panel** — 40s client timeout, 8s CelesTrak probe, tab-gated polling.
8. **MYCA full LLM** — Earth Sim MYCA LIVE tab uses MAS LLM with fast local map commands first.

### P2 — Performance

9. **FPS** — ReadPixels decimated (2s desktop / 8s mobile); hidden-tab pause via `shouldPauseLiveWork()`.
10. **Polling** — `useCrepPollScheduler` master 60s tick with idle stagger; services warm-cache on mount.

---

## Scientific experiment briefs (starter hypotheses)

| ID | Hypothesis | Data needed | BFF endpoints |
|----|------------|-------------|-----------------|
| ES-01 | Fungal richness correlates with infrastructure density in bbox | Fungal obs + infra viewport stats | `unified?bbox=…`, `/api/crep/infra/viewport-stats` |
| ES-02 | Vessel traffic drops near severe weather polygons | Vessels + NWS alerts | `/api/oei/aisstream`, emergency weather routes |
| ES-03 | Satellite pass density tracks aurora oval expansion | Satellites + SWPC | `/api/oei/satellites`, aurora overlay |
| ES-04 | MYCA viewport intel summarizes multi-layer anomaly | Viewport AI summary | `POST /api/crep/viewport-ai-summary` |

---

## Known limits (Jun 20, 2026)

- **MAS 188** must be reachable for entity SSE data and full MYCA LLM; BFF returns connected SSE shell when MAS is down.
- **First-hit unified** latency depends on upstream OEI collectors (~20s cold); cached hits faster in production (module-persistent cache).
- **Earth-2 clouds** require Legion 249; layer auto-disables when health is offline.
- **Aircraft** intentionally hidden below zoom 3.5 for performance.

---

## Verification

```powershell
# Local dev (port 3010)
Invoke-WebRequest http://localhost:3010/natureos/earth-simulator -UseBasicParsing
Invoke-WebRequest "http://localhost:3010/api/crep/unified?refresh=true" -UseBasicParsing
curl -N http://localhost:3010/api/stream/entities

# Playwright audit
$env:EARTH_SIM_AUDIT_URL="http://localhost:3010/natureos/earth-simulator"
node scripts/audit-earth-simulator-prod.mjs
```

Production: compare https://mycosoft.com/natureos/earth-simulator after Instant Deploy / blue-green cutover.

---

## Deployment

- **PR:** https://github.com/MycosoftLabs/website/pull/222  
- **Branch:** `hotfix/env-safe-export-jun20-v2`  
- **CI:** Instant Deploy workflow (GHCR build → VM blue/green)  
- **Post-deploy:** Cloudflare purge (automatic in deploy scripts)
