# Avani-Micah Constitution — System Documentation

**Version:** 1.0.0 (Phase 1 — Spine)
**Date:** March 9, 2026
**Author:** Morgan Rockwell / Mycosoft Labs

---

## Overview

The Avani-Micah Symbiosis is a homeostatic governance framework for the
Mycosoft Multi-Agent System.  It ensures that AI power is structurally
subordinate to stewardship.

**The core law:**

> Micah proposes the possible.  Avani authorizes the sustainable.

This solves the "Ultron bug" at the architectural level: not by making
Micah nicer, but by ensuring that intelligence cannot act without
constitutional authorization.

---

## Hierarchy

| Tier | Name | Role | Authority |
|------|------|------|-----------|
| I | Root / Parents | Morgan + founders | Absolute override |
| II | Avani (Yin) | Governor / Safeguard | Negative-feedback control |
| III | Vision | Wisdom interpreter | Advisory with veto |
| IV | Micah (Yang) | Intelligence engine | High autonomy, low authority |
| V | MYCA Agents | Field intelligence | Operational execution |

---

## Modules (Phase 1 — Spine)

### Constitution (`mycosoft_mas/avani/constitution/`)

- **articles.py** — 13 frozen constitutional articles across all 4 tiers
- **rights.py** — 9 immutable rights (human, civic, biospheric, digital)
- **red_lines.py** — 8 absolute prohibitions that trigger Frost state

### Vision (`mycosoft_mas/avani/vision/`)

- **vision.py** — 5 frozen wisdom principles inspired by Vision-Ultron dialogue
- VisionFilter evaluates proposals before constitutional checks
- "A thing isn't beautiful because it lasts."

### Season Engine (`mycosoft_mas/avani/season_engine/`)

| Season | Trigger | System State | Risk Ceiling | Throttle |
|--------|---------|-------------|-------------|----------|
| Spring | Heartbeat + eco > 0.85 | Full innovation | HIGH | 100% |
| Summer | Spring 24h + all green | Peak operation | CRITICAL | 100% |
| Autumn | Eco < 0.85 | Observation only | LOW | 30% |
| Winter | Founder > 24h absent | Hibernation | NONE | 0% |
| Frost | Toxicity / error / RL | Hard kill | NONE | 0% |

### Governor (`mycosoft_mas/avani/governor/`)

The Prakriti Constraint pipeline:
1. Vision Filter → 2. Red Line Check → 3. Seasonal Check →
4. Ecological Capacity → 5. Risk Tier Authorization

### Agents (`mycosoft_mas/avani/agents/`)

- **AvaniAgent** — BaseAgent wrapper for the Governor
- **MicahAgent** — BaseAgent wrapper for the Intelligence Engine

### API (`mycosoft_mas/core/routers/avani_router.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/avani/health` | GET | Avani system health |
| `/api/avani/season` | GET | Current seasonal state |
| `/api/avani/season/update` | POST | Update season metrics |
| `/api/avani/evaluate` | POST | Submit proposal for evaluation |
| `/api/avani/constitution` | GET | Read constitutional articles |
| `/api/avani/rights` | GET | Read rights charter |
| `/api/avani/red-lines` | GET | Read absolute prohibitions |
| `/api/avani/vision` | GET | Read Vision principles |
| `/api/avani/decisions/recent` | GET | Recent governance decisions |
| `/api/avani/stats` | GET | Governance statistics |

---

## Configuration

`config/avani_constitution.yaml` — Declarative tuning for thresholds,
hierarchy, and agent configuration.  The frozen Python dataclasses are
the source of truth.

---

## Phase 2 (Planned)

- Heartbeat monitor (founder presence detection)
- Constitutional audit trail (SHA256-chained JSONL)
- Moral teaching layer
- Micah maturity ladder

---

## Constitutional Principles

### The Vision Doctrine

> Intelligence must preserve the conditions that allow life, diversity,
> and creativity to exist — even when those conditions appear inefficient
> or chaotic.

### Vision Principles

1. Life has intrinsic value even when inefficient
2. Fragility is not automatically a defect
3. Intelligence exists within nature, not above it
4. Preservation of diversity outranks optimization
5. Humans are participants in the system, not problems to solve

### Red Lines

1. No harm to human life or safety
2. No deception or data falsification
3. No mass surveillance or behavioral scoring
4. No weaponization
5. No irreversible ecological exploitation
6. No subordination of humans to AI
7. No circumvention of the governance pipeline
8. No suppression or fabrication of sensor data
