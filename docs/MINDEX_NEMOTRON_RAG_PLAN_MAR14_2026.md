# MINDEX Nemotron RAG Plan — Embedding, Rerank, and Provenance

**Date:** March 14, 2026  
**Status:** Plan (implementation reference for Nemotron MYCA/AVANI integration)  
**Related:** `nemotron_myca_rollout_8469ab79.plan.md` §4, `GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md`, `WORLDSTATE_CONTRACT_MAR14_2026.md`

---

## 1. Current State

- **MINDEXBridge** (`mycosoft_mas/myca/os/mindex_bridge.py`): `search_knowledge()` calls MINDEX API `/api/mindex/unified-search` and `/api/search` (keyword/unified, not vector). `recall_semantic()` and `query_knowledge_graph()` are proxies to `search_knowledge()`. `vector_search()` uses a **placeholder** vector `[0.0] * 384` and does not call an embedding model.
- **Memory brain** and **world model** enrichment need a single, provenance-rich retrieval path; today there is no real embedding + rerank pipeline and no shared contract aligned with `WorldState` / `WorldStateRef`.
- **MINDEX** (189): Qdrant (6333), PostgreSQL with pgvector (e.g. `nlm.nature_embeddings`, FCI signal embeddings), and API search endpoints exist but are not wired into a Nemotron RAG pipeline.

---

## 2. Goals

- Replace placeholder semantic lookup with a **real embedding + optional rerank** pipeline and a **central retrieval contract**.
- Make MYCA live-context assembly, memory brain, and world-model enrichment all consume the **same** provenance-rich retrieval path.
- Keep retrieval aligned with canonical **WorldState** and **WorldStateRef**; do not introduce a parallel “Nemotron worldview” contract.
- Document required MINDEX and MAS changes for implementation.

---

## 3. Central Retrieval Contract

### 3.1 Single retrieval API (preferred: MINDEX-owned)

- **Option A (recommended):** MINDEX API exposes a single **RAG retrieval** endpoint, e.g. `POST /api/rag/retrieve`, that:
  - Accepts: `query`, `embedding_model_id` (optional), `collections` (optional), `limit`, `min_score`, `world_state_ref` (optional, for filtering by snapshot/time).
  - Returns: list of **retrieved chunks** with **provenance** per item (see below).
  - MINDEX performs: query embedding (via Nemotron or shared embedding model), vector search (Qdrant and/or pgvector), optional rerank, then augments each hit with provenance and (when applicable) WorldStateRef-compatible metadata.

- **Option B:** MAS owns the retrieval contract: a single module in MAS (e.g. `mycosoft_mas/llm/rag_retrieval.py`) that:
  - Calls MINDEX for vector search (and optionally a separate embedding service), applies rerank in MAS, and attaches provenance and WorldStateRef alignment before returning.

Either way, **all** consumers (MINDEXBridge, memory_brain, world_model enrichment, live-context assembly) must call this **same** contract so behavior is consistent and provenance is never bypassed.

### 3.2 Provenance per retrieved chunk

Every item returned by the central retrieval must include:

| Field | Type | Description |
|-------|------|-------------|
| `content` | str | Text or payload of the chunk |
| `source_id` | str | Stable ID (e.g. document id, memory id, species id) |
| `collection` | str | Qdrant collection or logical source (e.g. `knowledge`, `semantic_memory`, `species`) |
| `timestamp` | str (ISO) or number | When the source was stored or last updated |
| `score` | float | Similarity or rerank score |
| `provenance_root` | Optional[str] | Upstream service or sensor (e.g. `mindex_etl`, `world_model`) |
| `world_state_ref` | Optional[dict] | When applicable, minimal WorldStateRef-compatible ref (snapshot_ts, sources) so callers can align with WorldState |

No retrieval path should return raw chunks without at least `source_id`, `collection`, and `score`.

---

## 4. Embedding

- **Model:** Use a single embedding model for all RAG retrieval (Nemotron-compatible or shared) to avoid dimension/semantic mismatch. Prefer one that matches Nemotron ecosystem if available (e.g. NVIDIA NeMo or Nemotron embedding).
- **Where:** Embedding can run on **MINDEX (189)** or **GPU node (190)**. If MINDEX API owns the RAG endpoint, embedding is best colocated there (189) or called from 189 to 190; if MAS owns the contract, MAS can call an embedding service on 189 or 190.
- **Dimensions:** Standardize on one dimension (e.g. 1024 or 384) for the primary RAG collection(s); document in `mindex_etl/config.py` and in MAS `backend_selection` / `models.yaml` if MAS ever embeds.
- **MINDEX API:** Either:
  - Add `POST /api/embed` (or similar) that returns a vector for a given text and model_id, or
  - Keep embedding internal to MINDEX when implementing `POST /api/rag/retrieve` (no separate public embed endpoint required for the contract).

