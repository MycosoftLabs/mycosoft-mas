# Grounding Architecture — Locked Canonical Design

**Date:** March 14, 2026  
**Status:** Locked (implementation reference for Worldview Search Expansion)  
**Related:** `worldview_search_expansion_bcd26107.plan.md` Phase 0

---

## 1. Packet Path (GroundingGate)

Location: `mycosoft_mas/consciousness/grounding_gate.py`

### Flow

1. **`build_experience_packet(content, source, context, session_id, user_id)`**
   - Creates base `ExperiencePacket` with `GroundTruth`, `Observation`, `Uncertainty`, `Provenance`
   - Does NOT attach SelfState or WorldState
   - Caps observation payload at 10K chars
   - Sets `uncertainty.missingness["geo"]` if no geo in context

2. **`attach_self_state(ep)`**
   - Timeout: 500ms
   - Fast path: `STATE_SERVICE_URL/state` (StateService) when set
   - Fallback: gather from health_checker, WorldModel presence, agent_registry, consciousness metrics
   - Produces `SelfState(snapshot_ts, services, agents, active_plans)`

3. **`attach_world_state(ep)`**
   - Timeout: 1s
   - Fast path: `STATE_SERVICE_URL/world` (StateService) when set
   - Fallback: `WorldModel.get_cached_context()` for summary, sources, freshness
   - Optional NLM predict call: `MAS_API_URL/api/nlm/predict/sensors`
   - Produces `WorldStateRef(snapshot_ts, sources, freshness, summary, nlm_prediction)`

4. **`compute_provenance(ep)`**
   - SHA256 hash of canonical JSON (redact_secrets=True) for chain-of-custody

5. **`_store_ep(ep, session_id, user_id)`**
   - POST to `MINDEX_API_URL/api/mindex/grounding/experience-packets`
   - Soft-fail: logs and returns on error

6. **`wire_spatial_and_temporal(ep, context, session_id)`**
   - If geo: `SpatialService.store_point(session_id, lat, lon, ep_id)`
   - If session: `TemporalService.store_episode` when `should_start_episode`

### Validation

- **`validate(ep)`**: Requires `self_state`, `world_state`, `ground_truth.monotonic_ts`

---

## 2. World Refresh Loop (WorldModel)

Location: `mycosoft_mas/consciousness/world_model.py`

### `update()` — Active Throttled Loop

| Source     | Method              | Interval (s) | In update() |
|------------|---------------------|--------------|-------------|
| CREP       | `_update_crep()`    | 30           | Yes         |
| Earth2     | `_update_predictions()` | 300     | Yes         |
| NatureOS   | `_update_ecosystem()`   | 60       | Yes         |
| MycoBrain  | `_update_devices()`     | 10       | Yes         |
| NLM        | `_update_nlm()`         | 60       | Yes         |
| EarthLIVE  | `_update_earthlive()`   | 120      | Yes         |
| Presence   | `_update_presence()`    | 5        | Yes         |
| **MINDEX** | **`_update_mindex()`**  | **60**   | **Yes (added)** |

### `update_all()` — Legacy Full Sweep

- Iterates all `_sensors` (crep, earth2, natureos, mindex, mycobrain, nlm, earthlive, presence)
- Used for one-shot refresh; `update()` is the primary loop

### `get_cached_context()`

- Returns `{timestamp, summary, age_seconds, data: {crep, predictions, ecosystem, devices, nlm, presence}, cached: True}`
- **MINDEX data** is in `_current_state.knowledge_stats` but was not populated by `update()` before the fix; now populated via `_update_mindex()`

---

## 3. llm_brain — Direct Bridge Calls (Bypass ExperiencePacket)

Location: `mycosoft_mas/myca/os/llm_brain.py`

`_build_live_context()` assembles live context **without** consuming `ExperiencePacket`. It directly calls:

| # | Bridge/Service           | Method                       | Bypasses EP? |
|---|--------------------------|------------------------------|--------------|
| 1 | device_registry_api      | `get_device_registry_snapshot()` | Yes       |
| 2 | mindex_bridge            | `recall()`                   | Yes          |
| 3 | mas_bridge               | `recall_memory()`            | Yes          |
| 4 | mindex_bridge            | `query_knowledge_graph()`    | Yes (domain-gated) |
| 5 | crep_bridge              | `get_worldview_summary()`    | Yes          |
| 6 | earth2_bridge            | `get_weather_context()`      | Yes          |
| 7 | mycobrain_bridge         | `get_telemetry_summary()`    | Yes          |
| 8 | natureos_bridge          | `get_context_summary()`      | Yes          |
| 9 | mindex_bridge            | `search_knowledge()`         | Yes (domain-gated) |
|10 | world_model              | `update()`, `get_summary()`, `get_relevant_context()` | Yes |
|11 | presence_bridge          | `get_presence_summary()`     | Yes          |
|12 | nlm_bridge               | `get_summary()`              | Yes          |
|13 | world_root_service       | `build_world_root(slot_data)`| Yes          |

**Conclusion:** `llm_brain` does not read from `ExperiencePacket` or packet storage. It rebuilds context from bridges and world model each turn. Phase 5 of the plan addresses making EP the primary grounding object.

---

## 4. Canonical Read Model Decision

**Chosen:** `WorldState` snapshot plus selected source slots.

- **WorldStateRef** in ExperiencePacket remains summary-based (sources, freshness, summary) for lightweight attachment.
- **Full data** for reasoning comes from `WorldModel.get_cached_context()` / `get_relevant_context()`.
- **Future** `/api/myca/world` will expose the same canonical read model to website, CREP, Earth Simulator, and agents.

---

## 5. Specialist vs Passive API Boundary

| Layer                 | Type       | Examples                                          |
|-----------------------|------------|---------------------------------------------------|
| **Passive awareness** | Read-only  | `/api/myca/world`, `/summary`, `/region`, `/sources`, `/diff` |
| **Specialist commands** | Action   | CREP command contract (flyTo, showLayer, etc.)    |
| **Specialist simulation** | Action | Earth2 simulation endpoints                       |

- CREP command contract stays specialist (see `CREP_COMMAND_CONTRACT_MAR13_2026.md`).
- Earth2 simulation stays specialist.
- Worldstate routes remain **read-only** awareness APIs.

---

## 6. File Reference

| File | Role |
|------|------|
| `schemas/experience_packet.py` | EP, GroundTruth, SelfState, WorldStateRef, Observation, Uncertainty, Provenance |
| `consciousness/grounding_gate.py` | GroundingGate: build, attach, validate, store, wire |
| `consciousness/world_model.py` | WorldModel, WorldState, update loop, get_cached_context |
| `myca/os/llm_brain.py` | LLMBrain, _build_live_context (bridge fan-out) |
| `engines/state_service.py` | /state, /world for GroundingGate fast path |
| `core/routers/grounding_api.py` | /api/myca/grounding/status, /ep/{id}, /ep POST, /thoughts |
