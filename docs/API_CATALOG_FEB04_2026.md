# API Catalog - Full Spectrum Memory Registry
## Created: February 4, 2026

## Overview

This document catalogs all API endpoints across the Mycosoft ecosystem. The registry tracks 200+ endpoints across 6 core systems.

## Systems Overview

| System | Base URL | API Count | Description |
|--------|----------|-----------|-------------|
| MAS | http://192.168.0.188:8001 | 80+ | Multi-Agent System Orchestrator |
| Website | http://192.168.0.187:3000 | 40+ | Next.js Dashboard & Website |
| MINDEX | http://192.168.0.189:8000 | 50+ | Memory Index & Knowledge Graph |
| NatureOS | http://192.168.0.188:5000 | 30+ | Nature Operating System |
| MycoBrain | http://192.168.0.188:8080 | 20+ | IoT Device Management |
| NLM | http://192.168.0.188:8200 | 15+ | Nature Learning Models |

---

## MAS API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/metrics` | GET | Prometheus metrics |

### Memory API (`/api/memory/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/memory/write` | POST | Write to memory (with crypto integrity) |
| `/api/memory/read` | POST | Read from memory |
| `/api/memory/delete` | POST | Delete memory entry |
| `/api/memory/list/{scope}/{namespace}` | GET | List keys in namespace |
| `/api/memory/summarize` | POST | Summarize conversation |
| `/api/memory/audit` | GET | Get audit log |
| `/api/memory/health` | GET | Memory system health |

### Security API (`/api/security/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/security/audit/log` | POST | Log audit entry |
| `/api/security/audit/query` | GET | Query audit log |
| `/api/security/audit/stats` | GET | Audit statistics |
| `/api/security/health` | GET | Security service health |

### Registry API (`/api/registry/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/systems` | GET | List systems |
| `/api/registry/systems` | POST | Register system |
| `/api/registry/systems/{name}` | GET | Get system |
| `/api/registry/apis` | GET | List APIs |
| `/api/registry/apis/count` | GET | API count |
| `/api/registry/apis/index` | POST | Trigger indexing |
| `/api/registry/apis/index/sync` | POST | Sync indexing |
| `/api/registry/agents` | GET | List agents |
| `/api/registry/agents` | POST | Register agent |
| `/api/registry/services` | GET | List services |
| `/api/registry/services` | POST | Register service |
| `/api/registry/services/{name}/health` | POST | Update health |
| `/api/registry/devices` | GET | List devices |
| `/api/registry/devices` | POST | Register device |
| `/api/registry/devices/health` | GET | Device health |
| `/api/registry/devices/firmware` | GET | Firmware report |
| `/api/registry/devices/initialize` | POST | Init devices |
| `/api/registry/devices/{id}/status` | POST | Update status |
| `/api/registry/code/stats` | GET | Code statistics |
| `/api/registry/code/index` | POST | Index code |
| `/api/registry/stats` | GET | Registry stats |
| `/api/registry/health` | GET | Registry health |

### Graph API (`/api/graph/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph/nodes` | GET | List nodes |
| `/api/graph/nodes` | POST | Create node |
| `/api/graph/nodes/{id}` | GET | Get node |
| `/api/graph/nodes/by-name/{name}` | GET | Find by name |
| `/api/graph/nodes/{id}/neighbors` | GET | Get neighbors |
| `/api/graph/edges` | GET | List edges |
| `/api/graph/edges` | POST | Create edge |
| `/api/graph/path` | POST | Find path |
| `/api/graph/subgraph/{id}` | GET | Get subgraph |
| `/api/graph/build` | POST | Build graph |
| `/api/graph/build/sync` | POST | Sync build |
| `/api/graph/stats` | GET | Graph stats |
| `/api/graph/health` | GET | Graph health |

### Voice API (`/api/voice/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/voice/session` | POST | Create session |
| `/api/voice/tts` | POST | Text to speech |
| `/api/voice/stt` | POST | Speech to text |
| `/api/voice/health` | GET | Voice health |

### MINDEX Integration (`/api/mindex/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mindex/query` | POST | Query MINDEX |
| `/api/mindex/health` | GET | MINDEX health |

### NatureOS Integration (`/api/natureos/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/natureos/telemetry` | POST | Device telemetry |
| `/api/natureos/health` | GET | NatureOS health |

