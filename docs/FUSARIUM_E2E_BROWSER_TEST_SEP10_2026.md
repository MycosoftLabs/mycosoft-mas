# Fusarium E2E Browser Test — September 10, 2026

**Date:** Thursday 10 September 2026  
**Status:** Complete (verify-only; no deploy, no 187 touch, no website-main reset)  
**Classification:** UNCLASSIFIED  
**Tester:** test-engineer (Cursor)  
**Owner:** Morgan Rockcoons (CEO / CTO / COO / SAO)  
**CFO:** RJ Ricasata (never COO)  
**Related:** `WEBSITE/website-itdx-codex-v13/docs/FUSARIUM_DROID_PATH_C2_EARTH_SIM_SEP10_2026.md`, `WEBSITE/website-itdx-codex-v13/docs/EARTH_SIM_AEROSOL_LAYERS_SEP10_2026.md`, `WEBSITE/website-itdx-codex-v13/docs/FUSARIUM_OSINT_TOPO_DEVICES_TRACKING_SEP10_2026.md`

## Verdict first

**No fake live convoy.** Field catalog sites `mushroom-1`, `hyphae-1`, `psathyrella-buoy-com4` (`source=field`) are listed on `/api/earth-simulator/devices` and are **not** copied into the live movement COP.

**Worst leftover items (FAIL / DEGRADED):**

1. **DEGRADED — NLM unloaded on MAS 188.** `GET http://192.168.0.188:8001/api/nlm/health` → `200`, `model_loaded: false`, `bound_to_ollama: false`, `forecast_qualified: false`. Honest (not a stub `0.85 p`). Path-tree source remains `local-geometry` / Weka+NLM movement `NOT_SUPPLIED`.
2. **DEGRADED — Website BFF ITDX situation-assessment aborted.** `GET/POST http://localhost:3010/api/itdx/situation-assessment` closed the connection. Direct MAS `POST /api/itdx/situation-assessment` Fort Stewart slice **200** (`origin: SYNTHETIC_EXERCISE`, `live_cop: false`). UI Intel Feed can still show MYCA LIVE | ITDX chrome; live COP is not qualified.
3. **DEGRADED — Smoke + MINDEX env upstream empty.** Earth Sim smoke renderer is **NOT_SUPPLIED** (quarantined, contract). `/api/crep/environment/air-quality` and `/api/crep/environment/wildfires` return empty FeatureCollections with `meta.upstream: "unavailable"`. Wind BFF **200** with real u/v grids. Filter exists; animation of PM/FIRMS/smoke is empty/honest, not a dead checkbox at the API layer.

No **FAIL** for fake tracks, dead movement controls, or MAS/MINDEX 5xx on the probed health paths.

## 3010 repo

| Check | Result |
|---|---|
| Listen PID | `32692` (Next `start-server.js`) |
| Next binary path | `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\node_modules\next\...` (shared `node_modules`) |
| Movement BFF file on **main** | **Absent** (`website/app/api/fusarium/movement/snapshot/route.ts` does not exist) |
| Movement BFF file on **worktree** | **Present** (`website-itdx-codex-v13/app/api/fusarium/movement/snapshot/route.ts`) |
| Live 3010 `/api/fusarium/movement/snapshot` | **200** with worktree schema `mycosoft.fusarium.device-movement.v1` |

**Conclusion:** `http://localhost:3010` is serving the **ITDX worktree** `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13` (branch `cursor/itdx-codex-v13-connect-20260909`). Public `mycosoft.com` / Sandbox 187 were **not** touched.

Browser MCP (`plugin-browser-use`) discovery failed; `cursor-ide-browser` was not in the session catalog. Click proof used Playwright (Edge, headless) plus authenticated BFF GETs. That is not one screenshot: ITDX chip was expanded and collapsed; remaining env-tab toggles are proven at the BFF/map-contract layer and cited as **DEGRADED** where animation was not visually confirmed.

## Auth

| Action | Result |
|---|---|
| `POST /api/auth/local-dev-session` `{ redirectTo: "/fusarium/earth-simulator" }` | **200** (`mintOk: true`) — used for Playwright |
| Password grant | Not required after mint |
| Google owner (`morgan@mycosoft.org`) | Not used (local-dev session succeeded). Main auth was **not** reset. |

## Routes clicked / loaded

| Route | HTTP | Browser / Playwright | Notes |
|---|---|---|---|
| `/fusarium/login` | 200 | Loaded | Login page served |
| `/fusarium/earth-simulator` | 200 | Playwright after mint | ITDX chip present, default collapsed, expand/collapse **worked** |
| `/fusarium` | 200 | Playwright | **0** `itdx-earth-sim-overlay`; no evidence strip; no fictional replay dock |
| `/fusarium/soc` | 200 | Playwright | Same: no global ITDX overlay / dock |
| `/fusarium/itdx` | 200 | HTTP load | Workspace route served; not used as a floating dock host |
| `/fusarium/devices` | 200 | HTTP load | OSINT / catalog + live registry contract |
| `/fusarium/command-control` | 200 | HTTP load | C2 + movement snapshot consumer |
| `/fusarium/aerosol` | 200 | HTTP load | Same aerosol BFFs as Earth Sim env tab |

