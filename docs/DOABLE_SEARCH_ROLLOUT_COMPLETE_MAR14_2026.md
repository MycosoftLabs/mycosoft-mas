# Doable Search Rollout — Complete (Mar 14, 2026)

**Status:** Complete  
**Related plan:** Doable Search Rollout (attached plan file); `docs/DOABLE_SEARCH_AND_ANSWER_PIPELINE_MAR14_2026.md`

## Summary

The MAS-owned unified search pipeline is implemented: every query routes through one orchestration path, successful answers are persisted into MINDEX, and the website proxies to MAS with a canonical widget registry and missing-widget detection. Nemotron answers flow through the same storage pipeline.

## Delivered

### 1. MAS memory and semantic-search contract (repair-mas-search-contracts)
- MemoryCoordinator `recall()`/`store()` and semantic_search MINDEX adapter fixed; consciousness uses them for _restore_state/_save_state.

### 2. MAS search orchestrator (build-mas-search-orchestrator)
- `mycosoft_mas/consciousness/search_orchestrator.py` — `run_unified_search()`: MINDEX → memory → specialists → persistence.
- Consciousness, tool_orchestrator, and llm_brain route search through the orchestrator.
- `mycosoft_mas/core/routers/search_orchestrator_api.py` — POST `/api/search/execute` calls `run_unified_search`.

### 3. MINDEX answer schema (add-mindex-answer-schema)
- Migration `001_search_schema_mar14_2026.sql`: `search.query`, `search.answer_snippet`, `search.qa_pair`, `search.worldview_fact`, `search.answer_source`.
- `mindex_api/routers/search_answers.py`: GET/POST `/search/answers`, POST `/search/queries`, GET/POST `/search/qa`.
- ETL stub in `mindex_etl/jobs/` for answer materialization.

### 4. Website proxy and widget registry (convert-website-to-proxy)
- Website unified search and chat routes try MAS first (`USE_MAS_SEARCH`); on success return mapped results with `source: "mas"`.
- `lib/search/mas-search-proxy.ts`: `callMASSearchExecute()`, `mapMASResponseToUnified()`.
- `lib/search/widget-registry.ts`: `WidgetType`, `WIDGET_REGISTRY`, `RESULT_BUCKET_TO_WIDGET`, `getWidgetForResultBucket()`, `getBucketsWithMissingWidget()`, `getRegisteredButNotExported()`.
- `components/search/fluid/widgets/FallbackWidget.tsx` and canvas fallback rendering for unknown result buckets.

### 5. Registration and training (wire-registration-and-training)
- `mycosoft_mas/consciousness/search_registration.py`: `persist_search_to_mindex()`, `register_training_sink()`, `register_etl_intake_if_live()` (off hot path, fire-and-forget).
- Orchestrator schedules MINDEX persist + training sink + ETL intake after each search.
- Voice orchestrator chat persists answers to MINDEX via same pipeline.

### 6. Nemotron routing (align-nemotron-routing)
- Role-based routing via `get_backend_for_role(MYCA_CORE)` in router, frontier_router, llm_brain; `config/models.yaml` defines nemotron roles.
- `docs/NEMOTRON_ROUTING_AND_PERSISTENCE_MAR14_2026.md` documents alignment.
- Voice/orchestrator answers (Nemotron or Ollama) persisted to MINDEX search schema.

### 7. End-to-end validation (add-end-to-end-validation)
- **Website:** `e2e/search.spec.ts` — search page with q=, worldview query, unified API 200, homepage search entry; `playwright.config.ts` added.
- **MAS:** `tests/test_search_orchestrator.py` — `run_unified_search` return shape; `tests/test_search_registration.py` — _normalize_query, _result_hash, _snippet_from_payload.

## How to verify

- **MAS:** `poetry run pytest tests/test_search_orchestrator.py tests/test_search_registration.py -v`
- **Website e2e:** Start dev server (port 3010), then `npx playwright test e2e/search.spec.ts`
- **MINDEX:** Run migration `001_search_schema_mar14_2026.sql` on target PostgreSQL; GET/POST `/api/mindex/search/answers` (manual or integration test).
- **Search flow:** Open homepage → search "Amanita muscaria" or "flights over pacific" → results from MAS when `USE_MAS_SEARCH` is not false.

## Registries and docs updated

- This completion doc; `docs/NEMOTRON_ROUTING_AND_PERSISTENCE_MAR14_2026.md`.
- MASTER_DOCUMENT_INDEX and CURSOR_DOCS_INDEX updated with new/current docs.

## Post-rollout: Notepad gated on auth (Mar 14, 2026)

- Search notepad (add/remove/clear items) is gated on authenticated user: `SearchContextProvider` uses `useAuth()` and `notepadStorageKey = getNotepadStorageKey(user?.id)`.
- When not logged in: notepad shows empty, no localStorage read/write.
- When logged in: notepad persists per user in `localStorage` under `search-notepad-${user.id}`.
- See `website/components/search/SearchContextProvider.tsx`.

## Follow-up / known gaps

- **Follow-up plan:** `docs/SEARCH_FOLLOWUP_MAP_CREP_EARTH_INTERNAL_MAR14_2026.md` — Map/CREP full-screen, Earth Simulator naming, internal-only answers (planned, not in rollout).
- MINDEX answer schema migration must be applied on each environment (dev, sandbox, production).
- Second-search instant retrieval (GET `/search/answers?q=`) depends on prior writes; validate with a first search then repeat query.
- Playwright e2e can be extended for mobile path and widget coverage checks when selectors are stable.
