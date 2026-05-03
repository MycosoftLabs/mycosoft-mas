# MAY02 Rollout — Verification Evidence (May 03, 2026)

**Date:** May 03, 2026  
**Purpose:** Record LAN/dev smoke results for the MAY02 continuation matrix (appendix to `docs/MAY02_CONTINUATION_ROLLOUT_COMPLETE_MAY02_2026.md`).  
**Environment:** Dev PC on LAN `192.168.0.x`; local Next.js `3010` where noted.

## Commands run (summary)

| Check | Target | Result |
|-------|--------|--------|
| BFF inventory | `python scripts/natureos_bff_route_inventory.py` (MAS repo) | **64** `route.ts` handlers under `WEBSITE/website/app/api/natureos` |
| MAS health | `GET http://192.168.0.188:8001/health` | **200** |
| MAS heartbeat | `GET http://192.168.0.188:8001/agents/heartbeat/summary` | **200** |
| MAS heartbeat (alt path) | `GET http://192.168.0.188:8001/api/agents/heartbeat/summary` | **200** |
| MAS Petri v2 | `GET http://192.168.0.188:8001/api/simulation/petri/v2/health` | **200** body `{"service":"petri_engine_service","status":"ok","version":"0.1.0"}` |
| MINDEX health | `GET http://192.168.0.189:8000/health` | **200** |
| MINDEX genetics kingdom | `GET http://192.168.0.189:8000/api/mindex/genetics?kingdom=Fungi&limit=2` **without** `X-API-Key` | **401 Unauthorized** (router requires API key — expected) |
| MINDEX genomes kingdom | `GET .../api/mindex/genomes?kingdom=Fungi&limit=2` without key | **401** |
| Sandbox website | `GET http://192.168.0.187:3000/` | **200** |
| Earth-simulator redirect | `GET http://localhost:3010/earth-simulator` (no follow) | **308** `Location: /natureos/earth-simulator` |
| Petri BFF (local dev) | `GET http://localhost:3010/api/simulation/petri/v2/health` | **200** same Petri JSON as MAS proxy |
| MATLAB BFF health | `GET http://localhost:3010/api/natureos/matlab/health` | **200** `{"available":false,"mode":"Unavailable","message":"NatureOS backend unreachable"}` — honest degraded state when .NET backend absent |

## Notes

- **MYCA “Stale agents” badge** and **`?petriStats=1` UI** require browser sessions and optional MAS pause; not captured as HTTP-only proof here — use `docs/NATUREOS_STAGING_MATRIX_MAY02_2026.md` for full UI passes.
- **MINDEX genetics/genomes** kingdom filtering: verify with `X-API-Key` / internal token per deployment secrets (do not paste keys into docs).

## Session execution log

See **`docs/MAY03_SESSION_EXECUTION_LOG_MAY03_2026.md`** for files changed and post-commit verification in this implementation pass.
