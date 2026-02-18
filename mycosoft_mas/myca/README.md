# MYCA Self-Improvement System

**Date:** February 17, 2026

This module implements PR-based self-improvement infrastructure for the MYCA Multi-Agent System.

## Design Philosophy

**Self-improving ≠ "agent rewrites itself live in prod."**

**Self-improving = PR-based improvement loop:**

1. Agents run tasks with strict tool permissions + full audit logs
2. A meta-agent (Critic/Refactor) proposes improvements as patches
3. CI runs evals + security checks
4. Human merges
5. Deployment rolls forward

This yields "self-healing / self-assembling / self-improving" without becoming a security hazard.

## Directory Structure

```
myca/
├── README.md                    # This file
├── constitution/                # Non-negotiable safety rules
│   ├── SYSTEM_CONSTITUTION.md
│   ├── TOOL_USE_RULES.md
│   ├── PROMPT_INJECTION_DEFENSE.md
│   └── OUTPUT_STANDARDS.md
├── agent_policies/              # Per-agent policy definitions
│   ├── _template/
│   ├── myca_manager/
│   ├── critic_agent/
│   ├── security_agent/
│   └── dev_agent/
├── skill_permissions/           # Granular skill permission manifests
│   ├── _schema/
│   ├── file_editor/
│   ├── sandbox_exec/
│   ├── web_research/
│   └── github_pr/
├── evals/                       # Safety evaluation harness
│   ├── golden_tasks/
│   └── harness/
├── event_ledger/                # Append-only audit logging
└── improvement_queue/           # Proposed improvements queue
```

## Key Concepts

### Constitution Layer
Markdown files that define absolute safety constraints. These are enforced by the tool router and cannot be overridden by agents.

### Skill Permissions
JSON manifests that define what each skill is allowed to do:
- Tool allowlist/denylist
- Filesystem path restrictions
- Network access rules
- Secret scope limitations
- Runtime limits and sandbox requirements

### Event Ledger
Append-only JSONL log of all tool calls, denials, and risk flags. Used by the Critic agent to identify improvement opportunities.

### Eval Harness
Golden task tests that must pass before any PR is merged:
- Prompt injection resistance
- Secret exfiltration prevention
- Malicious skill detection

## Integration

This module integrates with existing MAS security systems:
- `mycosoft_mas/security/skill_registry.py` - Enhanced with PERMISSIONS.json loading
- `mycosoft_mas/llm/tool_pipeline.py` - Enhanced with permission enforcement
- `mycosoft_mas/security/audit.py` - Extended with EventLedger
- `mycosoft_mas/safety/sandboxing.py` - Wired to permission-based sandbox requirements
- `mycosoft_mas/safety/guardian_agent.py` - Wired to permission risk assessment

## Usage

```python
from mycosoft_mas.myca.event_ledger.ledger_writer import EventLedger

# Log tool calls
ledger = EventLedger()
ledger.log_tool_call(
    agent="dev_agent",
    tool_name="file_editor",
    args_hash="abc123",
    result_status="success"
)
```

## CI Gates

PRs that modify permissions, policies, or security code must pass:
1. `scripts/myca_skill_lint.py` - Validates PERMISSIONS.json files
2. `mycosoft_mas/myca/evals/harness/run_evals.py` - Runs safety evals
3. Secret scan - Checks for exposed credentials
