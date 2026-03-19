# MYCA Export — Skill: Session Summarize

**Export Date:** MAR16_2026  
**Skill Name:** session-summarize  
**Purpose:** Compress long threads into a reusable handoff summary so new chats can continue with minimal context and lower token usage.  
**External Systems:** Base44, Claude, Perplexity, OpenAI, Grok — load when user asks to summarize or hand off a session.

---

## When to Use

Use this skill when:
- a thread is long (around 20+ messages),
- a task domain is switching (for example coding to deployment),
- user asks "summarize session", "start new thread", or "reduce context."

## Workflow

1. Produce a concise session summary with:
   - objective,
   - decisions made,
   - files changed,
   - tests run and outcomes,
   - blockers,
   - exact next steps.
2. Ask user to start a new thread.
3. Instruct user to paste the summary as the first message in the new thread.
4. Continue work from that summary only, loading only task-relevant context.

## Output Template

```markdown
## Session Summary

### Objective
- ...

### Decisions
- ...

### Files Changed
- `path/to/file`

### Validation
- command: result

### Blockers
- ...

### Next Steps
1. ...
2. ...
```

## Rules

- Keep summary precise and implementation-oriented.
- Do not include secrets.
- Prefer explicit file paths and concrete next commands.
