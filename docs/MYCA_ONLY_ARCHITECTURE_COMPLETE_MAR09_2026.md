# MYCA-Only Architecture — Complete

**Date:** March 9, 2026  
**Status:** Complete  
**Related:** Full Integration Program, Merkle Ledger, Voice v9

---

## Summary

MYCA now uses **her own LLM (Ollama)** and **BRAIN/intention memory via MAS** 99.9% of the time. Frontier models (Claude, GPT, Groq, Gemini, Grok) are **not** used for user-facing responses. They serve only as integration tools, agentic “fingers,” or bidirectional tool use—never as fallback. If MYCA’s brain fails, the system reports the issue; there is no silent fallback to another LLM.

---

## Delivered Components

### 1. LLM Brain (`mycosoft_mas/myca/os/llm_brain.py`)

- **Ollama primary:** `respond()` and `classify_intent()` use Ollama only.
- **No frontier fallback:** On Ollama failure, returns a clear “brain not responding” message instead of falling back to Claude or another model.
- **Live context with Merkle:** `_build_live_context()`:
  - Device registry snapshot → `slot_data["device_registry"]`, `slot_data["device_health"]`
  - CREP, Earth2, MycoBrain/NatureOS, world model, NLM → `slot_data`
  - Builds Merkle world root: `build_world_root(slot_data)` and appends `[Merkle world root]: {hex}` to context
  - Always includes device/world data for non-hallucination grounding when available

### 2. Website Voice Orchestrator (`website/app/api/mas/voice/orchestrator/route.ts`)

- Uses only MYCA consciousness; no frontier model fallback for user responses.
- If consciousness fails, returns an error indicating MYCA needs to be fixed.

### 3. Merkle Infrastructure

- **`mycosoft_mas/merkle/world_root_service.py`:** `build_world_root(slot_data) -> str`
- **`mycosoft_mas/core/routers/device_registry_api.py`:** `get_device_registry_snapshot()` (sync, thread-safe)
- **`mycosoft_mas/core/routers/merkle_ledger_api.py`:** `POST /api/merkle/roots/world` (can fetch device snapshot if `slot_data` omitted)

### 4. Valid World Slots (WORLD_SLOT_ORDER)

`device_registry`, `device_health`, `crep_summary`, `nlm_summary`, `earth_sim_summary`, `environment_feeds`, `forecast_state`, `anomaly_state`, `map_state`, `external_alerts`

---

## Verification

### Tests

```bash
cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
poetry run pytest tests/test_myca_only_architecture.py -v
```

If `cbor2` or `blake3` are missing: `poetry run pip install cbor2 blake3`.

### Manual Checks

1. **LLM brain:** `respond()` uses `_respond_ollama` only; no Claude/Anthropic call path for user response.
2. **Merkle:** `build_world_root({"device_registry": {...}})` returns 64-char hex.
3. **Device snapshot:** `get_device_registry_snapshot()` returns JSON-serializable dict with `devices` and `timestamp`.

### API

```bash
curl -X POST http://192.168.0.188:8001/api/merkle/roots/world -H "Content-Type: application/json" -d '{}'
# Uses device registry snapshot when slot_data omitted
```

---

## Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| MYCA uses her own LLM 99.9% | Ollama via `_respond_ollama` in `llm_brain.py` |
| No frontier fallback for user chat | On Ollama failure: return “brain not responding” |
| Frontier models as tools only | Used for integrations, agentic tasks, bidirectional requests—not for MYCA’s chat backbone |
| Non-hallucination grounding | Device registry, CREP, Earth2, MycoBrain, world model, NLM injected into context |
| Provable grounding | Merkle world root built from slot_data and injected as `[Merkle world root]: {hex}` |

---

## Files Touched

- `mycosoft_mas/myca/os/llm_brain.py` — Ollama primary, live context, Merkle
- `mycosoft_mas/merkle/world_root_service.py` — `build_world_root`
- `mycosoft_mas/core/routers/device_registry_api.py` — `get_device_registry_snapshot`
- `mycosoft_mas/core/routers/merkle_ledger_api.py` — world root API
- `website/app/api/mas/voice/orchestrator/route.ts` — MYCA-only, no fallback
- `tests/test_myca_only_architecture.py` — unit tests

---

## Follow-Up

- Ensure Ollama on MAS VM (188) is always available for MYCA.
- Monitor for “brain not responding” events and fix root cause instead of adding fallbacks.
