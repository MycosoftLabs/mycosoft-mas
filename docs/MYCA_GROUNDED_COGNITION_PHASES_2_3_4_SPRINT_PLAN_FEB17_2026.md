# MYCA Grounded Cognition — Phases 2–4 Sprint Plan (Overnight to Morning)

**Date**: February 17, 2026  
**Status**: Active — Execute by morning  
**Scope**: Phases 2, 3, 4 + all unfinished items from `myca_grounded_cognition_integration_e350acb6.plan.md`  
**Goal**: Speech → chat → search → cognition pipeline working when superuser first talks to MYCA

---

## Executive Summary

This plan completes the Grounded Cognition stack (Phases 2–4) and all integration gaps in a single overnight sprint. Timeline is expressed in **hours**, not days/weeks/months. Each task has a minimal viable implementation (MVI) that ships.

---

## Part 1: Integration State and Gaps

### 1.1 What Exists (Last 7 Days)

| Component | Status | Location |
|-----------|--------|----------|
| Experience Packets, GroundingGate, ThoughtObjects | ✅ | `schemas/`, `grounding_gate.py`, `deliberation.py` |
| Error sanitization, LLM fallback | ✅ | `error_sanitizer.py`, `frontier_router.py`, `brain_api.py` |
| Grounding API, Error Triage API | ✅ | `grounding_api.py`, `error_triage_api.py` |
| GroundingStatusBadge, MYCALiveActivityPanel | ✅ | Website components |
| MYCAContext grounding state | ✅ | `contexts/myca-context.tsx` |
| Website proxy routes | ✅ | `/api/myca/grounding/*`, `/api/myca/thoughts` |
| SpatialService, TemporalService | ✅ **Stubs only** | `engines/spatial/`, `engines/temporal/` |
| NLM V0 (embodiment encoders, embeddings API) | ✅ | `nlm/`, `nlm_api.py` |
| First Light rituals, sensor fusion | ✅ | `first_light_rituals.py`, `sensor_fusion.py` |

### 1.2 What Is Missing or Unfinished

| Item | Plan Reference | Severity |
|------|----------------|----------|
| **Phase 2**: PostGIS/TimescaleDB integration | SpatialService, TemporalService stubs | HIGH |
| **Phase 3**: NLM full integration, Brain Cortex, Left/Right brain | Upgrade Plan Phase 3 | HIGH |
| **Phase 4**: IntentionService, FingerOrchestrator, ReflectionService | Upgrade Plan Phase 4 | HIGH |
| MYCA_GROUNDED_COGNITION=1 on MAS VM | Manual step | P0 — **blocking superuser** |
| WorldModel cache warming on startup | Gap analysis "cold start" | P0 |
| Grounding validation before streaming | Plan gap | P0 — **already implemented** (runs in `process_input`) |
| ThoughtObjectsPanel, ExperiencePacketView | Plan UI gaps | P2 |
| Grounding toggle in settings | Plan UI | P1 |
| PostGIS/TimescaleDB migrations | MINDEX VM | Phase 2 dependency |
| EP/ThoughtObject storage tables | MINDEX | Phase 2 dependency |

### 1.3 Speech → Chat → Search → Cognition Pipeline

```
User speaks → PersonaPlex STT → Website /api/mas/voice/orchestrator
    → MAS /api/myca/chat (or /chat/stream)
    → consciousness.process_input()
        → [if GROUNDED] GroundingGate (build EP → attach SelfState → attach WorldState → validate)
        → Attention → Working Memory → Intuition/Deliberation → LLM → stream tokens
    → Response back to user
```

**Current blocker for superuser first conversation**:
1. `MYCA_GROUNDED_COGNITION=0` → grounding bypassed; chat works but no EP/ThoughtObject enforcement
2. If enabled: cold WorldModel → `attach_world_state()` returns minimal; validation may fail or time out
3. No WorldModel cache warming → first request gets empty/stale WorldState

---

## Part 2: Phase 2 — Spatial + Temporal Engines (MVI by Morning)

### 2.1 SpatialService MVI (2–3 hours)

**Goal**: Replace stub with PostGIS-backed indexing. MINDEX VM has Postgres; add PostGIS extension.

| Task | Hour | Action |
|------|------|--------|
| MINDEX migration | 0–1 | Create `migrations/0016_postgis_spatial.sql`: `CREATE EXTENSION IF NOT EXISTS postgis;` + `spatial_points` table (id, session_id, lat, lon, h3_cell, ep_id, created_at) |
| SpatialService impl | 1–2 | `engines/spatial/service.py`: add `store_point()`, `query_nearby()` using raw SQL/SQLAlchemy; keep `index_point()` for H3 |
| Wire to GroundingGate | 2–2.5 | `grounding_gate.py`: if `context.get("geo")`, call `SpatialService.store_point()`; optional, non-blocking |
| Test | 2.5–3 | Unit test: store point, query; integration: EP with geo → spatial record |