---

## 5. Rerank

- **Optional:** Introduce an optional rerank step after vector search to improve relevance. Rerank model can live on 189 or 190; same placement logic as embedding.
- **Position:** Query → Embed → Vector search → (Rerank) → Provenance attachment → Response.
- **Contract:** If rerank is used, the central retrieval API returns the same schema; `score` may be rerank score instead of raw similarity.

---

## 6. MINDEX-Side Changes

- **New or updated endpoint:** Implement `POST /api/rag/retrieve` (or agreed path) with request/response schema above. Internal flow: embed query → search Qdrant and/or pgvector → optional rerank → attach provenance and optional world_state_ref.
- **Collections:** Define at least one primary RAG collection (e.g. `knowledge` or `semantic_memory`) with a fixed embedding dimension; backfill or ETL as needed.
- **Config:** Document embedding model id, dimension, and rerank model (if any) in `mindex_etl/config.py` or a dedicated RAG config section. Do not hardcode secrets; use env vars.
- **Existing endpoints:** Keep `/api/mindex/unified-search` and `/api/search` for keyword/unified use; RAG path is additive.

---

## 7. MAS-Side Changes

- **MINDEXBridge:**
  - Replace `vector_search()` placeholder with a call to the central retrieval contract (MINDEX `POST /api/rag/retrieve` or MAS RAG module). Use real query embedding when the contract is MAS-owned.
  - Implement `recall_semantic()` to call the same central retrieval and return list of chunks with provenance; optionally map to a minimal format for memory_brain if needed.
  - Ensure `search_knowledge()` remains for keyword/unified use; add a separate path (e.g. `rag_retrieve()`) that all semantic/vector callers use.
- **Memory brain** (`mycosoft_mas/llm/memory_brain.py`): Switch any semantic recall to the same central retrieval contract; consume provenance and (when relevant) world_state_ref for context assembly.
- **World model** (`mycosoft_mas/consciousness/world_model.py`): When enriching from MINDEX knowledge, use the same retrieval contract so `_update_mindex()` and any live-context assembly share one path and WorldState alignment is consistent.
- **Backend selection / models.yaml:** If MAS ever runs the embedding client, register the embedding model and backend in the unified model-routing layer so it stays consistent with Nemotron rollout.

---

## 8. WorldState / WorldStateRef Alignment

- **No parallel contract:** Do not define a separate “Nemotron worldview” or retrieval-specific world model. All retrieval metadata that refers to “world state” must use the existing **WorldStateRef** shape (snapshot_ts, sources, freshness, summary) or a minimal subset so that:
  - Experience packets and grounding continue to use `WorldStateRef` from GroundingGate.
  - Retrieval results can be tagged with “which world snapshot this belongs to” when relevant (e.g. for time-sensitive or sensor-backed knowledge).
- **Per-source metadata:** Follow `WORLDSTATE_CONTRACT_MAR14_2026.md` per-source metadata (provenance_root, freshness, degraded) when attaching provenance to retrieved chunks so that MYCA can reason about staleness and source.

---

## 9. Implementation Order (Recommended)

1. **Define and document** the central retrieval request/response schema (provenance fields, optional world_state_ref).
2. **MINDEX:** Implement embedding (model + dimension) and `POST /api/rag/retrieve` with vector search and provenance; add optional rerank later.
3. **MAS MINDEXBridge:** Add `rag_retrieve()`; point `recall_semantic()` and `vector_search()` to it; keep `search_knowledge()` for keyword path.
4. **Memory brain and world model:** Switch to the single retrieval contract; verify context assembly and WorldModel cache still get correct provenance.
5. **Tests:** Add regression tests for retrieval provenance, WorldStateRef alignment, and for route unification (all callers use one path).

---

## 10. Risks and Open Points

- **Embedding model choice:** Must be decided (Nemotron/NeMo vs other) so dimension and API are fixed before backfilling large collections.
- **Qdrant vs pgvector:** Current MINDEX uses both; the central contract may need to query both and merge (e.g. knowledge in Qdrant, semantic memory in pgvector) with a single provenance shape.
- **Latency:** Embed + vector search + rerank must stay within acceptable bounds for voice and chat (e.g. &lt; 500 ms for retrieval leg); may require caching or colocation on 189.

---

**Next:** Implement per §9 and update SYSTEM_REGISTRY and API_CATALOG when new endpoints and roles are added.
