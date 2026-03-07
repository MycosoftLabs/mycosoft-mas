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
| Mycorrhizae | http://192.168.0.188:8002 | 20+ | Protocol API: channels/streams, envelope verification + dedupe, replay ACK publish |
| NatureOS | http://192.168.0.188:5000 | 30+ | Nature Operating System |
| MycoBrain | http://192.168.0.188:8080 | 20+ | IoT Device Management |
| NLM | http://192.168.0.188:8200 | 15+ | Nature Learning Models |

---

## MAS API Endpoints

### Recent Runtime Updates (Mar 6, 2026)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/myca/grounding/ep/{ep_id}` | GET | Grounding EP inspection with placeholder fallback when upstream storage is unavailable |
| `/omnichannel/status` | GET | Omnichannel connector status with normalized env fallback handling |
| `/api/workspace/inbox` | GET | Aggregated workspace inbox alias used by MYCA OS comms polling |

### C-Suite API (`/api/csuite/*`) – Mar 7, 2026

Heartbeat, reporting, and escalation from executive-assistant VMs (CEO, CFO, CTO, COO) on Proxmox 90.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/csuite/heartbeat` | POST | C-Suite VM heartbeat (role, ip, status, assistant_name) |
| `/api/csuite/report` | POST | Task completion, executive summary, operating report |
| `/api/csuite/escalate` | POST | Escalation when Morgan's decision needed |
| `/api/csuite/assistants` | GET | List registered assistants (MYCA/MAS UI) |
| `/api/csuite/health` | GET | C-Suite API health check |

**Router:** `mycosoft_mas/core/routers/csuite_api.py`

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

### Ethics API (`/api/ethics/*`) – Mar 3, 2026

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ethics/evaluate` | POST | Run three-gate ethics pipeline on content |
| `/api/ethics/audit` | POST | Incentive audit; logs to Event Ledger |
| `/api/ethics/audit/{task_id}` | GET | Retrieve audit record |
| `/api/ethics/attention-budget/{channel}` | GET | Attention budget status |
| `/api/ethics/simulate` | POST | Second-order simulation |
| `/api/ethics/constitution` | GET | System Constitution (transparency) |
| `/api/ethics/health` | GET | Ethics engine health |

**Router:** `mycosoft_mas/core/routers/ethics_api.py`

### Ethics Training API (`/api/ethics/training/*`) – Mar 4, 2026

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ethics/training/sandbox` | POST | Create sandbox session |
| `/api/ethics/training/sandbox` | GET | List sessions |
| `/api/ethics/training/sandbox/{id}` | GET | Get session details |
| `/api/ethics/training/sandbox/{id}/chat` | POST | Chat with sandboxed MYCA |
| `/api/ethics/training/sandbox/{id}` | DELETE | Destroy session |
| `/api/ethics/training/scenarios` | GET | List scenarios |
| `/api/ethics/training/scenarios/{id}` | GET | Get scenario details |
| `/api/ethics/training/run` | POST | Run scenario on session |
| `/api/ethics/training/grades/{session_id}` | GET | Get grades for session |
| `/api/ethics/training/report` | POST | Generate aggregate report |
| `/api/ethics/training/observations` | GET | Observer MYCA notes |

**Router:** `mycosoft_mas/core/routers/ethics_training_api.py`

### Ingest API (`/api/ingest/*`) – Mar 7, 2026

External system ingestion into Supabase backbone; used by n8n before sheet sync.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ingest/external` | POST | Trigger Asana/Notion/GitHub ingest into Supabase (query: `sources=asana,notion,github`) |

**Router:** `mycosoft_mas/core/routers/ingest_api.py`

### Spreadsheet Sync API (`/api/spreadsheet/*`) – Mar 7, 2026

Master spreadsheet projection from Supabase; n8n triggers after ingest.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/spreadsheet/status` | GET | Sheet sync status from Supabase |
| `/api/spreadsheet/sync` | POST | Run master spreadsheet sync (Supabase → Google Sheet) |

**Router:** `mycosoft_mas/core/routers/spreadsheet_sync_api.py`

### API Keys (`/api/keys/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/keys/health` | GET | API keys service health |
| `/api/keys` | POST | Create a new API key |
| `/api/keys` | GET | List API keys for a user |
| `/api/keys/{key_id}` | DELETE | Revoke an API key |
| `/api/keys/verify` | POST | Verify API key and return metadata |

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

### n8n Workflows API (`/api/workflows/*`) – Feb 18, 2026

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflows/registry` | GET | Full workflow registry for MYCA |
| `/api/workflows/sync-both` | POST | Sync repo to both local and cloud n8n |
| `/api/workflows/execute` | POST | Execute workflow by name (voice/LLM); body: workflow_name, optional data |
| `/api/workflows/performance` | GET | Per-workflow execution stats (learning feedback) |
| `/api/workflows/list` | GET | List workflows |
| `/api/workflows/health` | GET | n8n health |
| `/api/workflows/stats` | GET | Workflow stats |
| `/api/workflows/{id}` | GET/PUT/DELETE | Get, update, delete workflow |
| `/api/workflows/{id}/activate` | POST | Activate workflow |
| `/api/workflows/{id}/deactivate` | POST | Deactivate workflow |
| `/api/workflows/create` | POST | Create workflow |
| `/api/workflows/sync` | POST | Sync to primary n8n |
| `/api/workflows/export-all` | POST | Export all to repo |

### Presence API (`/api/presence/*`) – Feb 24, 2026

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/presence/online` | GET | List online users (proxies to Website) |
| `/api/presence/sessions` | GET | List active sessions |
| `/api/presence/staff` | GET | List staff/admin presence |
| `/api/presence/stats` | GET | Presence statistics |
| `/api/presence/stream` | GET | SSE real-time presence updates |

**Router**: `mycosoft_mas/core/routers/presence_api.py`  
**Upstream**: Website `http://192.168.0.187:3000/api/presence` (PRESENCE_API_URL)

### WebSocket Streams (`/ws/*`) – Feb 28, 2026

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ws/agents/status` | WS | Live agent state stream |
| `/ws/devices/telemetry` | WS | All device telemetry stream |
| `/ws/memory/updates` | WS | Memory layer update stream |
| `/ws/tasks/progress` | WS | Task execution progress |
| `/ws/voice/stream` | WS | Bidirectional voice audio/text |
| `/ws/earth2/predictions` | WS | Earth2 prediction stream |
| `/ws/scientific/data` | WS | Scientific experiment telemetry |
| `/ws/system/health` | WS | Infrastructure/system health |

### Scientific API (`/api/scientific/*`) – Feb 28, 2026

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scientific/experiments` | GET, POST | List/create experiments (PostgreSQL-backed) |
| `/api/scientific/observations` | GET, POST | List/create observations (PostgreSQL-backed) |
| `/api/scientific/observations/live` | GET | Proxy live observations from NatureOS telemetry |
| `/api/scientific/datasets` | GET, POST | List/create datasets (PostgreSQL-backed) |
| `/api/scientific/datasets/species` | GET | Species/taxonomy query proxy to MINDEX |
| `/api/scientific/equipment/status` | GET | Equipment status from persisted lab equipment table |
| `/api/scientific/equipment` | POST | Register/create lab equipment |
| `/api/scientific/simulations/live` | GET | Live simulation status aggregation (PhysicsNeMo + Earth2) |

### SporeBase API (`/api/sporebase/*`) – Feb 28, 2026

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sporebase/order` | POST | Submit SporeBase order intake (replaces previous 501 response) |

### FCI API (`/api/fci/*`) – Feb 28, 2026

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/fci/hpl/execute` | POST | Execute HPL program (execution-lite parser + optional device dispatch) |

### Evolution API (`/api/evolution/*`) – Feb 10, 2026

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/evolution/run-scan` | POST | Run evolution scan |
| `/api/evolution/ideas/status` | GET | Get ideas status |
| `/api/evolution/discoveries` | GET | Get recent discoveries |
| `/api/evolution/recommendations` | GET | Get recommendations |
| `/api/evolution/evaluate` | POST | Record evaluation |

**Router**: `mycosoft_mas/core/routers/evolution_api.py`

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

### NLQ API (`/api/nlq/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/nlq/health` | GET | NLQ router health |
| `/api/nlq/query` | POST | Natural language query processing for search |

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

### IoT Envelope API (`/api/iot/*`) (FEB09 2026)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/iot/envelope/ingest` | POST | Forward unified envelope into Mycorrhizae |
| `/api/iot/replay/ack` | POST | Proxy replay ACK to Mycorrhizae |

### Network Device Registry API (`/api/devices/*`) (FEB09 2026)

This API provides heartbeat-based registration and management for remote MycoBrain devices connected via Tailscale, Cloudflare Tunnel, or LAN.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/devices/heartbeat` | POST | **Canonical** device heartbeat/registration (called by MycoBrain services) |
| `/api/devices/register` | POST | Legacy alias for `/heartbeat`; both behave identically |
| `/api/devices` | GET | List all network-registered devices (supports `status`, `include_offline` params) |
| `/api/devices/{device_id}` | GET | Get specific device info |
| `/api/devices/{device_id}` | DELETE | Unregister device from registry |
| `/api/devices/{device_id}/fci-summary` | POST | Store FCI summary in device extra (bridge from Mycorrhizae/FCI) |
| `/api/devices/{device_id}/command` | POST | Forward command to remote device via HTTP |
| `/api/devices/{device_id}/telemetry` | GET | Fetch telemetry from remote device |
| `/api/devices/health` | GET | Device registry health check |

**Router**: `mycosoft_mas/core/routers/device_registry_api.py`

**Heartbeat Payload**:
```json
{
  "device_id": "mycobrain-COM3",
  "device_name": "Beto-MycoBrain",
  "host": "100.x.x.x",
  "port": 8003,
  "connection_type": "tailscale",
  "firmware_version": "2.0.0",
  "capabilities": ["led", "buzzer", "sensors"],
  "location": "Remote-Beto"
}
```

### GPU Node API (`/api/gpu-node/*`) (FEB13 2026)

Manages mycosoft-gpu01 compute node (192.168.0.190): status, containers, deploy services. **Requires MAS restart on 188 after deploy.** See `docs/GPU_NODE_INTEGRATION_FEB13_2026.md`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/gpu-node/health` | GET | Router health |
| `/api/gpu-node/status` | GET | Full node status (GPU, containers) |
| `/api/gpu-node/reachable` | GET | SSH connectivity check |
| `/api/gpu-node/gpu` | GET | GPU memory, utilization, temp |
| `/api/gpu-node/containers` | GET | List containers |
| `/api/gpu-node/containers/{name}/logs` | GET | Container logs |
| `/api/gpu-node/containers/{name}/running` | GET | Is container running |
| `/api/gpu-node/deploy/container` | POST | Deploy custom container |
| `/api/gpu-node/deploy/service` | POST | Deploy known service (moshi-voice, earth2-inference, personaplex-bridge) |
| `/api/gpu-node/deploy/personaplex-split` | POST | Deploy split PersonaPlex (bridge on gpu01, inference on remote host) |
| `/api/gpu-node/containers/{name}` | DELETE | Stop and remove container |
| `/api/gpu-node/services` | GET | List known services |
| `/api/gpu-node/services/{name}/health` | GET | Service health |

**Router**: `mycosoft_mas/core/routers/gpu_node.py`

### Workflow API (`/api/workflow/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflow/trigger` | POST | Trigger workflow |
| `/api/workflow/status/{id}` | GET | Get status |

---

## Mycorrhizae API Endpoints (Protocol)

### Health & Info

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/info` | GET | Protocol info + stats |
| `/api/stats` | GET | Protocol stats |

### Channels API (`/api/channels/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/channels` | GET | List channels |
| `/api/channels` | POST | Create channel |
| `/api/channels/{channel}` | GET | Get channel info |
| `/api/channels/{channel}/publish` | POST | Publish message (envelope verification + dedupe path) |

### Streaming API (`/api/stream/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stream/replay/ack` | POST | Publish replay ACK events to device ACK channel |

### API Keys (`/api/keys/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/keys/bootstrap` | POST | One-time mint of first admin key (guarded by bootstrap token; only when zero keys exist) |
| `/api/keys` | GET, POST | List/create keys (admin) |
| `/api/keys/{key_id}` | GET, DELETE | Get/revoke key (admin) |
| `/api/keys/{key_id}/rotate` | POST | Rotate key (admin) |
| `/api/keys/validate` | POST | Validate a key (self-validate) |

---

## MINDEX API Endpoints

### Core APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

### Telemetry API (`/api/telemetry/*`) (FEB09 2026)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/telemetry/envelope` | POST | Ingest envelope and expand into samples (dedupe) |
| `/api/telemetry/samples` | GET | Query unified telemetry samples (includes verified flags) |
| `/api/telemetry/replay/start` | POST | Start replay session |
| `/api/telemetry/replay/{session_id}` | GET, PATCH, DELETE | Get/update/stop replay session |
| `/api/telemetry/health` | POST | Record device health state |
| `/api/telemetry/health/{device_slug}` | GET | Get device health history |
| `/api/telemetry/health/summary` | GET | 24h health summary |

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
| `/api/mindex/telemetry` | GET, POST | MINDEX telemetry proxy + envelope ingest |
| `/api/mindex/telemetry/samples` | GET | MINDEX samples proxy (verified flags) |
| `/api/mindex/research/search` | GET | MINDEX research search proxy |

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

---

## Petri Dish Simulation API Endpoints (Feb 20, 2026)

### MAS Petri Simulation (`/api/simulation/petri/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/simulation/petri/chemical/init` | POST | Initialize chemical fields |
| `/api/simulation/petri/chemical/step` | POST | Step chemical simulation via petridishsim |
| `/api/simulation/petri/metrics` | GET | Aggregate metrics from latest fields |
| `/api/simulation/petri/calibrate` | POST | Submit calibration payload |
| `/api/simulation/petri/session/create` | POST | Create session |
| `/api/simulation/petri/session/{id}` | GET | Get session |
| `/api/simulation/petri/session/{id}/reset` | POST | Reset session |
| `/api/simulation/petri/status` | GET | MAS + petridishsim status |
| `/api/simulation/petri/batch` | POST | Batch run (≤10k iterations) |
| `/api/simulation/petri/batch/scale` | POST | Scale batch (up to 1M iterations) |
| `/api/simulation/petri/batch/scale/{job_id}` | GET | Scale batch job status |
| `/api/simulation/petri/batch/scale/{job_id}/cancel` | POST | Cancel scale batch |
| `/api/simulation/petri/agent/control` | POST | MYCA agent control (monitor, adjust_env, contamination_response, multi_run) |
| `/api/simulation/petri/agent/audit` | GET | Audit trail of agent actions |
