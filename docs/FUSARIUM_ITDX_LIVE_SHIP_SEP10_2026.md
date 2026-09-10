# Fusarium ITDX live ship — 10 September 2026

**Date:** Thursday 10 September 2026  
**Status:** Shipped (website blue-green + GitHub save)  
**Classification:** UNCLASSIFIED  
**Owner:** Morgan Rockcoons (CEO / CTO / COO / SAO)  
**CFO:** RJ Ricasata (never COO)  
**E2E receipt:** `docs/FUSARIUM_E2E_BROWSER_TEST_SEP10_2026.md` (tester 88bb74ff) — **No FAIL. No fake live tracks.**

## Live URL

https://mycosoft.com/fusarium/earth-simulator — Google owner login (`morgan@mycosoft.org`).

## What to click

1. Sign in at `/fusarium/login` with Google owner.
2. Open **Earth Simulator**. Confirm the **ITDX** chip is present and **collapsed** (`Expand ITDX`). Expand / collapse; it must not appear on `/fusarium` or `/fusarium/soc`.
3. Nature → **Environment / Conditions**: OpenTopo, path / coordination / triangulation / path tree, aerosol PM / wind / modeled dispersal / smoke.
4. `/fusarium/command-control` — Device movement panel. Waypoints are **propose-only**.
5. `/fusarium/devices` — OSINT equipment library. Catalog cards are **not on-hand** unless the live registry names the same id.

## What shipped

| Surface | Truth |
|---|---|
| ITDX overlay | Earth-Sim-only collapsible chip. Default collapsed. No global dock / evidence strip / fictional replay on overview or SOC. |
| Post-1.4 config honesty | Optional 8765/8766 lab unset → **NOT_SUPPLIED / UNQUALIFIED**, never “ITDX backend is not configured.” Cite path is MAS 188 + MINDEX 189. |
| OSINT topo | AWS Terrain hillshade + optional OpenTopoMap (© OSM + SRTM / OpenTopoMap CC-BY-SA). Fort Stewart AO stays **-81.6072, 31.8697**. |
| Devices library | `/fusarium/devices` public manufacturer-class cards + live registry rows. Field seeds ≠ convoy. |
| Aerosol filters on Earth Sim env tab | PM, modeled spore dispersal, wind, AQ, FIRMS reuse aerosol/CREP/Earth-2 contracts. **Smoke renderer NOT_SUPPLIED** (CREP `SmokeLayer` stays quarantined). |
| Droid path / coordination / triangulation / hypothesis tree | `GET /api/fusarium/movement/snapshot`. Live polyline only with ≥2 telemetry fixes. Coordination needs ≥2 live devices. Triangulation live only with ≥3 observers; otherwise `live: false` / `unqualified-proposal`. Path tree always **hypothesis**. |
| Waypoints | **Propose-only.** `/api/devices/network/[id]/command` is ping/sensors. Receipt **NOT_SUPPLIED**. |
| Website ITDX BFF | New `GET/POST /api/itdx/situation-assessment` fails closed to JSON (`live_cop: false`). Owner UI still uses `/api/fusarium/itdx/situation`. Direct MAS POST remains 200 synthetic advisory. |

## NLM / Weka / Hess

Do **not** wait for NLM weights to load. Pointer: `docs/PERPLEXITY_DR_HESS_EMAIL_ATTACHMENT_HANDOFF_SEP10_2026.md`.

| Item | State |
|---|---|
| MAS `/api/nlm/health` | Honest `model_loaded: false`, `bound_to_ollama: false`, `forecast_qualified: false`. No stub `0.85 p`. |
| Fusarium ecology `p` | `null` until a qualified forecast family is promoted. |
| Weka | Evaluation workbench around recorded NLM probabilities. Not required to operate NLM. Trial / field readiness **NOT MET**. |
| ITDX Intel Feed | MAS `origin: SYNTHETIC_EXERCISE`, `live_cop: false`. Demo overlay ≠ live COP. |

## E2E (not cutover blockers)

**PASS:** 3010 worktree; ITDX Earth-Sim-only collapsed; no dock on overview/SOC; 1 live MAS device (`mycobrain-service-192-168-0-241`); catalog ≠ convoy; path/coord/tree contract; waypoints propose-only; OpenTopo; wind 200.

**DEGRADED (shipped anyway):** NLM unloaded; website `/api/itdx/situation-assessment` previously aborted (alias added this ship); smoke NOT_SUPPLIED; MINDEX AQ/FIRMS empty (`upstream: unavailable`).

## Live vs hypothesis vs NOT_SUPPLIED

| Kind | Examples |
|---|---|
| **Live** | MAS registry heartbeat position; wind BFF numeric grid; AVANI `/status` operational; movement `liveDeviceCount` may be 0 or 1 |
| **Hypothesis** | Path tree; triangulation without ≥3 live observers; Intel Feed synthetic exercise |
| **NOT_SUPPLIED** | Smoke renderer; NLM/Weka movement proposals; waypoint execution receipt; telemetry trails until ≥2 fixes; official Army / FOUO injects; MINDEX AQ/FIRMS features while upstream unavailable; forecast-qualified NLM |

## SHAs / PRs

Filled at merge time in the closeout block below.

Related website worktree: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13` (never reset dirty `WEBSITE/website` main / Launchpad WIP).

## How to verify live

- Origin `http://192.168.0.187:3000` HTTP 200
- `https://mycosoft.com` and `https://sandbox.mycosoft.com` HTTP 200
- `https://mycosoft.com/fusarium/earth-simulator` after Google owner login
- Movement snapshot: catalog ids `mushroom-1`, `hyphae-1`, `psathyrella-buoy-com4` must **not** appear as live convoy devices

## Related

- `docs/FUSARIUM_E2E_BROWSER_TEST_SEP10_2026.md`
- `docs/ITDX_NLM_E2E_STATE_SEP10_2026.md`
- `docs/NLM_WEIGHTS_IMPLEMENTED_MAS188_SEP10_2026.md`
- `docs/PERPLEXITY_DR_HESS_EMAIL_ATTACHMENT_HANDOFF_SEP10_2026.md`
- Website `docs/ITDX_V14_CONFIG_ERROR_FIX_SEP10_2026.md`
- Website `docs/FUSARIUM_DROID_PATH_C2_EARTH_SIM_SEP10_2026.md`
- Website `docs/EARTH_SIM_AEROSOL_LAYERS_SEP10_2026.md`
- Website `docs/FUSARIUM_OSINT_TOPO_DEVICES_TRACKING_SEP10_2026.md`