**Fallback**: If PostGIS install fails on MINDEX VM, keep stub; add `store_point`/`query_nearby` as no-op. Pipeline continues.

### 2.2 TemporalService MVI (2–3 hours)

**Goal**: Replace stub with TimescaleDB-backed episode storage. If TimescaleDB not available, use plain Postgres hypertable-style table.

| Task | Hour | Action |
|------|------|--------|
| MINDEX migration | 0–1 | Create `migrations/0017_temporal_episodes.sql`: `episodes` table (id, session_id, start_ts, end_ts, ep_ids jsonb, created_at). Optionally `CREATE EXTENSION IF NOT EXISTS timescaledb` if supported |
| TemporalService impl | 1–2 | `engines/temporal/service.py`: add `store_episode()`, `get_recent_episodes()`, `should_start_episode()` using existing rule-based logic + DB persistence |
| Wire to pipeline | 2–2.5 | `grounding_gate.py` or `core.py`: call `TemporalService.should_start_episode()`; if new episode, generate ID and store |
| Test | 2.5–3 | Unit test: episode boundary detection; integration: multi-turn session → episodes stored |

**Fallback**: Use plain PostgreSQL; skip TimescaleDB extension. Same schema works.

### 2.3 VM Modifications (Phase 2)

| VM | Change |
|----|--------|
| **MINDEX (189)** | Run migrations 0016, 0017. Ensure PostGIS extension available (`apt install postgresql-14-postgis-3` or equivalent on container/host) |
| **MAS (188)** | No schema change; SpatialService/TemporalService connect to MINDEX Postgres via `MINDEX_DB_URL` or equivalent |

---

## Part 3: Phase 3 — NLM Full Integration + Brain Cortex (MVI by Morning)

### 3.1 NLM Full Integration (2–3 hours)

**Goal**: Wire NLM predictions into EP.WorldState as "expected next" vs "observed".

| Task | Hour | Action |
|------|------|--------|
| NLM prediction endpoint | 0–1 | Add `POST /api/nlm/predict` to `nlm_api.py`: given current sensor packet, return predicted next-hour readings (use simple heuristic or existing encoder) |
| WorldState enrichment | 1–2 | In `grounding_gate.attach_world_state()`: if NLM client available, call predict; add `world_state.nlm_prediction` / `expected_next` to EP schema (optional field) |
| Wire to deliberation | 2–2.5 | `deliberation.py`: include NLM prediction in prompt context when present |
| Test | 2.5–3 | Integration: EP with world state → NLM prediction attached |

**Fallback**: NLM predict returns empty; EP continues without it. No blocking.

### 3.2 Brain Cortex — Left/Right Split (2–3 hours)

**Goal**: Split DeliberateReasoning output into analytic vs creative paths; simple corpus callosum arbitration.

| Task | Hour | Action |
|------|------|--------|
| Output style flags | 0–1 | Add `output_style: "analytic" | "creative"` to focus or context; default "balanced" |
| Left brain path | 1–1.5 | In `deliberation.py`: when style=analytic, append "Be precise, logical, cite evidence." to system prompt |
| Right brain path | 1.5–2 | When style=creative, append "Be exploratory, analogical, brainstorm freely." |
| Corpus callosum stub | 2–2.5 | Add `arbitrate_thoughts(analytic_thoughts, creative_thoughts) -> merged` — V0: concatenate; V1 later |
| Wire to pipeline | 2.5–3 | Optional: detect query type (e.g. "proof", "verify" → analytic; "imagine", "design" → creative) from content |

**Fallback**: Single path; style defaults to balanced. Behavior unchanged.

### 3.3 Cortex Modules — Stubs Only

| Module | Action | Hours |
|--------|--------|-------|
| Visual Cortex | Stub: route image/satellite refs through `Observation.modality=IMAGE`; no new code | 0.5 |
| Auditory Cortex | Stub: `source="voice"` already maps to `ObservationModality.VOICE` | 0 |
| Somatosensory | Stub: device telemetry in `WorldState` via existing WorldModel | 0 |

---

## Part 4: Phase 4 — IntentionService, FingerOrchestrator, ReflectionService (MVI by Morning)

### 4.1 IntentionService MVI (2–3 hours)

