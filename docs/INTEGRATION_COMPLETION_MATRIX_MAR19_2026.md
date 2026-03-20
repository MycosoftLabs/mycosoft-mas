# Integration Completion Matrix — Mar 19, 2026

**Date:** March 19, 2026  
**Status:** Live contract matrix  
**Related:** [PLATFORM_GAP_AUDIT_AND_BACKLOG_MAR19_2026.md](PLATFORM_GAP_AUDIT_AND_BACKLOG_MAR19_2026.md)

---

## Purpose

Each row is an **integration surface**. Columns: owning repo, env vars, health URLs, **definition of done**, linked canonical doc.

---

## Matrix

| Surface | Owning repo | Env vars | Health URL | Definition of done | Canonical doc |
|---------|-------------|----------|------------|--------------------|---------------|
| **MAS↔MINDEX** | MAS, MINDEX | `MINDEX_API_URL`, `MAS_API_URL` | `http://192.168.0.188:8001/health`, `http://192.168.0.189:8000/health` | All router pairs use shared models; timeouts aligned; 503 on upstream fail | [CREP_SYSTEM_INTEGRATION_AUDIT_MAR11_2026.md](CREP_SYSTEM_INTEGRATION_AUDIT_MAR11_2026.md) |
| **Website BFF** | WEBSITE | `MAS_API_URL`, `MINDEX_API_URL`, `NEXT_PUBLIC_*` | `http://localhost:3010/api/health` | Routes proxy to MAS/MINDEX; empty states on upstream failure; no mock data | [no-mock-data.mdc](../.cursor/rules/no-mock-data.mdc) |
| **NatureOS / SignalR** | WEBSITE, NatureOS | `NATUREOS_API_URL`, SignalR hub URL | — | Live-map and AI Studio use real SignalR; no stub endpoints | [SUPERAPP_ARCHITECTURE_AND_UNIFICATION_FEB19_2026.md](SUPERAPP_ARCHITECTURE_AND_UNIFICATION_FEB19_2026.md) |
| **CREP command** | MAS, WEBSITE | — | CREP dashboard loads | Commands flow MAS→WebSocket→CREP; schema matches contract; smoke: flyTo, showLayer per contract | [CREP_COMMAND_CONTRACT_MAR13_2026.md](CREP_COMMAND_CONTRACT_MAR13_2026.md) |
| **Device / MycoBrain** | MAS, WEBSITE | `MYCOBRAIN_*`, `MAS_REGISTRY_URL` | `http://localhost:8003/health` | Device Manager shows real devices; heartbeat→MAS; no mock device list | [CREP_SYSTEM_INTEGRATION_AUDIT_MAR11_2026.md](CREP_SYSTEM_INTEGRATION_AUDIT_MAR11_2026.md) |
| **Voice stack** | MAS, WEBSITE | `VOICE_PROVIDER`, PersonaPlex URLs | `http://localhost:8999/health` | speak→MAS→audio path works; bridge wired to real provider | [VOICE_TEST_QUICK_START_FEB18_2026.md](VOICE_TEST_QUICK_START_FEB18_2026.md) |
| **n8n** | MAS | `N8N_URL` | `http://192.168.0.188:5678/healthz` | Workflows trigger MAS/MINDEX; sync local+cloud per n8n-management | [.cursor/rules/n8n-management.mdc](../.cursor/rules/n8n-management.mdc) |
| **Scientific / FCI** | WEBSITE | — | `/api/bio/fci`, `/api/fci/devices` | useFCI and useFCIDevices fetch real APIs; empty state on failure; no mock device/session fallback | [no-mock-data.mdc](../.cursor/rules/no-mock-data.mdc) |

---

## Realtime spine (WebSocket / SSE / SignalR)

| Surface | Spine | Notes |
|---------|-------|-------|
| **Voice** | WebSocket (PersonaPlex Bridge 8999) | Full-duplex; bridge connects MAS to browser |
| **CREP** | WebSocket | Commands relay MAS→dashboard per [CREP_COMMAND_CONTRACT_MAR13_2026.md](CREP_COMMAND_CONTRACT_MAR13_2026.md) |
| **NatureOS** | SignalR (WebSocket) | Live-map, AI Studio; hub in NatureOS core-api |
| **Devices** | HTTP heartbeat (30s poll) | MycoBrain→MAS registry; no push spine |
| **n8n** | Webhooks (inbound) | Not push; workflows triggered by HTTP |

**GPU placement:** Voice (Moshi/PersonaPlex) and Earth2 run on **GPU node 192.168.0.190** in production; locally for dev. See [python-process-registry.mdc](../.cursor/rules/python-process-registry.mdc) port table. Bridge 8999, Moshi 8998; kill after testing to free VRAM.

---

## VM layout reference

| VM | IP | Key services |
|----|-----|--------------|
| Sandbox | 192.168.0.187 | Website 3000, MycoBrain 8003 |
| MAS | 192.168.0.188 | Orchestrator 8001, n8n 5678, Ollama 11434 |
| MINDEX | 192.168.0.189 | API 8000, Postgres 5432, Redis 6379, Qdrant 6333 |
| GPU node | 192.168.0.190 | Voice, Earth2, inference |
