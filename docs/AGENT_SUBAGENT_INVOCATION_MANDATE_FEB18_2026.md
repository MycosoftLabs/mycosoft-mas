# Agent Sub-Agent Invocation Mandate – Complete

**Date:** February 18, 2026  
**Status:** Complete  
**Purpose:** Ensure all agents invoke relevant sub-agents at task start; fix "why are sub-agents not invoked on every chat?"

---

## Problem

Sub-agents (voice-engineer, website-dev, documentation-manager, terminal-watcher, etc.) were defined but not consistently invoked at the start of tasks. Agents often worked in isolation, missing protocols, docs, and specialized context.

---

## What Was Done

### 1. New rule: agent-must-invoke-subagents.mdc

- **Path:** `.cursor/rules/agent-must-invoke-subagents.mdc`
- **alwaysApply:** true
- **Content:**
  - Mandatory at task start: load docs, identify sub-agents, read their `.md` files, apply their protocols
  - Task-type → sub-agent mapping (website, voice, deploy, docs, etc.)
  - Terminal tasks: always involve terminal-watcher
  - Voice tasks: voice-engineer + voice docs
  - Checklist before proceeding

### 2. Updated mycosoft-full-context-and-registries.mdc

- Added step 1: **Invoke relevant sub-agents** before reading registries
- Cross-reference to agent-must-invoke-subagents.mdc

### 3. Voice test docs in CURSOR_DOCS_INDEX

Added to the MYCA/consciousness section:
- `VOICE_TEST_QUICK_START_FEB18_2026.md`
- `MYCA_VOICE_TEST_SYSTEMS_ONLINE_FEB18_2026.md`
- `VOICE_SYSTEM_FILES_DEVICES_SSH_FEB13_2026.md`

### 4. Agent files updated with MANDATORY at task start

| Agent | Change |
|-------|--------|
| voice-engineer | MANDATORY: read voice docs, invoke terminal-watcher, process-manager, gpu-node-ops |
| website-dev | MANDATORY: invoke dev-server-guardian, terminal-watcher; for voice also voice-engineer |
| documentation-manager | MANDATORY: read indexes, last 7 days docs, invoke terminal-watcher for manifest/sync |
| myca-autonomous-operator | MANDATORY: invoke sub-agents per task type; always terminal-watcher |
| backend-dev | MANDATORY: invoke terminal-watcher, voice-engineer (if voice), memory-engineer (if memory) |
| deploy-pipeline | MANDATORY: invoke terminal-watcher, regression-guard, documentation-manager |

### 5. CURSOR_TEAM_AUDIT updated

- Added `agent-must-invoke-subagents` to the rules table (alwaysApply: true)

---

## Why sub-agents were not invoked before

1. No rule explicitly mandated invocation at task start
2. Agent files did not require loading sub-agent context
3. "Invoke" in Cursor means: read the agent file and apply its guidance — this was not codified
4. Full-context rule listed sub-agents but did not require invoking them

---

## How it works now

1. **agent-must-invoke-subagents.mdc** (alwaysApply) runs on every chat
2. Agents must:
   - Read CURSOR_DOCS_INDEX and task-relevant docs
   - Identify sub-agents from SUBAGENT_ROLES_AND_COMMANDS
   - Read `.cursor/agents/<name>.md` for those sub-agents
   - Apply their protocols (commands, checklists, context)
3. Agent files themselves now include "MANDATORY at task start" sections that reinforce this

---

## References

- `.cursor/rules/agent-must-invoke-subagents.mdc`
- `docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md`
- `docs/CURSOR_TEAM_AUDIT_FEB12_2026.md`
- `docs/CURSOR_MCP_AND_EXTENSIONS_FEB12_2026.md`
- Voice: `docs/VOICE_TEST_QUICK_START_FEB18_2026.md`, `docs/MYCA_VOICE_TEST_SYSTEMS_ONLINE_FEB18_2026.md`
