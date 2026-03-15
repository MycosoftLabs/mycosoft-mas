# Plasticity Forge Phase 1 — Complete

**Date**: March 14, 2026  
**Status**: Complete  
**Related plan**: `.cursor/plans/plasticity_forge_phase1_616372f3.plan.md`

## Overview

Phase 1 of the Plasticity Forge is complete. The foundation loop for MYCA + AVANI evolutionary digital intelligence is implemented with real data paths, frozen contracts, registry-backed lineage, real evaluation, and alias-based promotion/rollback. Public AI/about-page marketing updates remain deferred to a follow-on phase after runtime verification in production.

## What Was Delivered

### 1. Contracts frozen
- **ExperiencePacket**, **WorldState**, **SelfState**, **CandidateGenome**, **FitnessProfile**, **PromotionPolicy** — canonical schemas and degraded-state policy.
- No-mock-backend-science rule enforced; replacements use real APIs, MINDEX records, or explicit degraded states.
- **Docs**: `docs/PLASTICITY_FORGE_CONTRACTS_FROZEN_MAR14_2026.md`, `docs/GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md`.

### 2. Mock backend science removed
- NLM trainer, MINDEX physics/knowledge routers, website model-training and NLM panel no longer use mock data; they use real MINDEX/ETL or explicit degraded responses.
- **Files**: `mycosoft_mas/nlm/training/trainer.py`, MINDEX routers, `app/natureos/model-training/page.tsx`, `components/fungi-compute/nlm-panel.tsx` (and related backend surfaces).

### 3. Ownership locked
- **AVANI governance**: MAS only (`avani_router.py`, `governance/avani_message_evaluate.py`).
- **NLM runtime**: MAS/NLM repo; persistence and candidate lineage in MINDEX; GPU shadow/canary on VM 190; Jetson edge consumer only.
- **Doc**: `docs/PLASTICITY_FORGE_OWNERSHIP_LOCKED_MAR14_2026.md`.

### 4. AVANI NLM real runtime
- Real telemetry translation, persistence (e.g. `nlm.nature_embeddings`), and trainer data from MINDEX; no placeholder training paths.
- **Doc**: `docs/AVANI_NLM_REAL_RUNTIME_MAR14_2026.md`.

### 5. Mutation engine v0
- Narrow operators: routing, retrieval, prompt/program policy, LoRA/adapters, reward tweaks, distillation, pruning, quantization.
- **Code**: `mycosoft_mas/plasticity/mutation_engine.py`; MAS API: branch/mutate flows under `/api/plasticity/*`.

### 6. Plasticity registry
- MINDEX: candidate, training_run, eval_run, promotion_decision, runtime alias state, rollback lineage.
- Registry-backed alias resolution; MAS integration client: `mycosoft_mas/integrations/plasticity_registry.py`.

### 7. Real eval plane
- Mock eval execution replaced with real API-driven evaluation against live MYCA/AVANI surfaces, grounded ExperiencePacket inputs, regression anchors, and catastrophic-forgetting defenses.
- **Code**: `mycosoft_mas/myca/evals/run_evals.py` (real runner; no MockAgentRunner).

### 8. Promotion control (shadow/canary/active/rollback)
- **Promotion controller**: `mycosoft_mas/plasticity/promotion_controller.py` — `promote_to_active(alias, candidate_id)`, `rollback(alias)`.
- **MAS API**: POST `/api/plasticity/promote` (body: `alias`, `candidate_id`, optional `decided_by`), POST `/api/plasticity/rollback` (body: `alias`, optional `decided_by`).
- Uses existing Nemotron role routing; alias and lifecycle stored in MINDEX plasticity registry; promotion decisions recorded for audit.

### 9. Fitness policy
- **Hard gates and Pareto ranking**: `mycosoft_mas/plasticity/fitness_policy.py` — `evaluate_fitness`, `passes_hard_gates`, `pareto_rank`, `fitness_profile_to_dict`.
- When `PLASTICITY_REQUIRE_FITNESS_GATES=1`, promote endpoint rejects candidates that fail hard gates (safety, groundedness, latency, memory, Jetson envelope).

### 10. Simulation factory
- **Deterministic eval scenarios**: `mycosoft_mas/plasticity/simulation_factory.py` — scenario types (telemetry_replay, anomaly_injection, tool_failure, contradictory_source, ecological_counterfactual, coding_task, control_task, missing_sensor), `SimulationScenario`, factories and `list_scenario_types` / `scenario_to_dict`.

### 11. Compression lane
- **Edge recipes and Jetson acceptance**: `mycosoft_mas/plasticity/compression_lane.py` — `CompressionRecipe`, `EdgeAcceptanceGate`, distillation/quantization/pruning recipes, `check_edge_acceptance`, `list_recipe_types`.

### 12. Security and governance sandbox
- **Sandbox checks**: `mycosoft_mas/plasticity/security_governance_sandbox.py` — `run_sandbox_check`, `sandbox_check_required`, secret detection, optional signed-artifact check (`PLASTICITY_REQUIRE_SIGNED_ARTIFACT=1`), approval-tier check.
- When `PLASTICITY_SANDBOX_CHECK=1`, promote endpoint runs sandbox check and returns 400 if it fails.

## Environment variables (plasticity)

| Variable | Default | Effect |
|----------|--------|--------|
| `PLASTICITY_REQUIRE_FITNESS_GATES` | 0 | If 1, promote rejects candidates that fail fitness hard gates. |
| `PLASTICITY_SANDBOX_CHECK` | 0 | If 1, promote runs security/governance sandbox and rejects on failure. |
| `PLASTICITY_REQUIRE_SIGNED_ARTIFACT` | 0 | If 1 (and sandbox enabled), candidate must pass signed-artifact check. |

## Verification

- **Contracts**: Schemas and grounding doc in place; no-mock rule applied across touched surfaces.
- **Registry**: MINDEX plasticity router and MAS plasticity client support candidates, aliases, promotion decisions.
- **Promotion**: POST `/api/plasticity/promote` and POST `/api/plasticity/rollback` call controller; 400/404 on invalid input.
- **Full loop**: Telemetry → grounding → evidence → genome registry → mutation → trainer → candidates → eval → fitness → promotion/rollback is implemented; end-to-end runtime proof in production is recommended as next step.

## Deferred to follow-on phase

- Public `/ai` and about-page marketing updates (after runtime verification).
- Structural plasticity (expert birth/death, MoE topology) — explicitly out of Phase 1.

## Registries updated

- **MASTER_DOCUMENT_INDEX.md**: This completion doc added under Plasticity Forge Phase 1 (Mar 14, 2026).
- **API_CATALOG_FEB04_2026.md**: Plasticity API section added (branch, mutate, promote, rollback, health).
- **SYSTEM_REGISTRY_FEB04_2026.md**: Phase 1 complete and promotion/rollback API noted.

## Related documents

- `docs/PLASTICITY_FORGE_CONTRACTS_FROZEN_MAR14_2026.md`
- `docs/PLASTICITY_FORGE_OWNERSHIP_LOCKED_MAR14_2026.md`
- `docs/AVANI_NLM_REAL_RUNTIME_MAR14_2026.md`
- `docs/GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md`
