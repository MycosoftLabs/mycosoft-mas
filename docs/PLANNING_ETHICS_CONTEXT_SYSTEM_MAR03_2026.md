# Planning Engine → Ethics System Context and Document System

**Date:** March 3, 2026  
**Status:** Specification  
**Related:** `docs/MYCA_ETHICS_PHILOSOPHY_BASELINE_MAR03_2026.md`, `docs/MYCA_ETHICS_TRAINING_SYSTEM_MAR04_2026.md`, `docs/michele_alignment_debate_outline.docx.md`

## Overview

The **planning engine** must inform the **ethics system** what context to hold for simulations, training source material, and ethics guidelines. A document system governs ethics system updates, training capabilities, and plans so the ethics pipeline (Truth Gate, Incentive Gate, Horizon Gate) operates with accurate, up-to-date context.

## Flow: Planning Engine → Ethics System

```
Plans / Simulations / Training Material
           │
           ▼
   ┌───────────────────┐
   │ Planning Engine   │
   │ (plan-tracker,    │
   │  gap-agent,       │
   │  roadmap plans)   │
   └─────────┬─────────┘
             │
             │ Context handoff:
             │ - Active simulations
             │ - Training source material (what data is used)
             │ - Ethics guidelines (which rules apply)
             │ - Plan scope (what the system is executing)
             │
             ▼
   ┌───────────────────┐
   │ Ethics System     │
   │ (EthicsEngine,    │
   │  Truth/Incentive/ │
   │  Horizon Gates,   │
   │  IncentiveAuditor)│
   └───────────────────┘
```

The planning engine produces **context documents** that the ethics system consumes. The ethics system uses this context to:

- **Truth Gate:** Ground fact-checks in known simulations and source material; flag when source data is incomplete or biased (per Michele alignment outline).
- **Incentive Gate:** Know which training scenarios and incentives apply to current plans.
- **Horizon Gate:** Align 10-year projection with plan scope and simulation boundaries.

## Document Types

### 1. Ethics System Update Documents

| Field | Purpose |
|-------|---------|
| **Location** | `docs/` (dated, e.g. `ETHICS_UPDATE_*.md`) |
| **Content** | New ethics rules, gate thresholds, constitution changes |
| **Consumers** | EthicsEngine, IncentiveAuditor, deliberation prompt |
| **Trigger** | When ethics philosophy, constraints, or instincts change |

Example: `docs/MYCA_ETHICS_PHILOSOPHY_BASELINE_MAR03_2026.md` documents the three-gate pipeline and constitution 9–12.

### 2. Training Capabilities Documents

| Field | Purpose |
|-------|---------|
| **Location** | `docs/`, `mycosoft_mas/ethics/scenarios/` |
| **Content** | Available scenarios, vessel stages, grading rubrics, source material provenance |
| **Consumers** | TrainingEngine, SandboxManager, ethics training API |
| **Trigger** | When new scenarios are added or training source material changes |

Example: `docs/MYCA_ETHICS_TRAINING_SYSTEM_MAR04_2026.md` and scenario YAML files.

### 3. Plan Documents (Planning → Ethics Context)

| Field | Purpose |
|-------|---------|
| **Location** | `.cursor/plans/`, `docs/` |
| **Content** | Active plans, simulations in use, training source material for a plan, applicable ethics guidelines |
| **Consumers** | Ethics system context injection; Truth Gate (source gaps), Horizon Gate (plan scope) |
| **Trigger** | When a plan is activated, updated, or completed |

**Required context fields for plans (for ethics handoff):**

| Field | Description |
|-------|-------------|
| `simulations` | Which simulations are running or referenced (e.g. Petri, Earth2, SecondOrderSimulator) |
| `training_source_material` | What data sources the plan uses (archives, MINDEX, CREP, etc.); provenance and known gaps |
| `ethics_guidelines` | Which ethics rules apply (constitution constraints, instincts, gate thresholds) |
| `plan_scope` | What the plan is executing; horizon and stakeholder boundaries |

## Epistemic Alignment (Michele Outline)

The document system and planning→ethics handoff must support **epistemic discipline** as defined in `docs/michele_alignment_debate_outline.docx.md`:

| Principle | Planning/Ethics Implementation |
|-----------|-------------------------------|
| **Model uncertainty** | Truth Gate and plan context expose source gaps, missing evidence, contested records |
| **Detect archival gaps** | Training source material documents provenance; flag when data is incomplete or winner-biased |
| **Represent competing interpretations** | Ethics guidelines and scenarios support multi-perspective reasoning, not single-verdict collapse |
| **Temporal/spatial/event reasoning** | Simulations (Petri, Earth2, SecondOrderSimulator) feed context; not language-only |
| **Adaptive intelligence alignment** | Ethics includes epistemic quality, not just safety; Clarity Brief and certainty-theater detection |

See `docs/michele_alignment_debate_outline.docx.md` for full debate-ready outline on epistemic vs. safety alignment, source bias, and grounded intelligence.

## Document Update and Indexing

| Action | Responsibility |
|--------|----------------|
| **Create/update ethics docs** | Documentation-manager, ethics-related agents |
| **Register in indexes** | Add to `docs/MASTER_DOCUMENT_INDEX.md` and `.cursor/CURSOR_DOCS_INDEX.md` when vital |
| **Notify ethics system** | When ethics update or training capability docs change, ethics engine should reload context (future: config-driven or API-triggered) |
| **Plan→ethics handoff** | Plan-tracker / planning engine produces context; ethics system reads plan docs for active scope |

## Implementation Notes

1. **Current state:** Ethics system (EthicsEngine, gates, IncentiveAuditor) is implemented; planning engine is distributed (plan-tracker agent, gap-agent, `.cursor/plans/`, roadmap docs). Explicit context handoff is not yet wired.
2. **Next steps:** Define a `PlanningContextForEthics` contract (e.g. JSON or structured doc) that plans must populate; ethics system reads it before evaluate/audit when plan context is relevant.
3. **Simulations as training material:** Petri, Earth2, SecondOrderSimulator, and ethics training scenarios are all simulation/training sources. Document which apply to which plans.
4. **Source material gaps:** Per Michele outline, document when training or plan data is incomplete, biased, or missing so Truth Gate can express uncertainty explicitly.

## Related Documents

- `docs/MYCA_ETHICS_PHILOSOPHY_BASELINE_MAR03_2026.md` – Three-gate pipeline, constitution, instincts
- `docs/MYCA_ETHICS_TRAINING_SYSTEM_MAR04_2026.md` – Sandbox scenarios, grading, Observer
- `docs/michele_alignment_debate_outline.docx.md` – Epistemic alignment, source bias, adaptive intelligence
- `docs/SYSTEM_REGISTRY_FEB04_2026.md` – Systems, APIs, agents
- `docs/API_CATALOG_FEB04_2026.md` – API catalog
