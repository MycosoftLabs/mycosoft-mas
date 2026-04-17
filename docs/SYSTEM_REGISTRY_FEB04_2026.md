# System Registry Documentation
## Created: February 4, 2026

## Overview

The System Registry is a PostgreSQL-backed service that tracks all components of the Mycosoft ecosystem:
- **Systems**: Core platforms (MAS, Website, NatureOS, MINDEX, NLM, MycoBrain)
- **APIs**: All 200+ API endpoints across systems
- **Agents**: AI agents and their capabilities
- **Services**: Background services and workers
- **Devices**: MycoBrain IoT devices
- **Code Files**: Source code index across repositories

## Recent Updates (Apr 17, 2026)

- **MYCA Harness 2026** — Monorepo package `mycosoft_mas.harness` (Nemotron via backend selection + env overrides, PersonaPlex HTTP ASR/TTS, YAML static answers, **MINDEX unified search-in-LLM** for grounded text, turbo-quant placeholder, intention brain SQLite under `data/harness/`, harness MINDEX HTTP client + `record_execution`, NLM interface with lazy imports). **Default:** `GET/POST /api/harness/*` mounted from `myca_main.py` unless `HARNESS_API_DISABLED=1`. Optional `BRAIN_CHAT_USE_HARNESS` routes `POST /voice/brain/chat` through the harness. Docs: `docs/MYCA_MAS_HARNESS_COMPLETE_APR17_2026.md`, `config/harness.env.example`. Tests: `tests/test_harness_smoke.py`, `tests/test_harness_api.py`.

## Recent Updates (Apr 14, 2026)

- **Legion GPU watchdog + dev-PC policy** — Heavy inference (Moshi, PersonaPlex bridge, Earth-2 API) must not run on the developer workstation for routine Cursor/website work; use Legions **241/249**. Watchdog: `scripts/gpu-node/windows/Invoke-LegionGPUWatchdog.ps1`, `Register-LegionGPUWatchdog.ps1`. Doc: `docs/LEGION_GPU_WATCHDOG_AND_NO_LOCAL_GPU_APR14_2026.md`. Rule: `.cursor/rules/dev-machine-no-local-gpu-inference.mdc`.

## Recent Updates (Apr 13, 2026)

- **Cross-system integration topology** — Canonical split Legions (**192.168.0.241** voice, **192.168.0.249** Earth-2) documented; legacy **192.168.0.190** deprecated in runbooks. Doc: `docs/CROSS_SYSTEM_INTEGRATION_TOPOLOGY_RECONCILIATION_APR13_2026.md`. `docs/INTEGRATION_COMPLETION_MATRIX_MAR19_2026.md` updated. LAN health script: `scripts/verify_cross_system_health.ps1`.

## Recent Updates (Mar 19, 2026)

- **OpenViking Edge Memory Integration** — Bidirectional bridge between MAS 6-layer memory and OpenViking context databases on Jetson Orin edge devices:
  - **Agent:** `OpenVikingAgent` (`mycosoft_mas/agents/openviking_agent.py`) — manages device connections, sync, cross-device knowledge sharing, tiered context queries.
  - **Bridge:** `OpenVikingBridge` (`mycosoft_mas/memory/openviking_bridge.py`) — singleton bridge connecting MAS MemoryCoordinator to device OpenViking instances. Maps `viking://` paths to MAS memory layers (episodic, semantic, procedural).
  - **Sync Service:** `OpenVikingSyncService` (`mycosoft_mas/memory/openviking_sync.py`) — periodic (5min default) and event-driven sync. Cross-device knowledge sharing (federated learning). Publishes events to Redis `mas:openviking:sync` / `mas:openviking:events`.
  - **HTTP Client:** `OpenVikingClient` (`mycosoft_mas/edge/openviking_client.py`) — async client for OpenViking server API (port 1933). Supports filesystem ops (ls, tree, read, write, mkdir), search (find, grep), ingestion (add_resource), and session management.
  - **REST API (14 endpoints):** Router `openviking_api.py` at `/api/openviking/*`:
    - `POST /devices/register` — Register device OpenViking instance
    - `DELETE /devices/{device_id}` — Unregister device
    - `GET /devices` — List all registered devices
    - `POST /sync/{device_id}` — Trigger manual sync
    - `POST /sync/all` — Sync all devices
    - `POST /query/{device_id}` — Query device memory (with L0/L1/L2 tier)
    - `POST /push/{device_id}` — Push content to device
    - `GET /health` — Bridge health + device status
    - `GET /sync/status` — Background sync service status
    - `POST /sync/start` — Start periodic sync
    - `POST /sync/stop` — Stop periodic sync
    - `GET /sync/history` — Recent sync cycle history
    - `POST /devices/{device_id}/browse` — Browse device filesystem
    - `POST /devices/{device_id}/read` — Read device content with tier
  - **Layer Mapping:** `viking://memories/sensor-observations/` → episodic, `viking://memories/errors-learned/` → semantic, `viking://skills/` → procedural, `viking://resources/mas-agent-context/` → semantic.
  - **Tests:** `tests/test_openviking_bridge.py` — unit tests for client, bridge, sync, agent, API models + integration tests.
  - **Plan Doc:** `docs/OPENVIKING_INTEGRATION_PLAN_MAR19_2026.md`.