Playwright ITDX chip (10 Sep 2026 ~09:10 PT):

- `data-testid="itdx-earth-sim-overlay"` present on Earth Sim only
- Default: `aria-expanded="false"`, label **Expand ITDX**
- After click: expanded (`Collapse` + `#itdx-earth-sim-overlay-body`)
- Second click: collapsed again
- No “ITDX backend is not configured” dump; replay dock count `0`

## Layer / filter matrix

Contract: honest empty and hypothesis overlays are **PASS**. Smoke renderer **NOT_SUPPLIED** is **DEGRADED**, not FAIL.

| Capability | UI action | Network / BFF | MAS / MINDEX / NLM | Visible result | Mark |
|---|---|---|---|---|---|
| ITDX chip Earth Sim only | Expand / collapse on Earth Sim; load `/fusarium` + `/soc` | Overlay mount | n/a | Chip only on Earth Sim; default collapsed | **PASS** |
| No global ITDX dock | Load `/fusarium`, `/fusarium/soc` | Overlay count 0 | n/a | No floating dock | **PASS** |
| Intel Feed MYCA LIVE \| ITDX | Overlay chrome (owner) | MAS `POST /api/itdx/situation-assessment` 200; website BFF aborted | MAS `origin: SYNTHETIC_EXERCISE`, `live_cop: false` | Advisory / synthetic, not live COP | **DEGRADED** |
| Live position | Movement snapshot | `GET /api/fusarium/movement/snapshot` 200 | MAS registry heartbeat `mycobrain-service-192-168-0-241` | `liveDeviceCount: 1`, `source: mas`, `live: true` at 32.56289, -117.1357 | **PASS** |
| Catalog ≠ convoy | Devices BFF vs movement | `/api/earth-simulator/devices?refresh=1` lists field seeds | Not treated as live | Field ids **absent** from `snapshot.devices` | **PASS** |
| Path polyline | Snapshot `path` | Same BFF | Telemetry trails `NOT_SUPPLIED` | `path: "NOT_SUPPLIED"` (need ≥2 fixes) | **PASS** |
| Coordination | Snapshot `coordination` | Same BFF | Only 1 live device | `coordination: []` (needs ≥2 live) | **PASS** |
| Triangulation | Snapshot triangle | Same BFF | 1 observer + Fort Stewart AO fillers | `live: false`, `qualification: unqualified-proposal`, `fix: null` | **PASS** |
| Path tree | Snapshot `pathTree` | Same BFF | NLM/Weka movement `NOT_SUPPLIED` | `live: false`, branches labeled hypothesis | **PASS** |
| Waypoints / C2 execute | Command seam | `/api/devices/network/[deviceId]/command` is ping/sensors | n/a | `waypointCommand: propose-only`, `receipt: NOT_SUPPLIED` | **PASS** |
| OpenTopo | Env / Conditions | Cited OSM + SRTM / OpenTopoMap (CC-BY-SA) | n/a | Public OSINT overlay (implementation cited) | **PASS** (cite); animation not re-clicked after MCP loss |
| Particulates (PM) | Env filter `aerosolParticulate` | `/api/crep/environment/air-quality` 200 | MINDEX `mindex.atmos.air_quality` `upstream: unavailable`, `features: []` | Honest empty collection | **DEGRADED** |
| Wind | Env filter `aerosolWind` | `/api/earth2/layers/wind` 200 | Earth-2 u/v numeric grid present | Layer data supplied | **PASS** (API); map animation not visually re-toggled |
| Modeled spore dispersal | Env filter `aerosolModeledDispersal` | `/api/earth2/spore-dispersal` 200 | `runs: []`, `source: mas` | Honest empty | **DEGRADED** |
| Air quality / FIRMS | Existing Earth Sim filters | AQ + wildfires 200 | MINDEX upstream unavailable, `features: []` | Honest empty | **DEGRADED** |
| Smoke | Env filter `aerosolSmoke` | No renderer | CREP `SmokeLayer` quarantined | Filter exists; draw **NOT_SUPPLIED** | **DEGRADED** |
| Devices OSINT library | `/fusarium/devices` | Devices BFF 200 | Field cards not on-hand unless registry id matches | Field seeds labeled catalog; live row is MAS buoy service | **PASS** |
| Aerosol app 1:1 | `/fusarium/aerosol` | Same AQ / wind / spore / FIRMS BFFs | Same empties + wind grid | Filters share contracts with Earth Sim env tab | **PASS** (API parity) / **DEGRADED** (empty MINDEX AQ) |
| NLM processes | Path tree + `/api/nlm/health` | MAS NLM 200 | `model_loaded: false`, not Ollama | Honest unload; no invented p | **DEGRADED** |
| AVANI | Governor | `GET /api/avani/status` 200 | `is_operational: true`, season spring | Healthy | **PASS** |

## Backend probes (real)

Probed **10 Sep 2026 ~10:38–10:39 PT**. No mock payloads. Demo `live: false` / `live_cop: false` treated as honest.

### MAS `http://192.168.0.188:8001`

