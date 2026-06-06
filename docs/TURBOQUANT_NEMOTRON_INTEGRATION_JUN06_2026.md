# TurboQuant + Nemotron Integration — Research & Design

**Date:** June 06, 2026
**Status:** Design / RFC (research-first; reference implementation landed)
**Owner:** MYCA coding agent (Sandbox VM)
**Scope:** MAS (this repo), MINDEX (vector search), MYCA capabilities
**Companion docs:**
- `mindex/docs/TURBOQUANT_INTEGRATION_JUN06_2026.md` (cuVS/pgvector path)
- `docs/UNIFIED_LLM_ROUTING_NEMOTRON_MAR14_2026.md` (existing routing contract)

---

## 0. TL;DR

Two independent advances landed in mid-2026 that together let MYCA do **more with
less**:

1. **TurboQuant** (Google Research) — a *data-oblivious*, two-stage vector quantizer
   (**PolarQuant** + **QJL**) that compresses embeddings and KV-cache to ~3 bits/dim
   with near-zero accuracy loss, **no codebook training**, and **zero per-block scale
   overhead**. It beats Product Quantization / KIVI without dataset tuning.

2. **NVIDIA Nemotron 3** — an open hybrid Mamba-Transformer MoE family (**Ultra 550B**,
   **Super 120B**, **Nano 30B**, **Nano Omni 30B**) plus specialized
   **Retriever / Parse / Speech / Safety** models. Each model is best at a specific
   job, so MYCA should route per-capability rather than use one model for everything.

**Decision (per product owner):** **fully replace Ollama/Llama with Nemotron** as
MYCA's brain, and apply TurboQuant across MAS vector memory, MINDEX vector search, and
the Nemotron KV-cache serving lane.

**What this delivers:**

| Lever | Mechanism | Saving |
|-------|-----------|--------|
| Vector memory (Qdrant) | TurboQuant 3-bit codec | **~5× vs fp16, ~10× vs fp32** RAM/disk |
| MINDEX vector search | TurboQuant in cuVS load path | Larger indexes fit in GPU VRAM |
| Nemotron KV-cache | PolarQuant+QJL KV quant | **~6× KV memory**, longer context / VM |
| Model spend | Capability routing (Nano for 80% of calls) | Fewer Super/Ultra calls |

This document is **research + design first** (the chosen deliverable shape). A small,
**validated reference implementation** of the codec already ships in this PR at
`mycosoft_mas/memory/turboquant.py` with tests in `tests/test_turboquant.py`.

---

## 1. TurboQuant — how it works

Source: *TurboQuant: Redefining AI efficiency with extreme compression*, Google
Research (2025/2026).

### 1.1 The problem it fixes
Classic vector quantization (scalar/product quant) stores **per-block scale constants
in full precision**, adding 1–2 bits/number and eroding the compression it just
bought. It also needs **per-dataset codebooks** (PQ) or tuning (KIVI), which is fragile
across MYCA's many embedding models (OpenAI 1536-d, Gemini 768-d, MiniLM 384-d,
MINDEX `fci_signals` 768-d, `nlm_nature` 16-d, `image_similarity` 512-d).

### 1.2 Stage 1 — PolarQuant (high-quality compression)
1. **Random rotation.** Rotate each vector with a structured random orthogonal map
   (sign-flip + Walsh–Hadamard, `O(d log d)`). This makes the geometry **isotropic**:
   the coordinates of any vector become approximately `N(0, 1/d)`.
2. **Polar split.** Decompose into **radius** (magnitude, one tiny scalar) and
   **direction** (angles). Because the rotated direction's coordinates are tightly
   concentrated and their distribution is *known a priori*, a single **fixed
   Gaussian-optimal grid** quantizes them well — **for every dataset**, with **no
   stored scale** (the overhead PQ/KIVI pay).

### 1.3 Stage 2 — QJL (1-bit error correction)
The **Quantized Johnson–Lindenstrauss** transform projects the vector with a random
JL matrix and keeps only **sign bits** (+1/-1): 1 bit/dim, **zero scale overhead**.
It corrects Stage-1 residual and, crucially, supports an **asymmetric inner-product
estimator** — a full-precision *query* projection against stored *key* sign bits
recovers `⟨q,k⟩` without ever materializing the key:

```
⟨q, k⟩ ≈ sqrt(π/2) · ‖k‖ · mean_i( (S q)_i · sign((S k)_i) )
```

This is unbiased via the Gaussian identity `E[a·sign(b)] = sqrt(2/π)·cov(a,b)/std(b)`.
It is exactly what attention does over a KV-cache, which is why TurboQuant doubles as a
**KV-cache compressor** for LLM serving.