**Goal**: Goal decomposition and plan candidates. Minimal implementation.

| Task | Hour | Action |
|------|------|--------|
| Create module | 0–0.5 | `engines/intention/__init__.py`, `intention_service.py` |
| IntentGraph schema | 0.5–1 | `IntentGraph(goals: List[str], constraints: List[str], plan_candidates: List[Dict])` |
| Decompose | 1–2 | `IntentionService.decompose(user_directive: str) -> IntentGraph`: use LLM or rule-based (keyword extraction) to produce 1–3 goals, 0–2 constraints |
| Plan candidates | 2–2.5 | `plan_candidates`: list of `{steps: [...], confidence: float}` — V0: single candidate with one step = user_directive |
| Wire to deliberation | 2.5–3 | Optional: pass `IntentGraph` into deliberation context when present |

**Fallback**: IntentionService returns minimal graph; deliberation unchanged.

### 4.2 FingerOrchestrator MVI (2–3 hours)

**Goal**: Route to specific frontier models by task type. Wraps existing FrontierLLMRouter.

| Task | Hour | Action |
|------|------|--------|
| Create module | 0–0.5 | `engines/intention/finger_orchestrator.py` |
| Task type detection | 0.5–1 | `classify_task(content: str) -> str`: "code" | "reasoning" | "creative" | "general" |
| Provider mapping | 1–1.5 | code → Claude, reasoning → Claude, creative → Gemini, general → Gemini |
| Route | 1.5–2 | `FingerOrchestrator.route(content, context) -> AsyncGenerator`: call `FrontierLLMRouter` with hint for provider selection |
| Wire | 2–2.5 | Optional: deliberation uses FingerOrchestrator when `INTENTION_ENGINE_ENABLED=1` |

**Fallback**: FingerOrchestrator defaults to existing FrontierLLMRouter; no behavior change.

### 4.3 ReflectionService MVI (2–3 hours)

**Goal**: Post-LLM logging, outcome vs prediction, learning tasks.

| Task | Hour | Action |
|------|------|--------|
| Create module | 0–0.5 | `engines/reflection/__init__.py`, `reflection_service.py` |
| Log response | 0.5–1 | `ReflectionService.log_response(ep_id, response, session_id)`: append to JSONL file or MINDEX table |
| Outcome comparison | 1–1.5 | Stub: `compare_outcome(prediction, actual)` → `{match: bool, notes: str}`; V0: always match |
| Learning tasks | 1.5–2 | `create_learning_task(gap: str)`: insert into `knowledge_gaps` table or file |
| Wire to pipeline | 2–2.5 | In `core.process_input()` after deliberation yields: call `ReflectionService.log_response()` in background (fire-and-forget) |
| API | 2.5–3 | `GET /api/reflection/history` — return recent logs |

**Fallback**: ReflectionService no-op; pipeline continues.

---

## Part 5: Superuser First Conversation — Critical Path

### 5.1 Enable Grounded Cognition (30 min)

| Task | Action |
|------|--------|
| MAS VM .env | Add `MYCA_GROUNDED_COGNITION=1` |
| Restart container | `docker restart myca-orchestrator-new` or equivalent |
| Verify | `GET /api/myca/grounding/status` → `enabled: true` |

### 5.2 WorldModel Cache Warming (1 hour)

| Task | Action |
|------|--------|
| `core.py` awaken() | After `_initialize_components()`, call `await self._world_model.update()` once before accepting requests |
| Timeout | 5s max; if timeout, log and continue |
| Result | First `get_cached_context()` returns non-empty |

### 5.3 Grounding Timeout Tuning (30 min)

| Task | Action |
|------|--------|
| SELF_STATE_TIMEOUT | Keep 500ms; if health/presence slow, consider 1s |
| WORLD_STATE_TIMEOUT | Keep 1s; ensure WorldModel cache warm |
| Fallback | On timeout, use minimal SelfState/WorldState; do NOT fail validation |

### 5.4 Grounding Validation — No Hard Fail

**Current behavior**: If validation fails, `yield "[Grounding incomplete: ...]"` and return.

**Change**: On validation failure, log warning; proceed with minimal EP (allow cognition). Optionally set `ep.uncertainty.missingness["validation_failed"] = True`. This ensures superuser never gets blocked by a transient grounding gap.

---

## Part 6: UI, API, VM Checklist

### 6.1 UI Changes

| Component | Status | Action |
|-----------|--------|--------|
| GroundingStatusBadge | ✅ | Already in MYCAChatWidget |
| ThoughtObjectsPanel | Missing | Create minimal: list thoughts with claim + confidence; 1–2 hours |
| ExperiencePacketView | Missing | Create dev-only debug panel; 1 hour |
| Grounding toggle | Missing | Add to settings page: checkbox `Enable Grounded Cognition`; 30 min |

