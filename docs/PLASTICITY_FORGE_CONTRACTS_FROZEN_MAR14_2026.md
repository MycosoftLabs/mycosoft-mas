# Plasticity Forge Phase 1 — Contracts Frozen

**Date:** March 14, 2026  
**Status:** Canonical  
**Related:** `plasticity_forge_phase1_616372f3.plan.md`, `GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md`, `WORLDSTATE_CONTRACT_MAR14_2026.md`

---

## 1. Purpose

This document freezes the canonical contracts and policies for Plasticity Forge Phase 1. No implementation may contradict these contracts. Changes require a doc update and registry/index alignment.

---

## 2. Contract Summary

| Contract | Location | Owner / Use |
|----------|----------|-------------|
| **ExperiencePacket** | `schemas/experience_packet.py` | GroundingGate; all cognition input |
| **WorldState** | `consciousness/world_model.py` | WorldModel; full world snapshot |
| **WorldStateRef** | `schemas/experience_packet.py` | Attached to EP; lightweight ref |
| **SelfState** | `schemas/experience_packet.py` | SelfStateBuilder / StateService; MYCA internal snapshot |
| **CandidateGenome** | `schemas/plasticity_contracts.py` | Plasticity registry; model evolution lineage |
| **FitnessProfile** | `schemas/plasticity_contracts.py` | Eval plane; selection and promotion |
| **PromotionPolicy** | `schemas/plasticity_contracts.py` | Promotion controller; shadow/canary/active/rollback |

---

## 3. ExperiencePacket (existing — locked)

- **File:** `mycosoft_mas/schemas/experience_packet.py`
- **Fields:** `id`, `ground_truth`, `self_state`, `world_state`, `observation`, `uncertainty`, `provenance`, `event_boundary`, `episode_id`
- **Rule:** Every input (text/voice/sensor) entering MYCA's pipeline must be wrapped in an EP. No text or sensor input without an EP.
- **Validation:** Requires `self_state`, `world_state`, and `ground_truth.monotonic_ts` for grounded cognition (see GroundingGate.validate).

---

## 4. WorldState (existing — locked)

- **File:** `mycosoft_mas/consciousness/world_model.py`
- **Semantics:** Complete snapshot of MYCA's world perception (CREP, Earth2, NatureOS, MINDEX, device telemetry, NLM, EarthLIVE, presence). Per-source freshness and degraded flags as in WORLDSTATE_CONTRACT_MAR14_2026.md.
- **Owner:** WorldModel is the single writer; all sensors feed into it.

---

## 5. SelfState (existing — locked)

- **File:** `mycosoft_mas/schemas/experience_packet.py`
- **Fields:** `snapshot_ts`, `services`, `agents`, `active_plans`, `safety_mode`, `memory_indices`
- **Owner:** SelfStateBuilder or StateService; GroundingGate attaches to EP.

---

## 6. CandidateGenome (new — frozen)

- **File:** `mycosoft_mas/schemas/plasticity_contracts.py`
- **Purpose:** First-class record for every model evolution candidate. Lineage and rollback are derived from this.
- **Key fields:** `candidate_id`, `parent_candidate_ids`, `base_model_id`, `artifact_uri`, `mutation_operators_applied`, `data_curriculum_hash`, `training_code_hash`, `eval_suite_ids`, `eval_summary`, `safety_verdict`, latency/memory/watts, `jetson_compatible`, `lifecycle`, `rollback_target_candidate_id`, `alias`.
- **Lifecycle values:** `shadow`, `canary`, `active`, `rollback`, `archived`.
- **Rule:** Treat as immutable after creation; builder may set fields once.

---

## 7. FitnessProfile (new — frozen)

- **File:** `mycosoft_mas/schemas/plasticity_contracts.py`
- **Purpose:** Hard gates and soft (Pareto) objectives for candidate selection.
- **Hard gates (all must pass):** `safety_ok`, `provenance_complete`, `reproducible`, `regression_within_cap`, `hardware_envelope_ok`, `retention_above_threshold`.
- **Soft objectives (Pareto):** `task_success`, `groundedness`, `calibration`, `latency_score`, `memory_score`, `watts_score`, `retention_score`, `compression_ratio`, `edge_fitness`.
- **Joint MYCA + AVANI:** `myca_only_score`, `avani_only_score`, `joint_score` (optional).
- **Rule:** Reject if any hard gate fails; otherwise selection optimizes over soft objectives.

---

## 8. PromotionPolicy (new — frozen)

- **File:** `mycosoft_mas/schemas/plasticity_contracts.py`
- **Purpose:** Policy governing promotion from shadow/canary to active. Stored with promotion_decision in registry.
- **Key fields:** `policy_id`, `name`, `require_safety_verdict`, `require_min_canary_duration_seconds`, `require_min_eval_coverage`, `require_retention_above`, `require_regression_within_cap`, `require_approval_tier`.

---

## 9. Degraded-State Policy (canonical)

- **When data is partial or unavailable:** Sources in WorldState (and WorldStateRef) must set `degraded: true` and expose `freshness` and `staleness_reason` where applicable (see WORLDSTATE_CONTRACT_MAR14_2026.md).
- **UI and APIs:** Must show explicit degraded states with provenance and freshness; never substitute fake or mock data for missing data.
- **Eval and plasticity:** Candidates evaluated under degraded conditions must record which sources were degraded so that fitness and promotion decisions are interpretable.

---

## 10. No-Mock-Backend-Science Policy (canonical)

- **Rule:** No mock, fake, dummy, placeholder, or hardcoded sample data in any part of the Mycosoft system used for backend science, training, or evaluation.
- **Allowed:** Real backend API calls, real MINDEX database records, real ETL-backed derived facts, and explicit degraded states with provenance and freshness.
- **Forbidden:** Fake chemistry/physics/biology values, fake anomaly scores, fake training metrics, fake search categories, fake dashboards, and any simulated stats that are not clearly labeled as simulation for eval-only replay.
- **Replacement:** If an API or source is unavailable, show empty states or explicit "degraded" with reason; do not fall back to mock data.
- **Tests:** Test files may use fixtures; production code and production-facing APIs must not contain mock data.

---

## 11. File Reference

| File | Role |
|------|------|
| `schemas/experience_packet.py` | ExperiencePacket, SelfState, WorldStateRef, GroundTruth, Observation, Uncertainty, Provenance |
| `consciousness/world_model.py` | WorldState, WorldModel, DataFreshness |
| `consciousness/grounding_gate.py` | build_experience_packet, attach_self_state, attach_world_state, validate |
| `schemas/plasticity_contracts.py` | CandidateGenome, FitnessProfile, PromotionPolicy, CandidateLifecycle, MutationOperator |
| `docs/GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md` | Packet path and validation |
| `docs/WORLDSTATE_CONTRACT_MAR14_2026.md` | WorldState and WorldStateRef semantics |