### 1.4 Why it's the right fit for MYCA
- **Data-oblivious:** one codec for all embedding models and the KV-cache. No retraining
  when we swap embedding providers (we're moving to Nemotron-Retriever — see §2.4).
- **Zero overhead:** rotation and JL matrices are regenerated from an integer **seed**,
  never stored.
- **Provable:** near theoretical lower bounds; perfect needle-in-haystack on LongBench,
  RULER, ZeroSCROLLS, L-Eval per Google's benchmarks.

### 1.5 Reported & reproduced numbers
| Metric | Google (reported) | This repo's reference codec (measured) |
|--------|-------------------|----------------------------------------|
| Bit-width | 3-bit, ~0 accuracy loss | 3-bit direction + 1-bit sketch ≈ 3.08 b/dim |
| KV memory | 6× reduction | n/a (KV path is serving-side, §3.3) |
| Compression vs fp32 | — | **10.4×** (1536-d) |
| Compression vs fp16 | ~6× | **5.2×** (1536-d) |
| Reconstruction cosine | "zero accuracy loss" | **0.98** @3-bit, **0.99** @4-bit |
| Top-k recall vs fp32 | matches | **≥0.7** recon-only; **≥0.8** two-stage rerank |

(Reproduced by `tests/test_turboquant.py`, 8 tests passing.)

---

## 2. Nemotron 3 — full migration off Ollama

Source: NVIDIA Nemotron developer hub. Hybrid Mamba-Transformer MoE, up to **1M-token**
context, open weights, deployable via **NIM**, vLLM, SGLang, llama.cpp, or hosted NIM at
`build.nvidia.com`.

### 2.1 Model → capability map (route per job)
| Nemotron model | Size | Best at | MAS role(s) it replaces |
|----------------|------|---------|--------------------------|
| **Ultra** | 550B | Frontier reasoning: multi-step planning, tool use, synthesis, verify/recover | `nemotron_ultra`, hard `planning`, CEO/CFO/CTO corporate deep reasoning |
| **Super** | 120B | Best accuracy/GPU; complex multi-agent on a single node | `nemotron_super`, `myca_core`, corporate primary, consciousness |
| **Nano** | 30B | 4× throughput; fast sub-agents w/ targeted accuracy | `nemotron_nano`, `myca_edge`, infra/device/route agents, `fast` |
| **Nano Omni** | 30B | Multimodal (video/audio/image/text); doc-intelligence & computer-use | Vision/voice grounding, MycoBrain image, CREP screen reasoning |
| **Retriever** | — | Passage embedding + ranking for RAG | OpenAI `text-embedding-*`, MiniLM `embedding` role |
| **Parse** | — | Document understanding w/ spatial grounding (tables/text) | New: lab PDFs, invoices, compliance docs |
| **Speech** | — | ASR + TTS + speech-to-speech | Whisper STT, optionally ElevenLabs TTS |
| **Safety** | — | Multilingual moderation + jailbreak detection | `nemotron_safety`, guardian pre-filter |

### 2.2 The good news: the scaffold already exists
`mycosoft_mas/llm/backend_selection.py` **already** defines the Nemotron roles
(`NEMOTRON_SUPER/NANO/ULTRA/SPEECH/SAFETY/RAG`), env-driven mode switching
(`MYCA_BACKEND_MODE[_CATEGORY]=hybrid|nemotron|llama`), and `config/models.yaml`
`model_roles`. `OpenAICompatibleProvider` already speaks the NIM/OpenAI wire format.
**Migration is mostly configuration + removing Ollama fallbacks, not a rewrite.**

### 2.3 What "full replacement" actually requires
The current `get_backend_for_role()` falls back to `provider="ollama"` in **~6 code
paths** (lines ~228, 249, 388–392, 403–408, 412–418). A true cutover means:

1. **Add `Ultra` + `Omni` roles** to the role/model maps (Ultra exists as a constant but
   has no default model env; Omni is absent).
2. **Make `nemotron` the default mode**, not `hybrid`: set `MYCA_BACKEND_MODE=nemotron`
   and change the in-code default in `_get_backend_mode()` from `_MODE_HYBRID` to
   `_MODE_NEMOTRON` **(config change, reviewed)**.
3. **Replace Ollama fail-closed branches** with a Nemotron fail-closed: if no
   `NEMOTRON_BASE_URL`, fall back to the **local NIM** on the GPU VM (190) /
   `build.nvidia.com`, never to Ollama. (`_forced_selection_for_mode`,
   `get_backend_for_role` env-default branches.)
4. **Embedding role → Nemotron-Retriever** (§2.4), re-embedding migration (§4).
5. **Speech role → Nemotron-Speech**; **Safety role → Nemotron-Safety** pre-filter in
   the guardian path (without modifying protected `safety/guardian_agent.py` logic —
   wrap, don't edit).
6. **Decommission Ollama**: drop the `ollama` service from `docker-compose.yml`, retire
   `ollama_local_provider.py`, and update `.env.example` / `config/models.yaml` so
   `OLLAMA_*` are no longer referenced. Keep one release where `MYCA_BACKEND_MODE=llama`
   still works as an emergency rollback, then remove.

> **Infra note (read before changing ports):** today `resolve_nemotron_base_url()`
> defaults to `127.0.0.1:11434` — the **Ollama port** — because Nemotron has been
> running through Ollama's OpenAI-compatible shim. Per the VM table, real Nemotron
> serving belongs on the **GPU VM (190)** via NIM/vLLM. The cutover sets
> `NEMOTRON_BASE_URL=http://192.168.0.190:<nim_port>` and stops defaulting to 11434.
> **Do not** repurpose the MAS VM (188) Ollama port silently — that is exactly the
> class of cross-VM change CLAUDE.md warns about. Confirm the NIM port with infra and
> record it in `docs/SYSTEM_REGISTRY_FEB04_2026.md`.

### 2.4 Embeddings: Nemotron-Retriever
`mycosoft_mas/memory/embeddings.py` has `OpenAIEmbedder` (1536), `GeminiEmbedder`
(768), `LocalEmbedder` (384). Add a `NemotronRetrieverEmbedder` (NIM
`/v1/embeddings`, dimension per the chosen retriever variant) and make it the default
in `get_embedder()`. **Because TurboQuant is data-oblivious, the codec does not change
when the embedding dimension changes** — only the stored `dim` per collection.

### 2.5 Voice / multimodal
- `voice_v9/` currently routes STT→Whisper, TTS→ElevenLabs. Add **Nemotron-Speech**
  as a backend option behind the existing PersonaPlex bridge; keep ElevenLabs as a
  voice-style fallback initially.
- **Nemotron Nano Omni** powers vision/computer-use: MycoBrain camera frames, CREP
  dashboard screen reasoning, and lab document images — routed via a new `omni` role.

---

## 3. TurboQuant integration points in MAS

### 3.1 Vector memory (Qdrant) — primary win
Exploration found the storage paths:
- `mycosoft_mas/memory/semantic_memory.py` — Qdrant `semantic_facts`, COSINE, dim from
  embedder; `store_fact()` upsert, `query()` search.
- `mycosoft_mas/memory/myca_memory.py` — `QdrantSemanticIndex` (`myca_semantic_memory`),
  upsert L437–464, search L466–490.
- `mycosoft_mas/agents/memory_mixin.py` — `remember()`/`recall()` agent path.

Two deployment options:

**(A) Qdrant-native quantization (fastest to ship).** Qdrant supports scalar/binary
quantization in collection config. We can enable it immediately for a quick ~4× win,
but it is *not* TurboQuant (no random rotation, weaker recall on anisotropic data).
Use as a **bridge** while (B) is validated.

**(B) TurboQuant sidecar (the design target).** Store the compact `QuantizedVector`
(3-bit direction codes + 1-bit QJL sketch + fp16 norm + seed) in the Qdrant payload (or
a parallel pgvector `bytea` column), and keep Qdrant's HNSW over a **small QJL float
sketch** for ANN shortlisting. Re-rank the shortlist with `codec.score()`
(reconstruction). This is the `codec.rerank()` flow already implemented. Net: full
vectors no longer need to live in RAM at fp32.

Wiring (no protected files touched):
```python
from mycosoft_mas.memory.turboquant import TurboQuantCodec
codec = TurboQuantCodec(dim=embedder.dimension, bits=3)
qv = codec.encode(np.asarray(embedding))
payload["tq"] = {"norm": qv.norm, "codes": qv.direction_codes.tobytes(),
                 "sketch": qv.sketch_bits.tobytes(), "rot_dim": qv.rot_dim,
                 "seed": qv.seed}
```

### 3.2 Recommended path
Ship **(A)** behind a flag for an immediate footprint cut, run **(B)** in shadow mode on
`myca_semantic_memory`, compare recall on a labeled recall set, then promote (B).

### 3.3 Nemotron KV-cache lane
TurboQuant's headline use is KV-cache. When Nemotron is served on the GPU VM via
vLLM/NIM, enable KV quantization there (the serving layer owns the KV-cache, not this
repo). The existing `BackendSelection.cache_mode` / `serving_profile_id` /
`kvtc_artifact_id` fields are the hook: add a `cache_mode="turboquant_kv"` profile in
the serving/bundle manager so MAS can *select* a TurboQuant-KV serving lane per role.
This is where the **6× KV memory / longer context per GPU** materializes.

---

## 4. Rollout plan

| Phase | Action | Gate |
|-------|--------|------|
| **0. Land reference** *(this PR)* | Codec + tests + this design doc | tests green |
| **1. Nemotron shadow** | Stand up NIM on GPU VM 190; set `NEMOTRON_BASE_URL`; route `corporate` only (`MYCA_BACKEND_MODE_CORPORATE=nemotron`) | latency/accuracy parity |
| **2. Retriever + re-embed** | Add `NemotronRetrieverEmbedder`; dual-write embeddings; backfill | recall parity on labeled set |
| **3. TurboQuant memory (A→B)** | Qdrant quant flag, then TurboQuant sidecar shadow on `myca_semantic_memory` | recall ≥ fp32 − 2% |
| **4. Capability routing** | Nano (default) / Super (complex) / Ultra (frontier) / Omni (multimodal) / Speech / Safety | cost ↓, quality ≥ |
| **5. KV lane** | `turboquant_kv` serving profile on VM 190 | context length ↑, VRAM ↓ |
| **6. Decommission Ollama** | Default mode→`nemotron`; remove Ollama service/provider; keep 1 rollback release | 1 month stable |

Each phase is **env-flag gated and reversible** via `MYCA_BACKEND_MODE*`.

---

## 5. Risks & mitigations
- **Cross-VM port confusion** (Ollama 11434 vs NIM on 190): the #1 documented failure
  mode. Mitigation: explicit `NEMOTRON_BASE_URL`, registry update, no silent default
  reuse. **Confirm with infra before flipping defaults.**
- **Embedding dim change on re-embed:** dual-write + backfill, never in-place delete
  (CLAUDE.md: never delete data). TurboQuant itself is dim-agnostic.
- **Recall regression from 1-bit pre-filter:** always re-rank shortlist with
  `score()`; tune `sketch_dim`/`shortlist`. Two-stage recall measured ≥0.8.
- **Protected files:** Safety/guardian/orchestrator stay untouched — Nemotron-Safety is
  a *wrapper* pre-filter, not an edit to `safety/`.
- **Secrets:** `NEMOTRON_API_KEY` from env only; never committed.

---

## 6. Reference implementation (shipped in this PR)
- `mycosoft_mas/memory/turboquant.py` — `TurboQuantCodec` (PolarQuant + QJL),
  `randomized_rotation`, `PolarQuantizer`, `QJLSketch`, `QuantizedVector`,
  `encode/decode/score/estimate_inner_product/rerank/compression_ratio`. numpy-only,
  deterministic from seed, zero stored rotation/JL matrices.
- `tests/test_turboquant.py` — 8 tests: orthogonal+invertible rotation, reconstruction
  cosine, QJL unbiasedness, fp32 top-k recall (reconstruction), two-stage rerank on
  planted neighbors, compression ratio. **All passing.**

### Next code steps (follow-up PRs, per phase)
1. `NemotronRetrieverEmbedder` in `memory/embeddings.py` + default switch.
2. TurboQuant sidecar in `semantic_memory.py` / `myca_memory.py` upsert+query (flagged).
3. `omni`, `ultra` roles + Nemotron-default in `backend_selection.py` (reviewed config).
4. `turboquant_kv` serving profile in the serving/bundle manager.
5. New `core/routers/turboquant_api.py` exposing encode/recall stats for observability;
   register in `myca_main.py`; document in `API_CATALOG`.
6. Retire `ollama_local_provider.py` + docker-compose `ollama` service.

---

## 7. References
- Google Research — *TurboQuant: Redefining AI efficiency with extreme compression.*
- NVIDIA — *Nemotron* developer hub (Ultra/Super/Nano/Nano-Omni; Retriever/Parse/Speech/Safety).
- QJL: Zandieh et al., *1-bit Quantized Johnson–Lindenstrauss for KV-cache.*
- Internal: `docs/UNIFIED_LLM_ROUTING_NEMOTRON_MAR14_2026.md`,
  `docs/SYSTEM_REGISTRY_FEB04_2026.md`, `MEMORY.md`.
