# [Agent Name] Playbook

**Date:** February 17, 2026
**Version:** 1.0.0

## Purpose

Step-by-step procedures for common tasks this agent performs.

## Procedures

### Procedure 1: [Name]

**Trigger:** When this procedure should be invoked

**Steps:**
1. Step 1 description
2. Step 2 description
3. Step 3 description

**Success Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

**Failure Response:**
- If step fails, do X
- Escalate to Y if unrecoverable

---

### Procedure 2: [Name]

**Trigger:** When this procedure should be invoked

**Steps:**
1. Step 1 description
2. Step 2 description

**Success Criteria:**
- [ ] Criterion 1

---

## Emergency Procedures

### On Critical Failure
1. Stop current operation
2. Log full context to Event Ledger
3. Notify human operator
4. Do not attempt recovery without approval

### On Security Incident
1. Immediately halt affected operations
2. Preserve evidence (logs, state)
3. Notify Security Agent
4. Follow incident response procedure

## Notes

- Procedures should be atomic where possible
- Always log start and end of procedures
- Update this playbook after significant incidents
