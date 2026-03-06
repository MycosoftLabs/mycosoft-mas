# Cowork vs MYCA Scope — March 7, 2026

**Status:** Documentation  
**Purpose:** Clarify when to use Claude Cowork vs MYCA to reduce duplication and confusion.  
**Related:** `docs/MYCA_SUPPORT_UPGRADE_AUDIT_MAR07_2026.md`

---

## Overview

Two systems handle automation and assistant-style work:

| System | Location | Purpose |
|--------|----------|---------|
| **Claude Cowork (PlotCore)** | Cowork VM | COO, Secretary, HR automations; hourly/daily tasks |
| **MYCA** | MAS VM 188, MYCA VM 191 | Conversational AI, orchestration, Morgan-facing interface |

## When to Use Each

### Use Cowork For

- **Scheduled automations**: Hourly work intake, daily digest, HR-related flows
- **PlotCore workflows**: Tasks that run on a fixed schedule without real-time chat
- **Standalone HR/COO flows**: When no MYCA context or conversation is needed

### Use MYCA For

- **Conversational interaction**: Morgan (or staff) chatting with MYCA
- **Real-time delegation**: "Do X", "Check Y", "Deploy Z"
- **Context-aware responses**: Memory, grounding, staff/task context
- **Approval flows**: MYCA proposes → Morgan confirms in chat

## Overlap and Duplication Risk

| Area | Cowork | MYCA | Recommendation |
|------|--------|------|----------------|
| Secretary tasks | Yes (scheduled) | SecretaryAgent exists | Cowork for cron; MYCA for ad-hoc |
| Daily digest | Yes | Can create via MAS | Prefer Cowork for scheduled; MYCA can request/trigger |
| Meeting scheduling | Cowork workflows | MYCA could delegate | MYCA→Cowork handoff when built |
| Task assignment | — | Executive, delegation | MYCA owns |

## Handoff Pattern (Future)

When MYCA needs to trigger a Cowork workflow:

1. MYCA decides action (e.g. "schedule meeting")
2. MYCA calls Cowork webhook or API
3. Cowork runs workflow
4. Result flows back to MYCA (or notification)

**Not yet implemented** — document when built.

## "Where Does Morgan Get Work Done?"

Today:

- **Cowork** — Some scheduled tasks, HR/COO automations
- **MYCA** — Chat, delegation, real-time assistance
- **Cursor** — Code, agents, development

**Goal**: Unified front door — Morgan interacts primarily with MYCA; MYCA orchestrates Cowork, Cursor, and other tools behind the scenes.

## Related

- `docs/COWORK_VM_CONTINUITY_MAR04_2026.md` — Cowork VM and watchdog  
- `docs/MYCA_FULL_OMNICHANNEL_EXECUTION_COMPLETE_MAR06_2026.md`  
- `scripts/install-cowork-vm-watchdog.ps1`  
