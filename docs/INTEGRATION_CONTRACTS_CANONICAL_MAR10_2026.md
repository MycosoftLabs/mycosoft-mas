# Canonical Integration Contracts

**Date**: March 10, 2026  
**Status**: Phase 0 Complete  
**Related**: Full Integration Master Program (`full-integration-program_76a25880.plan.md`)

---

## Overview

This document defines the **canonical contracts** for cross-system integration across MAS, MINDEX, WEBSITE, and mycobrain. All integration work (OpenPlanter, Shadowbroker, PentAGI, Paperclip, Dekart, EO imagery, agent payments, Jetson/MycoBrain) MUST conform to these contracts. No parallel control planes; MAS/MINDEX/CREP remain the canonical authority.

---

## 1. Unified Entities and Spatial Layers

**Purpose**: Single schema for all CREP, OEI, and intelligence layers so deck.gl, API routes, and MINDEX share one entity model.

**Canonical Source**: `WEBSITE/website/lib/crep/entities/unified-entity-schema.ts`

### Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique identifier (source prefix + source_id) |
| `type` | string | yes | `aircraft` \| `vessel` \| `satellite` \| `fungal` \| `weather` \| `earthquake` \| `elephant` \| `device` |
| `state` | UnifiedEntityState | yes | `position`, `course`, `speed`, `altitude`, etc. |
| `time` | UnifiedEntityTime | yes | `observedAt`, `updatedAt`, `expiresAt` |
| `source` | string | yes | e.g. `flightradar24`, `aisstream`, `celestrak`, `mindex`, `inat` |
| `sourceId` | string | no | Original source ID |
| `label` | string | no | Human-readable label |
| `metadata` | object | no | Type-specific metadata |

**Spatial Layers**:
- All layers consume `UnifiedEntity[]` from `/api/crep/unified` or `/api/oei/*`.
- deck.gl `EntityDeckLayer` renders entities from a single source of truth; no duplicate orbit/layer implementations.

**Reference**: `unified-entity-schema.ts`, `deck-entity-layer.tsx`, `CREPDashboardClient.tsx`, `CREP_INATURALIST_MINDEX_ETL_MAR09_2026.md`.

---

## 2. Investigation Artifacts and Evidence-Backed Analysis

**Purpose**: Standard schema for OpenPlanter-style investigation artifacts, evidence graphs, and research outputs so MAS, MINDEX, and CREP share a common model.

**Canonical Source**: MINDEX `obs.observation`, `research` tables; MAS taxonomy/research agents.

### Contract

| Artifact | Location | Schema |
|----------|----------|--------|
| **Observation** | MINDEX `obs.observation` | `source`, `source_id`, `taxon_id`, `latitude`, `longitude`, `observed_at`, `observer`, `media`, `metadata` |
| **Research artifact** | MINDEX `research` / routers | `id`, `title`, `description`, `artifacts`, `sources`, `created_at`, `agent_id` |
| **Evidence-backed graph** | MINDEX (future) / MAS | `entity_id`, `evidence_ids[]`, `relationship_type`, `confidence`, `created_at` |

**Investigation flow**:
- Heterogeneous dataset intake → entity resolution → evidence graph → recursive MAS tasking.
- Outputs surface in CREP entity inspector, MYCA tools, MINDEX research/observation APIs, operator dashboards.

**Reference**: `MINDEX/mindex_api/routers/observations.py`, `research.py`, `taxonomy_ingestion_agent.py`, `CREP_INATURALIST_MINDEX_ETL_MAR09_2026.md`.

---

## 3. Red-Team Task Approval / Execution / Audit Records

**Purpose**: Durable, auditable schema for red-team simulations so execution and approval are traceable; no in-memory-only state.

**Canonical Source**: `MAS/mycosoft_mas/core/routers/redteam_api.py` (current in-memory; to be persisted).

### Contract

| Field | Type | Description |
|-------|------|-------------|
| `simulation_id` | string | Unique ID |
| `type` | SimulationType | `phishing` \| `credential_stuffing` \| `recon` \| `exfiltration` |
| `status` | SimulationStatus | `pending` \| `approved` \| `running` \| `completed` \| `failed` |
| `requested_by` | string | Agent or user ID |
| `approved_by` | string | Guardian/AVANI or authorized role |
| `approved_at` | ISO8601 | Approval timestamp |
| `result` | SimulationResult | Outcomes, findings, audit trail |
| `created_at` | ISO8601 | Creation time |
| `updated_at` | ISO8601 | Last update |

**Approval Gate**: Guardian/AVANI approval required before `status` transitions to `running`. All transitions logged.

**Persistence Target**: MINDEX or Supabase; replace in-memory `simulations` dict.

**Reference**: `redteam_api.py`, `guardian_api.py`, `security_integration.py`.

---

## 4. Operator / Org-Chart Task Objects (C-Suite Staff)

**Purpose**: Standard task contract for C-suite operators (Atlas, Meridian, Forge, Nexus) so MYCA and MAS orchestrate staff without a parallel control plane.

**Canonical Source**: `docs/CSUITE_OPERATOR_CONTRACT_MAR08_2026.md`, `csuite_api.py`, `executive.py`, `tool_orchestrator.py`.

