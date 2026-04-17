# MYCA MAS Harness — Implementation Complete APR17_2026

**Date:** 2026-04-17  
**Status:** Complete  
**Related:** Plan `MYCA MAS Harness` (in-repo harness spec), `docs/Harness Engineering for MYCA MAS.docx.md`

## Scope delivered

| Area | Implementation |
|------|----------------|
| Package | `mycosoft_mas.harness` — models, router, engine, planner, evaluator, optimization, Nemotron (`httpx` → OpenAI-compatible chat completions), PersonaPlex bridge (ASR/TTS), `static_search` (MINDEX `GET /api/mindex/unified-search`), optional `static_system` YAML, turbo-quant placeholder, intention brain, harness `MindexClient`, NLM interface (lazy imports), FastAPI `api.py` |
| STATIC (product) | **Search-in-LLM**: default text route `MINDEX_GROUNDED` retrieves via unified search and injects context into Nemotron system prompt — **no** YouTube or third-party video/transcript APIs |
| Nemotron | Delegates to configured base URL/model; defaults union with `get_backend_for_role(MYCA_CORE)` from `mycosoft_mas.llm.backend_selection` plus `HARNESS_*` / `NEMOTRON_*` overrides |
| API | `HARNESS_API_ENABLED` gates inclusion in `myca_main.py`: `GET /api/harness/health`, `POST /api/harness/packet` |
| Tests | `tests/test_harness_smoke.py` — static YAML, router, turbo-quant, engine paths (mocked LLM + MINDEX context), `record_execution` mocked |

## Environment variables

| Variable | Purpose |
|----------|---------|
| `HARNESS_API_ENABLED` | Mount harness router (`1` / `true`) |
| `HARNESS_GROUND_WITH_MINDEX` | Default `true`; set `false` for Nemotron-only text path |
| `HARNESS_MINDEX_SEARCH_TYPES` | Default unified-search `types` param (e.g. `biological`) |
| `HARNESS_MINDEX_TIMEOUT` | Seconds for MINDEX HTTP (default `45`) |
| `HARNESS_STATIC_ANSWERS_PATH` | YAML/JSON policy shortcuts |
| `HARNESS_INTENTION_DB_PATH` | SQLite path (default under `MAS/data/harness/intention_brain.sqlite`) |
| `HARNESS_ENABLE_TURBO_QUANT` | Placeholder compression telemetry on Nemotron path |
| `HARNESS_NLM_ENABLED` | Enable NLM package hooks when installed |
| `MINDEX_API_URL`, `MINDEX_API_KEY` | MINDEX REST + optional auth headers |
| `HARNESS_NEMOTRON_*` / `NEMOTRON_*` | Override Nemotron endpoint and model |

## Verification

```powershell
cd MAS/mycosoft-mas
poetry run pytest tests/test_harness_smoke.py -v
```

With MAS running and `HARNESS_API_ENABLED=1`:

```http
GET http://192.168.0.188:8001/api/harness/health
POST http://192.168.0.188:8001/api/harness/packet
Content-Type: application/json

{"query":"species notes for Agaricus"}
```

## Follow-ups

- MINDEX `POST /api/harness/execution` returns 404/501 until implemented on MINDEX VM — harness logs and skips gracefully.
- Optional NLM GPU deployment — keep lazy imports and `HARNESS_NLM_ENABLED` gate.

## Lessons learned

- Voice ingress must **clear `raw_audio` after ASR** so routing uses text semantics (`MINDEX_GROUNDED` vs stuck voice route).
- Single Nemotron configuration source: reuse `backend_selection` to avoid divergent defaults.