## Recent Updates (Mar 17, 2026)

- **MYCA2 PSILO sandbox** — Separate runtime (`myca2_core` / `myca2_edge` / `myca2_sandbox` / `psilo_overlay`); registry-backed LLM routing; PSILO sessions in MINDEX (`0023_myca2_psilo_registry.sql`); executive packet overlay when `myca2` or `psilo_session_id`; production alias promote/rollback gated. Doc: `docs/MYCA2_PSILO_STACK_COMPLETE_MAR17_2026.md`.

## Recent Updates (Mar 14, 2026)

- **RaaS Worldstate Monetization** — Paid live worldstate access for external agents ($1/min MYCA/AVANI):
  - Product: `live_worldstate_connection` in RaaS service catalog; meter by active minute.
  - Session lifecycle router: `mycosoft_mas/raas/session_lifecycle.py` — prefix `/api/raas/worldstate`.
  - Endpoints: POST /start, POST /heartbeat, POST /stop, GET /balance, GET /usage; all require `X-API-Key`; return 402 when balance exhausted.
  - Website: `/agent`, `/agent/dashboard`, Stripe checkout for prepaid minutes; proxy routes `/api/mas/raas/worldstate/balance`, `/api/mas/raas/worldstate/usage`.
  - Contract doc: `docs/MYCA_AVANI_WORLDSTATE_CONNECTION_CONTRACT_MAR14_2026.md`.

- **Worldview Search Expansion** — Worldstate API, collectors, GPU enrichment:
  - Worldstate API (`/api/myca/world/*`) — canonical passive awareness surface; reads from WorldModel and SelfState. Router: `mycosoft_mas/core/routers/worldstate_api.py`
  - Worldview collectors: P0 (EONET, Overpass, OurAirports, OpenSky, USGS quakes, NOAA NWS, Open-Meteo); P1/P2 (NOAA CO-OPS, USGS water, FIRMS). See `mycosoft_mas/collectors/`
  - GPU enrichment strategy: Earth2, PhysicsNeMo, PersonaPlex input backlogs and worldstate context envelope. Doc: `docs/GPU_ENRICHMENT_STRATEGY_MAR14_2026.md`
  - Grounding architecture locked: `docs/GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md`
  - Validation and sequencing: `docs/WORLDVIEW_VALIDATION_AND_SEQUENCING_MAR14_2026.md`

- **Doable Search Rollout** — MAS-owned unified search pipeline (Mar 14, 2026):
  - MAS: `mycosoft_mas/consciousness/search_orchestrator.py` — canonical fallback chain (MINDEX → memory → specialist → LLM); `search_registration.py` — persist to MINDEX + training sink.
  - MAS API: POST `/api/search/execute` — `mycosoft_mas/core/routers/search_orchestrator_api.py`; NLQ and tool_orchestrator route through orchestrator.
  - MINDEX: `search` schema (query ledger, answer_snippet, qa_pair, worldview_fact); router `mindex_api/routers/search_answers.py` — GET/POST `/api/mindex/search/answers`, POST queries/qa.
  - Website: search/chat routes proxy to MAS; `lib/search/mas-search-proxy.ts`, `lib/search/widget-registry.ts`; FallbackWidget for unmapped result types.
  - Completion: `docs/DOABLE_SEARCH_ROLLOUT_COMPLETE_MAR14_2026.md`; Nemotron routing: `docs/NEMOTRON_ROUTING_AND_PERSISTENCE_MAR14_2026.md`.

