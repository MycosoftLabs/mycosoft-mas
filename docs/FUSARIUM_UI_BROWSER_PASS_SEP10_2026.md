# Fusarium UI Browser Pass — September 10, 2026

**Date:** Thursday 10 September 2026  
**Status:** Complete (TEST ONLY — no blue-green, no 187, no website-main reset, no GPU)  
**Classification:** UNCLASSIFIED  
**Tester:** test-engineer (Cursor)  
**Owner:** Morgan Rockcoons (CEO / CTO / COO / SAO)  
**CFO:** RJ Ricasata (never COO)  
**Related:** `docs/FUSARIUM_E2E_BROWSER_TEST_SEP10_2026.md`, `docs/FUSARIUM_ITDX_LIVE_SHIP_SEP10_2026.md`, `docs/EARTH_SIM_PC_IPAD_DEMO_STABILITY_SEP10_2026.md`, `docs/ITDX_NLM_E2E_STATE_SEP10_2026.md`

## Verdict

**DEGRADED** — not FAIL. Desktop Earth Sim and NatureOS globes painted. ITDX is Earth-Sim-only, default collapsed, expand/collapse works on 1280 and (after a z-index bump) 768. No fake live convoy. NLM UI shows `forecast_qualified=false` and `p=null`, never stub `0.85`. No uncaught `pageerror`, no `webglcontextlost`, no failed JS chunks.

Live `https://mycosoft.com/fusarium/earth-simulator` is **200** but **login-gated** (Google owner). Globe / ITDX / filters were **not** exercised on live. 187 was not touched (`d0d48a45` owns that lane).

## Browser tools discovered

| Tool | Status |
|---|---|
| `plugin-browser-use-browser-use` | **error** — live discovery failed; `mcp_auth` timed out (30s) |
| `cursor-ide-browser` / Cursor internal browser MCP | **not in session catalog** |
| Playwright Chromium (ITDX worktree `node_modules`) | **used** — real clicks, console + network watchers, 1280 / 768 / 1024 viewports |

This is not a one-screenshot pass. Receipts: `docs/_fusarium_ui_browser_pass_sep10.json`, `docs/_fusarium_ui_recheck_sep10.json`, `docs/_fusarium_ui_api_probe_sep10.json`.

## 3010 vs live

| | `http://127.0.0.1:3010` | `https://mycosoft.com` |
|---|---|---|
| Origin | ITDX worktree `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13` (`npm run dev:next-only`, no GPU) | Public site (200). **Not rebuilt this pass.** |
| Auth | `POST /api/auth/local-dev-session` **200**, `supabaseSession: true` → `morgan@mycosoft.org` owner | Redirects Earth Sim → `/fusarium/login?redirectTo=/fusarium/earth-simulator`. Google owner form present. No owner Google session in this harness. |
| Earth Sim | Globe canvas=1. First compile **~130s**; later paints **2–4s**. ITDX chip present. | Login wall only. Cannot confirm ITDX chip, default-off layers, or movement/C2. |
| Lag vs 3010 | Current worktree (SOC alias + ITDX z-index 120 applied locally after first iPad click miss) | Live image **lags** this worktree for those two small fixes. Fusarium owner login chrome is present (not an old marketing page). |
| 5xx on watched BFFs | `/api/crep/waypoints` **503** (CREP). Fusarium / earth-simulator / movement / ITDX BFFs **200**. | Login page: no 5xx / no pageerror. |

## Auth / login

| Surface | Result |
|---|---|
| 3010 `/fusarium/login` (fresh context) | **200**, title `Fusarium Operator Sign In`, **Continue with owner Google**, no overflow |
| 3010 `/fusarium/login` (after mint) | Redirects to `/fusarium` overview (session already owner) |
| Live Earth Sim | **200** → same owner Google / email login. Other Google accounts denied (copy on page). |

## Route × viewport matrix

| Route | Viewport | HTTP / nav | ITDX dock | Globe | Overflow | Mark |
|---|---|---|---|---|---|---|
| `/fusarium/login` | 1280 | 200 | 0 | n/a | no | **PASS** |
| `/fusarium/earth-simulator` | 1280×800 | 200 | 1, default collapsed; expand→collapse | canvas=1, 2.1s after compile | no | **PASS** |
| `/natureos/earth-simulator` | 1280 | 200 | **0** | canvas=1, 3.4s | no | **PASS** |
| `/fusarium` | 1280 | 200 | **0** | n/a | no | **PASS** |
| `/fusarium/soc` (before fix) | 1280 | **404** `notFound()` (no catalog id `soc`) | 0 | n/a | no | **DEGRADED** → fixed |
| `/fusarium/soc` (after alias) | 768 | 307 unauth → login; owner **200** → `/fusarium/situational-awareness` | **0** | n/a | no | **PASS** |
| `/fusarium/devices` | 1280 | 200 DirtNet / catalog | 0 | n/a | no | **PASS** |
| `/fusarium/command-control` | 1280 | 200 Command & Control | 0 | n/a | no | **PASS** |
| `/fusarium/aerosol` | 1280 | 200 Aerosol app | 0 | n/a | no | **PASS** |
| `/fusarium/earth-simulator` | 768×1024 | 200 | chip present; first pass click timeout (z=90 vs Intel Feed z-90); **recheck expand/collapse PASS** after z=120 | canvas present | no | **PASS** (after fix) |
| `/fusarium/earth-simulator` | 1024×1366 | 200 | chip present (`Collapse` after session persist); first-pass click timeout | not fully re-clicked | no (1280 metrics) | **DEGRADED** (harness); chip exists |
| Live Earth Sim | 1280 | 200 login | not mounted | not painted | no | **DEGRADED** (auth wall) |

