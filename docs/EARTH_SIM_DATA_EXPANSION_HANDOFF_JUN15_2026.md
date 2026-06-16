# Earth Simulator Data Expansion — Master Plan + Cursor Backend Handoff

**Date:** June 15, 2026
**Author:** Claude Code (Earth Simulator v2 frontend)
**For:** Cursor (MINDEX + MAS backend) — and as the canonical frontend build spec
**Status:** Backend shipped locally (Jun 15, 2026) — **no prod deploy / no auto-start** until Morgan approves; flag `TRANSIT_RT_COLLECTOR_ENABLED=1` on MAS 188 only after blue-green sign-off. All work local-first.
**Source:** Jun 15 2026 multi-agent sensor audit — **333 public real-time sources, 12 domains, 16 missing whole categories**. Full catalog JSON: `C:\Users\Owner1\AppData\Local\Temp\sensor-catalog.json` (mirror into repo on request). Related: `AWS_MYCOSOFT_SCALE_UP_MASTER_PLAN_JUN15_2026.md` (Cursor's infra plan), Earth Sim v2 plan `soft-wobbling-sparkle.md`.

---

## 0. Division of labor & rules

| Lane | Owner | Repo |
|------|-------|------|
| Earth Sim v2 **frontend** — map layers, elevated movers, custom widgets | Claude Code | `WEBSITE/website` |
| **Backend** — MINDEX schema, MAS collectors, BFF/API routes for new feeds | **Cursor** | `MAS/mycosoft-mas`, `MINDEX` |
| AWS scale-up, backups, GPU, Worldview metering | Cursor | see AWS plan |

**Rules (all parties):** no production deploy until Morgan approves; never restart MAS 188 collectors during peak without blue-green; never change VM IPs/ports without the registry; new feeds default OFF (flag-gated) until proven; perf-budgeted (viewport/LOD/FPS) — never regress the live v1 globe.

**Ingestion pattern (decision):** two tiers.
- **Tier A — direct frontend fetch** (no MAS/MINDEX): for no-key public JSON/GeoJSON that is small + CORS-OK or proxiable. The website hits the source (or a thin `/api/crep/*` proxy on 187) and renders. Fast to ship, no backend dependency. Use for: CDIP, CO-OPS, HFRNet, NWS, USGS ShakeMap, WFIGS/CAL FIRE, GBIF/iNat, SWPC, CNEOS, ISS, ENC.
- **Tier B — MAS collector → MINDEX → BFF** (Cursor): for feeds needing keys/credentials, protobuf decoding, websockets, high volume, history, or cross-source fusion. Use for: GTFS-RT (protobuf), AISStream (websocket), GDELT/ACLED (volume + history), CDC NWSS, EIA, PortWatch, anything we want queryable/cached/metered (Worldview).

Each category below tags **[Tier A]** or **[Tier B]**.

---

## 1. Immediate builds — #1 Marine, #2 Planes, #3 Trolleys/Trains

### 1.1 — Marine no-key bundle **[Tier A]** (frontend; Cursor optional cache)

| Source | Endpoint | Format | Coverage / locations | Quality | Cadence |
|--------|----------|--------|----------------------|---------|---------|
| **CDIP wave buoys** | `https://cdip.ucsd.edu/data_access/justdar.cdip?{stn}+pm` (+ ERDDAP `https://erddap.cdip.ucsd.edu/erddap/`) | JSON/txt | SD: 201 Scripps, 191 Pt Loma S, 100 Torrey Pines, 220 Mission Bay, 153 Del Mar, 045 Oceanside; ~70 CA/US | Authoritative (Scripps) | 30 min |
| **NOAA CO-OPS tides + currents** | `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?...&product=water_level|currents_predictions|currents` | JSON | SD Bay 9410170, La Jolla 9410230; **PCT0031** bay-entrance current | Gov authoritative | 6 min (obs) / predictions |
| **HFRNet HF-radar surface currents** | `https://hfrnet-tds.ucsd.edu/thredds/` (NetCDF/WMS) + `https://cordc.ucsd.edu/projects/mapping/` | NetCDF/GeoJSON-able | SD/SCB 1–6 km grid vectors | Research-grade | hourly |
| **NOAA ENC nav channels** | `https://encdirect.noaa.gov/arcgis/rest/services/NavigationChartData/MarineTransportation/MapServer/1/query?...&f=geojson` | GeoJSON | SD Bay maintained channels/fairways (Layer 1) | Authoritative | weekly |
| **SCCOOS TJ-plume** | SCCOOS ERDDAP / plume tracker | JSON/img | TJ River outfall / IB | Research | sub-daily |

**Frontend layers (website):** `marineBuoysCdip` (wave-buoy markers, color by Hs), `tidesCurrents` (CO-OPS station markers + animated **current arrows** at PCT0031 driven by predictions), `surfaceCurrents` (HFRNet vector field / particle-advection overlay), `navChannels` (ENC channel polygons w/ maintained-depth label). All under a new **"Ocean & Coastal"** layer group; flag-gated; viewport-culled.

**Custom widgets (unique per source):**
- **WaveBuoyWidget** — Hs/Tp/Dp readout + a **directional wave-energy rose** + a 24 h Hs sparkline + water temp. (Click a CDIP marker.)
- **TideCurrentWidget** — a **tide curve** (today, with now-marker + next high/low) + a **current dial** (flood/ebb arrow, slack countdown, velocity). (Click a CO-OPS station.)
- **SurfaceCurrentWidget** — local current speed/direction at cursor from the HF-radar field + a mini streamline.
- **ChannelWidget** — channel name, maintained depth (DRVAL1), last-survey date.

**Backend (Cursor, optional):** these are no-key, so Tier A direct fetch is fine. *If* we want history/caching/metering, add MAS collector `ocean_collector` → MINDEX tables `ocean_wave_obs`, `ocean_tide_current_obs`, `ocean_surface_currents` (PostGIS), exposed via `/api/crep/ocean/*`. Not required for the first ship.

### 1.2 — Planes at true altitude + smooth animation **[frontend]**

Reuse the satellite mover (now smooth). New `mover-aircraft-layer.ts` (BlueSite harness): read `__crep_aircraft` (lng/lat/**altitude**/heading/id), place at cruise altitude via `visualZ(altMeters)` (above surface, below LEO sats), heading-rotated icons, same per-frame GPU interpolation (dedup + `lastInterval ≥ tick` + slight extrapolation), screen-space picking → `crep:asset:select`. Flag-gated `?es3d=1`; viewport/LOD-budgeted.
**Custom widget:** existing `FlightTrackerWidget` (callsign, alt, speed, heading, route) — wire the elevated mover's pick to it.
**Backend (Cursor):** ensure the **aircraft collector** on MAS 188 is healthy (AWS plan §9 — OpenSky/ADS-B); sparse planes = upstream feed, not the frontend. Optionally enrich `__crep_aircraft` with `geo_altitude` if missing.

### 1.3 — Trolley / train animation **[Tier B]** (MAS collector → MINDEX → BFF; frontend mover)

| Source | Endpoint | Format | Coverage | Auth |
|--------|----------|--------|----------|------|
| **SD MTS GTFS-RT** | VehiclePositions + TripUpdates protobuf (SDMTS/511 SD) | protobuf | MTS trolley + bus | key (SDMTS/511) |
| **Amtraker v3** | `https://api-v3.amtraker.com/v3/trains` | JSON | Amtrak incl. Pacific Surfliner | none |
| **NCTD COASTER/SPRINTER** | GTFS-RT (transit.land / NCTD) | protobuf | North County rail | key |
| **Metrolink / Caltrain** | GTFS-RT | protobuf | CA-wide | varies |

**Backend (Cursor) — required:** MAS collector `transit_rt_collector` decodes GTFS-RT protobuf (use `gtfs-realtime-bindings`) + Amtraker JSON, writes vehicle positions + trip/stop state to MINDEX `transit_vehicles` (id, route, trip, lat, lng, bearing, speed, **stop_id, status[INCOMING/STOPPED/IN_TRANSIT], next_stop_eta**), refreshed ~10–30 s. Static GTFS (routes/stops/**shapes**) → MINDEX `transit_routes/stops/shapes` for snapping. Expose `/api/crep/transit/vehicles?bbox=` + `/api/crep/transit/shapes`.
**Frontend:** `liveTransit` mover layer — animate vehicles **along the route shape** (snap to shape geometry, interpolate between RT updates), **stop accurately at stations** (when status=STOPPED hold at stop_id; ease in/out at stops/lights using shape + speed). Ground band (surface). Heading-rotated trolley/train icons.
**Custom widget:** **TransitVehicleWidget** — line badge + color, next stop + ETA, occupancy (if in feed), a **mini strip-map** of upcoming stops with the vehicle's position, on-time delta.

---

## 2. The 16 missing categories — full-detail spec (sources · locations/quality · live routes · custom widget · backend)

> For each: **[Tier]**, primary sources w/ endpoints + auth + coverage + cadence, the frontend layer, the **unique custom widget**, and the Cursor backend work.

### 2.1 Disease / public-health surveillance **[Tier B]** — *on-mission (fungal/biosecurity)*
- **Sources:** CDC **NWSS wastewater** (SARS-CoV-2, mpox, **H5N1**) via CDC NWSS / WastewaterSCAN (`data.cdc.gov` Socrata) — site-level lat/lng, weekly; **CDC FluView/ILINet** (region); **ProMED**/**HealthMap** outbreak alerts (geocoded events); **WHO EIOS**; **USDA APHIS** animal disease; **plant-disease** (Fusarium/wheat-blast biosecurity — relevant to FUSARIUM product). Quality: gov authoritative; cadence weekly→daily.
- **Frontend layer:** `healthSurveillance` — wastewater site markers (color by trend ↑/↓), outbreak event pins (ProMED), choropleth option for ILINet.
- **Custom widget:** **BiosurveillanceWidget** — pathogen tabs (COVID/flu/H5N1/mpox), a **trend sparkline** per site, latest concentration + % change, nearest-site summary, outbreak headline feed.
- **Backend (Cursor):** `health_collector` (Socrata + ProMED RSS/HealthMap) → MINDEX `health_wastewater`, `health_outbreaks` (PostGIS). Route `/api/crep/health/*`. **MINDEX:** add a `biosurveillance` schema; tie to FUSARIUM defense product.

### 2.2 Conflict / news / world-events **[Tier B]** — *biggest "what's happening now" gap*
- **Sources:** **GDELT 2.0** (`https://api.gdeltproject.org/api/v2/doc/doc` + GEO/GKG; 15-min geolocated events + tone), **ACLED** (curated conflict events, key), **GDACS** (global disaster alerts GeoJSON, no key), **ReliefWeb**/UN-OCHA, **LiveUAMap** (scrape). Coverage global; cadence 15 min (GDELT) → hourly.
- **Frontend layer:** `worldEvents` — event pins by type (conflict/protest/disaster), heat option, **tone-colored** GDELT GEO points.
- **Custom widget:** **WorldPulseWidget** — a **live event ticker** (newest first), filter by category, sentiment/tone gauge, source link, "events near viewport" count.
- **Backend (Cursor):** `events_collector` (GDELT GEO 2.0 + GDACS + ACLED) → MINDEX `world_events` (event_type, tone, mentions, geo, url, ts). Dedup + 7-day retention. Route `/api/crep/events?bbox=&type=`.

### 2.3 Agriculture / soil / vegetation **[Tier A/B]** — *on-mission (fungal/drought/fuel)*
- **Sources:** **USDA NASS CropScape/CDL** (10 m crop type, WMS/WCS), **Crop-CASMA / SMAP** soil moisture, **SoilGrids** (ISRIC), **NASA HLS / Sentinel-2 NDVI** greenness (GIBS tiles), **USDA NDMC VegDRI/QuickDRI** drought-veg, **OpenET** evapotranspiration. Coverage US/global; cadence daily→weekly tiles.
- **Frontend layer:** `agriculture` — CropScape WMS tiles, NDVI tile layer, soil-moisture raster; toggle sub-layers.
- **Custom widget:** **AgroSoilWidget** — at cursor/point: crop class, NDVI value + 30-day trend, soil moisture %, ET, drought class.
- **Backend (Cursor):** mostly tile/WMS proxy `/api/crep/agro/tiles` (Tier A). For point queries, `agro_collector` sampling SMAP/NDVI → MINDEX optional.

### 2.4 Internet / network health **[Tier B]**
- **Sources:** **Cloudflare Radar** (outages + BGP + traffic, key), **Georgia Tech IODA** (internet outages GeoJSON), **RIPEstat/RIPE Atlas**, **Downdetector** (scrape), submarine-cable fault notices. Coverage global; cadence minutes.
- **Frontend layer:** `networkHealth` — country/AS outage choropleth + cable-fault markers (ties to existing `submarineCables`).
- **Custom widget:** **NetHealthWidget** — outage status for region, BGP anomaly count, top down services (Downdetector), affected ASNs.
- **Backend (Cursor):** `nethealth_collector` (Cloudflare Radar + IODA) → MINDEX `network_outages`. Route `/api/crep/nethealth`.

### 2.5 Cryosphere — sea ice / icebergs / glaciers / snow **[Tier A]**
- **Sources:** **NSIDC MASIE** near-real-time sea-ice edge (GeoJSON/shp), **US National Ice Center** iceberg tracks (A/B/C bergs), **NIC IMS** snow/ice, **NASA ITS_LIVE** glacier velocity, USGS lake/river ice, **SNOTEL/SNODAS** snow. Coverage polar+global; cadence daily.
- **Frontend layer:** `cryosphere` — sea-ice edge polygon, iceberg markers (drift tracks), snow-depth raster, glacier-velocity tiles.
- **Custom widget:** **CryosphereWidget** — sea-ice extent vs climatology, nearest iceberg (id, size, drift), snow depth, glacier speed.
- **Backend (Cursor):** mostly Tier A proxy; optional `cryo_collector` for iceberg track history.

### 2.6 Water-quality chemistry + global floods **[Tier A/B]**
- **Sources:** **USGS Water Data OGC API** continuous (nitrate, turbidity, DO, pH, sp. conductance, chlorophyll, cyanobacteria — WaterQualityWatch retiring Feb 2026 → use OGC API), **Water Quality Portal**, **GloFAS** global flood, **GDACS floods**, **Dartmouth Flood Observatory**. Coverage US/global; cadence 15 min→daily.
- **Frontend layer:** `waterQuality` (gauge markers color by parameter) + `floods` (extend existing with GloFAS).
- **Custom widget:** **WaterChemWidget** — parameter tabs, value + threshold flag (e.g., HAB risk), 7-day trend, gauge metadata.
- **Backend (Cursor):** `waterchem_collector` (USGS OGC) → MINDEX `water_quality_obs`. Route `/api/crep/waterchem?bbox=`.

### 2.7 Cosmic-ray / particle-physics / fundamental geophysics **[Tier A/B]** — *the "weird curious thing"*
- **Sources:** **NMDB** real-time neutron monitors (station map + counts), **GMDN** muon, **IceCube/GCN** neutrino alerts, **LIGO/Virgo GraceDB + GCN** gravitational-wave alerts (event sky-maps!), **Pierre Auger**, **CTBTO IMS** infrasound/radionuclide. Coverage global station nets + event alerts; cadence minute→event.
- **Frontend layer:** `cosmicGeophysics` — neutron-monitor stations (color by count rate), **GW/neutrino alert sky-map overlays** (geo-projected credible regions), infrasound stations.
- **Custom widget:** **CosmicEventWidget** — latest GW/neutrino alert (event id, significance, distance, sky-map), neutron-count global level (Forbush decrease indicator), "alerts in last 24h."
- **Backend (Cursor):** `cosmic_collector` (NMDB + GCN/GraceDB websocket/RSS) → MINDEX `cosmic_events`, `neutron_obs`. Route `/api/crep/cosmic`. (GCN Kafka stream → MAS.)

### 2.8 Economic / shipping / supply-chain **[Tier B]**
- **Sources:** **UNCTAD PortWatch** (AIS-derived port calls + chokepoint transits, public ArcGIS), port congestion, Panama/Suez transit counts, commodity spot tickers, crypto nodes (**Bitnodes**, Ethernodes), exchange order-book (a **Deribit MCP** is attached). Coverage global ports/chokepoints; cadence daily (PortWatch) → realtime (markets).
- **Frontend layer:** `supplyChain` — port markers (congestion color), chokepoint transit-rate arrows (Panama/Suez/Malacca/Hormuz), crypto-node density.
- **Custom widget:** **SupplyChainWidget** — port congestion index + waiting ships, chokepoint daily transits + trend, commodity ticker strip.
- **Backend (Cursor):** `econ_collector` (PortWatch ArcGIS + Bitnodes + market APIs) → MINDEX `port_metrics`, `chokepoint_transits`. Route `/api/crep/econ/*`.

### 2.9 Industrial thermal / gas flaring **[Tier A]**
- **Sources:** **VIIRS Nightfire (EOG/Colorado)** live gas-flare + industrial-heat anomalies (location + temp + flared volume), **SkyTruth** flaring, **NOAA VNF v4**. Distinct from FIRMS wildfire. Coverage global; cadence daily.
- **Frontend layer:** `industrialHeat` — flare/heat anomaly markers sized by radiant heat (ties to existing `oilGas`, `factories`).
- **Custom widget:** **FlareHeatWidget** — site temp, flared volume estimate, source type, trend.
- **Backend (Cursor):** Tier A proxy of EOG VNF; optional MINDEX history.

### 2.10 Aviation hazards & airspace structure **[Tier A]**
- **Sources:** **VAAC volcanic-ash advisories** (GeoJSON), **AIRMET/SIGMET/PIREP** polygons (aviationweather.gov API), **OpenAIP/OurAirports** airspace + navaids, **NOTAMs**, **FAA TFRs**, space-launch + maritime hazard areas. Coverage global/US; cadence hourly→event.
- **Frontend layer:** `airspaceHazards` — SIGMET/ash polygons, airspace-class outlines, TFR rings (complements existing aviation movers).
- **Custom widget:** **AirspaceHazardWidget** — active SIGMETs/ash near viewport, hazard type/altitude band/validity, TFR reason.
- **Backend (Cursor):** Tier A (aviationweather.gov is no-key JSON); optional cache.

### 2.11 Crowdsourced / citizen IoT platforms **[Tier B]**
- **Sources:** **ThingSpeak** public channels, **Adafruit IO**, **Smart Citizen Kit** (smartcitizen.me API), **Sensor.Community** (already partly), TTN-mapper. Coverage global hobbyist; cadence minutes.
- **Frontend layer:** `citizenIot` — generic multi-sensor markers (type-tagged).
- **Custom widget:** **CitizenSensorWidget** — sensor type, latest reading(s), owner, a sparkline; "this is a community sensor" provenance note.
- **Backend (Cursor):** `iot_collector` (ThingSpeak/SmartCitizen public APIs) → MINDEX `citizen_sensors`. Route `/api/crep/iot?bbox=`.

### 2.12 Public-safety / crime / 911-CAD **[Tier B]**
- **Sources:** **PulsePoint** (already noted in wildfire), **SpotCrime API**, **CrimeMapping**, local open-data CAD (Socrata/ArcGIS calls-for-service — many cities incl. potentially SD). Coverage US cities; cadence minutes→daily.
- **Frontend layer:** `publicSafety` — incident pins by type (fire/medical/police/crime), recency fade.
- **Custom widget:** **IncidentFeedWidget** — live CAD feed near viewport, type/time/units, crime heat toggle.
- **Backend (Cursor):** `safety_collector` (Socrata CAD + SpotCrime) → MINDEX `safety_incidents` (24h TTL). Route `/api/crep/safety?bbox=`.

### 2.13 Astronomy / transient events **[Tier A/B]**
- **Sources:** **ZTF/ATLAS** transient brokers (**ALeRCE**, **Lasair**), **all-sky cameras** (AllSky network, GMN meteor cams), **satellite/ISS visible passes** per ground point, **Globe at Night** sky-brightness, light-pollution map (VIIRS DNB). Coverage global; cadence event/nightly.
- **Frontend layer:** `astronomy` — light-pollution raster, all-sky cam markers, "visible-now" satellite passes for the viewport center, transient alert pins (geo of discovery).
- **Custom widget:** **SkyWatchWidget** — for the viewport location: tonight's ISS/Starlink passes, sky-brightness (Bortle), latest bright transient (SN/asteroid), nearest all-sky cam.
- **Backend (Cursor):** `astro_collector` (ALeRCE/Lasair + pass prediction) → MINDEX optional; passes can be computed frontend (satellite.js).

### 2.14 Live-imagery layer (first-class "windows on Earth") **[Tier A — partly built]**
- **Sources:** already building this (Eagle Eye) — HDOnTap, YouTube live channels, EarthCam, Surfline, Skyline, Windy, traffic cams, fire cams, **NPS park cams**, **LiveATC** audio, reef/wildlife cams. *This category is ~50% done.* Extend: NPS cams, LiveATC audio overlay, more traffic-cam DOTs.
- **Frontend layer:** `eagleEyeCameras` (exists) + `eagleEyeEvents`; add an **audio** sub-type for LiveATC.
- **Custom widget:** existing VideoWallWidget + a new **AudioScannerWidget** (LiveATC/Broadcastify: live audio player + freq label).
- **Backend (Cursor):** none new (frontend seeds + resolvers handle it). Note in registry.

### 2.15 Radiation / nuclear **[Tier A]**
- **Sources:** **Safecast** (already), **EPA RadNet**, **IAEA IRMIS**, **EURDEP**, **uRADMonitor**, plus event reporting: **NRC event notifications**, **USCG NRC** oil/chem spill reports, **PHMSA** pipeline incidents. Coverage global+US; cadence hourly→event.
- **Frontend layer:** `radiation` — dose-rate sensor markers (color by µSv/h), spill/incident event pins.
- **Custom widget:** **RadiationWidget** — local dose rate vs background, nearest sensor, recent spill/incident events.
- **Backend (Cursor):** `rad_collector` (RadNet + uRADMonitor + NRC/PHMSA RSS) → MINDEX `radiation_obs`, `hazmat_incidents`. Route `/api/crep/radiation`.

### 2.16 Human-activity pulse **[Tier A/B]**
- **Sources:** **Strava Metro/heatmap** (tiles), **Wikipedia live-edit geostream** (`stream.wikimedia.org/v2/stream/recentchange` SSE — geocoded edits), **OSM minutely diffs**, transit ridership, Mapbox Movement. Coverage global; cadence realtime (SSE).
- **Frontend layer:** `humanPulse` — Wikipedia-edit geo-pings (live SSE → ephemeral pulses), Strava heat tiles, OSM-edit pings.
- **Custom widget:** **ActivityPulseWidget** — live edit/activity ticker (Wikipedia article being edited near here), heat intensity, edits/min.
- **Backend (Cursor):** Wikipedia/OSM SSE can be frontend (Tier A); Strava needs key (Tier B `pulse_collector`).

---

## 3. Consolidated Cursor backend handoff (MINDEX + MAS)

### 3.1 MINDEX — new tables (PostGIS; all with `geom`, `ts`, source, properties JSONB)
`ocean_wave_obs`, `ocean_tide_current_obs`, `ocean_surface_currents`, `transit_vehicles`, `transit_routes/stops/shapes`, `health_wastewater`, `health_outbreaks`, `world_events`, `network_outages`, `water_quality_obs`, `cosmic_events`, `neutron_obs`, `port_metrics`, `chokepoint_transits`, `citizen_sensors`, `safety_incidents`, `radiation_obs`, `hazmat_incidents`. Pattern: reuse the existing `eagle.video_sources` / map-bbox layer pattern (`/api/mindex/earth/map/bbox?layer=...`). **Add a generic `earth_layer_obs` (layer, geom, ts, value, props)** to avoid table sprawl for low-volume categories, with per-category materialized views.

### 3.2 MAS — new collectors (`mycosoft_mas/collectors/` or OEI connectors)
`transit_rt_collector` (GTFS-RT protobuf + Amtraker — **P0 for build #3**), `events_collector` (GDELT/GDACS/ACLED), `health_collector` (NWSS/ProMED), `cosmic_collector` (GCN/NMDB), `econ_collector` (PortWatch), `nethealth_collector`, `waterchem_collector`, `iot_collector`, `safety_collector`, `rad_collector`, `pulse_collector` (Strava). Each: own internal timeout, writes to MINDEX, **must not** block existing CREP/OEI collectors (per AWS plan §9 — collectors already degraded on 188; **fix base collectors first**).

### 3.3 BFF/API routes (website 187 → MAS/MINDEX)
`/api/crep/ocean/*`, `/api/crep/transit/vehicles|shapes`, `/api/crep/events`, `/api/crep/health/*`, `/api/crep/cosmic`, `/api/crep/econ/*`, `/api/crep/nethealth`, `/api/crep/waterchem`, `/api/crep/iot`, `/api/crep/safety`, `/api/crep/radiation`, `/api/crep/agro/tiles`. Mirror the existing `/api/crep/*` + `/api/oei/*` pattern; bbox-scoped; cache-friendly headers.

### 3.4 Env keys (per AWS plan; add as needed)
Have: AirNow, AISStream, OpenSky, FlightRadar24, Global Fishing Watch, Windy, Mapbox/Cesium/Google. **Cursor to provision (free-instant):** OpenAQ, PurpleAir, Synoptic, NASA Earthdata (TEMPO/S5P), FIRMS map key, EIA, SDMTS/511, ACLED, Cloudflare Radar, Strava. Store in `.credentials.local` / `.env` per VM — never git.

### 3.5 Sequencing for Cursor
**P0:** fix base CREP/OEI collectors on 188 (AWS §9) so aviation/maritime/sats are dense → directly improves builds #2/#3. **P1:** `transit_rt_collector` (#3). **P2:** `events_collector`, `health_collector` (highest mission value). **P3:** the rest by the priority in §2. Each behind a flag; no auto-start in prod without Morgan + blue-green.

---

## 4. Custom-widget catalog (frontend, Claude Code)
WaveBuoy · TideCurrent · SurfaceCurrent · Channel · TransitVehicle · Biosurveillance · WorldPulse · AgroSoil · NetHealth · Cryosphere · WaterChem · CosmicEvent · SupplyChain · FlareHeat · AirspaceHazard · CitizenSensor · IncidentFeed · SkyWatch · AudioScanner · Radiation · ActivityPulse. Each: glassmorphic CREP style, viewport/click-driven, lazy-loaded, accessible (data-testid + aria), perf-budgeted.

## 5. Build order (Claude Code, frontend)
1. **Marine no-key bundle** (§1.1) — Tier A, no backend dependency → ship first.
2. **Planes at altitude** (§1.2) — frontend mover.
3. **Trolley/train** (§1.3) — needs Cursor's `transit_rt_collector`; until then, Amtraker (no-key JSON) directly + MTS via 511 if keyed.
4. Then §2 categories by mission value: **2.1 disease**, **2.2 events**, **2.7 cosmic (GW alerts)**, **2.16 human pulse**, then the rest. Each = layer + custom widget + (Cursor) collector.

---

## 6. Cursor backend delivery — transit GTFS-RT (Jun 15, 2026)

| Layer | Path | Notes |
|-------|------|-------|
| MINDEX migration | `MINDEX/mindex/migrations/0015_transit_gtfs_rt.sql` | `transit.vehicles`, `routes`, `stops`, `shapes` (PostGIS) |
| MINDEX API | `GET /api/mindex/transit/vehicles?bbox=` · `GET /api/mindex/transit/shapes?bbox=` | Internal token; GeoJSON contract in §1.3 |
| MAS collector | `mycosoft_mas/collectors/transit_rt_collector.py` | Flag `TRANSIT_RT_COLLECTOR_ENABLED=1`; poll 20s; own timeout |
| Website BFF | `GET /api/crep/transit/vehicles?bbox=` · `GET /api/crep/transit/shapes?bbox=` | Proxies MINDEX; live fallback when empty (Amtraker + keyed GTFS-RT) |

**Verify locally:** San Diego bbox `?bbox=-117.35,32.55,-116.85,33.05` on port 3010. **Claude Code** can build animated ground mover against `/api/crep/transit/vehicles` (and `/shapes` once collector has loaded static GTFS).

**Next action for Morgan:** confirm this is the plan → Claude Code starts build #1 (marine) now; enable `TRANSIT_RT_COLLECTOR_ENABLED=1` on MAS 188 only after P0 collector stabilization + blue-green approval. No website/MAS prod deploy until approved.
