# Worldstate Contract — Canonical Design

**Date:** March 14, 2026  
**Status:** Canonical (Worldview Search Expansion Phase 4)  
**Related:** `worldview_search_expansion_bcd26107.plan.md`, `GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md`

---

## 1. Ownership and Boundaries

| Object | Owner | Location | Purpose |
|--------|-------|----------|---------|
| **WorldState** | WorldModel | `consciousness/world_model.py` | Canonical snapshot of external reality (CREP, Earth2, MINDEX, MycoBrain, etc.) |
| **SelfState** | SelfStateBuilder / StateService | `engines/self_state_builder.py`, `engines/state_service.py` | Canonical snapshot of MYCA's internal operating condition |
| **WorldStateRef** | GroundingGate (attached to EP) | `schemas/experience_packet.py` | Lightweight reference to world snapshot for packet attachment |
| **ExperiencePacket** | GroundingGate | `schemas/experience_packet.py`, `consciousness/grounding_gate.py` | Irreducible unit of grounded cognition; carries WorldStateRef + SelfState |

### Ownership Rules

- **WorldModel** is the single writer of `WorldState`; all sensors feed into it.
- **SelfStateBuilder** (or StateService when deployed) is the single writer of `SelfState`.
- **GroundingGate** attaches `WorldStateRef` and `SelfState` to `ExperiencePacket`; it does not own the underlying data.
- **ExperiencePacket** is immutable after attachment; retrieval is read-only.

---

## 2. Per-Source Metadata (WorldState)

Each source in WorldState shall expose:

| Field | Type | Description |
|-------|------|-------------|
| `data` | `Dict[str, Any]` | Payload from the source |
| `freshness` | `DataFreshness` | `STALE`, `FRESH`, `UNAVAILABLE`, `UNKNOWN` |
| `staleness_reason` | `Optional[str]` | Human-readable reason when stale (e.g. "CREP timeout", "MINDEX unreachable") |
| `provenance_root` | `Optional[str]` | Upstream service or sensor ID |
| `degraded` | `bool` | True when data is partial or fallback |

### DataFreshness Enum (existing)

Defined in `world_model` or shared schema: `STALE`, `FRESH`, `UNAVAILABLE`, `UNKNOWN`.

---

## 3. World Vocabulary (Typed Entity Shapes)

Normalized entity types for shared world model:

| Type | Description | Example Sources |
|------|-------------|-----------------|
| **moving_entity** | Flights, vessels, vehicles, satellites | CREP, OpenSky, AIS |
| **hazard_event** | Fires, storms, quakes, floods | EONET, USGS, NOAA |
| **environmental_field** | Weather, air quality, tides, streamflow | Earth2, Open-Meteo, CO-OPS |
| **infrastructure_asset** | Ports, dams, airports, power plants | OSM, OurAirports, OpenStreetMap |
| **observation** | Biodiversity sightings, sensor readings | MINDEX, iNaturalist, MycoBrain |

Future sources should map their outputs into these shapes for consistent querying.

---

## 4. Data Type Semantics

| Semantic | Meaning | Example |
|----------|---------|---------|
| **sensed** | Live or recent sensor/API data | CREP flight count, MycoBrain VOC |
| **predicted** | Model output (e.g. Earth2, NLM) | Weather forecast, hazard prediction |
| **inferred** | Derived from other data | Species range from occurrence density |
| **recalled** | Historical or episodic | Past decisions, stored observations |

Packets and API responses should tag slots with these semantics when known.

---

## 5. WorldStateRef Structure (Packet Attachment)

`WorldStateRef` remains summary-based for lightweight packet attachment:

```python
@dataclass
class WorldStateRef:
    snapshot_ts: str
    sources: List[str]
    freshness: str
    summary: Optional[str]
    nlm_prediction: Optional[Dict[str, Any]]
    # Optional: per-source metadata for inspection
    source_metadata: Optional[Dict[str, Dict[str, Any]]] = None
```

`source_metadata` maps source name → `{freshness, staleness_reason, degraded}` for inspection without full payload.

---

## 6. Specialist vs Passive API Boundary

| Layer | Type | Examples |
|-------|------|----------|
| **Passive awareness** | Read-only | `/api/myca/world`, `/summary`, `/region`, `/sources`, `/diff` |
| **Specialist commands** | Action | CREP command contract (flyTo, showLayer, etc.) |
| **Specialist simulation** | Action | Earth2 simulation endpoints |

Worldstate routes are **read-only**. Command and simulation APIs remain specialist.

---

## 7. File Reference

| File | Role |
|------|------|
| `schemas/experience_packet.py` | SelfState, WorldStateRef, ExperiencePacket definitions |
| `consciousness/world_model.py` | WorldModel, WorldState, update loop |
| `consciousness/grounding_gate.py` | attach_self_state, attach_world_state |
| `engines/self_state_builder.py` | Canonical SelfState builder |
| `engines/state_service.py` | /state, /world for GroundingGate fast path |
| `core/routers/grounding_api.py` | EP inspection, packet query surfaces |