## Recent Updates (Feb 28, 2026)

- Added scientific persistence service and models:
  - `mycosoft_mas/scientific/db_models.py`
  - `mycosoft_mas/scientific/__init__.py`
- Added scientific MAS routers:
  - `mycosoft_mas/core/routers/scientific_experiments_api.py`
  - `mycosoft_mas/core/routers/scientific_datasets_api.py`
  - `mycosoft_mas/core/routers/scientific_equipment_api.py`
- Added financial integration services:
  - `mycosoft_mas/integrations/mercury_client.py`
  - `mycosoft_mas/integrations/safe_agreement_client.py`
  - `mycosoft_mas/integrations/cap_table_service.py`
- Added research integration services:
  - `mycosoft_mas/integrations/pubpeer_client.py`
  - `mycosoft_mas/integrations/scholar_client.py`
- Replaced SporeBase order 501 response with order intake logic in `mycosoft_mas/core/routers/sporebase_api.py`.

## Recent Updates (Mar 8, 2026)

- CFO MCP Connector:
  - `mycosoft_mas/finance/discovery.py` — Canonical finance discovery: list_finance_agents, list_finance_services, list_finance_workloads, list_finance_tasks, delegate_finance_task, submit_finance_report, get_finance_status, get_finance_alerts
  - `mycosoft_mas/mcp/cfo_mcp_server.py` — Finance-specialized MCP server (8 tools)
  - `mycosoft_mas/core/routers/cfo_mcp_api.py` — REST API for Meridian: GET/POST /api/cfo-mcp/tools, /tools/call, /health
  - `mycosoft_mas/edge/meridian_adapter.py` — MeridianAdapter for Perplexity desktop on CFO VM (192.168.0.193); connects to CFO MCP, relays reports to csuite
  - C-Suite API upgrades: POST /api/csuite/finance-directive, POST /api/csuite/agent-report, GET /api/csuite/cfo/dashboard, GET /api/csuite/cfo/summary (Redis-backed report history)
  - MYCA federation: task_type finance/financial/cfo routes to run_finance_task in tool_orchestrator; webhook sources csuite and finance
  - Completion doc: `docs/CFO_MCP_CONNECTOR_COMPLETE_MAR08_2026.md`

## Recent Updates (Mar 7, 2026)

- Supabase Operational Backbone:
  - External ingest (Asana, Notion, GitHub) into Supabase `commitments`, `customer_vendors`, `liabilities`, `recruitment_roles`
  - LLM usage ledger persisted to Supabase `llm_usage_ledger` from `mycosoft_mas/llm/router.py`
  - Ingest API: `POST /api/ingest/external` — `mycosoft_mas/core/routers/ingest_api.py`
  - Spreadsheet sync: `GET/POST /api/spreadsheet/status|sync` — `spreadsheet_sync_api.py`
  - n8n workflow `myca-master-spreadsheet-sync` runs Ingest → Sync every 30 min
  - Completion doc: `docs/SUPABASE_OPERATIONAL_BACKBONE_COMPLETE_MAR07_2026.md`

- C-Suite OpenClaw VM Rollout:
  - Four executive-assistant VMs (CEO, CFO, CTO, COO) on Proxmox 90 (192.168.0.90:8006)
  - VM IPs: CEO 192.168.0.192, CFO 192.168.0.193, CTO 192.168.0.194, COO 192.168.0.195
  - `mycosoft_mas/core/routers/csuite_api.py` — heartbeat, report, escalate, list assistants
  - `config/proxmox202_csuite.yaml`, `config/csuite_role_manifests.yaml`, `infra/csuite/` (provision, bootstrap, heartbeat scripts)

## Recent Updates (Mar 6, 2026)

- MYCA OS runtime hardening:
  - `mycosoft_mas/myca/os/gateway.py`
  - `mycosoft_mas/myca/os/channels_health.py`
  - `mycosoft_mas/myca/os/comms_hub.py`
- Added first-class MYCA OS bridges:
  - `mycosoft_mas/myca/os/natureos_bridge.py`
  - `mycosoft_mas/myca/os/presence_bridge.py`
  - `mycosoft_mas/myca/os/nlm_bridge.py`
  - `mycosoft_mas/myca/os/staff_registry.py`
