# Doable Search and Answer Pipeline — Master Plan

**Date**: March 14, 2026  
**Status**: Plan  
**Related**: WORLD_VIEW_SEARCH_SUGGESTIONS_PLAN_MAR14_2026, Nemotron MYCA Rollout plan, GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026, WORLDSTATE_CONTRACT_MAR14_2026

## Principle: Every Search Must Be Doable

Every query (human, agent, robot, or machine) must be answerable by at least one available method. No search may dead-end. Results must be pulled into MINDEX, stored, categorized, normalized, and formatted so a second search returns instantly with data, widgets, and clickable widget actions. Missing widget types must be registered, implemented, and deployed. Every question must train the system (LLM, NLM, memory) and be registered for ETL and reuse so later users get instant answers.

---

## 1. Search Context (Full MYCA)

Every search must use the full MYCA context:

| Source | Role |
|--------|------|
| **MYCA brain** | Intention, reasoning, tool use |
| **Memory** | 6-layer (ephemeral → session → working → semantic → episodic → system) |
| **Intention** | User/agent intent, task context |
| **Finger** | Identity, permissions, session |
| **LLM capabilities** | Frontier models, Nemotron (when merged), local models |
| **MINDEX (localized)** | Species, compounds, genetics, research, CREP, Earth2, telemetry, all ingested data |
| **CREP** | Planes, ships, satellites, weather, live environmental picture |
| **WorldState** | Read-only worldstate envelope (grounding contract) |

**Rule**: Any user/agent search MUST be routed through a unified search-orchestration layer that (1) queries MINDEX, (2) enriches with MYCA brain/memory/intention, (3) calls CREP/Earth2/specialist when needed, (4) calls frontier LLM when the question is LLM-answerable, (5) stores any new answer or discovered data into MINDEX for the next search.

---

## 2. Data Pipeline: Ingest → Store → Answer

### 2.1 Pull into MINDEX

- Every result from any source (CREP, Earth2, LLM, specialist, scrapers) that can answer a user question must be:
  - **Pulled** into the pipeline (no discard of answerable content).
  - **Stored** in MINDEX (PostgreSQL + vector/Qdrant as appropriate).
  - **Categorized** (e.g. species, weather, flight, vessel, research, answer-snippet).
  - **Normalized** (schema, units, timestamps, provenance).
  - **Formatted** for retrieval (embeddings, keywords, filters).

### 2.2 Second Search = Instant Answer

- A second search for the same or similar question must:
  - Hit MINDEX first (and optionally MYCA memory).
  - Return **instant** results: data, answers, widgets.
  - **Widget**: Each result type must have a widget. If none exists, it is **missing** and must be registered and built.

### 2.3 Widget Registry and Missing Widgets

- **Widget registry**: Central list of result types and their widget components (e.g. species → SpeciesWidget, flights → CrepWidget, answer-snippet → AnswerWidget).
- **Missing widget**: When a result type has no widget, the system must (1) register it as missing, (2) create the widget (or stub), (3) deploy so that result type is renderable. "Instantly" where possible (e.g. generic card first, specialized widget in next deploy).

---

## 3. Training and Learning Pipeline

### 3.1 Every Question Trains the System

- **LLM**: Questions and chosen answers can be used for fine-tuning or prompt curation (per governance).
- **NLM**: Nature Learning Model receives question/answer pairs and world-view context for continual learning.
- **Memory**: Every question/answer pair is stored in semantic/episodic memory so MYCA and future users benefit.
- **MINDEX ETL**: Every question that triggers an ETL fetch (e.g. new species, new CREP slice) must be registered so the same question later is served from MINDEX without re-fetch.

### 3.2 Registration for Reuse

- First time a question is asked: run full pipeline (MINDEX + CREP + LLM + specialists), store results in MINDEX, store question in memory/ETL registry.
- Next time the same (or similar) question is asked: answer from MINDEX + memory first; only call live APIs/LLM if data is stale or missing.

---

## 4. Frontier LLM and Worldview

- Any question that can be answered by a **frontier LLM** (or Nemotron when integrated) must be routed to that model.
- The **answer** must be:
  - Returned to the user.
  - **Written into MINDEX** in context (e.g. answer-snippet, Q&A pair, or worldview fact).
  - **Worldview**: If the answer is about world state (e.g. weather, location, event), it must be added to or aligned with WorldState/Worldview so future searches and MYCA brain see it.

