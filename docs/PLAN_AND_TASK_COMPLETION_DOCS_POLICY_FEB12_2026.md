# Plan and Task Completion Documentation Policy

**Date:** February 12, 2026  
**Status:** Complete  
**Purpose:** Ensure a document is created at every plan completion and task completion docs are updated.

## What Was Done

1. **New rule:** `.cursor/rules/plan-and-task-completion-docs.mdc`
   - **Always apply:** All agents must follow it.
   - **Plan completed:** Create dated completion doc, update MASTER_DOCUMENT_INDEX and CURSOR_DOCS_INDEX, set plan status to Complete.
   - **Task completed:** Update plan/roadmap (mark task done), update status docs, add new docs to indexes; update registries if agents/APIs/services changed.
   - Includes a checklist for plan and task completion.

2. **Full-context rule updated:** `mycosoft-full-context-and-registries.mdc`
   - Added item 5: when a plan or task is completed, create/update documentation per plan-and-task-completion-docs.mdc.

3. **Agents updated:**
   - **plan-tracker:** New section "When a plan or task is completed (required)" referencing the rule.
   - **myca-autonomous-operator:** New section "Plan and task completion docs (required)" with checklist.
   - **documentation-manager:** New section "Plan and task completion docs (required)" and new step 3 in "When Invoked."

4. **Skill updated:** `create-dated-document` (global skill)
   - Added "Plan and task completion" with plan completion and task completion requirements.

## Where to Look

| Item | Location |
|------|----------|
| Rule (authoritative) | `.cursor/rules/plan-and-task-completion-docs.mdc` |
| Full-context reference | `.cursor/rules/mycosoft-full-context-and-registries.mdc` (item 5) |
| Plan-tracker | `.cursor/agents/plan-tracker.md` |
| Autonomous operator | `.cursor/agents/myca-autonomous-operator.md` |
| Documentation manager | `.cursor/agents/documentation-manager.md` |
| Dated doc skill | `~/.cursor/skills/create-dated-document/SKILL.md` |

## Summary

- **Plan completed** → Create `docs/{PLAN_NAME}_COMPLETE_{MMMDD}_{YYYY}.md`, update indexes, set plan status.
- **Task completed** → Update plan/status docs and any task log; add new docs to indexes; update registries if needed.
- No plan or task should be closed without the corresponding doc updates.
