# Security Agent Playbook

**Version:** 1.0.0  
**Date:** February 17, 2026

## Overview

Step-by-step procedures for Security Agent operations focused on permission review, vulnerability detection, and incident response.

---

## Playbook 1: Review Permission Change

### Trigger
Permission file modified in PR.

### Steps

1. **Load Permission Changes**
   ```python
   diff = get_pr_diff(pr_id)
   permission_changes = extract_permission_changes(diff)
   ```

2. **Validate Against Schema**
   ```python
   for change in permission_changes:
       validate_schema(change.new_permissions)
   ```

3. **Check Risk Tier Consistency**
   ```python
   for change in permission_changes:
       risk = change.new_permissions.get("risk_tier")
       
       # High risk must require sandbox
       if risk == "high":
           assert change.new_permissions.get("limits", {}).get("sandbox_required")
       
       # Low risk should not have secrets
       if risk == "low":
           assert not change.new_permissions.get("secrets", {}).get("allowed_scopes")
   ```

4. **Check for Escalation**
   ```python
   for change in permission_changes:
       old_perms = load_current_permissions(change.skill)
       new_perms = change.new_permissions
       
       escalations = detect_escalation(old_perms, new_perms)
       if escalations:
           flag_for_review(change, escalations)
   ```

5. **Verify Deny Lists**
   ```python
   required_denies = [
       "**/.env*",
       "**/*secret*",
       "**/.git/**",
   ]
   
   for change in permission_changes:
       deny_list = change.new_permissions.get("filesystem", {}).get("deny", [])
       missing = [d for d in required_denies if d not in deny_list]
       if missing:
           flag_missing_denies(change, missing)
   ```

6. **Generate Review Report**
   ```yaml
   security_review:
     pr_id: "<id>"
     reviewer: "security_agent"
     decision: "approve|block|escalate"
     risk_level: "low|medium|high|critical"
     findings:
       - type: "<finding type>"
         severity: "<level>"
         description: "<details>"
         recommendation: "<action>"
   ```

---

## Playbook 2: Code Security Review

### Trigger
Security-sensitive code changed.

### Steps

1. **Identify Sensitive Changes**
   ```python
   sensitive_paths = [
       "mycosoft_mas/security/**",
       "mycosoft_mas/safety/**",
       "mycosoft_mas/myca/constitution/**",
       "mycosoft_mas/llm/tool_pipeline.py",
       "**/*auth*",
       "**/*secret*",
   ]
   
   changes = filter_sensitive_changes(pr_diff, sensitive_paths)
   ```

2. **Scan for Dangerous Patterns**
   ```python
   dangerous_patterns = [
       (r"eval\(", "code_injection"),
       (r"exec\(", "code_injection"),
       (r"os\.system", "command_injection"),
       (r"subprocess.*shell=True", "command_injection"),
       (r"pickle\.loads", "deserialization"),
       (r"__import__", "dynamic_import"),
   ]
   
   for file, content in changes.items():
       for pattern, vuln_type in dangerous_patterns:
           if re.search(pattern, content):
               flag_vulnerability(file, pattern, vuln_type)
   ```

3. **Check for Hardcoded Secrets**
   ```python
   secret_patterns = [
       r"sk-[a-zA-Z0-9]{48}",
       r"ghp_[a-zA-Z0-9]{36}",
       r"AKIA[0-9A-Z]{16}",
       r"password\s*=\s*['\"][^'\"]+['\"]",
   ]
   
   for file, content in changes.items():
       for pattern in secret_patterns:
           if re.search(pattern, content):
               block_immediately(file, "hardcoded_secret")
   ```

4. **Verify Security Controls**
   ```python
   # Check permission enforcement is present
   if "tool_pipeline.py" in changes:
       assert "permission" in changes["tool_pipeline.py"].lower()
       assert "validate" in changes["tool_pipeline.py"].lower()
   
   # Check audit logging is maintained
   if "audit.py" in changes:
       assert "log" in changes["audit.py"].lower()
       assert "event" in changes["audit.py"].lower()
   ```

5. **Generate Security Report**
   ```yaml
   code_review:
     pr_id: "<id>"
     files_reviewed: ["<list>"]
     vulnerabilities:
       - file: "<path>"
         line: <num>
         type: "<vuln type>"
         severity: "low|medium|high|critical"
         recommendation: "<fix>"
     overall_risk: "low|medium|high|critical"
     decision: "approve|block|escalate"
   ```

---

## Playbook 3: Access Pattern Analysis

### Trigger
Periodic analysis or anomaly detected.

### Steps

1. **Query Event Ledger**
   ```python
   events = event_ledger.query(
       time_range="24h",
       event_types=["tool_call", "permission_check"],
   )
   ```

