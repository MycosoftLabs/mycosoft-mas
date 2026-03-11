# Full Integration — Read, Write, Search, Interact

**Date:** March 9, 2026  
**Status:** Reference  
**Related:** MYCA-Only Architecture, Full Integration Program

---

## Summary

MYCA and the AI stack are **readable, writable, searchable, and interactive** with all core systems. This document maps each system to its API surface so MYCA (and agents) can ground responses, store context, and act on data.

---

## System Map: Read / Write / Search / Interact

| System | Read | Write | Search | Interact (AI) | Base URL |
|--------|------|-------|--------|---------------|----------|
| **MAS** | ✅ | ✅ | ✅ | ✅ | `http://192.168.0.188:8001` |
| **MINDEX** | ✅ | ✅ | ✅ | ✅ | `http://192.168.0.189:8000` |
| **Device Registry** | ✅ | ✅ | — | ✅ | MAS `/api/devices/` |
| **Merkle World Root** | ✅ | ✅ | — | ✅ | MAS `/api/merkle/` |
| **CREP** | ✅ | — | ✅ | ✅ | MAS / CREP collectors |
| **Earth2** | ✅ | — | — | ✅ | MAS / Earth2 API |
| **NLM** | ✅ | — | — | ✅ | MAS / NLM |
| **MycoBrain** | ✅ | ✅ | — | ✅ | `localhost:8003` / Sandbox 187 |
| **Website** | ✅ | ✅ | — | ✅ | Sandbox 187:3000 |

---

## MAS (192.168.0.188:8001)

### Read

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Service health |
| `GET /api/devices/` | Device registry list |
| `GET /api/devices/network` | Network device snapshot |
| `GET /api/merkle/health` | Merkle ledger health |
| `GET /openapi.json` | API spec |

### Write

| Endpoint | Purpose |
|----------|---------|
| `POST /api/devices/heartbeat` | Device heartbeat (MycoBrain) |
| `POST /api/merkle/roots/world` | Build/store world root |
| `POST /api/chat` | Chat with MYCA |

### Search

| Endpoint | Purpose |
|----------|---------|
| `GET /api/devices/` | Filter devices by role/status |

### Interact (AI)

- **LLM brain** (`llm_brain.py`): Ollama primary; injects device/world context for grounding.
- **Merkle world root**: Built from `slot_data` and appended to context as `[Merkle world root]: {hex}`.
- **Device snapshot**: `get_device_registry_snapshot()` → `slot_data["device_registry"]`.

---

## MINDEX (192.168.0.189:8000)

### Read

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Service health |
| `GET /api/mindex/unified-search?q=` | Cross-table search (taxa, compounds, genetics) |
| `GET /api/mindex/taxa/` | Taxon list |
| `GET /api/mindex/compounds/` | Compounds |
| `GET /api/mindex/knowledge/` | Knowledge graph |

### Write

| Endpoint | Purpose |
|----------|---------|
| `POST /api/mindex/observations/` | Add observations |
| `POST /api/mindex/telemetry/` | Telemetry ingest |
| `POST /api/mindex/grounding/` | Grounding data |

### Search

| Endpoint | Purpose |
|----------|---------|
| `GET /api/mindex/unified-search?q=` | Main search: species, compounds, genetics |
| `GET /api/mindex/unified-search/taxa/by-location` | Taxa by location |

### Interact (AI)

- **Unified search**: AI can query species, compounds, genetics for grounded answers.
- **Grounding router**: Spatial, episodic, EPs for grounded cognition.
- **Knowledge router**: World model categories.

---

## Device Registry (via MAS)

- **Read**: `GET /api/devices/`, `GET /api/devices/network`, `get_device_registry_snapshot()` in code.
- **Write**: `POST /api/devices/heartbeat` (MycoBrain service).
- **Interact**: Snapshot injected into LLM context; MYCA knows which devices are online.

---

## Merkle World Root (via MAS)

- **Read**: `GET /api/merkle/health`, world root in context string.
- **Write**: `POST /api/merkle/roots/world` (build from `slot_data`).
- **Interact**: Root appended to LLM context for provable grounding.

---

## MycoBrain (localhost:8003 or Sandbox 187)

- **Read**: `GET /health`, `GET /devices`.
- **Write**: Serial commands to devices.
- **Interact**: Heartbeats to MAS; device list visible to MYCA.

---

## Tests

### Unit (always run)

```bash
poetry run pytest tests/test_myca_only_architecture.py -v --tb=short
```

### Integration (requires VMs reachable)

```bash
# Run when MAS/MINDEX VMs are up
poetry run pytest tests/test_full_integration_apis.py -v --tb=short

# Skip integration tests (e.g. CI without VMs)
SKIP_INTEGRATION=1 poetry run pytest tests/test_full_integration_apis.py -v
```

**Note:** MAS has rate limiting. If tests return `429 Too Many Requests`, the API is reachable; wait for the rate limit window to reset or run with `SKIP_INTEGRATION=1` to skip integration tests.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAS_API_URL` | `http://192.168.0.188:8001` | MAS orchestrator |
| `MINDEX_API_URL` | `http://192.168.0.189:8000` | MINDEX API |
| `SKIP_INTEGRATION` | `0` | Set `1` to skip integration tests |

---

## Verification Checklist

- [ ] MAS health: `curl http://192.168.0.188:8001/health`
- [ ] Device registry: `curl http://192.168.0.188:8001/api/devices/`
- [ ] Merkle world root: `curl -X POST http://192.168.0.188:8001/api/merkle/roots/world -H "Content-Type: application/json" -d '{}'`
- [ ] MINDEX health: `curl http://192.168.0.189:8000/health`
- [ ] MINDEX search: `curl "http://192.168.0.189:8000/api/mindex/unified-search?q=psilocybe"`
