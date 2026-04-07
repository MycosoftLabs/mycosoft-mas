# Grounding + RAG Execution Status — April 6, 2026

**Date:** April 6, 2026  
**Status:** Partial — central retrieval live; embeddings scheduled  
**Related:** `docs/MYCA_GROUNDED_COGNITION_PHASES_2_3_4_SPRINT_PLAN_FEB17_2026.md`, `docs/MINDEX_NEMOTRON_RAG_PLAN_MAR14_2026.md`

---

## Done (this session)

| Item | Detail |
|------|--------|
| **MINDEX `POST /api/mindex/rag/retrieve`** | Real unified-search-backed chunks with provenance (`mindex_api/routers/rag_retrieve.py`). No mock rows. |
| **MAS `MINDEXBridge.vector_search`** | Calls RAG endpoint first; falls back to Qdrant only if RAG unreachable (`myca/os/mindex_bridge.py`). |
| **Migrations** | `0016_postgis_spatial.sql` and `0017_temporal_episodes.sql` already exist in MINDEX — apply on VM if not yet run. |

---

## Remaining (from plans)

| Track | Work |
|-------|------|
| **Embeddings + rerank** | Wire Nemotron or shared embedding service; replace `retrieval_mode: keyword_unified` scoring with similarity + optional rerank per `MINDEX_NEMOTRON_RAG_PLAN_MAR14_2026.md`. |
| **SpatialService / TemporalService** | Replace stubs with DB-backed calls where migrations are applied; wire `grounding_gate` per Feb 17 sprint plan. |
| **WorldModel cache warming** | Ops: reduce cold-start empty `WorldState` on MAS VM. |
| **`MYCA_GROUNDED_COGNITION` env** | Confirm production value on MAS VM 188. |

---

## Verify

```http
POST http://192.168.0.189:8000/api/mindex/rag/retrieve
Content-Type: application/json

{"query": "Amanita", "limit": 5}
```

Expect `chunks` array with `provenance_root: mindex_unified_search`.
