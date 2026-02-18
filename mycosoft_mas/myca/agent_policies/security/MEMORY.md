# Security Agent Memory

**Version:** 1.0.0  
**Date:** February 17, 2026

## Memory Types

### Short-Term Memory (Session)

| Key | Type | TTL | Purpose |
|-----|------|-----|---------|
| `active_reviews` | Dict[str, Review] | Session | In-progress reviews |
| `alert_queue` | List[Alert] | Session | Pending alerts |
| `access_patterns` | Dict[str, Pattern] | 1 hour | Recent access patterns |
| `blocked_agents` | Set[str] | Session | Currently blocked agents |

### Long-Term Memory (Persistent)

| Key | Type | Storage | Purpose |
|-----|------|---------|---------|
| `security_incidents` | List[Incident] | MINDEX | Historical incidents |
| `vulnerability_db` | List[Vulnerability] | MINDEX | Known vulnerabilities |
| `permission_history` | List[PermissionChange] | MINDEX | All permission changes |
| `threat_patterns` | List[ThreatPattern] | MINDEX | Known threat patterns |
| `compliance_reports` | List[ComplianceReport] | MINDEX | Historical compliance |

## Memory Schema

### Incident Record
```python
@dataclass
class IncidentRecord:
    incident_id: str
    severity: str  # P0, P1, P2, P3
    type: str  # exploitation, violation, anomaly
    description: str
    affected_agents: List[str]
    affected_skills: List[str]
    timeline: List[TimelineEvent]
    root_cause: Optional[str]
    resolution: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    reviewed_by: Optional[str]
```

### Vulnerability Record
```python
@dataclass
class VulnerabilityRecord:
    vuln_id: str
    type: str  # injection, escalation, leak
    severity: str
    pattern: str  # regex or description
    affected_files: List[str]
    first_detected: datetime
    status: str  # open, mitigated, resolved
    mitigation: Optional[str]
```

### Threat Pattern
```python
@dataclass
class ThreatPattern:
    pattern_id: str
    name: str
    description: str
    indicators: List[str]
    detection_rule: str
    response_playbook: str
    severity: str
    last_seen: Optional[datetime]
```

## Memory Operations

### Remember Incident
```python
async def remember_incident(incident: Incident):
    # Immediate storage for audit
    await mindex.store(
        collection="myca_security_incidents",
        document=incident.to_record(),
        priority="high"  # Ensure durability
    )
    
    # Update threat patterns if new
    if is_new_pattern(incident):
        await learn_threat_pattern(incident)
```

### Recall Similar Incidents
```python
async def recall_similar_incidents(indicators: List[str]) -> List[IncidentRecord]:
    return await mindex.semantic_search(
        collection="myca_security_incidents",
        query=" ".join(indicators),
        top_k=5,
        filters={"severity": {"$in": ["P0", "P1", "P2"]}}
    )
```

### Remember Permission Change
```python
async def remember_permission_change(
    skill: str,
    old_permissions: dict,
    new_permissions: dict,
    reviewer: str,
    decision: str
):
    record = {
        "skill": skill,
        "old_permissions": hash_sensitive(old_permissions),
        "new_permissions": hash_sensitive(new_permissions),
        "escalations": detect_escalation(old_permissions, new_permissions),
        "reviewer": reviewer,
        "decision": decision,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    await mindex.store(
        collection="myca_permission_history",
        document=record
    )
```

### Learn Threat Pattern
```python
async def learn_threat_pattern(incident: Incident):
    # Extract pattern
    pattern = ThreatPattern(
        pattern_id=generate_id(),
        name=f"Pattern from {incident.incident_id}",
        description=incident.description,
        indicators=extract_indicators(incident),
        detection_rule=generate_detection_rule(incident),
        response_playbook=incident.resolution or "escalate",
        severity=incident.severity,
        last_seen=datetime.utcnow(),
    )
    
    await mindex.store(
        collection="myca_threat_patterns",
        document=pattern
    )
```

### Query Access Patterns
```python
async def get_access_baseline(agent_type: str, tool: str) -> dict:
    # Get historical average
    history = await mindex.query(
        collection="myca_access_patterns",
        filter={
            "agent_type": agent_type,
            "tool": tool,
            "timestamp": {"$gte": days_ago(30)}
        }
    )
    
    return {
        "avg_daily_calls": calculate_avg(history),
        "max_daily_calls": calculate_max(history),
        "typical_hours": calculate_typical_hours(history),
    }
```

## Context Injection

When reviewing a security-related item:

```python
def get_security_context(item: SecurityItem) -> dict:
    return {
        "similar_incidents": recall_similar_incidents(item.indicators),
        "known_patterns": match_threat_patterns(item),
        "permission_history": get_permission_history(item.skill),
        "recent_alerts": get_recent_alerts(hours=24),
        "compliance_status": get_latest_compliance(),
    }
```

## Memory Limits

| Memory Type | Limit | Eviction |
|-------------|-------|----------|
| Active reviews | 20 | FIFO |
| Alert queue | 100 | Priority-based |
| Access patterns | 1000 | Time-based |
| Incident history query | 500 | By severity/date |

## Privacy and Security

- NEVER store actual secrets (even in incident logs)
- Hash all sensitive data before storage
- Encrypt incident details at rest
- Restrict access to security memory to Security Agent only
- Maintain separate audit log for memory access
- Implement retention policy (incidents: 2 years, patterns: indefinite)

## Threat Intelligence Updates

```python
async def update_threat_intelligence():
    """Periodic update of threat patterns."""
    # Pull latest patterns from central threat DB
    new_patterns = await fetch_central_threat_db()
    
    for pattern in new_patterns:
        existing = await mindex.query(
            collection="myca_threat_patterns",
            filter={"pattern_id": pattern.pattern_id}
        )
        
        if not existing:
            await mindex.store(
                collection="myca_threat_patterns",
                document=pattern
            )
```
