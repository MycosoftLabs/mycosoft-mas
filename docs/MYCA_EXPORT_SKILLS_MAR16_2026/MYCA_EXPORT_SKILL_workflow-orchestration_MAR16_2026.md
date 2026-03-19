# MYCA Export — Skill: Workflow Orchestration

**Export Date:** MAR16_2026  
**Skill Name:** workflow-orchestration  
**Purpose:** Execute non-trivial work using plan-first, verify-first, and lessons-fed defaults. Use when running 3+ step tasks, architectural work, or anything that may require re-planning.  
**External Systems:** Base44, Claude, Perplexity, OpenAI, Grok — load when user has multi-step or architectural tasks.

---

## Canonical Sources of Truth

| Purpose | Location | Role |
|---------|----------|------|
| Active work | `.cursor/plans/*.plan.md` | Primary plan ledger; mark todos here |
| Durable completion | `docs/{TITLE}_{MMMDD}_{YYYY}.md` | Completion docs; add to MASTER_DOCUMENT_INDEX |
| Optional todo mirror | `tasks/todo.md` (MAS repo) | Lightweight operational summary |
| Optional lessons | `tasks/lessons.md` (MAS repo) | Lessons learned; appended by pattern |

## Executable Checklist

```
Workflow Progress:
- [ ] 1. Plan (or load plan)
- [ ] 2. Verify the plan
- [ ] 3. Execute
- [ ] 4. Mark progress
- [ ] 5. Verify
- [ ] 6. Elegance review (non-trivial only)
- [ ] 7. Document results
- [ ] 8. Capture lessons (when applicable)
```

### 1. Plan (or load plan)

- For 3+ step tasks: create or load a plan. Use `plan-tracker` when invoking.
- Read `.cursor/CURSOR_DOCS_INDEX.md` and task-relevant docs. For new plans: read last 72 hours of docs.
- Identify sub-agents; read their `.cursor/agents/<name>.md` and apply their protocols.

### 2. Verify the plan

- Confirm scope, dependencies, and acceptance criteria are clear.
- Check for re-plan triggers: blockers, scope drift, or a cleaner approach available.
- If destabilized: stop and re-plan. Do not continue blindly.

### 3. Execute

- Work through plan todos in order. Mark `in_progress` as you start each.
- Use sub-agents for focused work. Keep one tack per subagent.
- Execute operations yourself—never ask the user to run commands.

### 4. Mark progress

- Update plan file: `- [x]` for completed todos.
- Update status docs if they list the task.
- If `tasks/todo.md` exists, sync completed items.

### 5. Verify

- **Never mark complete without evidence.** Run tests, check logs, verify runtime behavior.
- Use `terminal-watcher` for build/test output; `test-engineer` for test design; `regression-guard` for pre-deploy validation.

### 6. Elegance review (non-trivial only)

- For non-trivial changes: ask whether there is a more elegant approach.
- Do not over-engineer obvious, small fixes.

### 7. Document results

- Create dated completion doc: `docs/{PLAN_NAME}_COMPLETE_{MMMDD}_{YYYY}.md`.
- Add to MASTER_DOCUMENT_INDEX (and CURSOR_DOCS_INDEX if vital).
- Update plan source status to Complete. Link to completion doc.

### 8. Capture lessons (when applicable)

- After user corrections or repeated mistakes: capture the lesson.
- Feed into rules, agent guidance, or `tasks/lessons.md` so the same mistake is less likely to recur.

## Key Rules

- Plan mode by default for 3+ step tasks.
- Stop and re-plan when execution destabilizes.
- No task marked complete without proof.
- Use subagents aggressively for focused work.
- Execute operations yourself. Never hand work back to the user.
