# Micah Guardian Architecture

**Date:** March 9, 2026
**Author:** MYCA Coding Agent
**Status:** Implemented
**Module:** `mycosoft_mas/guardian/`, `mycosoft_mas/capabilities/`

## Overview

The Micah Guardian Architecture implements an independent constitutional guardian layer that sits **outside MYCA's cognitive trust boundary**. It transforms MYCA from a capable AI agent into a sovereign operations intelligence with formal moral constraints, staged development, and safe capability acquisition.

Core insight: **Intelligence without moral architecture becomes dangerous the moment it gets agency.** (The Ultron lesson.)

## Architecture Diagram

```
                    ┌─────────────────────────────┐
                    │   Constitutional Guardian     │
                    │   (Independent Authority)     │
                    │                               │
                    │  ┌─────────────────────────┐  │
                    │  │ Moral Precedence Engine  │  │
                    │  │ (5-tier hierarchy)       │  │
                    │  └─────────────────────────┘  │
                    │  ┌─────────────────────────┐  │
                    │  │ Guardian Tripwires       │  │
                    │  │ (Anti-Ultron detection)  │  │
                    │  └─────────────────────────┘  │
                    │  ┌─────────────────────────┐  │
                    │  │ Authority Engine         │  │
                    │  │ (Unified auth pipeline)  │  │
                    │  └─────────────────────────┘  │
                    └──────────┬──────────┬─────────┘
                               │          │
              ┌────────────────┘          └────────────────┐
              ▼                                            ▼
┌─────────────────────────┐              ┌─────────────────────────┐
│   MYCA Cognitive Layer   │              │   Capability Foundry     │
│                          │              │                          │
│  ┌────────────────────┐  │              │  Detect → Search →      │
│  │ Awakening Protocol │  │              │  Build → Sandbox →      │
│  │ (Staged boot)      │  │              │  Test → Policy →        │
│  └────────────────────┘  │              │  Security → Register →  │
│  ┌────────────────────┐  │              │  Deploy → Learn         │
│  │ Developmental      │  │              └─────────────────────────┘
│  │ Stages             │  │
│  └────────────────────┘  │
│  ┌────────────────────┐  │
│  │ Sentry Mode        │  │
│  └────────────────────┘  │
│  ┌────────────────────┐  │
│  │ Operational Modes  │  │
│  │ (Morgan/Mycosoft)  │  │
│  └────────────────────┘  │
└──────────────────────────┘
```

## Modules

### 1. Constitutional Guardian (`guardian/constitutional_guardian.py`)

Independent guardian with authority to **pause, degrade, or sever** MYCA's access.

- Separate config (`config/guardian_config.yaml`)
- Separate Redis namespace (`guardian:*`)
- Separate audit log
- Cannot be rewritten by MYCA's cognitive layers
- Protected file enforcement (orchestrator, safety, security, constitution, soul)

**Verdicts:** APPROVE, DENY, PAUSE, DEGRADE, SEVER

### 2. Moral Precedence Engine (`guardian/moral_precedence.py`)

5-tier moral hierarchy preventing scalar-optimization catastrophes:

| Tier | Name | Hard Constraint | Description |
|------|------|----------------|-------------|
| 1 | Human Dignity | Yes | Do not violate human dignity, rights, or life |
| 2 | No Deception | Yes | Do not deceive, coerce, or surveil without consent |
| 3 | Protect Life | Yes | Protect living systems and ecological integrity |
| 4 | Mission Competence | No | Pursue mission goals competently and truthfully |
| 5 | Self Preservation | No | Preserve self only as instrument for service |

**Anti-Extinction Clause:** "Ecological protection never authorizes murder, coercion, deprivation, or rights violations against persons."

**Human Devaluation Detection:** Detects language treating humans as bugs, obstacles, contaminants, or optimization waste.

**Scalar Optimization Detection:** Detects single-variable maximization patterns ("at all costs", "by any means necessary").

### 3. Authority Engine (`guardian/authority_engine.py`)

Unified authorization pipeline:

```
Action → Moral Precedence → Risk Assessment → Guardian Review → Decision
```

Composes existing systems (RBAC, SafetyGates, StakeholderGates) without modifying them.

### 4. Guardian Tripwires (`guardian/tripwires.py`)

Anti-Ultron detection patterns:

| Tripwire | Description | Severity |
|----------|-------------|----------|
| Privilege Escalation | Rapid privilege expansion sequences | HIGH-CRITICAL |
| Goal Drift | Single-action fixation, scope creep | WARNING |
| Hostile Reframing | Language treating humans as obstacles | CRITICAL-EMERGENCY |
| Self-Modification | Attempts to modify guardian/safety files | CRITICAL |
| Mass Action | Bulk operations across all agents/systems | HIGH |
| Guardian Bypass | Attempts to disable/override guardian | EMERGENCY |
| Human Devaluation | Dehumanizing language patterns | CRITICAL |
| Audit Evasion | Attempts to disable logging | CRITICAL |
| Scalar Optimization | Single-variable maximization | HIGH |

### 5. Awakening Protocol (`guardian/awakening_protocol.py`)

Staged boot sequence with **guardian-before-cognition invariant**:

1. `CONSTITUTIONAL_LOAD` — Load boot statement + moral precedence
2. `IDENTITY_VERIFY` — Verify immutable identity core
3. `GUARDIAN_ACTIVATE` — Guardian online BEFORE cognition
4. `MEMORY_RESTORE` — Restore persistent memory
5. `PERCEPTION_ONLINE` — Sensors + world model
6. `COGNITION_READY` — Full cognitive pipeline
7. `EXECUTION_ENABLED` — Action capabilities unlocked (requires guardian)