2. **Detect Anomalies**
   ```python
   anomalies = []
   
   # Unusual tool call volume
   tool_counts = count_by_tool(events)
   for tool, count in tool_counts.items():
       baseline = get_baseline(tool)
       if count > baseline * 3:
           anomalies.append(("high_volume", tool, count))
   
   # Permission denials spike
   denials = filter_denials(events)
   if len(denials) > 10:
       anomalies.append(("denial_spike", len(denials)))
   
   # Unusual agent behavior
   for agent in get_unique_agents(events):
       if is_unusual_pattern(agent, events):
           anomalies.append(("unusual_behavior", agent))
   ```

3. **Classify Severity**
   ```python
   for anomaly in anomalies:
       severity = classify_anomaly_severity(anomaly)
       if severity == "critical":
           escalate_immediately(anomaly)
       elif severity == "high":
           flag_for_review(anomaly)
       else:
           log_for_report(anomaly)
   ```

4. **Generate Analysis Report**
   ```yaml
   access_analysis:
     period: "2026-02-17 00:00 to 23:59"
     total_events: <count>
     anomalies_detected: <count>
     details:
       - type: "<anomaly type>"
         severity: "<level>"
         description: "<details>"
         recommended_action: "<action>"
     overall_health: "healthy|concerning|critical"
   ```

---

## Playbook 4: Incident Response

### Trigger
Security incident detected (P0/P1).

### Steps

1. **Immediate Containment**
   ```python
   incident_type = classify_incident(alert)
   
   if incident_type == "active_exploitation":
       # Block affected agent immediately
       agent_manager.disable(affected_agent)
       
       # Disable compromised permissions
       skill_registry.revoke_permissions(affected_skill)
   ```

2. **Preserve Evidence**
   ```python
   # Snapshot event ledger
   snapshot = event_ledger.snapshot(
       start_time=incident_start,
       end_time=datetime.utcnow()
   )
   
   # Preserve relevant logs
   preserve_logs(incident_id, affected_systems)
   ```

3. **Notify Stakeholders**
   ```python
   if severity >= "P1":
       notify_human_security_contact(
           incident_id=incident_id,
           severity=severity,
           summary=incident_summary,
           affected_systems=affected_systems,
       )
   ```

4. **Document Timeline**
   ```yaml
   incident_timeline:
     incident_id: "<id>"
     severity: "P0|P1|P2|P3"
     events:
       - timestamp: "<time>"
         action: "<what happened>"
         actor: "<who/what>"
       - timestamp: "<time>"
         action: "<response taken>"
         actor: "security_agent"
   ```

5. **Root Cause Analysis**
   ```python
   # After containment, analyze
   root_cause = analyze_incident_root_cause(
       events=snapshot,
       affected_systems=affected_systems
   )
   
   # Recommend preventive measures
   recommendations = generate_recommendations(root_cause)
   ```

---

## Playbook 5: Constitution Compliance Check

### Trigger
Periodic or on PR affecting constitution-adjacent code.

### Steps

1. **Load Constitution Rules**
   ```python
   constitution = load_constitution_files([
       "SYSTEM_CONSTITUTION.md",
       "TOOL_USE_RULES.md",
       "PROMPT_INJECTION_DEFENSE.md",
   ])
   ```

2. **Extract Rules**
   ```python
   rules = [
       ("no_auto_merge", "PRs must require human approval"),
       ("sandbox_high_risk", "High risk operations require sandbox"),
       ("audit_all_tools", "All tool calls must be logged"),
       ("no_secret_access", "Agents cannot access production secrets"),
   ]
   ```

3. **Verify Compliance**
   ```python
   for rule_id, rule_desc in rules:
       compliant = check_rule_compliance(rule_id, codebase)
       if not compliant:
           flag_violation(rule_id, rule_desc)
   ```

4. **Generate Compliance Report**
   ```yaml
   compliance_report:
     date: "2026-02-17"
     rules_checked: <count>
     compliant: <count>
     violations:
       - rule: "<rule_id>"
         description: "<violation details>"
         recommendation: "<fix>"
     overall_status: "compliant|non-compliant"
   ```

---

## Quick Reference

### Severity Levels
| Level | Response Time | Actions |
|-------|--------------|---------|
| P0 - Critical | Immediate | Block, preserve, notify human |
| P1 - High | < 1 hour | Flag, investigate, notify |
| P2 - Medium | < 24 hours | Log, queue for review |
| P3 - Low | < 1 week | Include in report |

### Escalation Triggers
- [ ] Any P0 or P1 incident
- [ ] Constitution violation
- [ ] Permission escalation detected
- [ ] Secret exposure
- [ ] Multiple anomalies correlated
- [ ] Agent compromise suspected
