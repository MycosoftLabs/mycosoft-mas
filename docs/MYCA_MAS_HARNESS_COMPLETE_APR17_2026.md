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
| API | **Default on:** `GET /api/harness/health`, `POST /api/harness/packet` unless `HARNESS_API_DISABLED=1` or legacy `HARNESS_API_ENABLED=false` |
| Brain | Optional `BRAIN_CHAT_USE_HARNESS=1` or `POST /voice/brain/chat` with `"use_harness": true` → harness path (no memory recall on that turn) |
| Tests | `tests/test_harness_smoke.py`, `tests/test_harness_api.py` — router, planner intention, FastAPI routes, mocked LLM + MINDEX |

## Environment variables

| Variable | Purpose |
|----------|---------|
| `HARNESS_API_DISABLED` | Set `1` to **omit** `/api/harness/*` from MAS |
| `HARNESS_API_ENABLED` | Legacy: `false` / `off` disables router (same as disabled) |
| `BRAIN_CHAT_USE_HARNESS` | Set `1` so `POST /voice/brain/chat` uses harness instead of memory brain |
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
poetry run pytest tests/test_harness_smoke.py tests/test_harness_api.py -v
```

With MAS running (harness routes on by default):

```http
GET http://192.168.0.188:8001/api/harness/health
POST http://192.168.0.188:8001/api/harness/packet
Content-Type: application/json

{"query":"species notes for Agaricus"}
```

## System-wide rollout (Apr 17, 2026 update)

- Orchestrator loads `/api/harness/*` unless explicitly disabled (see env table).
- Planner attaches **`intention`** (active goal) into `HarnessResult.structured.plan` when the intention DB has a pending/active goal.
- Example env template: `config/harness.env.example`.

## Follow-ups

- MINDEX `POST /api/harness/execution` returns 404/501 until implemented on MINDEX VM — harness logs and skips gracefully.
- Optional NLM GPU deployment — keep lazy imports and `HARNESS_NLM_ENABLED` gate.
- `POST /voice/brain/stream` does not yet offer a harness branch (non-streaming chat only).

## Lessons learned

- Voice ingress must **clear `raw_audio` after ASR** so routing uses text semantics (`MINDEX_GROUNDED` vs stuck voice route).
- Single Nemotron configuration source: reuse `backend_selection` to avoid divergent defaults.
