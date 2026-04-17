# MYCA Harness

Integrates Nemotron (OpenAI-compatible HTTP, aligned with `get_backend_for_role(MYCA_CORE)` + env overrides), PersonaPlex bridge ASR/TTS, **MINDEX unified search-in-LLM** (`GET /api/mindex/unified-search` → Nemotron context), YAML static answers, turbo-quant telemetry placeholder, intention brain (SQLite under `data/harness/`), MINDEX HTTP + `record_execution`, optional Supabase REST, and NLM (optional, lazy imports).

## Quick use (Python)

```python
from mycosoft_mas.harness import HarnessEngine, HarnessPacket

engine = HarnessEngine()
import asyncio
asyncio.run(engine.run(HarnessPacket(query="Why use MDP v1 on devices?")))
```

## HTTP API

Routes mount **by default**. Disable with `HARNESS_API_DISABLED=1` if needed.

- `GET /api/harness/health`
- `POST /api/harness/packet` with JSON `HarnessPacket`

**Brain chat:** `POST /voice/brain/chat` with `{ "use_harness": true }` or env `BRAIN_CHAT_USE_HARNESS=1` routes the message through `HarnessEngine` (MINDEX-grounded Nemotron path) instead of the memory-integrated brain.

## STATIC answers

Copy `static_answers.example.yaml` to a writable path and set `HARNESS_STATIC_ANSWERS_PATH`.

## Turbo-quant

`HARNESS_ENABLE_TURBO_QUANT=1` logs compression ratio/time; replace internals under NDA.

## Tests

`pytest tests/test_harness_smoke.py tests/test_harness_api.py`
