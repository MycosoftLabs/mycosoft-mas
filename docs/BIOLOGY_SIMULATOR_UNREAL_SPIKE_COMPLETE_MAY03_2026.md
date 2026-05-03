# Biology Simulator — Unreal Pixel Streaming Spike Complete (May 03, 2026)

**Date:** May 03, 2026  
**Status:** Spike complete (architecture + env contract + UI surfacing)  
**Related plan shell:** `docs/BIOLOGY_SIMULATOR_UNREAL_INTEGRATION_PLAN_MAY01_2026.md`

## Architecture (target state)

| Concern | Recommendation |
|---------|------------------|
| **Delivery** | **Pixel Streaming** for interactive Unreal viewport in-browser; alternative **USD / glTF** export path for non-streamed previews (out of MVP scope). |
| **Security** | Stream URLs must be **HTTPS** or same-site; signaling servers isolated from public DB credentials; MAS task envelope carries session/user scope only — no secrets in browser. |
| **MAS** | Future “spawn simulation” tasks should return `{ job_id, stream_ticket }` minted by Unreal sidecar — not raw GPU credentials. |

## Env contract (implemented)

| Variable | Purpose |
|----------|---------|
| `UNREAL_PIXEL_STREAM_URL` / `NEXT_PUBLIC_UNREAL_PIXEL_STREAM_URL` | Player/WebRTC entry URL when streaming is live. |
| `UNREAL_SIGNALING_URL` / `NEXT_PUBLIC_UNREAL_SIGNALING_URL` | Optional signaling endpoint for multi-peer setups. |

## Website

- `GET /api/natureos/biology-simulator/unreal-bridge` — returns `{ bridge, enabled, pixelStreamUrl, signalingUrl, message }` from env only (**no fake stream**).
- `BiologySimulatorUnrealPanel` — displays configured vs roadmap-only state on biology simulator landing.

## Deferred

- Hosting Unreal packaged build + Pixel Streaming infra on LAN/VPC.
- USD pipeline from lab digital twin tooling.
