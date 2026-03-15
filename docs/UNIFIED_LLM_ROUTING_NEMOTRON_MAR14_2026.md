# Unified LLM Routing and Nemotron Integration — Design

**Date:** 2026-03-14  
**Status:** Design complete; implementation in progress  
**Related:** Nemotron MYCA Rollout plan, `config/models.yaml`, `llm/backend_selection.py`

## 1. Purpose

Route **all** MAS LLM entry points through a single backend-selection contract so that:

- Nemotron can be added as one first-class backend without leaving MAS “split-brained.”
- Model roles (MYCA core, edge, speech, safety, RAG) are defined in one place and consumed by LLMRouter, FrontierLLMRouter, and LLMBrain.

## 2. Current State (Three Uncoordinated Paths)

| Entry point | Location | How it picks model/backend today |
|------------|----------|-----------------------------------|
| **LLMRouter** | `llm/router.py` | Uses `LLMConfig` (models.yaml + env); `_select_provider()` + `_select_model()`; OpenAI-compatible + OpenAI + Azure. |
| **FrontierLLMRouter** | `llm/frontier_router.py` | Hardcoded sequence: Ollama → Gemini → Claude → OpenAI; no shared config. |
| **LLMBrain** | `myca/os/llm_brain.py` | Anthropic primary, Ollama fallback; `OLLAMA_URL` / `OLLAMA_MODEL` and `ANTHROPIC_API_KEY` only. |

**Memory brain** (`llm/memory_brain.py`) uses FrontierLLMRouter for voice/brain chat. Brain API (`core/routers/brain_api.py`) uses memory brain. So voice path is: bridge → brain API → memory brain → FrontierLLMRouter.

**Risks:** Adding Nemotron to only one of these keeps MYCA behavior inconsistent. All three must use the same contract for backend and model role selection.

## 3. Target: Single Backend-Selection Contract

### 3.1 Contract (programmatic)

- **Module:** `mycosoft_mas.llm.backend_selection`
- **API:**
  - `get_backend_for_role(role: ModelRole) -> BackendSelection`
  - `BackendSelection`: `provider: str`, `base_url: str`, `model: str`, `api_key: str` (optional)
  - `ModelRole`: enum or literal: `nemotron_super` | `nemotron_nano` | `nemotron_ultra` | `nemotron_speech` | `nemotron_safety` | `nemotron_rag` | `myca_core` | `myca_edge` | `planning` | `execution` | `fast` | `embedding` | `fallback`

Role semantics:

- **nemotron_super** — MYCA core reasoning (replaces current “primary” in brain/Frontier).
- **nemotron_nano** — Edge/device tasks; low latency.
- **nemotron_ultra** — Future high-depth tier (reserved).
- **nemotron_speech** — ASR/TTS adjunct (future).
- **nemotron_safety** — Safety/guardrails adjunct (future).
- **nemotron_rag** — RAG/retrieval embedding/rerank (future).
- **myca_core** — Alias for default MYCA path (today: Ollama or Nemotron super when configured).
- **myca_edge** — Alias for edge path (Nemotron nano when configured).
- Existing task types (**planning**, **execution**, **fast**, **embedding**, **fallback**) map to the same contract so LLMRouter can use it.

### 3.2 Configuration

- **config/models.yaml**
  - Add provider `nemotron` (OpenAI-compatible):
    - `base_url`, `model` (or per-role model names).
  - Add `model_roles` (or equivalent) mapping:
    - `myca_core` → `nemotron` / `nemotron-super` (or `local`/Ollama until Nemotron is deployed).
    - `myca_edge` → `nemotron` / `nemotron-nano`.
    - `nemotron_super`, `nemotron_nano`, `nemotron_ultra`, etc., to provider + model.
  - Keep existing `roles` (planning_model, execution_model, etc.) and, where applicable, point them at the same backend contract so one place controls “which backend for which role.”
- **Environment**
  - `NEMOTRON_BASE_URL` — OpenAI-compatible Nemotron endpoint (e.g. GPU node or NAS-served).
  - `NEMOTRON_MODEL_SUPER`, `NEMOTRON_MODEL_NANO`, etc. (optional overrides).