### Workflow API (`/api/workflow/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflow/trigger` | POST | Trigger workflow |
| `/api/workflow/status/{id}` | GET | Get status |

---

## MINDEX API Endpoints

### Core APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

### Memory API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/memory/write` | POST | Write memory |
| `/api/memory/read` | POST | Read memory |
| `/api/memory/delete` | POST | Delete memory |
| `/api/memory/list/{scope}/{namespace}` | GET | List keys |
| `/api/memory/health` | GET | Memory health |

### Ledger API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ledger/stats` | GET | Ledger statistics |
| `/api/ledger/verify` | POST | Verify chain |
| `/api/ledger/blocks` | GET | List blocks |
| `/api/ledger/entries/{type}` | GET | Get entries |
| `/api/ledger/health` | GET | Ledger health |

---

## Website API Endpoints (Next.js)

### API Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents` | GET, POST | Agent management |
| `/api/topology` | GET | Agent topology |
| `/api/memory` | GET, POST | Memory proxy |
| `/api/voice/tts` | POST | TTS proxy |
| `/api/voice/stt` | POST | STT proxy |
| `/api/voice/session` | POST | Voice session |
| `/api/natureos/devices` | GET | Device list |
| `/api/natureos/telemetry` | POST | Telemetry |
| `/api/scientific/experiments` | GET, POST | Experiments |
| `/api/bio/sensors` | GET | Biosensor data |

---

## Memory Scopes

All memory APIs support these scopes:

| Scope | TTL | Storage | Description |
|-------|-----|---------|-------------|
| `conversation` | 1 hour | Redis | Dialog context |
| `user` | Permanent | PostgreSQL + Qdrant | User preferences |
| `agent` | 24 hours | Redis | Agent working memory |
| `system` | Permanent | PostgreSQL | Global MAS state |
| `ephemeral` | 1 minute | In-memory | Scratch space |
| `device` | Permanent | PostgreSQL | Device state |
| `experiment` | Permanent | PostgreSQL + Qdrant | Scientific data |
| `workflow` | 7 days | Redis + PostgreSQL | N8N executions |

---

## Authentication

Most endpoints require authentication via:
- API Key header: `X-API-Key: <key>`
- JWT token: `Authorization: Bearer <token>`

---

## Rate Limits

| Tier | Requests/min | Burst |
|------|-------------|-------|
| Default | 100 | 200 |
| Premium | 1000 | 2000 |
| Internal | Unlimited | N/A |

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing/invalid auth |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

---

## Related Documentation

- [System Registry](./SYSTEM_REGISTRY_FEB04_2026.md)
- [Memory Integration Guide](./MEMORY_INTEGRATION_GUIDE_FEB04_2026.md)
- [Cryptographic Integrity](./CRYPTOGRAPHIC_INTEGRITY_FEB04_2026.md)

---

## Physics API Endpoints (Feb 9, 2026)

### MAS Physics Proxy (`/api/physics/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/physics/health` | GET | PhysicsNeMo service health |
| `/api/physics/gpu` | GET | GPU status for physics runtime |
| `/api/physics/models` | GET | List loaded physics models |
| `/api/physics/simulate` | POST | Generic simulation dispatch by type |
| `/api/physics/diffusion` | POST | Diffusion simulation |
| `/api/physics/fluid` | POST | Fluid flow simulation |
| `/api/physics/heat` | POST | Heat transfer simulation |
| `/api/physics/reaction` | POST | Reaction kinetics simulation |

### Local PhysicsNeMo Service (`localhost:8400`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health |
| `/gpu/status` | GET | CUDA/GPU memory status |
| `/physics/models` | GET | List loaded models |
| `/physics/models/load` | POST | Load model metadata entry |
| `/physics/models/unload` | POST | Unload model metadata entry |
| `/physics/diffusion` | POST | Finite-difference diffusion |
| `/physics/heat-transfer` | POST | Heat transfer solver |
| `/physics/fluid-flow` | POST | Viscous flow surrogate |
| `/physics/reaction` | POST | Reaction/diffusion kinetics |
| `/physics/neural-operator` | POST | Neural-operator style transformation |
| `/physics/pinn` | POST | PINN-style equation solve endpoint |
