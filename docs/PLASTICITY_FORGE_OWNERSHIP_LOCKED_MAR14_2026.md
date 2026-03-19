# Plasticity Forge Phase 1 — Source-of-Truth Ownership Locked (Mar 14, 2026)

**Status:** Locked  
**Related:** Plasticity Forge Phase 1 plan, `docs/PLASTICITY_FORGE_CONTRACTS_FROZEN_MAR14_2026.md`, `docs/GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md`

## Purpose

This document is the single source of truth for **who owns what** in the MYCA + AVANI + NLM + Plasticity Forge stack. No component may drift into another’s ownership without an explicit, documented decision.

## Canonical Ownership

| Concern | Owner | Location / boundary | Notes |
|--------|--------|----------------------|--------|
| **AVANI governance** | MAS | `mycosoft_mas/core/routers/avani_router.py`, `mycosoft_mas/governance/avani_message_evaluate.py` | Ingress, evaluation, and constitutional governance live in MAS only. |
| **NLM runtime (model service)** | MAS/NLM repo | `MAS/NLM/nlm/api/main.py`, `NLM/nlm/client.py`, `NLM/nlm/telemetry/translation_layer.py` | The dedicated NLM repo is the **real** model-service boundary. MAS exposes compatibility surfaces (proxy/alias) only. |
| **Persistence & candidate lineage** | MINDEX | VM 192.168.0.189, MINDEX API 8000, Postgres/Redis/Qdrant; training runs, evals, embeddings, lineage, worldview facts, answer provenance | All durable state for training, evals, and model lineage lives in MINDEX. |
| **GPU shadow/canary serving** | VM 190 (GPU node) | 192.168.0.190 | Heavier candidate serving and shadow/canary evals run on the GPU node. MAS holds stable aliases; promotion control stays in MAS. |
| **Jetson** | Edge consumer only | 192.168.0.123 (Jetson device) | Phase 1: Jetson is an **edge inference/collection target** only. Not a promotion authority, not a training host. |
| **Orchestrator / identity / proxy** | MAS | `mycosoft_mas/core/myca_main.py`, `mycosoft_mas/core/routers/nlm_api.py`, `mycosoft_mas/myca/os/nlm_bridge.py` | MAS orchestrates, proxies to NLM when `NLM_API_URL` is set, and owns live alias resolution. No forking of NLM logic into MAS. |

## Boundaries That Must Not Blur

1. **AVANI**  
   - All governance and message evaluation: **MAS only**. No duplicate AVANI brain in NLM or website.

2. **NLM**  
   - Real model runtime and telemetry translation: **MAS/NLM repo** (and, when deployed, NLM service on 188 or 190).  
   - MAS provides **compatibility surfaces**: `/api/nlm/*` (health, status, predict, translate, training/status) either in-process or by proxying to `NLM_API_URL`. New NLM logic (e.g. new prediction types, new translation steps) belongs in the NLM repo, not in MAS.

3. **Persistence**  
   - Training runs, eval runs, candidate genome, promotion decisions, lineage: **MINDEX only**. MAS and NLM consume MINDEX; they do not become the source of truth for durable training/lineage state.

4. **Promotion / alias**  
   - Promotion authority and alias state (shadow, canary, active, rollback): **MAS** (e.g. `config/models.yaml`, `mycosoft_mas/llm/backend_selection.py`), with registry-backed control to be added in Phase 1. GPU node (190) runs candidates; MAS holds the alias and promotion control.

5. **Jetson**  
   - Phase 1: **Edge consumer only**. No training, no promotion authority, no NLM training host on Jetson.

## VM and URL Topology

- **MAS:** 192.168.0.188:8001  
- **MINDEX:** 192.168.0.189:8000  
- **NLM service (when deployed):** `NLM_API_URL` (e.g. http://192.168.0.188:8200 or http://192.168.0.190:8200)  
- **GPU node:** 192.168.0.190 (shadow/canary serving; optional NLM service)  
- **Jetson:** 192.168.0.123 (edge only)

Clients (including MAS and website) must use these boundaries: MINDEX for persistence, NLM_API_URL for the real NLM service when configured, MAS for AVANI and alias/promotion.

## Verification

- AVANI: All ingress paths that require governance call MAS AVANI (avani_router / avani_message_evaluate).  
- NLM: Standalone NLM service is implemented in `MAS/NLM`; MAS nlm_api is compatibility/proxy only.  
- MINDEX: Training/eval/lineage and worldview persistence live in MINDEX VM and API.  
- Jetson: Documented and used only as edge inference/collection in Phase 1.

## References

- Plan: `.cursor/plans/plasticity_forge_phase1_616372f3.plan.md`  
- Contracts: `docs/PLASTICITY_FORGE_CONTRACTS_FROZEN_MAR14_2026.md`  
- VM layout: `docs/VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md`  
- System registry: `docs/SYSTEM_REGISTRY_FEB04_2026.md`
