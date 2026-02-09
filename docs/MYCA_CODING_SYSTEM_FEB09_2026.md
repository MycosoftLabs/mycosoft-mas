# MYCA Autonomous Coding System

**Date**: February 9, 2026
**Author**: Morgan / MYCA
**Status**: Complete

## Overview

MYCA can now write, modify, and deploy code autonomously using Claude Code running on the Sandbox VM (192.168.0.187). This gives MYCA the ability to create new agents, fix bugs, add API endpoints, write skills, and deploy changes -- all triggered from voice, the website, or the AI Studio.

## Architecture

```
Trigger (Voice/Web/API) -> Intent Classifier (coding category)
  -> Orchestrator -> CodingAgent
  -> SSH to VM 187 -> Claude Code CLI
  -> Git branch -> Code changes -> Tests -> Commit
  -> Optional deployment
```

## Components

### 1. CLAUDE.md (Project Rules)

Location: MAS repo root `CLAUDE.md`

Tells Claude Code everything about the Mycosoft system: 117+ agents, 200+ endpoints, BaseAgent patterns, safety rules, deployment procedures, and file locations.

### 2. Claude Code Subagents

Location: `.claude/agents/`

| Subagent | Purpose |
|----------|---------|
| agent-builder | Creates new MAS agents (BaseAgent/V2) |
| api-developer | Creates/modifies FastAPI endpoints |
| bug-fixer | Diagnoses and fixes bugs |
| deployer | Deploys to VMs (187/188/189) |
| test-runner | Runs tests and validates changes |
| skill-writer | Extends existing agent capabilities |

### 3. CodingAgent

Location: `mycosoft_mas/agents/coding_agent.py`

Methods added:
- `invoke_claude_code(task, repo, max_turns, budget)` -- SSH to VM, run `claude -p`
- `create_agent_via_claude(description)` -- Create new agent with safety
- `fix_bug_via_claude(error, files)` -- Fix bug with git checkpoint
- `create_endpoint_via_claude(description)` -- Create API endpoint
- `deploy_via_claude(target_vm)` -- Deploy to VMs
- `_execute_with_safety(type, prompt, repo)` -- Git branch + execute + audit

### 4. Coding API Endpoints

Location: `mycosoft_mas/core/routers/coding_api.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/coding/claude/task` | POST | General coding task |
| `/coding/claude/create-agent` | POST | Create new agent |
| `/coding/claude/fix-bug` | POST | Fix bug from error |
| `/coding/claude/create-endpoint` | POST | Create API endpoint |
| `/coding/claude/deploy` | POST | Deploy to VM |
| `/coding/claude/health` | GET | Claude Code availability |

### 5. Safety Hooks

Location: `scripts/validate-coding-command.sh`, `scripts/auto-lint.sh`

- PreToolUse: Blocks destructive commands (rm -rf, DROP TABLE, protected files)
- PostToolUse: Auto-lint after file edits

### 6. Intent Classifier Enhancement

Location: `mycosoft_mas/voice/intent_classifier.py`

Added patterns for: create agent, add endpoint, write skill, deploy changes, review code, modify agent.

## Safety Rules

1. Git branch created before every coding task
2. Tests run after every change
3. Protected files cannot be modified (orchestrator, guardian, security)
4. Destructive commands blocked by PreToolUse hook
5. Budget limit ($5 per task) prevents runaway costs
6. Turn limit (20) prevents infinite loops

## Usage Examples

### Voice
"MYCA, create a new agent that monitors disk space on all VMs"

### API
```bash
curl -X POST http://192.168.0.188:8001/coding/claude/create-agent \
  -H "Content-Type: application/json" \
  -d '{"description": "An agent that monitors disk space on all VMs and alerts when usage exceeds 80%"}'
```

### Self-Improvement
System Monitor detects recurring error -> Orchestrator submits fix_bug task -> CodingAgent invokes Claude Code -> Bug fixed automatically.

## VM Setup Required

On Sandbox VM (192.168.0.187):
1. Claude Code installed (already done)
2. Set `ANTHROPIC_API_KEY` environment variable
3. Push MAS repo code so CLAUDE.md and .claude/ are available
4. Test: `claude -p "What is this project?" --output-format json`

## Related Documents

- [SYSTEM_REGISTRY_FEB04_2026.md](./SYSTEM_REGISTRY_FEB04_2026.md) - Agent registry
- [API_CATALOG_FEB04_2026.md](./API_CATALOG_FEB04_2026.md) - API catalog
- [VOICE_AI_COMPLETE_SYSTEM_FEB04_2026.md](./VOICE_AI_COMPLETE_SYSTEM_FEB04_2026.md) - Voice system