### 3.3 How Each Consumer Uses the Contract

1. **LLMRouter**
   - For each request, resolve task type (or explicit role) to `ModelRole`.
   - Call `get_backend_for_role(role)`.
   - If backend is `openai_compatible` / `nemotron`, use `OpenAICompatibleProvider` with returned `base_url` and `model`; otherwise use existing provider map.
   - Keep existing health/fallback logic, but preferred provider/model come from the contract.

2. **FrontierLLMRouter**
   - Replace hardcoded Ollama → Gemini → Claude → OpenAI with:
     - Primary: `get_backend_for_role("myca_core")` (or `nemotron_super` when Nemotron is primary).
     - Fallback: same contract’s fallback list (e.g. gemini, claude, openai) or contract-defined fallback role.
   - So “frontier” becomes “best available from the unified contract” instead of a separate sequence.

3. **LLMBrain**
   - Replace direct Anthropic + Ollama with:
     - Primary: `get_backend_for_role("myca_core")` (or `nemotron_super`).
     - Fallback: contract’s fallback for that role (e.g. ollama, then anthropic if configured).
   - Use returned `base_url` + `model` with an OpenAI-compatible client when provider is `openai_compatible`/`nemotron`.

4. **Memory brain**
   - No direct backend choice; it uses FrontierLLMRouter. So once FrontierLLMRouter uses the contract, memory brain and brain API automatically use the unified routing.

## 4. Nemotron Model Roles (Summary)

| Role | Purpose | Default model (when Nemotron deployed) |
|------|---------|--------------------------------------|
| nemotron_super | MYCA core, voice brain, chat | e.g. nemotron-super or config |
| nemotron_nano | Edge, device, low latency | e.g. nemotron-nano |
| nemotron_ultra | Future high-depth | Reserved |
| nemotron_speech | ASR/TTS | Future |
| nemotron_safety | Guardrails | Future |
| nemotron_rag | Embedding/rerank | Future |

Until Nemotron is deployed, `myca_core` can still resolve to Ollama (or existing local_first) so behavior stays unchanged.

## 5. Implementation Notes

- **backend_selection.py**: Load from `config/models.yaml` and env; expose `get_backend_for_role(role)` and `BackendSelection`; support role aliases (e.g. `myca_core` → nemotron_super or current default).
- **models.yaml**: Add `nemotron` provider and `model_roles` (or extend `roles`) for Nemotron and myca_core/myca_edge.
- **LLMRouter**: In `_select_provider` / `_select_model`, optionally use `get_backend_for_role(task_type)` when a role is requested; otherwise keep current behavior during transition.
- **FrontierLLMRouter**: Refactor to call `get_backend_for_role("myca_core")` for primary and contract fallbacks for secondary.
- **LLMBrain**: Refactor to use `get_backend_for_role("myca_core")` and contract fallback instead of hardcoded Anthropic + Ollama.

No change to Brain API or memory brain beyond the fact that they use the routers that now go through the contract.

## 6. Files to Touch

| File | Change |
|------|--------|
| `config/models.yaml` | Add nemotron provider; add model_roles (or roles) for Nemotron and myca_core/myca_edge. |
| `mycosoft_mas/llm/backend_selection.py` | New: contract implementation, `get_backend_for_role()`, `BackendSelection`, `ModelRole`. |
| `mycosoft_mas/llm/config.py` | Optional: load model_roles; or backend_selection loads models.yaml directly. |
| `mycosoft_mas/llm/router.py` | Use backend_selection for provider/model when role is given or task type maps to role. |
| `mycosoft_mas/llm/frontier_router.py` | Use get_backend_for_role("myca_core") and contract fallbacks. |
| `mycosoft_mas/myca/os/llm_brain.py` | Use get_backend_for_role("myca_core") and contract fallback. |

This design delivers a unified Nemotron-capable model-routing layer and specifies how LLMRouter, FrontierLLMRouter, and LLMBrain all use the same backend-selection contract.
