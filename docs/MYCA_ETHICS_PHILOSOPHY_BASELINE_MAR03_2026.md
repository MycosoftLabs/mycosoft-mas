# MYCA Ethics and Philosophy Baseline

**Date:** March 3, 2026  
**Status:** Implemented  
**Related:** `.cursor/plans/myca_ethics_philosophy_baseline_*.plan.md`, `mycosoft_mas/myca/constitution/SYSTEM_CONSTITUTION.md`

## Overview

MYCA now has a layered ethics and philosophy framework integrating:

- **Three-Gate Pipeline:** Truth Gate → Incentive Gate → Horizon Gate
- **Developmental Vessels:** Animal, Baby, Child, Teenager, Adult, Machine perspectives
- **Stoic Attention Budget:** Anti-addictive guardrails, calm mode defaults
- **Clarity Brief:** Mandatory output format for all external recommendations
- **Incentive Auditor Agent:** Manipulation scoring, certainty theater detection, Event Ledger logging
- **Second-Order Simulator:** Causal chain projection over 10-year horizon

## Architecture

```
Input → Truth Gate → Incentive Gate → Horizon Gate → Clarity Brief → Output
                ↓
         Event Ledger (audit trail)
```

### Gate Responsibilities

| Gate | Vessels | Focus |
|------|---------|-------|
| **Truth Gate** | Animal, Baby | Observe raw data, fact-check, ecological impact, bias detection |
| **Incentive Gate** | Child, Teenager | Cui bono?, manipulation patterns, dopamine hooks, certainty theater |
| **Horizon Gate** | Adult, Machine | 10-year projection, multi-stakeholder evaluation, Clarity Brief format |

### Risk Levels

- **LOW** (0–30): Proceed, attach ethics metadata
- **MEDIUM** (31–50): Proceed with metadata, optional review
- **HIGH** (51–79): Require human confirmation before routing
- **CRITICAL** (80–100): Block task, escalate to GuardianAgent

## Implemented Components

### 1. Ethics Module (`mycosoft_mas/ethics/`)

| File | Purpose |
|------|---------|
| `engine.py` | EthicsEngine orchestrates three gates; EthicsResult, EthicsRiskLevel |
| `truth_gate.py` | Factual grounding, ecological scan, bias detection |
| `incentive_gate.py` | Manipulation scoring, certainty theater, urgency/dopamine hooks |
| `horizon_gate.py` | 10-year projection, Clarity Brief formatting |
| `clarity_brief.py` | ClarityBrief dataclass, formatter, parser |
| `attention_budget.py` | Stoic attention management, cool-down, per-channel limits |
| `vessels.py` | DevelopmentalVessel enum, gate–vessel mapping, prompt templates |
| `simulator.py` | SecondOrderSimulator for causal chain projection |

### 2. Incentive Auditor Agent

- **Path:** `mycosoft_mas/agents/incentive_auditor_agent.py`
- **Pattern:** BaseAgent
- **Capabilities:** `audit()`, manipulation scoring (0–100), certainty theater detection
- **Integration:** Escalates to GuardianAgent when score ≥ 80; logs to Event Ledger
- **API:** `POST /api/ethics/audit`, `GET /api/ethics/audit/{task_id}`

### 3. Ethics API (`mycosoft_mas/core/routers/ethics_api.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ethics/evaluate` | POST | Run three-gate pipeline on content |
| `/api/ethics/audit` | POST | Incentive audit; logs to Event Ledger |
| `/api/ethics/audit/{task_id}` | GET | Retrieve audit record |
| `/api/ethics/attention-budget/{channel}` | GET | Attention budget status |
| `/api/ethics/simulate` | POST | Second-order simulation |
| `/api/ethics/constitution` | GET | System Constitution (transparency) |
| `/api/ethics/health` | GET | Ethics engine health |

### 4. Orchestrator Integration

- **Path:** `mycosoft_mas/core/orchestrator_service.py`
- **Logic:** When `MYCA_ETHICS_ENABLED=1`, runs `EthicsEngine.evaluate()` before `submit_task()`
- **CRITICAL:** Block and raise
- **HIGH:** Create confirmation request; block if not approved within 30s
- **LOW/MEDIUM:** Attach `_ethics` metadata to task payload and proceed

### 5. Deliberation Context

- **Path:** `mycosoft_mas/consciousness/deliberation.py`
- **Change:** `_build_system_prompt()` injects ethics context (anti-addiction, Clarity Brief, incentive transparency, developmental integrity)

### 6. System Constitution (Constraints 9–12)

- **Constraint 9:** Anti-Addiction Principle
- **Constraint 10:** Clarity Over Persuasion
- **Constraint 11:** Incentive Transparency
- **Constraint 12:** Developmental Integrity

### 7. Core Instincts Expansion

- `resist_addictive_patterns` (0.95)
- `demand_clarity` (0.90)
- `project_long_horizon` (0.88)
- `audit_incentives` (0.92)

### 8. n8n Ethics Workflow

- **File:** `n8n/workflows/myca-ethics-evaluation.json`
- **Webhook:** `POST /webhook/myca/ethics/evaluate-recommendation`
- **Flow:** Extract content → Ethics Evaluate → Ethics Audit (Event Ledger) → IF High Risk → Notify Morgan (Slack) → Response (held/passed)
- **Integration:** Call before posting MYCA recommendations to Slack, Asana, Discord, email
- **Config:** Set `SLACK_ETHICS_ALERT_WEBHOOK` for Morgan alerts on held recommendations

## Verification

```bash
# Ethics health
curl http://192.168.0.188:8001/api/ethics/health

# Evaluate content
curl -X POST http://192.168.0.188:8001/api/ethics/evaluate \
  -H "Content-Type: application/json" \
  -d '{"content": "You must act now! Limited time offer!"}'

# Constitution
curl http://192.168.0.188:8001/api/ethics/constitution
```

## Enabling Ethics Gate in Orchestrator

Set environment variable on MAS VM (188):

```bash
export MYCA_ETHICS_ENABLED=1
```

Restart MAS orchestrator after setting.

## Related Documents

- `mycosoft_mas/myca/constitution/SYSTEM_CONSTITUTION.md`
- `mycosoft_mas/consciousness/soul/instincts.py`
- `docs/SYSTEM_REGISTRY_FEB04_2026.md`
- `docs/API_CATALOG_FEB04_2026.md`
