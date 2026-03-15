# Nemotron Routing and Persistence Alignment (Mar 14, 2026)

**Status:** Complete (Doable Search Rollout — Workstream 5)

## Summary

Nemotron is a first-class backend role in MAS. All LLM entry points resolve the model via `get_backend_for_role(role)`; Nemotron-generated answers (and Ollama fallback) flow through the same MINDEX answer persistence pipeline.

## Role-based routing

- **Config:** `config/models.yaml` — `model_roles.myca_core` / `nemotron_super` → `nemotron:${NEMOTRON_MODEL_SUPER}`; `myca_edge` / `nemotron_nano` → `nemotron:${NEMOTRON_MODEL_NANO}`. When `NEMOTRON_BASE_URL` is not set, backend_selection falls back to Ollama.
- **Owners:** `mycosoft_mas/llm/backend_selection.py`, `mycosoft_mas/llm/router.py`, `mycosoft_mas/llm/frontier_router.py`, `mycosoft_mas/myca/os/llm_brain.py`.
- **Behavior:** `get_backend_for_role(MYCA_CORE)` is used for primary MYCA responses; router task types map to roles; FrontierLLMRouter and LLMBrain use the same resolver. No website-side direct provider bypass for chat — website uses MAS voice orchestrator and search proxy.

## Same storage pipeline

- **Search:** `consciousness/search_orchestrator.run_unified_search()` builds `result_payload`; after episodic memory store, it schedules `persist_search_to_mindex`, `register_training_sink`, and `register_etl_intake_if_live` (fire-and-forget). Answers are written to MINDEX `search.answer_snippet` / `search.query`.
- **Voice/chat:** After returning a response, `voice_orchestrator_chat` in `myca_main.py` schedules `persist_search_to_mindex(payload.message, minimal_payload, ...)` so Nemotron/Ollama replies are stored in the same MINDEX search schema.
- **Training sink:** `data/search_training_sink.jsonl` receives records from search (and can be extended for voice) for NLM/LLM curation off the hot path.

## Website

- Search and unified routes proxy to MAS `/api/search/execute`. Chat uses MAS voice orchestrator. Direct provider fallback for model selection has been removed in favor of MAS orchestration.

## References

- Doable Search Rollout plan (Workstream 5)
- `docs/UNIFIED_LLM_ROUTING_NEMOTRON_MAR14_2026.md` (if present)
- `mycosoft_mas/consciousness/search_registration.py`
- `mycosoft_mas/llm/backend_selection.py`
