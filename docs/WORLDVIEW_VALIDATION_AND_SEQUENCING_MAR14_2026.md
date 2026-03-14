# Worldview Rollout — Validation, Documentation, and Implementation Sequencing

**Date:** March 14, 2026  
**Status:** Reference (Phase 8 of Worldview Search Expansion Plan)  
**Related:** `worldview_search_expansion_bcd26107.plan.md` Phase 8

---

## 1. Validation Strategy

### 1.1 ETL Verification

| Check | Command / Action | Pass Criteria |
|-------|------------------|---------------|
| GBIF all-life | Run GBIF ingest with `domain=all_life` | Returns non-fungal taxa |
| GBIF fungi-only | Run GBIF ingest with `domain=fungi` | Returns fungal taxa only |
| iNaturalist all-life | Run iNat ingest with configurable root | Returns non-fungal taxa |
| iNaturalist fungi-only | Run iNat ingest with fungi preset | Returns fungal taxa only |
| MAS reconciliation | Resolve non-fungal species name | Correct kingdom, no Fungi corruption |
| MAS reconciliation | Resolve fungal species | Index Fungorum used when appropriate |

### 1.2 Website Search Verification

| Query | Expected | Pass |
|-------|----------|------|
| `flights over pacific` | CREP widget visible | ✓ |
| `satellite passes` | CREP or map widget visible | ✓ |
| `earth2 climate forecast` | Earth2 widget visible | ✓ |
| `river levels` | No collapse to species-only | ✓ |
| `Amanita muscaria` | Fungal resolution, species widget | ✓ |
| Mobile: same queries | Equivalent worldview handling | ✓ |

### 1.3 Worldstate API Verification

| Endpoint | Check | Pass |
|----------|-------|------|
| `/api/myca/world/summary` | Returns same reality as WorldModel | ✓ |
| `/api/myca/world/region?lat=X&lon=Y` | Summarizes local hazards, entities, env | ✓ |
| `/api/myca/world/sources` | Freshness and failures visible | ✓ |

### 1.4 Grounding Verification

| Check | Pass |
|-------|------|
| WorldModel.update() covers CREP, Earth2, MINDEX, MycoBrain, NLM, EarthLIVE, Presence | ✓ |
| SelfState built once, reused | ✓ |
| ExperiencePacket attachments show source set, freshness, provenance | ✓ |
| No degraded source replaced with fake content | ✓ |

### 1.5 No-Mock-Data Rule

- Empty, degraded, or stale states must be explicit.
- API failures return error states or empty arrays, not fallback mock data.
- Search empty states: "No results" not fake suggestions.

---

## 2. Registry Updates (Worldview-Related)

### 2.1 SYSTEM_REGISTRY_FEB04_2026.md

Add under Recent Updates:

- **Worldstate API** (Mar 14, 2026): MAS `/api/myca/world/*` — canonical passive awareness surface; reads from WorldModel and SelfState.
- **Worldview collectors** (Mar 14, 2026): P0 (EONET, Overpass, OurAirports, OpenSky, USGS quakes, NOAA NWS, Open-Meteo); P1/P2 (NOAA CO-OPS, USGS water, FIRMS).
- **GPU enrichment strategy** (Mar 14, 2026): Earth2, PhysicsNeMo, PersonaPlex input backlogs and worldstate context envelope.

### 2.2 API_CATALOG_FEB04_2026.md

Add Worldstate API section:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/myca/world` | GET | Full worldstate snapshot |
| `/api/myca/world/summary` | GET | Compact summary for context |
| `/api/myca/world/region` | GET | Region-filtered summary (lat, lon, radius) |
| `/api/myca/world/sources` | GET | Source freshness and status |
| `/api/myca/world/diff` | GET | Diff since last turn (when implemented) |

**Router:** `mycosoft_mas/core/routers/worldstate_api.py`

---

## 3. Implementation Sequencing (Follow-On)

Recommended order for remaining worldview work:

| # | Task | Owner | Depends On |
|---|------|-------|------------|
| 1 | PersonaPlex context from `/api/myca/world/summary` | myca-voice | Worldstate API |
| 2 | Earth2 inference seeded from worldstate | earth2-ops | Worldstate API |
| 3 | PhysicsNeMo boundary conditions from WorldState | scientific-systems | Worldstate API |
| 4 | ERA5/GFS/Copernicus adapters for Earth2 | earth2-ops | P2 source backlog |
| 5 | `format_for_voice_context()` helper | voice-engineer | Worldstate summary |
| 6 | llm_brain EP-first grounding path | backend-dev | Phase 4 EP unification |

---

## 4. Documentation Checklist

| Doc | Purpose |
|-----|---------|
| `GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md` | Packet path, WorldModel, llm_brain |
| `GPU_ENRICHMENT_STRATEGY_MAR14_2026.md` | Earth2, PhysicsNeMo, PersonaPlex inputs |
| `WORLDSTATE_VS_SPECIALIST_COMMAND_BOUNDARY_MAR14_2026.md` | Passive vs specialist API boundary |
| `WORLD_VIEW_SEARCH_SUGGESTIONS_PLAN_MAR14_2026.md` | Search suggestions, MINDEX cohesion |
| `WORLDVIEW_VALIDATION_AND_SEQUENCING_MAR14_2026.md` | This document |

---

## 5. Cross-References

- `worldview_search_expansion_bcd26107.plan.md` — Master plan
- `docs/MASTER_DOCUMENT_INDEX.md` — Full doc index
- `.cursor/CURSOR_DOCS_INDEX.md` — Vital docs for agents
