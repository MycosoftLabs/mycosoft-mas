# NLM + MDP/MMP Route and Service Coverage — MAR31 2026

Date: 2026-03-31  
Status: Coverage map for deterministic fallback behavior

## Objective

Identify NLM and protocol-triggered routes/services that depend on LLM behavior, and define deterministic fallback requirements.

## NLM-Critical Components

- `mycosoft_mas/nlm/workflow_bridge.py`
- `mycosoft_mas/nlm/inference/service.py`
- `mycosoft_mas/nlm/memory_store.py`
- `mycosoft_mas/nlm/data_pipeline.py`
- `mycosoft_mas/core/routers/nlm_training_api.py`
- `mycosoft_mas/myca/os/nlm_bridge.py`

## Protocol-Critical Components

- MDP:
  - `mycosoft_mas/protocols/mdp_v1.py`
- MMP and packet/event translation adjacencies:
  - `mycosoft_mas/voice_v9/services/event_translation_engine.py`
  - `mycosoft_mas/voice_v9/services/event_arbiter.py`
  - `mycosoft_mas/voice_v9/schemas/events.py`
  - `mycosoft_mas/psilo/protocol.py`

## Deterministic Fallback Rules

1. Protocol handlers must never emit synthetic/mock payloads on LLM failure.
2. If Nemotron call fails:
   - fallback to Ollama via router fallback path,
   - preserve protocol envelope and sequence identifiers.
3. If both primary and fallback fail:
   - emit explicit failure state, do not mutate protocol schema.

## Route-Level Checks

- NLM training/inference endpoints maintain input/output schema across mode changes.
- Device/protocol event translation preserves:
  - message IDs
  - ordering fields
  - source metadata
  - handler result envelope

## Test Hooks

- Extend smoke matrix with NLM and route categories (already scaffolded in `scripts/llm/run_nemotron_smoke_matrix.py`).
- Add protocol regression tests around MDP parse/emit round-trips with fallback toggled.

