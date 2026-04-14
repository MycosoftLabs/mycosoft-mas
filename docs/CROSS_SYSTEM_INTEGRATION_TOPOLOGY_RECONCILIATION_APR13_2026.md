# Cross-System Integration Topology Reconciliation — Apr 13, 2026

**Date:** April 13, 2026  
**Status:** Active runbook pointer  
**Related:** [INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md](INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md) (updated for split Legions)

## Purpose

Document the **canonical LAN topology** for CREP, Earth-2, MINDEX, NatureOS/Fusarium, MycoBrain, and MYCA voice/brain so runbooks, `.cursor` rules, and `gpu_node_client.py` defaults stay aligned.

## Canonical IPs

| Role | IP | Ports / notes |
|------|-----|----------------|
| Sandbox | 192.168.0.187 | Website 3000, MycoBrain 8003 |
| MAS | 192.168.0.188 | Orchestrator 8001, n8n 5678 |
| MINDEX | 192.168.0.189 | API 8000, Postgres, Redis, Qdrant |
| Voice Legion | 192.168.0.241 | PersonaPlex bridge 8999, Moshi 8998, Ollama 11434 |
| Earth-2 Legion | 192.168.0.249 | Earth-2 API 8220 (WSL; refresh portproxy after WSL IP change) |

Legacy **192.168.0.190** as a single combined GPU node is **deprecated** in documentation; use 241/249 explicitly.

## Env variables (MAS / website)

- `GPU_VOICE_IP`, `MOSHI_API_URL`, `OLLAMA_BASE_URL` / Nemotron host → voice Legion.
- `GPU_EARTH2_IP`, `EARTH2_API_URL` → `http://192.168.0.249:8220` (or LAN hostname).
- Sandbox website: `MAS_API_URL`, `MINDEX_API_URL`, `PERSONAPLEX_BRIDGE_URL`, `NEXT_PUBLIC_*` — container must load **`--env-file`** when merging keys.

## Verification commands

**Script (Windows, from repo root):** `powershell -ExecutionPolicy Bypass -File scripts/verify_cross_system_health.ps1`

```bash
curl -sS -o /dev/null -w "%{http_code}" http://192.168.0.188:8001/health
curl -sS -o /dev/null -w "%{http_code}" http://192.168.0.189:8000/health
curl -sS -o /dev/null -w "%{http_code}" http://192.168.0.241:8999/health
curl -sS -o /dev/null -w "%{http_code}" http://192.168.0.249:8220/health
```

### LAN probe snapshot (dev machine; YMMV)

From a single off-LAN or filtered session, MINDEX (189) and Sandbox (187) may return **200** while MAS (188), Voice (241), and Earth-2 (249) return **unreachable** — run the script on a workstation on `192.168.0.0/24` for authoritative results.

## Earth-2 and CREP chain (code reference)

- Website `GET /api/earth2` proxies to `MAS_API_URL/api/earth2/status` (see `WEBSITE/website/app/api/earth2/route.ts`).
- MAS implements `GET /api/earth2/status` in `mycosoft_mas/core/routers/earth2_api.py`, which delegates to the Earth-2 service (env `EARTH2_API_URL` → Legion **249**).
- CREP map commands remain per [CREP_COMMAND_CONTRACT_MAR13_2026.md](CREP_COMMAND_CONTRACT_MAR13_2026.md); no code change required for topology reconciliation.

## Voice canonical path (code reference)

- PersonaPlex bridge health is proxied at `GET /api/test-voice/bridge/health` (`WEBSITE/website/app/api/test-voice/bridge/health/route.ts`) → `PERSONAPLEX_BRIDGE_URL` on LAN.
- `callMasBrain` in `app/api/mas/voice/orchestrator/route.ts` posts to `POST /voice/brain/chat` on MAS ([CANONICAL_MYCA_VOICE_PATH_MAR14_2026.md](CANONICAL_MYCA_VOICE_PATH_MAR14_2026.md)).

## NatureOS / Fusarium / MycoBrain

- Configure MINDEX on **189** with `natureos_api_key`, `natureos_ingest_path`, `fusarium_fanout_enabled` per [MINDEX_JETSON_NATUREOS_FUSARIUM_PIPELINE_COMPLETE_APR08_2026.md](MINDEX_JETSON_NATUREOS_FUSARIUM_PIPELINE_COMPLETE_APR08_2026.md).
- MycoBrain heartbeats and device registry: matrix row **Device / MycoBrain** in [INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md](INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md).

## Files updated with this reconciliation

- `docs/INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md` — matrix row for voice env/health; GPU placement; VM table.
- `.cursor/rules/vm-layout-and-dev-remote-services.mdc`, `python-process-registry.mdc`, `vm-ssh-mcp.mdc`, `run-servers-externally.mdc`, `mycosoft-full-context-and-registries.mdc`.