| Endpoint | Status | Cite |
|---|---|---|
| `/health` | 200 | `status: degraded` — postgres/redis healthy; collectors skipped (`MAS_SKIP_BACKGROUND_STARTUP`) |
| `/api/nlm/health` | 200 | `model_loaded: false`, `model_name: nlm`, `bound_to_ollama: false`, `forecast_qualified: false`. NLM ≠ Ollama. |
| `/api/avani/status` | 200 | `system: avani-governor`, `is_operational: true` |
| `POST /api/itdx/situation-assessment` body `{"slice":{"name":"Fort Stewart","bbox":[-81.70,31.80,-81.45,32.05],"center":[31.88,-81.61]}}` | 200 (~44 KB) | `schema_version: itdx.situation_assessment/v1`, `source: mas`, `origin: SYNTHETIC_EXERCISE`, `execution: ADVISORY_ONLY`, `synthetic: true`, `live_cop: false`, Fort Stewart AO echoed |
| `/api/devices` | 200 | Live registry includes `mycobrain-service-192-168-0-241` (Psathyrella Aquatic MycoBrain Buoy, host `192.168.0.241:8003`, location `32.56289,-117.13570`) |
| `GET /api/devices/heartbeat` | 404 | Heartbeat is ingest (POST), not a GET catalog — not treated as a UI FAIL |

### MINDEX `http://192.168.0.189:8000`

| Endpoint | Status | Cite |
|---|---|---|
| `/health` | 200 | `{"status":"healthy"}` |
| `/api/mindex/health` | 200 | `db: ok`, `service: mindex`, `version: 3.0.0` |

UI-written retain: this pass **read** live registry + empty AQ/FIRMS collections. No new Fusarium write was forced (verify-only). Movement snapshot is derived (not a MINDEX insert). AQ/FIRMS `upstream: unavailable` means the Earth Sim env tab cannot show MINDEX-backed PM/fire animation until that collector is supplied.

### Website BFF (`localhost:3010`)

| Route | Status | Cite |
|---|---|---|
| `/api/earth-simulator/devices?refresh=1` | 200 | Field seeds + one MAS live row |
| `/api/fusarium/movement/snapshot` | 200 | See snapshot excerpt below |
| `/api/crep/environment/air-quality` | 200 | Empty FC, MINDEX AQ unavailable |
| `/api/earth2/layers/wind` | 200 | Numeric wind grid |
| `/api/earth2/spore-dispersal` | 200 | `runs: []` |
| `/api/crep/environment/wildfires` | 200 | Empty FC, MINDEX wildfires unavailable |
| `/api/itdx/situation-assessment` | abort | Connection closed; use MAS direct |

No 5xx on the Fusarium page routes or the movement / devices / aerosol BFFs above.

## Movement snapshot excerpt (authoritative COP)

`GET http://localhost:3010/api/fusarium/movement/snapshot` at `2026-09-10T17:39:36.603Z`:

- `classification: UNCLASSIFIED`
- `liveDeviceCount: 1`
- Live device: `mycobrain-service-192-168-0-241` / `source: mas` / `live: true` / `path: NOT_SUPPLIED`
- `coordination: []`
- `triangulation.live: false` / `qualification: unqualified-proposal` / note: fewer than three live observers
- `pathTree.live: false` / `source: local-geometry` / Weka+NLM movement **NOT_SUPPLIED**
- `commandSeam.waypointCommand: propose-only` / `receipt: NOT_SUPPLIED`
- `sources.telemetryTrails: NOT_SUPPLIED`, `sources.itdxWeka: NOT_SUPPLIED`

Field catalog (`mushroom-1`, `hyphae-1`, `psathyrella-buoy-com4`) **not** in `devices[]`.

## What was not visually re-toggled

After browser-use MCP stayed in `error` and this lane was ordered **not to deploy / not to reset main**, Environment / Conditions checkboxes were **not** each flipped in a second Playwright pass. Contract + BFF receipts cover draw-or-honest-empty. Treat map-animation of wind vectors as **API PASS / visual DEGRADED** until a human or a later browser session toggles them on the worktree Earth Sim tab.

## Leftover FAIL / DEGRADED

| Item | Mark | Why leftover |
|---|---|---|
| NLM weights / forecast qualification on 188 | DEGRADED | `model_loaded: false`; path tree stays local hypothesis |
| Website `/api/itdx/situation-assessment` | DEGRADED | Abort vs MAS 200 synthetic advisory |
| MINDEX AQ + FIRMS upstream | DEGRADED | Empty features; PM/fire layers cannot animate |
| Smoke renderer | DEGRADED | Quarantined by contract |
| Env-tab click animation | DEGRADED | MCP unavailable; not a dead control |
| Fake live tracks | none | **Not observed** |
| 5xx on Earth Sim BFFs | none | **Not observed** |
| Global ITDX dock on `/fusarium` or `/soc` | none | **Not observed** |

## Out of scope (honored)

- No blue-green, no Sandbox `192.168.0.187` changes, no `mycosoft.com` cutover
- No website-main reset / dirty-tree cleanup
- No new feature program
- Deploy-pipeline owner: `d0d48a45`
