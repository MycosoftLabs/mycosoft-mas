# MYCA Harness Integration Patch — Apr 17, 2026

**Status:** Implemented (initial)  
**Scope:** Repository alignment, Nemotron, PersonaPlex, STATIC video, static system, turbo-quant, intention brain, MINDEX/Supabase, NLM, tests, API surface.

## Location

Python package: `mycosoft_mas.harness` (MAS monorepo).

## Modules

| Module | Role |
|--------|------|
| `config.py` | `HarnessConfig.from_env()` — Nemotron/PersonaPlex/MINDEX/Supabase/YouTube/static paths |
| `models.py` | `RouteType`, `HarnessPacket`, `HarnessResult` |
| `router.py` | Classify packets → STATIC / STATIC_VIDEO / NEMOTRON / NLM / PERSONAPLEX_VOICE |
| `nemotron_client.py` | OpenAI-compatible streaming to `NEMOTRON_API_URL` / Ollama host |
| `persona_plex.py` | Bridge HTTP ASR/TTS; voice embeddings NATF0…VARM4 |
| `static_video_tool.py` | YouTube Data API search + timedtext transcripts + cache dir |
| `static_system.py` | YAML/JSON lookups (`HARNESS_STATIC_ANSWERS_PATH`) |
| `turbo_quant.py` | Placeholder compressor (zlib) + NDA flag — swap under NDA delivery |
| `intention_brain.py` | SQLite goals + NLM anomaly escalation |
| `mindex_client.py` | MINDEX HTTP + optional Supabase REST + execution logging |
| `nlm_interface.py` | Optional `nlm` imports; AVANI threshold hook |
| `planner.py` | Plan steps aligned with intention brain |
| `evaluator.py` | MINDEX cross-check for species mentions |
| `optimization.py` | Benchmark helpers |
| `engine.py` | `HarnessEngine.run()` orchestrator |
| `api.py` | FastAPI `POST /api/harness/packet`, `GET /api/harness/health` |

## HTTP exposure

Harness routes mount **by default**. Use **`HARNESS_API_DISABLED=1`** to omit `/api/harness/*`. Legacy: `HARNESS_API_ENABLED=false` also disables.

## Environment variables

- `NEMOTRON_API_URL`, `NEMOTRON_MODEL`, `NEMOTRON_API_KEY` / `OPENAI_API_KEY`
- `PERSONAPLEX_BRIDGE_URL` (default Voice Legion pattern in docs)
- `MINDEX_API_URL`
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (optional direct REST)
- `YOUTUBE_DATA_API_KEY` (STATIC video search)
- `HARNESS_STATIC_ANSWERS_PATH` (defaults to bundled `static_answers.example.yaml`)
- `HARNESS_INTENTION_DB_PATH`
- `HARNESS_ENABLE_TURBO_QUANT`, `HARNESS_TURBO_QUANT_NDA`
- `HARNESS_NLM_ENABLED`

## Safety

- MINDEX writes are best-effort to `/api/harness/execution` if deployed; otherwise skipped.
- NLM predictions route through `guardian_veto` threshold; full **AVANIGuardian** integration requires tensor pipeline.
- Static answers are configuration-only — review before production.

## Verification

```bash
cd mycosoft-mas
pytest tests/test_harness_smoke.py -v
```

## References

- NLM: `MAS/NLM/README.md`, `nlm.data.rooted_frame_builder`, `nlm.model.nlm_model`
- AVANI: `nlm/guardian/avani.py`
