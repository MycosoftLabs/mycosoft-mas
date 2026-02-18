# [Agent Name] Policy

**Date:** February 17, 2026
**Version:** 1.0.0
**Status:** Template

## Role

Brief description of this agent's purpose and responsibilities.

## Capabilities

### Allowed Actions
- Action 1
- Action 2
- Action 3

### Forbidden Actions
- Action that must never be taken
- Another forbidden action

## Tool Access

| Tool | Access Level | Notes |
|------|--------------|-------|
| tool_name | read/write/execute | Constraints |

## High-Impact Actions

The following actions require explicit human approval:
- [ ] Action requiring approval
- [ ] Another action requiring approval

## Interaction Rules

### With Other Agents
- Can delegate to: [agent_list]
- Receives from: [agent_list]
- Reports to: [agent_list]

### With External Systems
- Network access: yes/no
- Secret access: scopes

## Output Requirements

### Mandatory Outputs
- Output type 1
- Output type 2

### Format
- Use structured formats (checklists, JSON, etc.)
- Include acceptance criteria
- List all artifacts

## Error Handling

### On Failure
1. Log to Event Ledger
2. Notify appropriate party
3. Propose recovery steps

### On Denial
1. Log denial with reason
2. Suggest alternative approach
3. Escalate if necessary

## Self-Improvement

This agent may propose improvements via:
- Adding regression tests
- Updating PLAYBOOK.md
- Proposing policy changes (via PR)

## References

- `PLAYBOOK.md` - Operational procedures
- `MEMORY.md` - Memory access patterns
- `EVALS.md` - Evaluation criteria
