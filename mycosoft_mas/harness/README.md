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

Enable with `HARNESS_API_ENABLED=1` on MAS. Then:

- `GET /api/harness/health`
- `POST /api/harness/packet` with JSON `HarnessPacket`

## STATIC answers

Copy `static_answers.example.yaml` to a writable path and set `HARNESS_STATIC_ANSWERS_PATH`.

## Turbo-quant

`HARNESS_ENABLE_TURBO_QUANT=1` logs compression ratio/time; replace internals under NDA.

## Tests

`pytest tests/test_harness_smoke.py`
