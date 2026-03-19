# AVANI NLM Real Runtime (Mar 14, 2026)

**Status:** Implemented  
**Related:** Plasticity Forge Phase 1, `docs/PLASTICITY_FORGE_OWNERSHIP_LOCKED_MAR14_2026.md`, `docs/PLASTICITY_FORGE_CONTRACTS_FROZEN_MAR14_2026.md`

## Purpose

This document describes the **real** AVANI/NLM runtime: telemetry translation, optional persistence to MINDEX, and trainer data sources. No placeholder training paths or mock science; all data flows are real or explicitly degraded.

## Real Telemetry Path

1. **Raw data** enters the NLM service (MAS/NLM repo) via:
   - `POST /api/translate` — body: `TranslateRequest` (raw, envelopes, source_id, context, **persist**).
   - `POST /api/telemetry/ingest-verified` — for verified device telemetry.

2. **Translation layer** (`NLM/nlm/telemetry/translation_layer.py`):
   - Raw → normalized values → bio-tokens → **Nature Message Frame (NMF)**.
   - NMF is the canonical intermediate; it is returned as JSON from `/api/translate`.

3. **Optional persist to MINDEX** (when `persist=true` in the translate request):
   - NLM service calls `POST {MINDEX_API_URL}/api/mindex/nlm/nmf` with body:
     - `packet`: full NMF dict (from `nmf.to_dict()`),
     - `source_id`: string,
     - `anomaly_score`: float (default 0.0).
   - MINDEX stores the record in `nlm.nature_embeddings` (packet as JSONB, source_id, anomaly_score; `embedding` column nullable until an embedding pipeline exists).
   - Environment: `MINDEX_API_URL` (default `http://localhost:8000`), `MINDEX_API_KEY` (optional, for X-API-Key when MINDEX has API keys configured).
   - Response: translate endpoint returns the NMF dict and, when persist was requested, a `persist` key with either MINDEX’s success payload (`embedding_id`, `ts`) or `{ "success": false, "error": "..." }`.

4. **Trainer data sources** (MAS repo: `mycosoft_mas/nlm/training/trainer.py`):
   - **Real only:** Trainer uses `MINDEXClient` to fetch training data from MINDEX (e.g. telemetry, research, genetics). No mock metrics or fake categories.
   - When no training runtime is configured or a category has no real source, the trainer reports **degraded** state with clear provenance (no silent fallback to fake data).

## Components

| Component | Location | Role |
|-----------|----------|------|
| NLM API (translate, nmf, ingest) | `MAS/NLM/nlm/api/main.py` | Real NLM runtime boundary; translate + optional MINDEX persist. |
| Translation layer | `MAS/NLM/nlm/telemetry/translation_layer.py` | Raw → normalized → bio-tokens → NMF. |
| NMF model | `MAS/NLM/nlm/telemetry/nmf.py` | Nature Message Frame structure and serialization. |
| MINDEX NLM router | `MINDEX/mindex_api/routers/nlm_router.py` | `POST /api/mindex/nlm/nmf` — persists NMF to `nlm.nature_embeddings`. |
| MAS NLM trainer | `mycosoft_mas/nlm/training/trainer.py` | Real MINDEX-backed training; degraded when no runtime or no real source. |
| MAS NLM compatibility | `mycosoft_mas/core/routers/nlm_api.py`, `mycosoft_mas/myca/os/nlm_bridge.py` | Proxy/status; real model service is NLM repo. |

## Verification

- **Translate:** `POST /api/translate` with valid raw payload returns NMF JSON; with `persist: true` and MINDEX reachable, response includes `persist.success` and `embedding_id`/`ts` from MINDEX.
- **Trainer:** No mock data; only real MINDEX sources; degraded state is explicit when data or runtime is missing.
- **Persistence:** MINDEX `nlm.nature_embeddings` receives records only from real NLM translate (persist) or equivalent verified ingest paths.

## References

- Ownership: `docs/PLASTICITY_FORGE_OWNERSHIP_LOCKED_MAR14_2026.md`  
- Contracts: `docs/PLASTICITY_FORGE_CONTRACTS_FROZEN_MAR14_2026.md`  
- Grounding: `docs/GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md`  
- Plan: `.cursor/plans/plasticity_forge_phase1_616372f3.plan.md`
