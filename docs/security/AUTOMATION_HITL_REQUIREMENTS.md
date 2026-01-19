# Mycosoft SOC - Automation & Human-in-the-Loop Requirements

**Version:** 2.0.0  
**Last Updated:** January 18, 2026  
**Classification:** INTERNAL SECURITY DOCUMENT

---

## Table of Contents

1. [Overview](#overview)
2. [Automation Philosophy](#automation-philosophy)
3. [Automated Processes](#automated-processes)
4. [Human-in-the-Loop (HITL) Requirements](#human-in-the-loop-hitl-requirements)
5. [Decision Matrix](#decision-matrix)
6. [Escalation Procedures](#escalation-procedures)
7. [Runbooks](#runbooks)
8. [Approval Workflows](#approval-workflows)

---

## Overview

The Mycosoft SOC implements a balanced approach between automation for speed and human oversight for critical decisions. This document defines when automation should act independently versus when human approval is required.

### Core Principles

1. **Speed for Detection** - Automated detection runs 24/7
2. **Automation for Low-Risk** - Low-severity actions auto-execute
3. **Human Review for High-Impact** - Blocking, quarantine requires approval
4. **Audit Everything** - All actions logged regardless of automation level
5. **Override Capability** - Humans can always override automation

---

## Automation Philosophy

### Automation Tiers

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTOMATION TIERS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TIER 1: FULLY AUTOMATED (No human involvement)                  │
│  ├── Log collection                                              │
│  ├── Event normalization                                         │
│  ├── Threat intelligence updates                                 │
│  ├── Dashboard updates                                           │
│  └── Alert generation                                            │
│                                                                  │
│  TIER 2: AUTOMATED WITH NOTIFICATION (Human informed)            │
│  ├── Suspicious IP flagging                                      │
│  ├── Port scan detection                                         │
│  ├── Anomaly detection                                           │
│  ├── Failed login tracking                                       │
│  └── Traffic anomaly alerts                                      │
│                                                                  │
│  TIER 3: AUTOMATED WITH APPROVAL (Human must approve)            │
│  ├── IP blocking (external)                                      │
│  ├── User account suspension                                     │
│  ├── Firewall rule changes                                       │
│  ├── Network scan execution                                      │
│  └── Playbook execution (high severity)                          │
│                                                                  │
│  TIER 4: HUMAN ONLY (No automation)                              │
│  ├── Device quarantine                                           │
│  ├── Production changes                                          │
│  ├── Incident escalation to external                             │
│  ├── Data breach notification                                    │
│  └── System recovery from backup                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Automated Processes

### 1. Data Collection & Monitoring

| Process | Frequency | Automation Level | Notes |
|---------|-----------|------------------|-------|
| UniFi client polling | 30 seconds | Tier 1 | Fully automated |
| UniFi alarm collection | Real-time | Tier 1 | Via API polling |
| Suricata log parsing | Real-time | Tier 1 | File tail |
| Threat intel updates | 6 hours | Tier 1 | Tor exit nodes |
| IP reputation cache | 1 hour TTL | Tier 1 | Per-IP |

### 2. Event Processing

| Event Type | Detection | Classification | Response |
|------------|-----------|----------------|----------|
| Port scan | Automated | Automated | Tier 2 (notify) |
| Brute force | Automated | Automated | Tier 3 (approval) |
| Geo-fence violation | Automated | Automated | Tier 2/3 |
| Malware signature | Automated | Automated | Tier 3 (approval) |
| DDoS pattern | Automated | Automated | Tier 2 (notify) |

### 3. Alert Generation

```yaml
# Alert Automation Rules

info_severity:
  automation: Tier 1
  action: Log only
  notification: None
  retention: 7 days

low_severity:
  automation: Tier 1
  action: Log and flag
  notification: Dashboard only
  retention: 30 days

medium_severity:
  automation: Tier 2
  action: Log, flag, alert
  notification: Dashboard + Email digest
  retention: 90 days

high_severity:
  automation: Tier 2
  action: Log, flag, immediate alert
  notification: Dashboard + Email + SMS
  retention: 1 year

critical_severity:
  automation: Tier 3
  action: Log, flag, alert, prepare playbook
  notification: All channels + phone call
  retention: 7 years
```

### 4. Scheduled Automation

| Task | Schedule | Automation Level | Approval |
|------|----------|------------------|----------|
| Network scan (internal) | Weekly (Sunday 2AM) | Tier 2 | Pre-approved |
| Vulnerability scan | Weekly (Sunday 4AM) | Tier 2 | Pre-approved |
| Compliance check | Daily (6AM) | Tier 1 | None |
| Backup verification | Daily (3AM) | Tier 1 | None |
| Report generation | Weekly (Monday 8AM) | Tier 1 | None |
| Threat intel refresh | Every 6 hours | Tier 1 | None |
| Certificate expiry check | Daily | Tier 2 | None |

---

## Human-in-the-Loop (HITL) Requirements

### Critical Decisions Requiring Human Approval

| Decision | Approver(s) | SLA | Fallback |
|----------|-------------|-----|----------|
| Block external IP | Any admin | 15 min | Auto-block after 3 critical events |
| Quarantine device | Morgan or Chris | 30 min | Alert only if unavailable |
| Suspend user account | Morgan only | 1 hour | N/A |
| Production deployment | 2 admins | N/A | N/A |
| Incident public disclosure | Morgan + Legal | N/A | N/A |
| Data breach notification | Morgan + Legal | N/A | N/A |
| Recovery from backup | Morgan or Chris | 30 min | N/A |

### Approval Workflow

```
┌──────────────────────────────────────────────────────────────┐
│                    APPROVAL WORKFLOW                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │   Event     │────▶│  Analysis   │────▶│  Decision   │    │
│  │  Detected   │     │  (Auto)     │     │  Required?  │    │
│  └─────────────┘     └─────────────┘     └──────┬──────┘    │
│                                                  │           │
│                             ┌────────────────────┼───────┐   │
│                             │ NO                 │ YES   │   │
│                             ▼                    ▼       │   │
│                      ┌─────────────┐      ┌─────────────┐│   │
│                      │  Execute    │      │   Queue     ││   │
│                      │  Playbook   │      │  Approval   ││   │
│                      └─────────────┘      └──────┬──────┘│   │
│                                                  │       │   │
│                                           ┌──────▼──────┐│   │
│                                           │   Notify    ││   │
│                                           │  Approvers  ││   │
│                                           └──────┬──────┘│   │
│                                                  │       │   │
│                             ┌────────────────────┼───────┘   │
│                             │                    │           │
│                      ┌──────▼──────┐      ┌──────▼──────┐   │
│                      │  Timeout    │      │  Approved/  │   │
│                      │  Action     │      │  Denied     │   │
│                      └─────────────┘      └─────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### HITL Scenarios

#### Scenario 1: Brute Force Attack Detected

```
1. DETECTION (Automated - Tier 1)
   - Suricata detects 10+ failed SSH attempts from 203.0.113.50
   - Event logged with severity=HIGH

2. CLASSIFICATION (Automated - Tier 1)
   - IP lookup: Country=CN (high-risk)
   - AbuseIPDB: 95% confidence score
   - Classification: Brute Force Attack

3. ALERT (Automated - Tier 2)
   - Dashboard alert created
   - Email sent to all admins
   - SMS sent to Morgan

4. PROPOSED ACTION (Automated - Tier 3)
   - System proposes: Block IP for 24 hours
   - Awaiting approval

5. APPROVAL (Human Required)
   - Admin reviews evidence
   - Approves block → IP blocked
   - OR Denies → Monitoring continues

6. LOGGING (Automated - Tier 1)
   - Decision logged with approver ID
   - Timestamp recorded
   - Evidence preserved
```

#### Scenario 2: Unauthorized Access Attempt

```
1. DETECTION (Automated)
   - Login attempt from 185.220.101.1 (Tor exit node)
   - User: morgan@mycosoft.com
   - Location: Russia (not in allowed locations)

2. CLASSIFICATION (Automated)
   - Tor exit: YES
   - High-risk country: YES
   - Valid credentials: YES (concerning)
   - Classification: CRITICAL - Possible account compromise

3. IMMEDIATE ACTIONS (Automated - Tier 2)
   - Session blocked
   - Login attempt rejected
   - All sessions for user invalidated

4. ESCALATION (Automated - Tier 3)
   - Incident created automatically
   - Proposed: Suspend account pending verification
   - All channels notified

5. HUMAN DECISION REQUIRED
   - Is this actually Morgan using VPN/Tor?
   - Contact Morgan via known phone number
   - If confirmed attack: Full incident response
   - If false positive: Whitelist and document
```

#### Scenario 3: Device Quarantine

```
1. DETECTION (Automated)
   - Device 192.168.0.200 exhibiting C2 beacon behavior
   - Connections to known malware domain

2. ANALYSIS (Automated)
   - Device: IoT camera (low criticality)
   - Behavior: Confirmed malicious
   - Impact: Potential lateral movement

3. PROPOSED ACTION (System - Tier 4)
   - Move device to VLAN 99 (Quarantine)
   - Requires HUMAN APPROVAL

4. APPROVAL PROCESS
   - Morgan or Chris must approve
   - Must respond within 30 minutes
   - If no response: Alert only (no auto-quarantine)

5. WHY NO AUTO-QUARANTINE?
   - Could disrupt legitimate operations
   - False positives possible
   - Physical access may be needed
   - Business context required
```

---

## Decision Matrix

### Automated Response Matrix

| Threat Type | Severity | Confidence | Action | Automation |
|-------------|----------|------------|--------|------------|
| Port scan | LOW | Any | Log | Tier 1 |
| Port scan | MEDIUM | >80% | Alert | Tier 2 |
| Brute force | HIGH | >90% | Propose block | Tier 3 |
| Malware beacon | CRITICAL | >95% | Propose quarantine | Tier 4 |
| DDoS | HIGH | >80% | Rate limit | Tier 2 |
| Geo violation | MEDIUM | 100% | Block request | Tier 2 |
| Data exfil | CRITICAL | >70% | Alert + investigate | Tier 4 |

### Confidence Thresholds

```yaml
# Minimum confidence for automated action
thresholds:
  log_only: 0%           # Always log
  flag_suspicious: 50%   # Flag for review
  alert_admin: 70%       # Send alerts
  propose_action: 80%    # Queue for approval
  auto_execute: 95%      # Only for LOW severity
```

### Override Rules

| Condition | Override Behavior |
|-----------|-------------------|
| Admin online | Always require approval |
| Admin offline >30min | Execute Tier 2 actions |
| Admin offline >2hr | Execute pre-approved Tier 3 |
| Confirmed attack pattern | Auto-execute defense |
| Business hours | Stricter HITL requirements |
| After hours | More automation allowed |

---

## Escalation Procedures

### Escalation Path

```
┌─────────────────────────────────────────────────────────────┐
│                   ESCALATION PATH                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Level 1: Dashboard Alert                                    │
│     │     (All events)                                       │
│     │     Response: 24 hours                                 │
│     ▼                                                        │
│  Level 2: Email Notification                                 │
│     │     (Medium+ severity)                                 │
│     │     Response: 4 hours                                  │
│     ▼                                                        │
│  Level 3: SMS Alert                                          │
│     │     (High+ severity)                                   │
│     │     Response: 1 hour                                   │
│     ▼                                                        │
│  Level 4: Phone Call                                         │
│     │     (Critical severity)                                │
│     │     Response: 15 minutes                               │
│     ▼                                                        │
│  Level 5: All-Hands Emergency                                │
│           (Active breach)                                    │
│           Response: Immediate                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### On-Call Schedule

| Role | Primary | Secondary | Escalation |
|------|---------|-----------|------------|
| Security Lead | Morgan | Chris | 15 min |
| Network Admin | Chris | Garrett | 30 min |
| System Admin | RJ | Beto | 30 min |
| Backup Contact | Any admin | - | 1 hour |

### Escalation Triggers

| Condition | Escalation Level |
|-----------|-----------------|
| Unacknowledged alert (1hr) | +1 level |
| Multiple high severity (3+) | +1 level |
| Critical event | Start at Level 4 |
| Confirmed breach | Immediate Level 5 |
| System unavailable | Level 3 minimum |

---

## Runbooks

### Runbook: Brute Force Response

```yaml
runbook:
  name: "Brute Force Attack Response"
  id: RB-001
  version: 1.0
  
  trigger:
    event_type: "brute_force"
    severity: ["high", "critical"]
    threshold: "5 failed attempts in 5 minutes"
    
  automated_steps:
    - action: "log_event"
      tier: 1
      
    - action: "lookup_ip_reputation"
      tier: 1
      
    - action: "classify_threat"
      tier: 1
      
    - action: "create_alert"
      tier: 2
      channels: ["dashboard", "email"]
      
  human_decision:
    question: "Block source IP?"
    options:
      - "block_24h"
      - "block_permanent"
      - "monitor_only"
      - "whitelist"
    timeout: "30m"
    timeout_action: "monitor_only"
    
  post_decision:
    - action: "execute_decision"
    - action: "log_audit_trail"
    - action: "update_threat_intel"
    
  recovery:
    - action: "verify_block_effective"
    - action: "check_no_legitimate_impact"
    - action: "schedule_review"
      delay: "24h"
```

### Runbook: Device Quarantine

```yaml
runbook:
  name: "Device Quarantine"
  id: RB-002
  version: 1.0
  
  trigger:
    event_type: ["malware_detected", "c2_beacon", "data_exfil"]
    severity: "critical"
    
  pre_conditions:
    - "device_identified"
    - "threat_confirmed"
    - "admin_available"
    
  automated_steps:
    - action: "identify_device"
    - action: "assess_criticality"
    - action: "document_connections"
    - action: "prepare_quarantine_config"
    
  human_decision:
    required: true
    approvers: ["morgan", "chris"]
    question: "Execute quarantine to VLAN 99?"
    evidence_required:
      - "threat_evidence"
      - "device_info"
      - "impact_assessment"
    timeout: "30m"
    timeout_action: "alert_only"  # No auto-quarantine
    
  execution_steps:
    - action: "backup_device_config"
    - action: "move_to_vlan_99"
    - action: "block_internet_access"
    - action: "enable_forensic_logging"
    
  rollback:
    trigger: "false_positive_confirmed"
    steps:
      - "restore_vlan"
      - "restore_access"
      - "document_false_positive"
```

### Runbook: Incident Response

```yaml
runbook:
  name: "Security Incident Response"
  id: RB-003
  version: 1.0
  
  phases:
    identification:
      automation: "tier_1"
      steps:
        - "detect_anomaly"
        - "classify_event"
        - "initial_triage"
        
    containment:
      automation: "tier_3"
      human_required: true
      steps:
        - "isolate_affected_systems"
        - "preserve_evidence"
        - "prevent_spread"
        
    eradication:
      automation: "tier_4"
      human_required: true
      steps:
        - "remove_threat"
        - "patch_vulnerabilities"
        - "update_defenses"
        
    recovery:
      automation: "tier_4"
      human_required: true
      steps:
        - "restore_systems"
        - "verify_functionality"
        - "monitor_for_recurrence"
        
    lessons_learned:
      automation: "none"
      human_required: true
      steps:
        - "conduct_postmortem"
        - "update_procedures"
        - "train_team"
```

---

## Approval Workflows

### Standard Approval Workflow

```
┌─────────────────────────────────────────────────────────────┐
│              STANDARD APPROVAL WORKFLOW                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. ACTION REQUESTED                                         │
│     │                                                        │
│     ├── Requester: System/User                               │
│     ├── Action: [Block IP / Quarantine / etc]                │
│     ├── Evidence: Attached                                   │
│     └── Priority: [Normal/Urgent/Emergency]                  │
│                                                              │
│  2. NOTIFICATION                                             │
│     │                                                        │
│     ├── Email to approvers                                   │
│     ├── Dashboard notification                               │
│     └── SMS for urgent/emergency                             │
│                                                              │
│  3. REVIEW                                                   │
│     │                                                        │
│     ├── Approver views evidence                              │
│     ├── Checks impact assessment                             │
│     └── Verifies threat validity                             │
│                                                              │
│  4. DECISION                                                 │
│     │                                                        │
│     ├── APPROVE: Action executes immediately                 │
│     ├── DENY: Action cancelled, logged                       │
│     ├── MODIFY: Adjusted action proposed                     │
│     └── ESCALATE: Passed to higher authority                 │
│                                                              │
│  5. EXECUTION                                                │
│     │                                                        │
│     ├── Action performed                                     │
│     ├── Results logged                                       │
│     └── Confirmation sent                                    │
│                                                              │
│  6. AUDIT                                                    │
│     │                                                        │
│     └── Full trail preserved for compliance                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Emergency Approval Workflow

```yaml
emergency_workflow:
  trigger: "critical_active_threat"
  
  immediate_actions:  # No approval needed
    - "enable_enhanced_logging"
    - "alert_all_admins"
    - "prepare_isolation"
    
  fast_approval:
    timeout: "5 minutes"
    approvers: 1  # Only 1 needed
    channels: ["sms", "phone"]
    
  fallback:
    condition: "no_response_5min"
    action: "execute_defensive_playbook"
    notify: "all_admins"
    
  post_emergency:
    - "full_review_required"
    - "incident_report_mandatory"
    - "approval_gap_documented"
```

### Approval Matrix

| Action | Approvers Needed | Timeout | Fallback |
|--------|-----------------|---------|----------|
| Block IP (temp) | 1 admin | 30 min | Monitor |
| Block IP (perm) | 2 admins | 4 hours | Temp block |
| Quarantine device | Morgan or Chris | 30 min | Alert only |
| Suspend user | Morgan only | 1 hour | None |
| Emergency response | 1 admin | 5 min | Auto-execute |
| Production change | 2 admins | N/A | None |
| Data breach notify | Morgan + Legal | N/A | None |

---

## Audit Requirements

### What Must Be Logged

| Category | Data Logged | Retention |
|----------|-------------|-----------|
| All events | Full event details | 90 days |
| Decisions | Who, what, when, why | 1 year |
| Approvals | Approver, timestamp, evidence | 7 years |
| Denials | Same as approvals | 7 years |
| Overrides | Full justification required | 7 years |
| Timeouts | What timed out, fallback taken | 1 year |

### Audit Log Format

```json
{
  "audit_id": "AUD-2026-001234",
  "timestamp": "2026-01-18T12:38:00Z",
  "event_type": "approval_decision",
  "action": "block_ip",
  "target": "203.0.113.50",
  "decision": "approved",
  "approver": {
    "id": "morgan-001",
    "name": "Morgan",
    "role": "super_admin"
  },
  "evidence": {
    "threat_score": 95,
    "source": "abuseipdb",
    "events_triggered": 12
  },
  "execution": {
    "status": "completed",
    "timestamp": "2026-01-18T12:38:05Z"
  }
}
```

---

## Continuous Improvement

### Review Cycle

| Review Type | Frequency | Participants |
|-------------|-----------|--------------|
| Automation effectiveness | Weekly | Security team |
| False positive rate | Weekly | Security team |
| HITL response times | Monthly | All admins |
| Runbook accuracy | Quarterly | Security team |
| Full process audit | Annually | External + Internal |

### Metrics to Track

- Mean time to detect (MTTD)
- Mean time to respond (MTTR)
- Automation accuracy rate
- False positive rate
- Human override frequency
- Approval queue depth
- SLA compliance

---

**Document Control:**
- Created: January 18, 2026
- Owner: Morgan (super_admin)
- Review Cycle: Monthly
- Next Review: February 18, 2026
