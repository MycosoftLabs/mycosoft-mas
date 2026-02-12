"""
Security Agents V2 - February 12, 2026

MAS v2 security agents for the Security Operations Center.
Includes GuardianAgentV2, SecurityMonitorAgent, and ThreatResponseAgent.

These agents handle:
- Action evaluation and risk assessment
- Security monitoring and anomaly detection
- Threat response and incident management
- Playbook execution
- SOC integration
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from mycosoft_mas.agents.v2.base_agent_v2 import BaseAgentV2
from mycosoft_mas.runtime import AgentTask

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk levels for security evaluation."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatCategory(str, Enum):
    """Categories of security threats."""
    MALWARE = "malware"
    INTRUSION = "intrusion"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DOS = "denial_of_service"
    ANOMALY = "anomaly"
    POLICY_VIOLATION = "policy_violation"
    RECONNAISSANCE = "reconnaissance"
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════
# GUARDIAN AGENT V2
# ═══════════════════════════════════════════════════════════════

class GuardianAgentV2(BaseAgentV2):
    """
    Guardian Agent V2 - Safety monitoring and policy enforcement.
    
    Evaluates agent actions against security policies,
    blocks dangerous operations, and logs all decisions.
    
    Capabilities:
    - evaluate_action: Check if an action is safe to execute
    - set_threshold: Configure risk thresholds for action types
    - get_blocked_actions: List blocked actions
    - emergency_lockdown: Block all non-essential actions
    """
    
    @property
    def agent_type(self) -> str:
        return "guardian"
    
    @property
    def category(self) -> str:
        return "security"
    
    @property
    def display_name(self) -> str:
        return "Guardian Agent"
    
    @property
    def description(self) -> str:
        return "Monitors and enforces safety policies across MAS"
    
    def __init__(self, agent_id: str = "guardian-agent", **kwargs):
        super().__init__(agent_id, **kwargs)
        
        # Risk thresholds by action type
        self.risk_thresholds: Dict[str, RiskLevel] = {
            "lab_operation": RiskLevel.MEDIUM,
            "data_access": RiskLevel.LOW,
            "external_communication": RiskLevel.MEDIUM,
            "database_write": RiskLevel.MEDIUM,
            "file_system": RiskLevel.LOW,
            "network_request": RiskLevel.LOW,
            "spawn_agent": RiskLevel.MEDIUM,
            "execute_code": RiskLevel.HIGH,
            "admin_command": RiskLevel.HIGH,
            "critical_infrastructure": RiskLevel.CRITICAL,
        }
        
        # Blocked actions history
        self.blocked_actions: List[Dict[str, Any]] = []
        
        # Lockdown state
        self.lockdown_active = False
        self.lockdown_until: Optional[datetime] = None
        
        # Register task handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register security task handlers."""
        self.register_handler("evaluate_action", self._handle_evaluate_action)
        self.register_handler("set_threshold", self._handle_set_threshold)
        self.register_handler("get_blocked_actions", self._handle_get_blocked_actions)
        self.register_handler("emergency_lockdown", self._handle_emergency_lockdown)
        self.register_handler("release_lockdown", self._handle_release_lockdown)
        self.register_handler("get_risk_thresholds", self._handle_get_risk_thresholds)
    
    def get_capabilities(self) -> List[str]:
        return [
            "evaluate_action",
            "set_threshold",
            "get_blocked_actions",
            "emergency_lockdown",
            "release_lockdown",
            "get_risk_thresholds",
        ]
    
    def _assess_risk(
        self, 
        action_type: str, 
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> RiskLevel:
        """Assess the risk level of an action."""
        # Critical keyword detection
        param_str = str(parameters).lower()
        dangerous_keywords = [
            "dangerous", "delete_all", "drop_database", "rm -rf",
            "format", "shutdown", "override", "bypass_auth",
        ]
        
        for keyword in dangerous_keywords:
            if keyword in param_str:
                return RiskLevel.CRITICAL
        
        # Action-specific risk assessment
        high_risk_actions = ["stimulate", "inject", "modify_genome", "reset_firmware"]
        if action_type in high_risk_actions:
            return RiskLevel.HIGH
        
        medium_risk_actions = ["write_config", "update_schema", "deploy", "restart_service"]
        if action_type in medium_risk_actions:
            return RiskLevel.MEDIUM
        
        # Default based on action type prefix
        if action_type.startswith("admin_"):
            return RiskLevel.HIGH
        if action_type.startswith("delete_"):
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    def _compare_risk(self, risk: RiskLevel, threshold: RiskLevel) -> bool:
        """Compare risk against threshold. Returns True if risk is acceptable."""
        levels = [RiskLevel.NONE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return levels.index(risk) <= levels.index(threshold)
    
    async def _handle_evaluate_action(self, task: AgentTask) -> Dict[str, Any]:
        """Evaluate an action for safety."""
        action_type = task.payload.get("action_type", "unknown")
        parameters = task.payload.get("parameters", {})
        requester = task.payload.get("requester", task.requester_agent)
        context = task.payload.get("context")
        
        # Check lockdown
        if self.lockdown_active:
            now = datetime.now(timezone.utc)
            if self.lockdown_until and now < self.lockdown_until:
                self.blocked_actions.append({
                    "action": action_type,
                    "requester": requester,
                    "timestamp": now.isoformat(),
                    "reason": "emergency_lockdown",
                })
                logger.warning(f"Blocked action during lockdown: {action_type}")
                return {
                    "approved": False,
                    "risk_level": "blocked",
                    "action": action_type,
                    "reason": "System is in emergency lockdown",
                }
            else:
                # Lockdown expired
                self.lockdown_active = False
                self.lockdown_until = None
        
        # Assess risk
        risk = self._assess_risk(action_type, parameters, context)
        threshold = self.risk_thresholds.get(action_type, RiskLevel.MEDIUM)
        
        # Make decision
        approved = self._compare_risk(risk, threshold)
        
        if not approved:
            self.blocked_actions.append({
                "action": action_type,
                "requester": requester,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "risk_level": risk.value,
                "threshold": threshold.value,
                "reason": f"Risk {risk.value} exceeds threshold {threshold.value}",
            })
            logger.warning(f"Blocked action: {action_type} (risk: {risk.value}, threshold: {threshold.value})")
        else:
            logger.debug(f"Approved action: {action_type} (risk: {risk.value})")
        
        # Log to MINDEX
        await self.log_to_mindex(
            "evaluate_action",
            {
                "action": action_type,
                "risk": risk.value,
                "approved": approved,
                "requester": requester,
            },
            success=approved,
        )
        
        return {
            "approved": approved,
            "risk_level": risk.value,
            "threshold": threshold.value,
            "action": action_type,
            "reason": None if approved else f"Risk {risk.value} exceeds threshold {threshold.value}",
        }
    
    async def _handle_set_threshold(self, task: AgentTask) -> Dict[str, Any]:
        """Set risk threshold for an action type."""
        action_type = task.payload.get("action_type")
        threshold = task.payload.get("threshold")
        
        if not action_type or not threshold:
            return {"status": "error", "message": "action_type and threshold required"}
        
        try:
            risk_level = RiskLevel(threshold)
            self.risk_thresholds[action_type] = risk_level
            logger.info(f"Set threshold for {action_type} to {threshold}")
            
            return {
                "status": "success",
                "action_type": action_type,
                "threshold": threshold,
            }
        except ValueError:
            return {"status": "error", "message": f"Invalid threshold: {threshold}"}
    
    async def _handle_get_blocked_actions(self, task: AgentTask) -> Dict[str, Any]:
        """Get list of blocked actions."""
        limit = task.payload.get("limit", 50)
        return {
            "blocked_actions": self.blocked_actions[-limit:],
            "total_blocked": len(self.blocked_actions),
        }
    
    async def _handle_get_risk_thresholds(self, task: AgentTask) -> Dict[str, Any]:
        """Get all risk thresholds."""
        return {
            "thresholds": {k: v.value for k, v in self.risk_thresholds.items()},
            "lockdown_active": self.lockdown_active,
        }
    
    async def _handle_emergency_lockdown(self, task: AgentTask) -> Dict[str, Any]:
        """Activate emergency lockdown."""
        duration_minutes = task.payload.get("duration_minutes", 15)
        reason = task.payload.get("reason", "Manual activation")
        
        self.lockdown_active = True
        from datetime import timedelta
        self.lockdown_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        
        logger.critical(f"EMERGENCY LOCKDOWN activated for {duration_minutes} minutes. Reason: {reason}")
        
        return {
            "status": "lockdown_active",
            "duration_minutes": duration_minutes,
            "until": self.lockdown_until.isoformat(),
            "reason": reason,
        }
    
    async def _handle_release_lockdown(self, task: AgentTask) -> Dict[str, Any]:
        """Release emergency lockdown."""
        authorization = task.payload.get("authorization")
        
        # In production, verify authorization
        self.lockdown_active = False
        self.lockdown_until = None
        
        logger.info("Emergency lockdown released")
        
        return {
            "status": "lockdown_released",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# SECURITY MONITOR AGENT V2
# ═══════════════════════════════════════════════════════════════

class SecurityMonitorAgentV2(BaseAgentV2):
    """
    Security Monitor Agent V2 - Continuous security monitoring.
    
    Monitors system events, detects anomalies, and triggers alerts.
    
    Capabilities:
    - monitor_events: Process security events
    - analyze_anomaly: Analyze potential anomalies
    - get_alerts: Get recent alerts
    - set_rule: Add/update detection rules
    """
    
    @property
    def agent_type(self) -> str:
        return "security_monitor"
    
    @property
    def category(self) -> str:
        return "security"
    
    @property
    def display_name(self) -> str:
        return "Security Monitor"
    
    @property
    def description(self) -> str:
        return "Continuous security monitoring and anomaly detection"
    
    def __init__(self, agent_id: str = "security-monitor-agent", **kwargs):
        super().__init__(agent_id, **kwargs)
        
        # Recent alerts
        self.alerts: List[Dict[str, Any]] = []
        self.max_alerts = 500
        
        # Detection rules
        self.detection_rules: Dict[str, Dict[str, Any]] = {
            "high_request_rate": {
                "threshold": 100,
                "window_seconds": 60,
                "severity": "medium",
            },
            "failed_auth_attempts": {
                "threshold": 5,
                "window_seconds": 300,
                "severity": "high",
            },
            "suspicious_data_access": {
                "pattern": "sensitive|classified|secret",
                "severity": "high",
            },
        }
        
        # Event counters
        self.event_counts: Dict[str, int] = {}
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register monitor task handlers."""
        self.register_handler("monitor_events", self._handle_monitor_events)
        self.register_handler("analyze_anomaly", self._handle_analyze_anomaly)
        self.register_handler("get_alerts", self._handle_get_alerts)
        self.register_handler("set_rule", self._handle_set_rule)
        self.register_handler("clear_alerts", self._handle_clear_alerts)
    
    def get_capabilities(self) -> List[str]:
        return [
            "monitor_events",
            "analyze_anomaly",
            "get_alerts",
            "set_rule",
            "clear_alerts",
        ]
    
    def _create_alert(
        self,
        title: str,
        description: str,
        severity: str,
        category: ThreatCategory,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a security alert."""
        alert = {
            "id": f"alert-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(self.alerts)}",
            "title": title,
            "description": description,
            "severity": severity,
            "category": category.value,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "status": "new",
        }
        
        self.alerts.append(alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts.pop(0)
        
        logger.warning(f"Security alert created: {title} ({severity})")
        
        return alert
    
    async def _handle_monitor_events(self, task: AgentTask) -> Dict[str, Any]:
        """Process security events."""
        events = task.payload.get("events", [])
        
        alerts_created = []
        
        for event in events:
            event_type = event.get("type", "unknown")
            
            # Increment event counter
            self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
            
            # Check detection rules
            for rule_name, rule in self.detection_rules.items():
                if self._check_rule(event, rule):
                    alert = self._create_alert(
                        title=f"Rule triggered: {rule_name}",
                        description=f"Event type: {event_type}",
                        severity=rule.get("severity", "medium"),
                        category=ThreatCategory.ANOMALY,
                        source=event.get("source", "unknown"),
                        metadata={"event": event, "rule": rule_name},
                    )
                    alerts_created.append(alert)
        
        return {
            "events_processed": len(events),
            "alerts_created": len(alerts_created),
            "alerts": alerts_created,
        }
    
    def _check_rule(self, event: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """Check if an event triggers a rule."""
        # Pattern matching
        if "pattern" in rule:
            import re
            event_str = str(event).lower()
            if re.search(rule["pattern"], event_str):
                return True
        
        # Threshold checking (simplified)
        if "threshold" in rule:
            event_type = event.get("type", "unknown")
            count = self.event_counts.get(event_type, 0)
            if count >= rule["threshold"]:
                return True
        
        return False
    
    async def _handle_analyze_anomaly(self, task: AgentTask) -> Dict[str, Any]:
        """Analyze a potential anomaly."""
        data = task.payload.get("data", {})
        context = task.payload.get("context", {})
        
        # Simplified anomaly analysis
        anomaly_score = 0.0
        factors = []
        
        # Check for unusual patterns
        if "error" in str(data).lower():
            anomaly_score += 0.2
            factors.append("Contains error indicators")
        
        if "failed" in str(data).lower():
            anomaly_score += 0.3
            factors.append("Contains failure indicators")
        
        if context.get("after_hours"):
            anomaly_score += 0.2
            factors.append("After hours activity")
        
        if context.get("new_source"):
            anomaly_score += 0.3
            factors.append("New/unknown source")
        
        is_anomaly = anomaly_score >= 0.5
        
        if is_anomaly:
            self._create_alert(
                title="Anomaly detected",
                description=f"Score: {anomaly_score:.2f}, Factors: {', '.join(factors)}",
                severity="medium" if anomaly_score < 0.7 else "high",
                category=ThreatCategory.ANOMALY,
                source="anomaly_analysis",
                metadata={"data": data, "score": anomaly_score, "factors": factors},
            )
        
        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "factors": factors,
            "recommendation": "Investigate" if is_anomaly else "Normal activity",
        }
    
    async def _handle_get_alerts(self, task: AgentTask) -> Dict[str, Any]:
        """Get recent alerts."""
        limit = task.payload.get("limit", 50)
        severity = task.payload.get("severity")
        status = task.payload.get("status")
        
        filtered_alerts = self.alerts
        
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a["severity"] == severity]
        
        if status:
            filtered_alerts = [a for a in filtered_alerts if a["status"] == status]
        
        return {
            "alerts": filtered_alerts[-limit:],
            "total": len(filtered_alerts),
        }
    
    async def _handle_set_rule(self, task: AgentTask) -> Dict[str, Any]:
        """Add or update a detection rule."""
        rule_name = task.payload.get("rule_name")
        rule_config = task.payload.get("config")
        
        if not rule_name or not rule_config:
            return {"status": "error", "message": "rule_name and config required"}
        
        self.detection_rules[rule_name] = rule_config
        
        return {
            "status": "success",
            "rule_name": rule_name,
            "config": rule_config,
        }
    
    async def _handle_clear_alerts(self, task: AgentTask) -> Dict[str, Any]:
        """Clear alerts."""
        before = task.payload.get("before")  # ISO timestamp
        
        if before:
            self.alerts = [a for a in self.alerts if a["timestamp"] > before]
        else:
            self.alerts = []
        
        return {
            "status": "success",
            "remaining_alerts": len(self.alerts),
        }


# ═══════════════════════════════════════════════════════════════
# THREAT RESPONSE AGENT V2
# ═══════════════════════════════════════════════════════════════

class ThreatResponseAgentV2(BaseAgentV2):
    """
    Threat Response Agent V2 - Automated threat response.
    
    Executes security playbooks, coordinates incident response,
    and manages containment actions.
    
    Capabilities:
    - execute_playbook: Run a security playbook
    - contain_threat: Execute containment action
    - escalate_incident: Escalate to SOC
    - create_incident: Create SOC incident
    """
    
    @property
    def agent_type(self) -> str:
        return "threat_response"
    
    @property
    def category(self) -> str:
        return "security"
    
    @property
    def display_name(self) -> str:
        return "Threat Response"
    
    @property
    def description(self) -> str:
        return "Automated threat response and incident management"
    
    def __init__(self, agent_id: str = "threat-response-agent", **kwargs):
        super().__init__(agent_id, **kwargs)
        
        # Playbooks
        self.playbooks: Dict[str, Dict[str, Any]] = {
            "isolate_host": {
                "description": "Isolate a compromised host",
                "steps": [
                    {"action": "notify_soc", "priority": "high"},
                    {"action": "block_network", "target": "host"},
                    {"action": "capture_forensics"},
                    {"action": "notify_admin"},
                ],
            },
            "block_ip": {
                "description": "Block malicious IP address",
                "steps": [
                    {"action": "add_to_blocklist"},
                    {"action": "terminate_connections"},
                    {"action": "log_event"},
                ],
            },
            "account_lockout": {
                "description": "Lock compromised account",
                "steps": [
                    {"action": "disable_account"},
                    {"action": "revoke_sessions"},
                    {"action": "notify_user"},
                    {"action": "notify_security_team"},
                ],
            },
        }
        
        # Incident history
        self.incidents: List[Dict[str, Any]] = []
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register threat response handlers."""
        self.register_handler("execute_playbook", self._handle_execute_playbook)
        self.register_handler("contain_threat", self._handle_contain_threat)
        self.register_handler("escalate_incident", self._handle_escalate_incident)
        self.register_handler("create_incident", self._handle_create_incident)
        self.register_handler("get_playbooks", self._handle_get_playbooks)
        self.register_handler("add_playbook", self._handle_add_playbook)
    
    def get_capabilities(self) -> List[str]:
        return [
            "execute_playbook",
            "contain_threat",
            "escalate_incident",
            "create_incident",
            "get_playbooks",
            "add_playbook",
        ]
    
    async def _handle_execute_playbook(self, task: AgentTask) -> Dict[str, Any]:
        """Execute a security playbook."""
        playbook_name = task.payload.get("playbook_name")
        target = task.payload.get("target")
        context = task.payload.get("context", {})
        
        if playbook_name not in self.playbooks:
            return {"status": "error", "message": f"Unknown playbook: {playbook_name}"}
        
        playbook = self.playbooks[playbook_name]
        
        logger.info(f"Executing playbook: {playbook_name} for target: {target}")
        
        results = []
        for step in playbook["steps"]:
            # Simulate step execution
            step_result = {
                "action": step["action"],
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            results.append(step_result)
            await asyncio.sleep(0.1)  # Simulate work
        
        # Log to MINDEX
        await self.log_to_mindex(
            "execute_playbook",
            {
                "playbook": playbook_name,
                "target": target,
                "steps_completed": len(results),
            },
            success=True,
        )
        
        return {
            "status": "success",
            "playbook": playbook_name,
            "target": target,
            "steps_executed": len(results),
            "results": results,
        }
    
    async def _handle_contain_threat(self, task: AgentTask) -> Dict[str, Any]:
        """Execute a containment action."""
        action_type = task.payload.get("action_type")
        target = task.payload.get("target")
        reason = task.payload.get("reason")
        
        logger.warning(f"Containment action: {action_type} on {target}")
        
        # Simulate containment
        # In production, this would integrate with firewalls, WAF, etc.
        
        return {
            "status": "contained",
            "action": action_type,
            "target": target,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def _handle_escalate_incident(self, task: AgentTask) -> Dict[str, Any]:
        """Escalate an incident."""
        incident_id = task.payload.get("incident_id")
        reason = task.payload.get("reason")
        new_severity = task.payload.get("severity", "high")
        
        logger.warning(f"Escalating incident {incident_id} to {new_severity}")
        
        return {
            "status": "escalated",
            "incident_id": incident_id,
            "new_severity": new_severity,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def _handle_create_incident(self, task: AgentTask) -> Dict[str, Any]:
        """Create a SOC incident."""
        title = task.payload.get("title")
        description = task.payload.get("description")
        severity = task.payload.get("severity", "medium")
        category = task.payload.get("category", "unknown")
        
        incident = {
            "id": f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(self.incidents)}",
            "title": title,
            "description": description,
            "severity": severity,
            "category": category,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": self.agent_id,
        }
        
        self.incidents.append(incident)
        
        logger.info(f"Created incident: {incident['id']}")
        
        return {
            "status": "created",
            "incident": incident,
        }
    
    async def _handle_get_playbooks(self, task: AgentTask) -> Dict[str, Any]:
        """Get available playbooks."""
        return {
            "playbooks": {
                name: {
                    "description": pb["description"],
                    "steps_count": len(pb["steps"]),
                }
                for name, pb in self.playbooks.items()
            }
        }
    
    async def _handle_add_playbook(self, task: AgentTask) -> Dict[str, Any]:
        """Add a new playbook."""
        name = task.payload.get("name")
        description = task.payload.get("description")
        steps = task.payload.get("steps", [])
        
        if not name or not steps:
            return {"status": "error", "message": "name and steps required"}
        
        self.playbooks[name] = {
            "description": description or f"Playbook: {name}",
            "steps": steps,
        }
        
        return {
            "status": "success",
            "playbook": name,
        }


# Export all agents
__all__ = [
    "RiskLevel",
    "ThreatCategory",
    "GuardianAgentV2",
    "SecurityMonitorAgentV2",
    "ThreatResponseAgentV2",
]
