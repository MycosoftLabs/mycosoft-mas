# Earth Sim PC / iPad Demo Stability — September 10, 2026

**Date:** Thursday 10 September 2026  
**Status:** Audit + worktree fixes (no 187 blue-green, no `WEBSITE/website` main reset, no local GPU)  
**Classification:** UNCLASSIFIED  
**Owner:** Morgan Rockcoons (CEO / CTO / COO / SAO)  
**CFO:** RJ Ricasata (never COO)  
**Related:** `docs/FUSARIUM_E2E_BROWSER_TEST_SEP10_2026.md`, `docs/CURSOR_FUSARIUM_EARTHSIM_IPAD_FIX_SEP03_2026.md`

## Surfaces

| Entry | Live route | Stack |
|---|---|---|
| **Fusarium** | `http://localhost:3010/fusarium/earth-simulator` | Shared CREP MapLibre globe + ITDX chip + movement/C2 host |
| **NatureOS** | `http://localhost:3010/natureos/earth-simulator` | Same `CREPDashboardLoader` + `EarthSimulatorViewportLock`. `/apps/earth-simulator` redirects here. |
| NatureOS C# app | `NATUREOS/NatureOS/src/dashboard` | Legacy DeviceMap dashboard — **not** the live globe |

3010 served the ITDX worktree movement contract (`mycosoft.fusarium.device-movement.v1`). Public `mycosoft.com` / Sandbox 187 were not touched.

## Matrix — route × viewport

Playwright (Edge, headless) after `POST /api/auth/local-dev-session`. One MapLibre canvas per Earth Sim load. No pageerror, no WebGL-lost, no OOM string, no horizontal overflow.

| Route | Viewport | Result | Notes |
|---|---|---|---|
| `/natureos/earth-simulator` | 1280×800 PC | **OK** | canvas=1; no ITDX; 14s to settle |
| `/natureos/earth-simulator` | 768×1024 iPad | **LAG** | canvas=1; no crash; 21s first paint |
| `/natureos/earth-simulator` | 1024×1366 iPad Pro | **LAG** | canvas=1; 32s first paint |
| `/fusarium/earth-simulator` | 1280×800 PC | **LAG** | canvas=1; ITDX collapsed `live=false`; expand/collapse PASS; movement/C2 present; 33s |
| `/fusarium/earth-simulator` | 768×1024 iPad | **LAG** | Same chrome; 31s; no overflow |
| `/fusarium/earth-simulator` | 1024×1366 iPad Pro | **LAG** | Same chrome; 33s; no overflow |
| `/fusarium` (control) | after Earth Sim | **OK** | ITDX overlay count **0** |

No **ERROR** or **CRASH** in this pass. **LAG** is first-paint / WebGL boot time, not a thrown exception.

Movement snapshot at probe time: `liveDeviceCount: 0`, honest empty (no invented tracks). Smoke stays **NOT_SUPPLIED** / quarantined.

## What was fixed (ITDX worktree)

| Fix | File |
|---|---|
| Ships, satellites, weather radar, lightning, Eagle Eye **off at boot** (PC + iPad) | `lib/crep/earth-simulator-boot.ts` |
| Same ids added to tablet heavy-off set | `CREPDashboardClient.tsx` `HEAVY_TABLET_OFF_LAYER_IDS` |
| ITDX replay MapLibre layer only on `/fusarium/earth-simulator` | `ITDXReplayLayer.tsx` |
| Pause ITDX replay clock when `document.hidden` | `lib/itdx/replay-store.ts` |
| Pause satellite rAF when tab hidden; resume on visible | `lib/crep/satellite-animation.ts` |
| Movement COP poll only when overlays on, Fusarium path only, pause when hidden | `device-movement-layers.tsx`, `device-movement-panel.tsx` |
| iPad ITDX chip: 16px / 44px targets, `touch-action: manipulation` | `ITDXEarthSimOverlay.tsx` + CSS |
| Movement/C2 safe-area + `text-base` | `earth-sim-movement-host.tsx` |
| WebGL lost: `preventDefault`, flag, resize/repaint on restore; `map.remove()` already on unmount | `components/ui/map.tsx` |
| Viewport lock `min-h-dvh` | `EarthSimulatorViewportLock.tsx` |

Boot check (`tsx`): `ships/satellites/weatherRadar/stormLightning/eagleEyeCameras` all `enabled:false`; EcM fungal stays on.

## Worst 3 risks for a live iPad demo

1. **First-paint lag (21–33s)** — globe + CREP boot still slow on tablet viewports. **Not fully fixed.** Do not hammer filters during the first half-minute. Default-off heavy layers reduces crash risk once painted.
2. **Operator “all-on” of ships + satellites + radar** — still the fastest way to freeze an iPad GPU. **Default-off is fixed**; toggling them together is still a live risk. Keep aerosol smoke off (quarantined).
3. **iPadOS backgrounding / WebGL context loss** — Safari can drop the context when switching apps. **Handler added** (`preventDefault` + restore). Residual: a hard tab-kill still requires a refresh.

## Out of scope

- No blue-green / 187 deploy (other owner).  
- No reset of dirty `WEBSITE/website` main.  
- No local GPU / Earth-2 inference started.  
- NatureOS C# frontend not changed (not the live globe).