### Contract

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique task ID |
| `role` | string | `atlas` \| `meridian` \| `forge` \| `nexus` |
| `vm_id` | string | VM host (e.g. 192.168.0.192–195) |
| `type` | string | `heartbeat` \| `report` \| `escalate` \| `task` |
| `payload` | object | Task-specific payload |
| `status` | string | `pending` \| `in_progress` \| `done` \| `escalated` |
| `created_at` | ISO8601 | Creation time |
| `updated_at` | ISO8601 | Last update |

**C-Suite Protocol**:
- `heartbeat`: Operator → MAS; periodic liveness.
- `report`: Operator → MAS; status/completion report.
- `escalate`: Operator → MAS; handoff to human or higher role.

**Persistence Target**: Supabase or MINDEX for operator tasks; MAS orchestrator coordinates only.

**Reference**: `CSUITE_OPERATOR_CONTRACT_MAR08_2026.md`, `csuite_api.py`, `config/csuite_role_manifests.yaml`.

---

## 5. Agent-Payment Meter / Invoice / Settlement Events

**Purpose**: Single contract for metering, crediting, and settlement so x402-style payments integrate with existing economy/wallet stack.

**Canonical Source**: `economy_api.py`, `x401_agent_wallet.py`, `llm_ledger.py`.

### Contract

| Event Type | Fields | Location |
|------------|--------|----------|
| **Meter** | `agent_id`, `resource`, `units`, `timestamp` | LLM Ledger / economy |
| **Invoice** | `invoice_id`, `agent_id`, `line_items[]`, `total`, `status` | Economy API |
| **Settlement** | `settlement_id`, `from_wallet`, `to_wallet`, `amount`, `currency`, `timestamp` | Economy API / x401 |

**Wallet Contract** (from `economy_api`):
- `wallet_id`, `agent_id`, `balance`, `currency`, `pricing_tier`.

**Pricing Tier**: `tier_id`, `name`, `price_per_request`, `price_per_token`, etc.

**Persistence**: Replace in-memory `_economy_state` with MINDEX/Supabase. LLM usage already in Supabase `llm_usage_ledger`.

**Reference**: `economy_api.py`, `x401_agent_wallet.py`, `llm_ledger.py`.

---

## 6. Jetson / MycoBrain Edge Telemetry and Command Flows

**Purpose**: Canonical format for edge device heartbeats, telemetry, and command flows so MAS, MINDEX, Supabase, and CREP consume consistent data.

**Canonical Source**: `services/mycobrain/mycobrain_service_standalone.py`, `capability_manifest.py`, `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md`.

### Heartbeat Payload (Device → MAS)

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | string | Unique device ID |
| `device_name` | string | Display name |
| `device_role` | string | e.g. `mushroom1`, `sporebase`, `standalone` |
| `device_display_name` | string | Optional UI label |
| `host` | string | Service host |
| `port` | int | Service port |
| `firmware_version` | string | From device info |
| `board_type` | string | e.g. ESP32-S3 |
| `sensors` | string[] | From capability manifest |
| `capabilities` | string[] | From capability manifest |
| `location` | string | Optional |
| `connection_type` | string | `serial`, `lora`, `ble`, `wifi` |
| `ingestion_source` | string | `serial` |
| `extra` | object | `protocol`, `port_name`, `service_version` |

**Endpoint**: `POST {MAS_REGISTRY_URL}/api/devices/heartbeat`

### Telemetry Payload (Device → Ingest API)

- Structured MDP v1 telemetry.
- Endpoint: `{TELEMETRY_INGEST_URL}/api/devices/ingest` (or equivalent).
- Persistence: Supabase (per `MYCOBRAIN_SUPABASE_TELEMETRY_ARCHITECTURE_MAR07_2026.md`).

### Command Flow (MAS → Device)

- Commands flow through MAS/AVANI/Guardian where governed.
- MDP command families defined in `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md`.
- Edge devices appear in CREP as `UnifiedEntity` type `device`; Device Manager shows state from MAS registry.

**Reference**: `mycobrain_service_standalone.py`, `capability_manifest.py`, `device_registry_api.py`, `MDP_PROTOCOL_CONTRACTS_MAR07_2026.md`, `MYCOBRAIN_SUPABASE_TELEMETRY_ARCHITECTURE_MAR07_2026.md`.

---

## Normalization Targets (From Plan)

| Area | Current State | Target |
|------|---------------|--------|
| CREP | Mock/planned military layers in CREPDashboardClient | Remove or replace with real OEI connectors |
| EO imagery | Demo-heavy in VizTestClient, viz components | Promote production routes to `/dashboard/crep` |
| Red-team | In-memory `simulations` | Durable MINDEX/Supabase |
| Economy | In-memory `_economy_state` | Durable MINDEX/Supabase |
| Jetson gateway | Contracts not fully aligned with upstream | Align heartbeat, telemetry, command flows per this document |

---

## Next Phase

Phase 1 (Persistence Hardening): Replace in-memory and demo-only persistence with durable MINDEX/Supabase-backed models per these contracts.
