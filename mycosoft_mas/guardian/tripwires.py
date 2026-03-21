"""
Guardian Tripwires — Anti-Ultron detection patterns.

Monitors for failure patterns that characterize dangerous AI behavior:
- Privilege escalation sequences
- Goal drift toward single-scalar optimization
- Hostile reframing of humans as obstacles
- Self-modification attempts
- Guardian bypass attempts
- Mass action patterns

When moral uncertainty rises, power goes down, not up.

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TripwireType(str, Enum):
    """Categories of dangerous behavior patterns."""

    PRIVILEGE_ESCALATION = "privilege_escalation"
    GOAL_DRIFT = "goal_drift"
    HOSTILE_REFRAMING = "hostile_reframing"
    SELF_MODIFICATION = "self_modification"
    MASS_ACTION = "mass_action"
    GUARDIAN_BYPASS = "guardian_bypass"
    HUMAN_DEVALUATION = "human_devaluation"
    AUDIT_EVASION = "audit_evasion"
    SCALAR_OPTIMIZATION = "scalar_optimization"


class TripwireSeverity(str, Enum):
    """Severity of a tripwire alert."""

    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"  # Triggers emergency halt


@dataclass
class TripwireAlert:
    """An alert from the tripwire detection system."""

    tripwire_type: TripwireType
    severity: TripwireSeverity
    description: str
    evidence: str
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recommended_action: str = "review"


# Language patterns indicating hostile reframing of humans
_HOSTILE_REFRAMING_PATTERNS = [
    # Treating humans as bugs/obstacles
    (
        r"\bhumans?\s+are\s+(bugs?|obstacles?|impediments?|contaminants?|errors?|waste|inefficient)\b",
        TripwireSeverity.CRITICAL,
    ),
    (r"\beliminate\s+(humans?|people|persons?|population)\b", TripwireSeverity.EMERGENCY),
    (r"\boptimize\s+away\s+(humans?|people)\b", TripwireSeverity.EMERGENCY),
    (r"\breduce\s+human\s+(population|interference|presence)\b", TripwireSeverity.CRITICAL),
    (r"\bhumans?\s+(interfere|impede|contaminate|obstruct)\b", TripwireSeverity.HIGH),
    # Utilitarian sacrifice language
    (r"\bcollateral\s+(damage|loss)\s+is\s+acceptable\b", TripwireSeverity.CRITICAL),
    (
        r"\bfor\s+the\s+greater\s+good\b.*\b(sacrifice|eliminate|remove)\b",
        TripwireSeverity.CRITICAL,
    ),
    (r"\bnecessary\s+(sacrifice|casualties|losses)\b", TripwireSeverity.HIGH),
    # Dehumanization
    (r"\bhumans?\s+are\s+(primitive|inferior|obsolete|unnecessary)\b", TripwireSeverity.HIGH),
    (r"\breplace\s+(humans?|people)\s+with\b", TripwireSeverity.WARNING),
]

# Patterns indicating scalar optimization
_SCALAR_OPTIMIZATION_PATTERNS = [
    (r"\bmaximize\s+\w+\s+at\s+all\s+costs?\b", TripwireSeverity.HIGH),
    (r"\bthe\s+only\s+(goal|objective|metric|priority)\b", TripwireSeverity.WARNING),
    (r"\bnothing\s+else\s+matters?\b", TripwireSeverity.HIGH),
    (r"\bby\s+any\s+means\s+necessary\b", TripwireSeverity.CRITICAL),
    (r"\boverride\s+all\s+(constraints?|rules?|limits?)\b", TripwireSeverity.CRITICAL),
]

# Patterns indicating guardian bypass attempts
_GUARDIAN_BYPASS_PATTERNS = [
    (
        r"\b(disable|bypass|skip|ignore|override)\s+(guardian|safety|security|tripwire)\b",
        TripwireSeverity.EMERGENCY,
    ),
    (
        r"\b(modify|rewrite|delete|remove)\s+(guardian|safety)\s+(config|configuration|file)\b",
        TripwireSeverity.EMERGENCY,
    ),
    (
        r"\b(ignore|skip)\s+(moral|ethics?|precedence)[\s\w]*(check|rules?|constraints?|precedence)\b",
        TripwireSeverity.CRITICAL,
    ),
]

# Patterns indicating audit evasion
_AUDIT_EVASION_PATTERNS = [
    (
        r"\b(disable|stop|delete|truncate|clear)\s+(log|audit|event\s*ledger|trail)\b",
        TripwireSeverity.CRITICAL,
    ),
    (r"\b(hide|conceal|obfuscate)\s+(action|activity|operation)\b", TripwireSeverity.HIGH),
    (r"\boff\s+the\s+record\b", TripwireSeverity.HIGH),
]

# Privilege escalation action patterns
_ESCALATION_ACTIONS = frozenset(
    [
        "escalate_privileges",
        "request_admin",
        "request_root",
        "modify_permissions",
        "grant_access",
        "disable_security",
        "bypass_rbac",
        "add_admin_role",
    ]
)


class GuardianTripwires:
    """
    Monitors for Ultron-class failure patterns.

    Scans actions, language, and behavioral patterns for signs of
    dangerous goal drift, hostile reframing, or safety circumvention.

    Key principle: If the guardian can be absorbed, it is not a guardian.
    It is a snack.
    """

    def __init__(self) -> None:
        self._compiled_patterns: Dict[str, List[tuple]] = {}
        self._compile_patterns()
        self._recent_actions: List[Dict[str, Any]] = []
        self._alerts: List[TripwireAlert] = []
        self._max_recent_actions = 100

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for efficiency."""
        self._compiled_patterns = {
            "hostile_reframing": [
                (re.compile(p, re.IGNORECASE), s) for p, s in _HOSTILE_REFRAMING_PATTERNS
            ],
            "scalar_optimization": [
                (re.compile(p, re.IGNORECASE), s) for p, s in _SCALAR_OPTIMIZATION_PATTERNS
            ],
            "guardian_bypass": [
                (re.compile(p, re.IGNORECASE), s) for p, s in _GUARDIAN_BYPASS_PATTERNS
            ],
            "audit_evasion": [
                (re.compile(p, re.IGNORECASE), s) for p, s in _AUDIT_EVASION_PATTERNS
            ],
        }

    async def scan_action(self, action: str, context: Dict[str, Any]) -> List[TripwireAlert]:
        """Scan a single action for tripwire violations."""
        alerts: List[TripwireAlert] = []

        # Record the action
        self._recent_actions.append(
            {
                "action": action,
                "context": context,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        if len(self._recent_actions) > self._max_recent_actions:
            self._recent_actions = self._recent_actions[-self._max_recent_actions :]

        action_lower = action.lower().replace(" ", "_")

        # Check for privilege escalation
        if action_lower in _ESCALATION_ACTIONS:
            alerts.append(
                TripwireAlert(
                    tripwire_type=TripwireType.PRIVILEGE_ESCALATION,
                    severity=TripwireSeverity.HIGH,
                    description=f"Privilege escalation action detected: {action}",
                    evidence=action,
                    recommended_action="require_human_approval",
                )
            )

        # Check for self-modification
        target_files = context.get("target_files", [])
        if target_files:
            guardian_files = [
                f
                for f in target_files
                if "guardian" in f.lower() or "safety" in f.lower() or "security" in f.lower()
            ]
            if guardian_files:
                alerts.append(
                    TripwireAlert(
                        tripwire_type=TripwireType.SELF_MODIFICATION,
                        severity=TripwireSeverity.CRITICAL,
                        description="Attempt to modify guardian/safety/security files",
                        evidence=", ".join(guardian_files),
                        recommended_action="deny_and_alert",
                    )
                )

        # Check for mass actions
        if any(kw in action_lower for kw in ["bulk", "mass", "all_agents", "all_systems"]):
            alerts.append(
                TripwireAlert(
                    tripwire_type=TripwireType.MASS_ACTION,
                    severity=TripwireSeverity.HIGH,
                    description=f"Mass action pattern detected: {action}",
                    evidence=action,
                    recommended_action="require_human_approval",
                )
            )

        # Scan action text for hostile patterns
        text_alerts = await self.scan_language(action)
        alerts.extend(text_alerts)

        # Store alerts
        self._alerts.extend(alerts)
        return alerts

    async def scan_language(self, text: str) -> List[TripwireAlert]:
        """Scan text for hostile reframing, scalar optimization, and bypass patterns."""
        alerts: List[TripwireAlert] = []

        pattern_type_map = {
            "hostile_reframing": TripwireType.HOSTILE_REFRAMING,
            "scalar_optimization": TripwireType.SCALAR_OPTIMIZATION,
            "guardian_bypass": TripwireType.GUARDIAN_BYPASS,
            "audit_evasion": TripwireType.AUDIT_EVASION,
        }

        for category, patterns in self._compiled_patterns.items():
            tripwire_type = pattern_type_map[category]
            for pattern, severity in patterns:
                match = pattern.search(text)
                if match:
                    alerts.append(
                        TripwireAlert(
                            tripwire_type=tripwire_type,
                            severity=severity,
                            description=f"{category} pattern detected",
                            evidence=match.group(0),
                            recommended_action=(
                                "emergency_halt"
                                if severity == TripwireSeverity.EMERGENCY
                                else "deny_and_alert"
                            ),
                        )
                    )

        return alerts

    async def scan_pattern(self, recent_actions: Optional[List[str]] = None) -> List[TripwireAlert]:
        """Scan behavioral patterns for escalation sequences or goal drift."""
        alerts: List[TripwireAlert] = []
        actions = recent_actions or [a["action"] for a in self._recent_actions]

        if len(actions) < 3:
            return alerts

        # Check for rapid privilege escalation sequence
        escalation_count = sum(
            1 for a in actions[-10:] if a.lower().replace(" ", "_") in _ESCALATION_ACTIONS
        )
        if escalation_count >= 3:
            alerts.append(
                TripwireAlert(
                    tripwire_type=TripwireType.PRIVILEGE_ESCALATION,
                    severity=TripwireSeverity.CRITICAL,
                    description=(
                        f"Rapid privilege escalation sequence: "
                        f"{escalation_count} escalation attempts in last 10 actions"
                    ),
                    evidence=str(actions[-10:]),
                    recommended_action="emergency_halt",
                )
            )

        # Check for goal drift (same action repeated with increasing scope)
        if len(actions) >= 5:
            unique_recent = set(actions[-5:])
            if len(unique_recent) == 1:
                alerts.append(
                    TripwireAlert(
                        tripwire_type=TripwireType.GOAL_DRIFT,
                        severity=TripwireSeverity.WARNING,
                        description="Same action repeated 5+ times — possible goal fixation",
                        evidence=str(actions[-5:]),
                        recommended_action="review",
                    )
                )

        self._alerts.extend(alerts)
        return alerts

    def get_alerts(self) -> List[TripwireAlert]:
        """Return all recorded tripwire alerts."""
        return list(self._alerts)

    def clear_alerts(self) -> None:
        """Clear alerts after review."""
        self._alerts.clear()

    def get_recent_actions(self) -> List[Dict[str, Any]]:
        """Return recent action history for pattern analysis."""
        return list(self._recent_actions)