---

## 5. Fix “Unanswerable” Search — Permanently

**Current gap**: Not all questions can be answered in search.

**Target**:

1. **Unified search orchestration** (MAS or website): Single entrypoint that (a) queries MINDEX, (b) enriches with MYCA brain/memory, (c) calls CREP/Earth2/specialists, (d) calls LLM when appropriate, (e) aggregates and stores.
2. **Fallback chain**: MINDEX → memory → CREP → Earth2 → LLM. No query returns “no results” without having tried the full chain.
3. **Answer storage**: Any successful answer (from any source) is written to MINDEX so the next identical or similar query is answered from MINDEX instantly.
4. **Tests**: Every suggestion and every test query must be run through the pipeline and verified; add to ETL/memory so MINDEX has context to answer again.

---

## 6. Suggestion Buttons (Hero) — UI Fix

**Done (Mar 14, 2026)**:

- Try: suggestion buttons were moved **outside** the hero card (which had `overflow-hidden`) so they are never clipped.
- They are a single line, scale with viewport, and use horizontal scroll (`overflow-x-auto`) when needed; `min-h-[44px]` and touch-friendly; "Try:" label always visible.

**File**: `website/components/home/hero-search.tsx`.

---

## 7. Clear Pipeline: Learning + Instant Answer

For **LLM-like**, **MINDEX**, **CREP**, and **MYCA-brain** responses:

| Step | Action |
|------|--------|
| 1. Ingest | Query received (search/voice/agent). |
| 2. Route | Orchestrator decides: MINDEX first, then memory, CREP, Earth2, LLM. |
| 3. Execute | Call each source as needed; aggregate. |
| 4. Store | Write any new data or answer into MINDEX (and worldview if applicable). |
| 5. Learn | Register question/answer for NLM, memory, ETL. |
| 6. Respond | Return to user with data + widgets + answer. |

This pipeline must be documented in code and in runbooks so every developer and agent can trace a query from input to stored answer to instant second search.

---

## 8. Nemotron 3 Preparation

- **Nemotron MYCA Rollout** plan (`.cursor/plans/nemotron_myca_rollout_8469ab79.plan.md`) is in progress; another agent is merging Nemotron capability.
- **Doable search alignment**:
  - Nemotron (when live) becomes one of the LLM paths in the unified model-routing layer.
  - Answers from Nemotron must flow into the same pipeline: store in MINDEX, update worldview, register for training/memory.
  - Search orchestration must call Nemotron-capable brain when the question is LLM-answerable and Nemotron is selected by config.

---

## 9. Implementation Checklist (High Level)

- [ ] **Unified search orchestration** endpoint (MAS or website) that chains MINDEX → memory → CREP → Earth2 → LLM.
- [ ] **MINDEX schema** for answer-snippets, Q&A pairs, and worldview facts; ETL jobs to ingest from LLM/CREP/Earth2.
- [ ] **Widget registry** and missing-widget detection; deploy path for new widget types.
- [ ] **Question/answer registration** for memory, NLM, and ETL so repeated questions hit MINDEX first.
- [ ] **Tests**: Add each Try: suggestion and key test queries to an automated pipeline that verifies ETL → MINDEX → second-search answer.
- [ ] **Nemotron**: When merged, plug Nemotron into the same orchestration and storage pipeline.
- [ ] **Docs**: Update SYSTEM_REGISTRY, API_CATALOG, and MASTER_DOCUMENT_INDEX when new endpoints and widgets exist.

---

## 10. References

| Doc | Purpose |
|-----|---------|
| `docs/WORLD_VIEW_SEARCH_SUGGESTIONS_PLAN_MAR14_2026.md` | World-view suggestions, MINDEX expansion, cohesion. |
| `docs/GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md` | WorldState, packet build, grounding. |
| `docs/WORLDSTATE_CONTRACT_MAR14_2026.md` | Worldstate read API and contract. |
| `docs/WORLDSTATE_VS_SPECIALIST_COMMAND_BOUNDARY_MAR14_2026.md` | Worldstate vs CREP/specialist commands. |
| `.cursor/plans/nemotron_myca_rollout_8469ab79.plan.md` | Nemotron 3 integration for MYCA/AVANI. |