- Promoted new runtime task federation surfaces:
  - `mycosoft_mas/myca/os/tool_orchestrator.py`
  - `mycosoft_mas/integrations/github_client.py`
- Expanded workspace and omnichannel surfaces:
  - `mycosoft_mas/core/routers/workspace_api.py`
  - `mycosoft_mas/core/routers/omnichannel_api.py`

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                       System Registry                            â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”             â”‚
â”‚  â”‚   Systems   â”‚  â”‚    APIs     â”‚  â”‚   Agents    â”‚             â”‚
â”‚  â”‚   (6+)      â”‚  â”‚   (200+)    â”‚  â”‚   (50+)     â”‚             â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜             â”‚
â”‚                                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”             â”‚
â”‚  â”‚  Services   â”‚  â”‚   Devices   â”‚  â”‚ Code Files  â”‚             â”‚
â”‚  â”‚   (20+)     â”‚  â”‚   (8+)      â”‚  â”‚  (1000+)    â”‚             â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜             â”‚
â”‚                                                                  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚
                              â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                      PostgreSQL Database                         â”‚
â”‚  Schema: registry                                                â”‚
â”‚  Tables: systems, apis, agents, services, devices, code_files   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## API Endpoints

### Systems

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/systems` | GET | List all systems |
| `/api/registry/systems/{name}` | GET | Get system by name |
| `/api/registry/systems` | POST | Register/update system |

### APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/apis` | GET | List APIs (filterable) |
| `/api/registry/apis/count` | GET | Get total API count |
| `/api/registry/apis/index` | POST | Trigger API indexing |
| `/api/registry/apis/index/sync` | POST | Synchronous indexing |

### Agents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/agents` | GET | List agents |
| `/api/registry/agents` | POST | Register agent |

### Services

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/services` | GET | List services |
| `/api/registry/services` | POST | Register service |
| `/api/registry/services/{name}/health` | POST | Update health |

### Devices

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/devices` | GET | List devices |
| `/api/registry/devices` | POST | Register device |
| `/api/registry/devices/health` | GET | Health summary |
| `/api/registry/devices/firmware` | GET | Firmware report |
| `/api/registry/devices/initialize` | POST | Init known devices |
| `/api/registry/devices/{id}/status` | POST | Update status |

**IoT signing key note (FEB09 2026):**
- Device Ed25519 public keys are expected to be stored as base64 in a registry-accessible location.
- Current contract key: `publicKeyB64` (32-byte Ed25519 public key, base64) in `telemetry.device.metadata` (MINDEX) and/or `registry.devices.metadata`.

### Network diagnostics and UniFi Site Manager (Mar 25, 2026)

- **MAS surface**: `/api/network/*` — DNS, latency, connectivity, full diagnostics (local UniFi controller via `UNIFI_HOST` / `UNIFI_API_KEY` when set), and **UniFi Site Manager** cloud proxy under `/api/network/unifi-site-manager/*`.
- **Site Manager**: Ubiquiti cloud API at `https://api.ui.com` (override with `UNIFI_SITE_MANAGER_BASE_URL`). Orchestrator env: `UNIFI_SITE_MANAGER_API_KEY` or `UI_COM_API_KEY` (required for cloud routes).
- **Code**: `mycosoft_mas/core/routers/network_api.py`, `mycosoft_mas/integrations/unifi_site_manager_client.py`. See `docs/API_CATALOG_FEB04_2026.md` (Network Diagnostics and UniFi Site Manager section).

### Network Device Registry (Feb 9, 2026)