ITDX / movement targets on desktop: **Expand ITDX 115×44**, **Show movement / C2 178×44**. Nature legend buttons remain denser (~28px CREP chrome) — not treated as FAIL.

## Earth Sim clicks (3010)

1. Waited for globe (first hit paid Next compile ~130s; later 2–4s).  
2. ITDX chip: `Expand ITDX` → body showed Fort Stewart AO, **MAS NLM degraded. forecast_qualified=false. p=null. live=false.** Collapse worked. No “ITDX backend is not configured”.  
3. Nature → Legend / Filters → Environment / Conditions, **one at a time** (on then off; never ships+sats+radar together):

| Filter | Found | Toggled on→off | Mark |
|---|---|---|---|
| OpenTopo (`opentopoBasemap`) | yes | first click timed out (visible, not stable) | **DEGRADED** |
| Aerosol PM | yes | true → false | **PASS** |
| Aerosol wind | yes | true → false | **PASS** |
| Modeled spore dispersal | yes | true → false | **PASS** |
| Aerosol smoke | yes | true → false (renderer still NOT_SUPPLIED) | **DEGRADED** (honest) |
| Device movement paths | yes | true → false | **PASS** |
| Device coordination | yes | true → false | **PASS** |
| Device triangulation | yes | true → false | **PASS** |
| Hypothesis path tree | yes | true → false | **PASS** |

4. Devices secondary tab click **missed** on the first 1280 pass (`devicesTab: false`) — control exists (`data-crep-left-secondary-tab="devices"`). **DEGRADED** harness / scroll.  
5. Movement / C2 button clicked (44px). Compact panel text was empty 800ms later (button still read “Show”). Snapshot BFF **200**. **DEGRADED** visual panel body.  
6. Recheck 768: `weatherRadar` / `stormLightning` `aria-pressed=false`. Ships/sats are INFRA ids (not in Nature env legend) — boot file still default-off.

## Backend probes (real, ~10 Sep 2026 10:58–11:12 PT)

### MAS `192.168.0.188:8001`

| Endpoint | Status | Cite |
|---|---|---|
| `/health` | 200 | `status: degraded` — postgres/redis healthy; collectors skipped |
| `/api/nlm/health` | 200 | **`model_loaded: true`**, SHA `0c5fb815…`, `bound_to_ollama: false`, `forecast_qualified: false`, `training_origin: synthetic`, `p stays null` |
| `/api/avani/status` | 200 | `is_operational: true`, season spring |
| `POST /api/itdx/situation-assessment` Fort Stewart | 200 | `origin: SYNTHETIC_EXERCISE`, `live_cop: false`, `synthetic: true`, **no 0.85** |

### MINDEX `192.168.0.189:8000`

| Endpoint | Status | Cite |
|---|---|---|
| `/health` | 200 | healthy |

### Website BFF `localhost:3010`

| Route | Status | Cite |
|---|---|---|
| `/api/fusarium/movement/snapshot` | 200 | `liveDeviceCount: 0`, `pathTree.live: false`, `triangulation.live: false` / `unqualified-proposal`, `waypointCommand: propose-only`, trails/Weka **NOT_SUPPLIED**. Field seeds **absent**. |
| `/api/earth-simulator/devices?refresh=1` | 200 | Catalog only: `mushroom-1`, `hyphae-1`, `psathyrella-buoy-com4` (`source=field`). **Not** copied into movement COP. |
| `/api/crep/environment/air-quality` | 200 | empty FC, `upstream: unavailable` |
| `/api/crep/environment/wildfires` | 200 | empty FC, `upstream: unavailable` |
| `/api/earth2/layers/wind` | 200 | numeric u/v grid |
| `/api/earth2/spore-dispersal` | 200 | `runs: []` |
| `GET/POST /api/itdx/situation-assessment` | **200** | Was **abort/DEGRADED** on the morning E2E. Now JSON, `live_cop: false`. |