### 6.2 API/Route Changes

| Endpoint | Status | Action |
|----------|--------|--------|
| GET /api/myca/grounding/status | ✅ | Done |
| GET /api/myca/grounding/ep/{id} | Stub | Implement: return EP from in-memory store or MINDEX; 1 hour |
| GET /api/myca/thoughts | ✅ | Done |
| POST /api/errors/triage | ✅ | Done |
| GET /api/reflection/history | New | Add in ReflectionService router; 30 min |

### 6.3 VM Modifications Summary

| VM | Changes |
|----|---------|
| **MAS (188)** | `MYCA_GROUNDED_COGNITION=1`; redeploy with new code (engines, reflection, intention) |
| **MINDEX (189)** | Migrations 0016 (PostGIS/spatial), 0017 (temporal/episodes); apply via migration runner |
| **Sandbox (187)** | Rebuild website with ThoughtObjectsPanel, grounding toggle; purge Cloudflare |

---

## Part 7: Execution Order (Hour-by-Hour)

| Hour | Phase | Task |
|------|-------|------|
| 0–1 | 2 | MINDEX migrations 0016, 0017 |
| 1–2 | 2 | SpatialService impl, TemporalService impl |
| 2–3 | 2 | Wire spatial/temporal to grounding; test |
| 3–4 | 3 | NLM predict endpoint, WorldState enrichment |
| 4–5 | 3 | Left/Right brain split in deliberation |
| 5–6 | 4 | IntentionService, FingerOrchestrator stubs |
| 6–7 | 4 | ReflectionService, wire to pipeline |
| 7–8 | Critical | WorldModel cache warm, grounding validation soft-fail |
| 8–9 | Critical | Enable MYCA_GROUNDED_COGNITION=1, deploy MAS |
| 9–10 | UI | ThoughtObjectsPanel, grounding toggle |
| 10–11 | Deploy | Rebuild MAS, MINDEX, Website; purge CF; smoke test |

---

## Part 8: Conflicts and Resolutions

| Conflict | Resolution |
|----------|------------|
| NLM V0 (First Light) vs Phase 3 NLM | First Light NLM is seed; Phase 3 adds prediction + WorldState wiring |
| Consciousness v1 vs Grounded | Feature flag; when ON, EP required before LLM |
| Self-Healing vs ReflectionService | Self-Healing = runtime error triage; ReflectionService = post-response learning loop |
| Streaming vs grounding | Grounding runs *before* first token; streaming starts after validation. No conflict. |

---

## Part 9: Files to Create/Modify

### New Files

- `migrations/0016_postgis_spatial.sql`
- `migrations/0017_temporal_episodes.sql`
- `engines/intention/__init__.py`, `intention_service.py`, `finger_orchestrator.py`
- `engines/reflection/__init__.py`, `reflection_service.py`
- `components/myca/ThoughtObjectsPanel.tsx`
- `components/myca/ExperiencePacketView.tsx` (dev)
- Settings: grounding toggle

### Modified Files

- `engines/spatial/service.py` — implement store_point, query_nearby
- `engines/temporal/service.py` — implement store_episode, get_recent_episodes
- `grounding_gate.py` — wire spatial/temporal; soft-fail validation
- `consciousness/core.py` — WorldModel cache warm in awaken()
- `deliberation.py` — Left/Right brain paths; optional IntentionService
- `core/myca_main.py` — register reflection router

---

## Part 10: Verification Checklist (Morning)

- [ ] `GET http://192.168.0.188:8001/api/myca/grounding/status` → `enabled: true`
- [ ] Superuser sends "Hello MYCA" via chat → response without "[Grounding incomplete...]"
- [ ] Superuser sends via voice → same
- [ ] GroundingStatusBadge shows "grounded" or "processing" (not stuck on "ungrounded")
- [ ] ThoughtObjectsPanel shows at least one thought after a response
- [ ] No API key or internal error text in user-facing messages
- [ ] MAS, MINDEX, Sandbox all healthy

---

## Related Documents

- `docs/GROUNDED_COGNITION_V0_FEB17_2026.md`
- `docs/MYCA_GROUNDED_COGNITION_INTEGRATION_COMPLETE_FEB17_2026.md`
- `docs/MYCA_Grounded_Cognition_Upgrade_Plan.docx.md`
- `C:\Users\admin2\.cursor\plans\myca_grounded_cognition_integration_e350acb6.plan.md`
