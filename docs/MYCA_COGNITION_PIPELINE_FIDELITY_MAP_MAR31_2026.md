# MYCA Cognition Pipeline Fidelity Map — MAR31 2026

Date: 2026-03-31  
Status: Baseline mapping for Nemotron migration

## Scope

Map brain, intention, memory, and consciousness paths that must preserve behavior while switching provider/model routing.

## Core Pipeline Components

- Brain orchestration:
  - `mycosoft_mas/myca/os/llm_brain.py`
  - `mycosoft_mas/consciousness/unified_router.py`
- Intention classification:
  - `mycosoft_mas/consciousness/intent_engine.py`
  - `mycosoft_mas/myca/os/turn_packet_builder.py`
- Memory and deliberation:
  - `mycosoft_mas/consciousness/working_memory.py`
  - `mycosoft_mas/consciousness/deliberation.py`
  - `mycosoft_mas/consciousness/world_model.py`
- Consciousness surface:
  - `mycosoft_mas/core/routers/consciousness_api.py`
  - `mycosoft_mas/consciousness/soul/*.py`

## Fidelity Requirements

1. **Intent stability**
   - Same prompt should keep intent class and confidence band within tolerance.

2. **Memory grounding integrity**
   - Retrieved context blocks remain attached to final answer path.

3. **Consciousness response structure**
   - `message`, `session_id`, emotional state fields remain compatible.

4. **Deliberation trace continuity**
   - Thought counters and routing telemetry are still produced under Nemotron.

## Gating Checks

- Compare Llama vs Nemotron outputs for representative prompts per category.
- Reject promotion if:
  - structured correctness falls below gate,
  - fallback rate exceeds gate,
  - intent drift exceeds acceptable threshold.

## Recommended Probe Sets

- Corporate decision prompt
- Infrastructure incident triage prompt
- Device troubleshooting prompt
- Route planning/orchestration prompt
- NLM retrieval-heavy prompt
- Consciousness introspection prompt

