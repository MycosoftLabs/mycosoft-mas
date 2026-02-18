# Manager Agent Playbook

**Version:** 1.0.0  
**Date:** February 17, 2026

## Overview

Step-by-step procedures for common Manager Agent operations.

---

## Playbook 1: Process New Improvement Proposal

### Trigger
New item added to improvement queue.

### Steps

1. **Read Proposal**
   ```python
   proposal = improvement_queue.get_next()
   ```

2. **Validate Proposal Format**
   - Check required fields present
   - Verify proposal is not duplicate
   - Ensure proposal is not malicious (prompt injection check)

3. **Classify Proposal Type**
   | Type | Route To |
   |------|----------|
   | Bug fix | Dev Agent |
   | New feature | Dev Agent + Security review |
   | Permission change | Security Agent |
   | Failure fix | Critic Agent |
   | Documentation | Dev Agent |

4. **Create Task(s)**
   ```yaml
   task:
     id: "task_<proposal_id>_<seq>"
     type: "<classification>"
     assignee: "<agent_type>"
     priority: "<calculated>"
     deadline: "<sla_based>"
     context:
       proposal_id: "<id>"
       requirements: "<extracted>"
   ```

5. **Assign to Agent Queue**
   ```python
   task_queue.assign(task, agent_type)
   event_ledger.log_task_assignment(task)
   ```

6. **Monitor Progress**
   - Check task status every 60 seconds
   - Handle timeouts (10 min default)
   - Log all state transitions

---

## Playbook 2: Handle Task Completion

### Trigger
Agent reports task complete.

### Steps

1. **Verify Completion**
   - Check all deliverables present
   - Verify CI status is green
   - Confirm no security flags

2. **Route Based on Outcome**
   | Outcome | Action |
   |---------|--------|
   | Success + CI green | Queue for human review |
   | Success + CI red | Route to Critic |
   | Partial completion | Re-queue remaining work |
   | Failure | Log and escalate |

3. **Update State**
   ```python
   improvement_queue.update_status(
       proposal_id=proposal_id,
       status="ready_for_review" | "needs_rework",
       details={...}
   )
   ```

4. **Notify Human** (if ready for review)
   ```yaml
   notification:
     channel: escalation
     type: review_ready
     proposal_id: "<id>"
     summary: "<brief description>"
     ci_status: "green"
     files_changed: ["<list>"]
   ```

---

## Playbook 3: Handle CI Failure

### Trigger
CI reports failure for submitted PR.

### Steps

1. **Classify Failure Type**
   | Type | Route To |
   |------|----------|
   | Test failure | Critic Agent |
   | Lint failure | Dev Agent (auto-fix) |
   | Build failure | Dev Agent |
   | Security scan | Security Agent |
   | Eval failure | Critic Agent |

2. **Create Failure Analysis Task**
   ```yaml
   task:
     id: "fix_<pr_id>_<failure_type>"
     type: "failure_analysis"
     assignee: "<determined_agent>"
     context:
       pr_id: "<id>"
       failure_type: "<type>"
       failure_log: "<url or content>"
       original_task: "<task_id>"
   ```

3. **Track Retry Count**
   - Max 3 automatic retries
   - Escalate to human after max retries

4. **Update Proposal Status**
   ```python
   improvement_queue.update_status(
       proposal_id=proposal_id,
       status="ci_failed",
       failure_count=failure_count,
       details={"failure_type": "...", "assigned_to": "..."}
   )
   ```

---

## Playbook 4: Handle Agent Timeout

### Trigger
Task exceeds deadline without completion.

### Steps

1. **Check Agent Health**
   ```python
   agent_status = agent_manager.get_status(agent_id)
   ```

2. **Decide Action**
   | Status | Action |
   |--------|--------|
   | Healthy, still working | Extend deadline |
   | Unresponsive | Kill and reassign |
   | Crashed | Log error, reassign |
   | Blocked | Investigate blocker |

3. **Reassign if Needed**
   - Try same agent type first
   - If repeated failures, try different agent
   - Log reassignment reason

4. **Escalate if Repeated**
   - More than 2 timeouts → human escalation
   - Include all context and logs

---

## Playbook 5: Coordinate Multi-Agent Task

### Trigger
Improvement requires multiple agents.

### Steps

1. **Plan Execution Order**
   ```yaml
   execution_plan:
     - stage: 1
       tasks:
         - agent: dev
           task: "implement_feature"
           dependencies: []
     - stage: 2
       tasks:
         - agent: security
           task: "security_review"
           dependencies: ["implement_feature"]
         - agent: critic
           task: "add_tests"
           dependencies: ["implement_feature"]
     - stage: 3
       tasks:
         - agent: dev
           task: "address_feedback"
           dependencies: ["security_review", "add_tests"]
   ```

2. **Execute Stages**
   - Run tasks in parallel within stage
   - Wait for all tasks in stage before next
   - Handle failures at any stage

3. **Aggregate Results**
   - Combine all outputs
   - Resolve conflicts if any
   - Create unified PR

---

## Quick Reference

### Status Codes
| Code | Meaning |
|------|---------|
| `queued` | Awaiting assignment |
| `assigned` | Agent working on it |
| `in_review` | Awaiting human review |
| `ci_running` | CI in progress |
| `ci_failed` | CI failed |
| `approved` | Human approved |
| `merged` | Complete |
| `rejected` | Human rejected |

### Escalation Triggers
- [ ] Task timeout > 2x
- [ ] CI failure > 3x
- [ ] Security flag raised
- [ ] Constitution violation
- [ ] Agent crash
- [ ] Ambiguous requirements
