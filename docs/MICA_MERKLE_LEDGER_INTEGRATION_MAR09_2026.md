# MICA/MYCA Merkleized Cognition Ledger Integration — Mar 9, 2026

**Status:** Complete (Phase 1)  
**Related:** `merkle/mica_merkle_spec/`, `mycosoft_mas/merkle/`, Full Integration Program

## Summary

The **Merkleized Cognition Ledger** from `merkle/` is integrated into MAS as a Merkle DAG/forest. Event leaves are content-addressed; temporal, spatial, self, world, and thought roots are computed per tick. BLAKE3-256 over deterministic CBOR is used for hashing.

## What Was Delivered

### 1. Package and Dependencies

- **`mycosoft_mas.merkle`** — `root_builder.py` with `EventRootBuilder`, `SnapshotRootBuilder`, `ThoughtRootBuilder`
- **Dependencies** — `blake3`, `cbor2` in `pyproject.toml`

### 2. Root Types

| Root | Description |
|------|-------------|
| `TemporalRoot(t)` | Merkle root of event leaves for tick `t` |
| `SpatialBucketRoot(c,t)` | Merkle root of leaves in space cell `c` at tick `t` |
| `SpatialRoot(t)` | Merkle root of spatial bucket roots for tick `t` |
| `EventRoot(t)` | `H(temporal \|\| spatial)` for tick `t` |
| `SelfRoot(t)` | Merkle root of MYCA self-state (agents, tasks, memory, tools, etc.) |
| `WorldRoot(t)` | Merkle root of external world model (CREP, NLM, Earth2, devices, etc.) |
| **`ThoughtPlanRoot(t)`** | Super-root: `H(tick \|\| self_root \|\| world_root \|\| event_root \|\| prev \|\| policy)` |

### 3. MAS FastAPI Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/merkle/health` | GET | Merkle ledger health |
| `/api/merkle/event/hash` | POST | Compute event leaf hash from canonical CBOR |
| `/api/merkle/roots/temporal` | POST | Build temporal root from ordered event hashes |
| `/api/merkle/roots/thought` | POST | Build thought root (self, world, event, prev, policy) |
| `/api/merkle/proof/inclusion` | POST | Build Merkle inclusion proof |

### 4. MINDEX Migration

- **`migrations/0021_mica_merkle_ledger.sql`** — Schema `mica`:
  - `ca_object`, `event_object`, `root_record`, `root_member`
  - `self_snapshot`, `world_snapshot`, `claim_object`, `thought_context`
  - `action_receipt`, `watermark_state`, `mutable_head`

### 5. Spec Bundle

- **`merkle/mica_merkle_spec/`** — README, proto, CDDL, SQL reference

## Verification

```bash
# Health check
curl http://192.168.0.188:8001/api/merkle/health

# Event hash
curl -X POST http://192.168.0.188:8001/api/merkle/event/hash \
  -H "Content-Type: application/json" \
  -d '{"event_id":"ev-1","device_id":"dev-1","ts_event_ns":1000,"source":"sensor",...}'

# Thought root
curl -X POST http://192.168.0.188:8001/api/merkle/roots/thought \
  -H "Content-Type: application/json" \
  -d '{"tick_id":1000,"thought_time_ns":1000000,"actor_id":"myca",...}'
```

## Consciousness Integration (Next Step)

Per spec, **every reasoning step** should take `ThoughtPlanRoot(t)` before tool calls, plans, or speech. Recommended flow:

1. Before orchestrator/consciousness reasoning: call `POST /api/merkle/roots/thought` with current self/world/event roots (or placeholders).
2. Attach returned `thought_plan_root` to the reasoning context.
3. Chain lineage: `ThoughtPlanRoot → IntentRoot → PlanRoot → ActionRoot → ReceiptRoot`.

Orchestrator/consciousness code should be updated to call this API at the start of each reasoning cycle. The API is ready; the call site integration is future work.

## Architecture Fit

- **MAS** = live plane (orchestrator, agents, tool execution)
- **MINDEX** = historical truth plane (ledger tables, content-addressed objects)
- **Mycorrhizae/MMP** = normalized event transport → canonical event leaf
- **Ingestion:** Device/ETL/FCI/CREP/Earth2 → MMP envelope → event leaf → hash → tick roots → MINDEX ledger + MAS live state

## Files Touched

| Path | Change |
|------|--------|
| `mycosoft_mas/merkle/__init__.py` | Package exports |
| `mycosoft_mas/merkle/root_builder.py` | Event, snapshot, thought builders |
| `mycosoft_mas/core/routers/merkle_ledger_api.py` | FastAPI router |
| `mycosoft_mas/core/myca_main.py` | Router include |
| `pyproject.toml` | blake3, cbor2 |
| `MINDEX/mindex/migrations/0021_mica_merkle_ledger.sql` | MINDEX schema |
| `merkle/mica_merkle_spec/` | Spec bundle (reference) |

## Apply MINDEX Migration

On MINDEX Postgres (VM 189):

```bash
psql -h 192.168.0.189 -U mindex -d mindex -f mindex/migrations/0021_mica_merkle_ledger.sql
```

Or via your migration runner if applicable.