No 5xx on `/api/fusarium/*` or `/api/earth-simulator/*` in this pass.

## Console — every captured error class

Uncaught exceptions (`pageerror`): **none**. WebGL-lost flag: **false**. No `Loading chunk` / failed chunk messages.

| Type | Text (deduped) | Count class | Treat as |
|---|---|---|---|
| error | `Each child in a list should have a unique "key" prop` — `OuterLayoutRouter` | repeated on navigations | **DEGRADED** React warning, not a thrown exception |
| error | `Failed to load resource: 404` | `/api/Monitoring/health`, `/api/Devices`, `/api/fusarium/adapters`, `/api/fusarium/catalog/modalities`, `/api/fusarium/v1`, `/api/fusarium/v1/readiness`, `/api/fusarium/v1/connectors`, `/api/fusarium/v1/mission-areas`, `/api/fusarium/v1/missions`, `/fusarium/soc` (before alias) | **DEGRADED** leftover BFFs / NatureOS-style probes; not Earth Sim 5xx |
| error | `Failed to load resource: 503` | `/api/crep/waypoints` (4 hits) | **DEGRADED** unexpected CREP 5xx |
| warning | `[EntityStream] MAS entity stream disabled on public origin…` | Earth Sim | honest / expected on 3010 |
| warning | `[CREP] Buoy: Failed to fetch buoy data: AbortError` | Earth Sim | abort, not fake tracks |
| warning | `[.WebGL-…] GPU stall due to ReadPixels` | driver perf | not context-lost |
| log | Map loaded / jurisdiction / native entity layers / NEXRAD / ESRI imagery / railway | Earth Sim boot | OK |

## PASS / DEGRADED / FAIL matrix

| Check | Mark | Note |
|---|---|---|
| 3010 is ITDX worktree | **PASS** | movement schema `mycosoft.fusarium.device-movement.v1` |
| Login → Earth Sim / NatureOS Earth Sim | **PASS** | mint + clicks; NatureOS no ITDX |
| ITDX Earth-Sim-only, default collapsed | **PASS** | 0 on `/fusarium`, SA, devices, C2, aerosol, NatureOS |
| ITDX expand/collapse | **PASS** | 1280 + 768 recheck |
| No ITDX dock on overview | **PASS** | |
| `/fusarium/soc` | **PASS** after alias | was 404; now → situational-awareness, no dock |
| Env filters one-at-a-time | **PASS** / OpenTopo **DEGRADED** | 8/9 toggled; no ships+sats+radar combo |
| Movement / C2 control | **DEGRADED** | 44px control present; panel body not captured |
| Devices page | **PASS** | catalog ≠ convoy |
| Command-control page | **PASS** | |
| Aerosol app | **PASS** | same AQ/wind/spore contracts |
| NLM UI no stub 0.85 `p` | **PASS** | overlay `p=null`; MAS `forecast_qualified=false`, `model_loaded=true` |
| Fake live tracks | **PASS** | none; `liveDeviceCount: 0`; field ids not in snapshot |
| Uncaught JS / WebGL-lost / failed chunks | **PASS** | none |
| `/api/fusarium/*` + `/api/earth-simulator/*` 5xx | **PASS** | none |
| `/api/crep/*` 5xx | **DEGRADED** | waypoints 503 |
| Website ITDX situation-assessment | **PASS** | 200 (was abort) |
| MINDEX AQ / FIRMS | **DEGRADED** | honest empty |
| Smoke draw | **DEGRADED** | NOT_SUPPLIED / quarantined |
| NLM forecast qualification | **DEGRADED** | tensors loaded, not a calibrated `p` |
| iPad 768 overflow / 44px ITDX | **PASS** | after z-index 120 |
| iPad 1024 full click matrix | **DEGRADED** | chip present; first suite timed out before z-index fix |
| Live Earth Sim demo chrome | **DEGRADED** | 200 login wall; no Google owner in harness |
| Fake live convoy | **FAIL if seen** | **not seen** |

## Small worktree fixes this pass (3010 only)

| Fix | File | Why |
|---|---|---|
| ITDX chip `z-index` 90 → **120** | `website-itdx-codex-v13/components/itdx/itdx-earth-sim-overlay.module.css` | Intel Feed is `z-[90]`; iPad Expand click resolved but could not stabilize. Recheck 768 expand/collapse **PASS**. |
| `/fusarium/soc` → situational-awareness | `website-itdx-codex-v13/app/fusarium/(dashboard)/soc/page.tsx` | Reproduced Next `notFound()`. Unauth still 307 to login. |

No 187. No GPU. No website `main` reset.

## Out of scope (honored)

- No blue-green / Sandbox 187 (`d0d48a45`)
- No website-main dirty-tree cleanup
- No local Moshi / PersonaPlex / Earth-2 GPU
- Live Google owner login not completed (no interactive Google in this MCP session)
