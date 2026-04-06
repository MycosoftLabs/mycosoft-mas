# MINDEX LLM Persistence and Retrieval Metadata Map — MAR31 2026

Date: 2026-03-31  
Status: Planned contract for Nemotron migration observability

## Objective

Ensure MINDEX-linked retrieval and persistence flows retain provenance when backend switches between Nemotron and Ollama fallback.

## Required Metadata Contract

For every persisted MYCA/NLM inference event, append:

- `llm_provider` (e.g. `nemotron`, `ollama`)
- `llm_model` (resolved model ID)
- `backend_mode` (`hybrid`, `nemotron`, `llama`)
- `role_category` (`corporate`, `infra`, `device`, `route`, `nlm`, `consciousness`)
- `fallback_used` (boolean)
- `fallback_reason` (nullable string)
- `latency_ms` (numeric)
- `timestamp_utc` (ISO timestamp)

## Current Anchors

- Routing telemetry source:
  - `mycosoft_mas/llm/router.py`
  - `mycosoft_mas/llm/backend_selection.py`
- MINDEX and world-state adjacencies:
  - `mycosoft_mas/consciousness/sensors/mindex_sensor.py`
  - `mycosoft_mas/core/routers/worldstate_api.py`
  - `mycosoft_mas/nlm/workflow_bridge.py`
  - `mycosoft_mas/nlm/memory_store.py`

## Persistence Plan

1. **Router telemetry first**
   - Use `raw_response.routing` as canonical source for provider/model/mode/fallback.

2. **Pipeline adapters**
   - NLM bridge and world-state persistence paths must pass telemetry fields unchanged.

3. **Schema-safe rollout**
   - Add nullable columns/fields first.
   - Backfill from existing logs where possible.
   - Enforce non-null only after all writers are updated.

4. **Read-path parity**
   - Retrieval APIs should expose provenance for analysis dashboards and cutover audits.

## Validation Queries (Target)

- Fallback rate by category over 24h.
- p95 latency by provider/model over 24h.
- Share of requests by backend mode and category.
- Error-rate split by provider.