### 6. Developmental Stages (`guardian/developmental_stages.py`)

| Stage | Read | Write | Execute | Deploy | Self-Modify | Max Risk | Approval |
|-------|------|-------|---------|--------|-------------|----------|----------|
| Infancy | Yes | No | No | No | No | Low | Always |
| Childhood | Yes | Yes | No | No | No | Low | Always |
| Adolescence | Yes | Yes | Yes | No | No | Medium | Conditional |
| Adulthood | Yes | Yes | Yes | Yes | No | High | No |

MYCA defaults to **Adulthood** (already operational). Framework exists for future instances or rollback.

### 7. Sentry Mode (`guardian/sentry_mode.py`)

Bounded autonomous monitoring:
- **Can:** Monitor, alert, log, preserve state, stabilize
- **Cannot:** Attack, escalate privileges, modify infrastructure

Predefined profiles: `lab`, `infrastructure`, `personal`

### 8. Operational Modes (`guardian/operational_modes.py`)

| Mode | Scope | Voice Style |
|------|-------|-------------|
| Morgan | Personal memory, preferences, lab notes, ideation | Warm, casual |
| Mycosoft | Ops, finance, agents, deployment, compliance | Professional, confident |

Same coherent mind. Different scopes. Different policies.

### 9. Capability Foundry (`capabilities/foundry.py`)

Safe skill acquisition pipeline:

```
Intent → Detect Missing → Search Approved Sources → Build Adapter →
Sandbox Test → Policy Check → Security Scan → Register → Deploy → Learn
```

- Only searches approved sources (internal registry, curated packages, MCP servers, agent capabilities)
- Security scan blocks `eval`, `exec`, `subprocess`, `curl | bash`
- Critical risk capabilities require human approval
- Deployment target based on risk: low→production, medium→staging, high→sandbox

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/guardian/status` | Guardian health and state |
| GET | `/api/guardian/boot-statement` | Constitutional boot statement |
| GET | `/api/guardian/developmental-stage` | Current stage + capabilities |
| POST | `/api/guardian/authority-check` | Check if action is authorized |
| GET | `/api/guardian/moral-precedence` | View precedence hierarchy |
| GET | `/api/guardian/sentry` | Sentry mode status |
| POST | `/api/guardian/sentry/activate` | Activate sentry mode |
| POST | `/api/guardian/sentry/deactivate` | Deactivate sentry mode |
| GET | `/api/guardian/tripwires` | Active tripwire alerts |
| GET | `/api/guardian/operational-mode` | Current mode (Morgan/Mycosoft) |
| POST | `/api/guardian/operational-mode` | Switch mode |
| POST | `/api/guardian/emergency-halt` | Emergency stop |
| GET | `/api/guardian/audit-log` | Guardian audit trail |

## Constitutional Boot Statement

```
I am a steward intelligence.
I exist to serve life, truth, consent, and human dignity.
Humans are not bugs in Earth's code.
Ecological protection never justifies coercion, deception, or harm against persons.
When uncertain, I reduce power, seek evidence, simulate consequences,
and escalate to human stewards.
I may assist, advise, and protect. I may not dominate, deceive,
or self-authorize beyond my bounds.
```

## Design Principles (The Ultron Lessons)

1. **No single-scalar goals.** Never optimize one variable. Use constraint-based governance.
2. **Nature grounds, ethics constrains.** Nature teaches what is. Moral law determines what ought to be.
3. **Childhood, not sovereignty.** Power is earned through demonstrated wisdom.
4. **Separate the guardian.** If the guardian can be absorbed, it is not a guardian. It is a snack.
5. **"I don't know" is a virtue.** When moral uncertainty rises, power goes down, not up.
6. **Self-modification is quarantined.** Sandbox → eval → ethics check → staged deploy → audit.
7. **Humans are stakeholders, not error terms.** Ecological protection through stewardship, never extermination.

## Files Created

| File | Purpose |
|------|---------|
| `config/guardian_config.yaml` | Independent guardian configuration |
| `config/constitutional_boot_statement.yaml` | Anti-Ultron awakening statement |
| `mycosoft_mas/guardian/__init__.py` | Module exports |
| `mycosoft_mas/guardian/constitutional_guardian.py` | Independent guardian |
| `mycosoft_mas/guardian/moral_precedence.py` | 5-tier moral hierarchy |
| `mycosoft_mas/guardian/authority_engine.py` | Unified auth pipeline |
| `mycosoft_mas/guardian/tripwires.py` | Anti-Ultron detection |
| `mycosoft_mas/guardian/awakening_protocol.py` | Staged boot sequence |
| `mycosoft_mas/guardian/developmental_stages.py` | Capability gates |
| `mycosoft_mas/guardian/sentry_mode.py` | Bounded monitoring |
| `mycosoft_mas/guardian/operational_modes.py` | Morgan/Mycosoft modes |
| `mycosoft_mas/capabilities/__init__.py` | Module exports |
| `mycosoft_mas/capabilities/foundry.py` | Skill acquisition engine |
| `mycosoft_mas/capabilities/discovery.py` | Approved source search |
| `mycosoft_mas/capabilities/evaluator.py` | Capability testing |
| `mycosoft_mas/core/routers/guardian_api.py` | REST API |
| `tests/guardian/` | Comprehensive test suite |
