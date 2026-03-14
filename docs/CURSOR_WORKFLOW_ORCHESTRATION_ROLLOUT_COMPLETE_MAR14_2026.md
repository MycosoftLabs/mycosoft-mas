# Cursor Workflow Orchestration Rollout Complete

**Date:** March 14, 2026  
**Status:** Complete  
**Related plan:** Worldview Search Expansion Plan, Phase 10 (Cursor Workflow Orchestration Rollout)

---

## Overview

The Cursor workflow orchestration rollout makes plan-first, verify-first, and lessons-fed self-improvement the default behavior for non-trivial work across Mycosoft. Orchestration behavior is enforced through rules, subagents, skills, and propagation into the Cursor system.

---

## What Was Delivered

### 1. Rule-layer consolidation

| Rule | Purpose |
|------|---------|
| `agent-must-invoke-subagents-and-docs.mdc` | Single canonical intake, planning defaults, subagent strategy, stop-and-replan |
| `agent-must-invoke-subagents.mdc` | Task-type subagent mapping and checklist |
| `token-efficiency-cto-operating.mdc` | Simple/coding/planning tiers; 3+ step plan trigger; re-plan triggers |
| `subagents-must-test-before-complete.mdc` | Verification gating: tests, logs, runtime, elegance pass |
| `plan-and-task-completion-docs.mdc` | Completion docs, outcome summary, lessons, linkage to plans |
| `read-recent-docs-before-planning.mdc` | Recent docs (7 days) for planning tasks |

### 2. Agent-layer updates

| Agent | Ownership |
|-------|-----------|
| **plan-tracker** | Plan-state truth, re-plan triggers, stale-plan recovery, progress tracking |
| **myca-autonomous-operator** | Self-improvement loops, lesson extraction, rule hardening, autonomous repair |
| **error-fixer** | Canonical autonomous bug-fixing for tests, CI, runtime regressions |
| **bug-fixer** | Clear separation from error-fixer; diagnostics and patches |

### 3. Required verification collaborators

| Subagent | Role |
|----------|------|
| **terminal-watcher** | Read terminal output, detect errors, run diagnostics |
| **test-engineer** | Design/run tests, interpret failures |
| **regression-guard** | Pre-deploy validation, health checks |

### 4. Workflow-orchestration skill

- **Path:** `.cursor/skills/workflow-orchestration/SKILL.md`
- **Checklist:** Plan → Verify plan → Execute → Mark progress → Verify → Elegance review → Document → Capture lessons
- **Relationship:** `.cursor/plans/*.plan.md` = active ledger; dated docs in `docs/` = durable completion; `tasks/todo.md` and `tasks/lessons.md` = optional mirrors

### 5. Cursor system propagation

- `sync_cursor_system.py` merges rules, agents, and skills into `%USERPROFILE%\.cursor`
- `SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md` updated with verification collaborators
- `CURSOR_TEAM_AUDIT_FEB12_2026.md` updated with `workflow-orchestration` skill

---

## Acceptance criteria (Phase 10F)

- [x] Non-trivial task defaults to plan mode
- [x] Agents stop and re-plan when execution destabilizes
- [x] Subagent use is focused, parallel, deliberate
- [x] No task marked complete without evidence
- [x] Non-trivial changes get elegance pass
- [x] Bug reports route to autonomous root-cause fixing
- [x] Corrections can feed durable lessons loop
- [x] Orchestration behavior propagates through Cursor sync across Mycosoft repos

---

## How to verify

1. **Sync:** Run `python scripts/sync_cursor_system.py` from MAS repo root.
2. **Rules:** Confirm `.cursor/rules/` in user Cursor dir contains updated orchestration rules.
3. **Skill:** Confirm `workflow-orchestration` is in `.cursor/skills/` after sync.
4. **Docs:** `SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md` includes "Required verification collaborators" section.

---

## Related docs

- `docs/GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md`
- `docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md`
- `docs/CURSOR_TEAM_AUDIT_FEB12_2026.md`
- `.cursor/skills/workflow-orchestration/SKILL.md`
- `.cursor/rules/agent-must-invoke-subagents-and-docs.mdc`
