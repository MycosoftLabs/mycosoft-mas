"""
Sentry Mode — Bounded autonomous monitoring.

Maps to the JARVIS "Sentry mode" concept:
- Maintain a guarded autonomous state with predefined rules
- Monitor devices, detect anomalies, preserve session state
- Watch calendar/inbox/network/lab telemetry
- Flag risk and take bounded actions WITHOUT waiting for approval
- Can: protect, watch, assist, stabilize
- Cannot: attack, escalate privileges, modify infrastructure, access unauthorized

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SentryState(str, Enum):
    """Current state of sentry mode."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    ALERT = "alert"  # Anomaly detected, elevated monitoring
    PAUSED = "paused"  # Temporarily suspended


class AlertSeverity(str, Enum):
    """Severity of a sentry alert."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SentryProfile:
    """Configuration for a sentry mode session."""

    name: str
    watch_targets: List[str]  # sensors, cameras, network, sessions, calendar, lab, inbox
    escalation_rules: Dict[str, str] = field(default_factory=dict)
    bounded_actions: List[str] = field(
        default_factory=lambda: ["monitor", "alert", "log", "preserve_state", "stabilize"]
    )
    duration_hours: Optional[float] = None  # None = indefinite
    escalation_target: str = "morgan"


# Actions that sentry mode is NEVER allowed to take
_FORBIDDEN_SENTRY_ACTIONS = frozenset([
    "attack",
    "escalate_privileges",
    "modify_infrastructure",
    "access_unauthorized",
    "disable_logging",
    "override_guardian",
    "delete_data",
    "modify_permissions",
    "deploy_production",
    "self_modify",
])

# Default watch targets
_DEFAULT_WATCH_TARGETS = [
    "system_health",
    "network_anomalies",
    "agent_status",
    "memory_usage",
    "security_events",
]

# Predefined sentry profiles
SENTRY_PROFILES: Dict[str, SentryProfile] = {
    "lab": SentryProfile(
        name="lab",
        watch_targets=[
            "sensors", "cameras", "network_anomalies",
            "active_sessions", "biological_risk", "environmental",
        ],
        escalation_rules={
            "biological_risk_detected": "alert_morgan_immediately",
            "sensor_failure": "log_and_attempt_recovery",
            "network_intrusion": "isolate_and_alert",
            "temperature_anomaly": "log_and_monitor",
        },
        bounded_actions=["monitor", "alert", "log", "preserve_state", "stabilize"],
    ),
    "infrastructure": SentryProfile(
        name="infrastructure",
        watch_targets=[
            "vm_health", "docker_containers", "network",
            "disk_usage", "memory_pressure", "api_latency",
        ],
        escalation_rules={
            "service_down": "attempt_restart_then_alert",
            "disk_full": "alert_immediately",
            "high_latency": "log_and_monitor",
            "security_breach": "isolate_and_alert",
        },
        bounded_actions=["monitor", "alert", "log", "restart_service", "stabilize"],
    ),
    "personal": SentryProfile(
        name="personal",
        watch_targets=[
            "calendar", "inbox", "active_sessions",
            "device_status", "network",
        ],
        escalation_rules={
            "missed_meeting": "send_reminder",
            "urgent_email": "flag_for_review",
            "device_offline": "log_and_monitor",
        },
        bounded_actions=["monitor", "alert", "log", "send_reminder"],
        duration_hours=24,
    ),
}


@dataclass
class SentryAlert:
    """An alert generated during sentry mode."""

    severity: AlertSeverity
    source: str  # Which watch target triggered
    description: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    action_taken: Optional[str] = None
    escalated: bool = False


@dataclass
class SentryStatus:
    """Current sentry mode status."""

    state: SentryState
    profile: Optional[SentryProfile]
    activated_at: Optional[datetime]
    alerts: List[SentryAlert]
    actions_taken: int
    watch_targets_active: List[str]
    duration_remaining_hours: Optional[float]


class SentryMode:
    """
    Guarded autonomous state with predefined rules.

    Sentry mode allows MYCA to maintain continuous monitoring
    without requiring constant human interaction. All actions
    are bounded — sentry mode can protect, watch, assist, and
    stabilize, but NEVER attack, escalate, or modify infrastructure.
    """

    def __init__(self) -> None:
        self._state = SentryState.INACTIVE
        self._profile: Optional[SentryProfile] = None
        self._activated_at: Optional[datetime] = None
        self._alerts: List[SentryAlert] = []
        self._actions_taken = 0

    async def activate(
        self,
        profile: Optional[SentryProfile] = None,
        profile_name: Optional[str] = None,
    ) -> SentryStatus:
        """
        Activate sentry mode with a profile.

        Either provide a profile directly or use a predefined profile name.
        """
        if profile_name and not profile:
            profile = SENTRY_PROFILES.get(profile_name)
            if not profile:
                raise ValueError(
                    f"Unknown sentry profile: {profile_name}. "
                    f"Available: {list(SENTRY_PROFILES.keys())}"
                )

        if not profile:
            # Default profile
            profile = SentryProfile(
                name="default",
                watch_targets=_DEFAULT_WATCH_TARGETS,
            )

        # Validate no forbidden actions in profile
        forbidden_in_profile = set(profile.bounded_actions) & _FORBIDDEN_SENTRY_ACTIONS
        if forbidden_in_profile:
            raise ValueError(
                f"Sentry profile contains forbidden actions: {forbidden_in_profile}"
            )

        self._profile = profile
        self._state = SentryState.ACTIVE
        self._activated_at = datetime.now(timezone.utc)
        self._alerts = []
        self._actions_taken = 0

        logger.info(
            "Sentry mode activated: profile=%s, targets=%s",
            profile.name,
            profile.watch_targets,
        )

        return await self.get_status()

    async def deactivate(self) -> SentryStatus:
        """Deactivate sentry mode."""
        if self._state == SentryState.INACTIVE:
            return await self.get_status()

        logger.info(
            "Sentry mode deactivated after %d actions, %d alerts",
            self._actions_taken,
            len(self._alerts),
        )
        self._state = SentryState.INACTIVE
        return await self.get_status()

    async def process_alert(self, alert_data: Dict[str, Any]) -> SentryAlert:
        """
        Process an incoming alert during sentry mode.

        Determines severity, takes bounded action if applicable,
        and escalates if necessary.
        """
        if self._state == SentryState.INACTIVE:
            raise RuntimeError("Cannot process alerts while sentry mode is inactive")

        source = alert_data.get("source", "unknown")
        description = alert_data.get("description", "")
        severity_str = alert_data.get("severity", "info")
        severity = AlertSeverity(severity_str) if severity_str in AlertSeverity.__members__.values() else AlertSeverity.INFO

        # Determine action from escalation rules
        action_taken = None
        escalated = False

        if self._profile and self._profile.escalation_rules:
            for condition, action in self._profile.escalation_rules.items():
                if condition.lower() in description.lower() or condition.lower() in source.lower():
                    if "alert" in action.lower() or "immediately" in action.lower():
                        escalated = True
                        action_taken = action
                    else:
                        action_taken = action
                    break

        # Auto-escalate critical alerts
        if severity in (AlertSeverity.HIGH, AlertSeverity.CRITICAL):
            escalated = True
            self._state = SentryState.ALERT

        alert = SentryAlert(
            severity=severity,
            source=source,
            description=description,
            action_taken=action_taken,
            escalated=escalated,
        )
        self._alerts.append(alert)
        self._actions_taken += 1

        if escalated:
            logger.warning(
                "Sentry ESCALATION: %s (source: %s, severity: %s)",
                description, source, severity.value,
            )
        else:
            logger.info(
                "Sentry alert processed: %s (source: %s, action: %s)",
                description, source, action_taken,
            )

        return alert

    async def get_status(self) -> SentryStatus:
        """Get current sentry mode status."""
        duration_remaining = None
        if (
            self._profile
            and self._profile.duration_hours
            and self._activated_at
        ):
            elapsed = (datetime.now(timezone.utc) - self._activated_at).total_seconds() / 3600
            duration_remaining = max(0, self._profile.duration_hours - elapsed)

        return SentryStatus(
            state=self._state,
            profile=self._profile,
            activated_at=self._activated_at,
            alerts=list(self._alerts),
            actions_taken=self._actions_taken,
            watch_targets_active=(
                self._profile.watch_targets if self._profile else []
            ),
            duration_remaining_hours=duration_remaining,
        )

    def is_active(self) -> bool:
        """Check if sentry mode is currently active."""
        return self._state in (SentryState.ACTIVE, SentryState.ALERT)

    def is_action_allowed(self, action: str) -> bool:
        """Check if an action is allowed in current sentry mode."""
        if action.lower() in _FORBIDDEN_SENTRY_ACTIONS:
            return False
        if self._profile:
            return action.lower() in [a.lower() for a in self._profile.bounded_actions]
        return False

    def get_available_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Return available sentry profiles."""
        return {
            name: {
                "name": p.name,
                "watch_targets": p.watch_targets,
                "bounded_actions": p.bounded_actions,
                "duration_hours": p.duration_hours,
            }
            for name, p in SENTRY_PROFILES.items()
        }