This new API provides heartbeat-based registration for remote MycoBrain devices.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/devices/heartbeat` | POST | **Canonical** device heartbeat/registration |
| `/api/devices/register` | POST | Legacy alias for `/heartbeat`; both behave identically |
| `/api/devices` | GET | List all network-registered devices |
| `/api/devices/{device_id}` | GET | Get specific device info |
| `/api/devices/{device_id}` | DELETE | Unregister device |
| `/api/devices/{device_id}/fci-summary` | POST | Store FCI summary (Mycorrhizae/FCI bridge) |
| `/api/devices/{device_id}/command` | POST | Forward command to remote device |
| `/api/devices/{device_id}/telemetry` | GET | Fetch telemetry from remote device |
| `/api/devices/health` | GET | Device registry health check |

**Router**: `mycosoft_mas/core/routers/device_registry_api.py`
**Registered in**: `mycosoft_mas/core/myca_main.py`

### Network Device Service

| Service | Host | Port | Description |
|---------|------|------|-------------|
| MycoBrain Remote Service | Remote machines | 8003 | Local device manager with heartbeat |

**Heartbeat System**:
- Devices send heartbeats every 30 seconds (configurable)
- Heartbeats include: device_id, host, port, status, connection_type
- Connection types: `tailscale`, `cloudflare`, `lan`
- Devices auto-detected via Tailscale IP or manual configuration

### n8n Workflows API (Feb 18, 2026)

MYCA has full view and full access to n8n workflows. Source of truth: repo `n8n/workflows/*.json`. Sync-both pushes to local (N8N_LOCAL_URL) and cloud (N8N_URL) so production and local dev stay in sync.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflows/registry` | GET | Full workflow registry for MYCA (id, name, active, category, webhook_base, source_url, count) |
| `/api/workflows/sync-both` | POST | Sync repo workflows to both local and cloud n8n (body: `{"activate_core": true}` optional) |
| `/api/workflows/list` | GET | List workflows |
| `/api/workflows/health` | GET | n8n health |
| `/api/workflows/stats` | GET | Workflow stats |
| `/api/workflows/{id}` | GET/PUT/DELETE | Get, update, delete workflow |
| `/api/workflows/{id}/activate` | POST | Activate workflow |
| `/api/workflows/{id}/deactivate` | POST | Deactivate workflow |
| `/api/workflows/create` | POST | Create workflow |
| `/api/workflows/sync` | POST | Sync to primary n8n |
| `/api/workflows/export-all` | POST | Export all to repo |

### Evolution API (Feb 10, 2026)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/evolution/run-scan` | POST | Run evolution scan |
| `/api/evolution/ideas/status` | GET | Get ideas status |
| `/api/evolution/discoveries` | GET | Get recent discoveries |
| `/api/evolution/recommendations` | GET | Get recommendations |
| `/api/evolution/evaluate` | POST | Record evaluation |

**Router**: `mycosoft_mas/core/routers/evolution_api.py`  
**Registered in**: `mycosoft_mas/core/myca_main.py`

**Router**: `mycosoft_mas/core/routers/n8n_workflows_api.py`  
**Rule**: `.cursor/rules/n8n-management.mdc`  
**Agents**: n8n-workflow, n8n-ops, n8n-workflow-sync

### Ethics API (Mar 3, 2026)

Three-gate ethics pipeline (Truth → Incentive → Horizon), Incentive Auditor, Clarity Brief, Stoic attention budgeting.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ethics/evaluate` | POST | Run three-gate pipeline on content |
| `/api/ethics/audit` | POST | Incentive audit; logs to Event Ledger |
| `/api/ethics/audit/{task_id}` | GET | Retrieve audit record |
| `/api/ethics/attention-budget/{channel}` | GET | Attention budget status |
| `/api/ethics/simulate` | POST | Second-order simulation |
| `/api/ethics/constitution` | GET | System Constitution |
| `/api/ethics/health` | GET | Ethics engine health |

**Router**: `mycosoft_mas/core/routers/ethics_api.py`  
**Agent**: IncentiveAuditorAgent (`mycosoft_mas/agents/incentive_auditor_agent.py`)  
**Doc**: `docs/MYCA_ETHICS_PHILOSOPHY_BASELINE_MAR03_2026.md`

### Ethics Training API (Mar 4, 2026)

Sandbox MYCA instances for ethics training; scenarios; grading; Observer integration.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ethics/training/sandbox` | POST | Create sandbox session |
| `/api/ethics/training/sandbox` | GET | List sessions |
| `/api/ethics/training/sandbox/{id}` | GET/DELETE | Get/destroy session |
| `/api/ethics/training/sandbox/{id}/chat` | POST | Chat with sandboxed MYCA |
| `/api/ethics/training/scenarios` | GET | List scenarios |
| `/api/ethics/training/scenarios/{id}` | GET | Get scenario details |
| `/api/ethics/training/run` | POST | Run scenario on session |
| `/api/ethics/training/grades/{session_id}` | GET | Get grades |
| `/api/ethics/training/report` | POST | Aggregate report |
| `/api/ethics/training/observations` | GET | Observer MYCA notes |

**Router**: `mycosoft_mas/core/routers/ethics_training_api.py`  
**Doc**: `docs/MYCA_ETHICS_TRAINING_SYSTEM_MAR04_2026.md`

### Presence API (Feb 24, 2026)

MYCA live awareness of online users, active sessions, and staff presence. Proxies to Website presence API. Used by consciousness world model and deliberation.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/presence/online` | GET | List online users |
| `/api/presence/sessions` | GET | List active sessions |
| `/api/presence/staff` | GET | List staff/admin presence |
| `/api/presence/stats` | GET | Presence statistics |
| `/api/presence/stream` | GET | SSE real-time presence |

**Router**: `mycosoft_mas/core/routers/presence_api.py`  
**Upstream**: Website `PRESENCE_API_URL` (default http://192.168.0.187:3000/api/presence)  
**Auth**: `x-service-key: PRESENCE_SERVICE_KEY` for service-to-service  
**Doc**: `docs/myca/atomic/MYCA_PRESENCE.md`

### C-Suite API (Mar 7, 2026)

Heartbeat, reporting, and escalation from executive-assistant VMs (CEO, CFO, CTO, COO) back into MAS/MYCA.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/csuite/heartbeat` | POST | C-Suite VM heartbeat (role, ip, status, assistant_name) |
| `/api/csuite/report` | POST | Task completion, executive summary, operating report |
| `/api/csuite/escalate` | POST | Escalation when Morgan's decision needed |
| `/api/csuite/assistants` | GET | List registered assistants (MYCA/MAS UI) |
| `/api/csuite/health` | GET | C-Suite API health check |

**Router**: `mycosoft_mas/core/routers/csuite_api.py`  
**Doc**: `docs/CSUITE_OPENCLAW_VM_ROLLOUT_COMPLETE_MAR07_2026.md`  
**VMs**: CEO 192.168.0.192, CFO .193, CTO .194, COO .195 (Proxmox 90 host at 192.168.0.90:8006)

### Agent Event Bus (Feb 9, 2026)

WebSocket endpoint for agent-to-agent real-time messaging. Bridges to Redis pub/sub channels.

| Endpoint | Transport | Description |
|----------|-----------|-------------|
| `/ws/agent-bus` | WebSocket | Agent Event Bus – persistent connection, session tracking, heartbeats |
| `/a2a/v1/ws` | WebSocket | A2A protocol with streaming responses |

**Feature flags**: `MYCA_AGENT_BUS_ENABLED`, `MYCA_A2A_WS_ENABLED`  
**Redis channels**: `agents:tasks`, `agents:tool_calls`  
**Router**: `mycosoft_mas/realtime/agent_bus.py`, `mycosoft_mas/core/routers/a2a_websocket.py`  
**Docs**: `docs/WEBSOCKET_AGENT_BUS_FEB09_2026.md`, `docs/AGENT_BUS_MIGRATION_GUIDE_FEB09_2026.md`

### MAS WebSocket Streams (Feb 28, 2026)

Live streams for agents, devices, memory, tasks, voice, Earth2, scientific telemetry, and system health.

| Endpoint | Transport | Description |
|----------|-----------|-------------|
| `/ws/agents/status` | WebSocket | Live agent state stream |
| `/ws/devices/telemetry` | WebSocket | All device telemetry stream |
| `/ws/memory/updates` | WebSocket | Memory layer update stream |
| `/ws/tasks/progress` | WebSocket | Task execution progress |
| `/ws/voice/stream` | WebSocket | Bidirectional voice audio/text |
| `/ws/earth2/predictions` | WebSocket | Earth2 prediction stream |
| `/ws/scientific/data` | WebSocket | Scientific experiment telemetry |
| `/ws/system/health` | WebSocket | Infrastructure/system health |

**Redis channels**: `agents:status`, `devices:telemetry`, `memory:updates`, `tasks:progress`, `earth2:predictions`, `experiments:data`, `system:health`  
**Routers**: `mycosoft_mas/core/routers/agent_status_ws.py`, `device_telemetry_ws.py`, `memory_updates_ws.py`, `task_progress_ws.py`, `voice_stream_ws.py`, `earth2_predictions_ws.py`, `scientific_data_ws.py`, `system_health_ws.py`

### Petri Dish Simulation API (Feb 20, 2026)

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
| `/api/simulation/petri/agent/control` | POST | MYCA agent control |
| `/api/simulation/petri/agent/audit` | GET | Audit trail |

**Router**: `mycosoft_mas/core/routers/petri_sim_api.py`  
**Services**: `petri_persistence`, `petri_batch_engine`  
**Voice commands**: petri.monitor, petri.adjust_env, petri.contamination_response, petri.multi_run  
**Registered in**: `mycosoft_mas/core/myca_main.py`

### Code Files

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/code/stats` | GET | Code statistics |
| `/api/registry/code/index` | POST | Trigger indexing |
| `/api/registry/code/index/sync` | POST | Synchronous indexing |

### Statistics & Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/registry/stats` | GET | Overall stats |
| `/api/registry/health` | GET | Health check |

## Data Models

### SystemInfo

```python
class SystemInfo(BaseModel):
    id: UUID
    name: str                    # e.g., "MAS", "Website"
    type: SystemType             # mas, website, natureos, mindex, nlm, mycobrain
    url: str                     # e.g., "http://192.168.0.188:8001"
    description: str
    status: str                  # active, inactive, maintenance
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

### APIInfo

```python
class APIInfo(BaseModel):
    id: UUID
    system_id: UUID
    path: str                    # e.g., "/api/memory/write"
    method: str                  # GET, POST, PUT, DELETE
    description: str
    tags: List[str]
    request_schema: Dict
    response_schema: Dict
    auth_required: bool
    deprecated: bool
    metadata: Dict[str, Any]
```

### DeviceInfo

```python
class DeviceInfo(BaseModel):
    id: UUID
    device_id: str               # e.g., "sporebase-001"
    name: str                    # e.g., "SporeBase Alpha"
    type: DeviceType             # sporebase, mushroom1, nfc, sensor, gateway
    firmware_version: str
    hardware_version: str
    status: str
    last_seen: datetime
    config: Dict
    telemetry: Dict
    metadata: Dict
```

## Usage Examples

### Python

```python
from mycosoft_mas.registry.system_registry import get_registry

async def example():
    registry = get_registry()
    
    # List all systems
    systems = await registry.list_systems()
    
    # Get specific system
    mas = await registry.get_system("MAS")
    
    # List APIs for a system
    apis = await registry.list_apis(system_name="MAS")
    
    # Get registry statistics
    stats = await registry.get_registry_stats()
    print(f"Total APIs: {stats['apis']}")
    print(f"Total Devices: {stats['devices']}")
```

### HTTP

```bash
# List all systems
curl http://192.168.0.189:8000/api/registry/systems

# Get API count
curl http://192.168.0.189:8000/api/registry/apis/count

# Update device status
curl -X POST "http://192.168.0.189:8000/api/registry/devices/sporebase-001/status?status=online"
```

## Database Schema

```sql
-- Systems table
CREATE TABLE registry.systems (
    id UUID PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    description TEXT,
    type VARCHAR(50),
    url VARCHAR(512),
    status VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- APIs table
CREATE TABLE registry.apis (
    id UUID PRIMARY KEY,
    system_id UUID REFERENCES registry.systems(id),
    path VARCHAR(512),
    method VARCHAR(10),
    description TEXT,
    tags VARCHAR(255)[],
    auth_required BOOLEAN,
    deprecated BOOLEAN,
    UNIQUE(system_id, path, method)
);

-- Devices table
CREATE TABLE registry.devices (
    id UUID PRIMARY KEY,
    device_id VARCHAR(100) UNIQUE,
    name VARCHAR(100),
    type VARCHAR(50),
    firmware_version VARCHAR(50),
    status VARCHAR(50),
    last_seen TIMESTAMPTZ
);
```

## Indexing

### API Indexing

The API Indexer automatically discovers endpoints from:
1. **OpenAPI specifications** (`/openapi.json`)
2. **Swagger specifications** (`/swagger/v1/swagger.json`)
3. **Known routes** (fallback for systems without OpenAPI)

```python
from mycosoft_mas.registry.api_indexer import index_all_apis

result = await index_all_apis()
# Returns: {"total_apis": 234, "systems": {...}}
```

### Code Indexing

The Code Indexer scans all repositories:
- `mas`: Python files
- `website`: TypeScript/TSX files
- `natureos`: C# files
- `mycobrain`: C++/Arduino files

```python
from mycosoft_mas.registry.code_indexer import index_all_code

result = await index_all_code()
# Returns: {"total_files": 1500, "total_lines": 250000}
```

## Integration with Knowledge Graph

The registry data is automatically synced to the Knowledge Graph:

```
System (MAS) â”€â”€containsâ”€â”€> API (/api/memory/write)
System (MAS) â”€â”€containsâ”€â”€> Agent (MYCA)
System (MycoBrain) â”€â”€managesâ”€â”€> Device (SporeBase)
```

## Files

| File | Purpose |
|------|---------|
| `mycosoft_mas/registry/system_registry.py` | Core registry service |
| `mycosoft_mas/registry/api_indexer.py` | API discovery |
| `mycosoft_mas/registry/code_indexer.py` | Code file indexing |
| `mycosoft_mas/registry/device_registry.py` | Device management |
| `mycosoft_mas/core/routers/registry_api.py` | REST API endpoints |
| `migrations/015_system_registry.sql` | Database schema |

## Related Documentation

- [API Catalog](./API_CATALOG_FEB04_2026.md)
- [Memory Integration Guide](./MEMORY_INTEGRATION_GUIDE_FEB04_2026.md)
- [Cryptographic Integrity](./CRYPTOGRAPHIC_INTEGRITY_FEB04_2026.md)

---

## Manager Agent (Feb 28, 2026)

### Registered Agent

| Agent ID | Class | Category | Capabilities |
|----------|-------|----------|--------------|
| `manager-agent` | `ManagerAgent` | core | `routing`, `intent_classification`, `agent_selection` |

### Module

| File | Purpose |
|------|---------|
| `mycosoft_mas/agents/manager_agent.py` | Task routing, intent classification, and agent selection |

---

## Guardian Agent (Feb 28, 2026)

### Registered Agent

| Agent ID | Class | Category | Capabilities |
|----------|-------|----------|--------------|
| `guardian-agent` | `GuardianAgent` | security | `safety_classification`, `pii_filter`, `tool_risk_gating` |

### Module

| File | Purpose |
|------|---------|
| `mycosoft_mas/agents/guardian_agent.py` | Safety classification, PII filtering, tool risk gating |

---

## PhysicsNeMo Integration (Feb 9, 2026)

### Registered Service

| Service | Host | Port | Type | Notes |
|---------|------|------|------|-------|
| PhysicsNeMo Local Service | Dev Machine | 8400 | GPU physics inference | On-demand container: `nvcr.io/nvidia/physicsnemo/physicsnemo:25.06` |

### Registered Agent

| Agent ID | Class | Category | Capabilities |
|----------|-------|----------|--------------|
| `physicsnemo-agent` | `PhysicsNeMoAgent` | scientific | `physics_simulation`, `neural_operator`, `pinn_solver`, `cfd_surrogate`, `gpu_status` |

### Router

| Router File | Prefix | Purpose |
|-------------|--------|---------|
| `mycosoft_mas/core/routers/physicsnemo_api.py` | `/api/physics` | MAS proxy for PhysicsNeMo simulation endpoints |

---

## Liquid AI Fungal Integration (Mar 9, 2026)

Liquid AI-inspired adaptive temporal processing for FCI biosignals, fungal memory bridging, and recursive self-improvement with benchmark tracking.

### New Components

| Component | File | Purpose |
|-----------|------|---------|
| `LiquidTemporalProcessor` | `mycosoft_mas/engines/liquid_temporal/processor.py` | Adaptive time-constant biosignal processing (LTC-inspired) |
| `FungalMemoryBridge` | `mycosoft_mas/memory/fungal_memory_bridge.py` | Memristive state tracking, biological bookmarks, pattern consolidation |
| `RecursiveSelfImprovementEngine` | `mycosoft_mas/engines/recursive_improvement/engine.py` | Observe → Hypothesize → Test → Integrate → Verify cycle |
| `LiquidFungalIntegrationAgent` | `mycosoft_mas/agents/v2/liquid_fungal_agent.py` | Orchestrating v2 agent |

### Registered Agent

| Agent ID | Class | Category | Capabilities |
|----------|-------|----------|--------------|
| `liquid-fungal-integration` | `LiquidFungalIntegrationAgent` | scientific | `process_biosignal`, `bridge_memory`, `run_improvement_cycle`, `benchmark`, `get_adaptation_status` |

### Router

| Router File | Prefix | Purpose |
|-------------|--------|---------|
| `mycosoft_mas/core/routers/liquid_fungal_api.py` | `/api/liquid-fungal` | Liquid fungal integration endpoints |
