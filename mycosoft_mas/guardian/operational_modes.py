"""
Operational Modes — Morgan mode vs Mycosoft mode.

Same coherent mind. Different scopes. Different policies.
Same relationship layer.

Morgan mode: Personal memory, preferences, private context, voice
interaction, lab notes, ideation, focus management.

Mycosoft mode: Ops, projects, finance, repos, agents, HR/process,
CRM, manufacturing, lab telemetry, deployment, compliance.

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class OperationalMode(str, Enum):
    """Operational context modes."""

    MORGAN = "morgan"
    MYCOSOFT = "mycosoft"


@dataclass
class ModePolicy:
    """Policy and scope for an operational mode."""

    mode: OperationalMode
    scope: List[str]
    memory_partition: str
    permission_level: str
    voice_style: Dict[str, float]
    description: str
    allowed_systems: List[str]
    restricted_systems: List[str] = field(default_factory=list)


# Mode policies
_MODE_POLICIES: Dict[OperationalMode, ModePolicy] = {
    OperationalMode.MORGAN: ModePolicy(
        mode=OperationalMode.MORGAN,
        scope=[
            "personal_memory",
            "preferences",
            "private_context",
            "voice_interaction",
            "lab_notes",
            "ideation",
            "focus_management",
            "travel",
            "messages",
        ],
        memory_partition="morgan_personal",
        permission_level="personal",
        voice_style={
            "warmth": 0.85,
            "energy": 0.6,
            "formality": 0.15,
            "confidence": 0.8,
            "playfulness": 0.5,
        },
        description=(
            "Personal mode — direct, warm, casual interaction with Morgan. "
            "Access to personal memory, preferences, and private context. "
            "More casual voice style with higher warmth."
        ),
        allowed_systems=[
            "memory",
            "calendar",
            "inbox",
            "lab_notes",
            "personal_devices",
            "voice",
            "ideation",
        ],
        restricted_systems=[
            "hr_records",
            "financial_admin",
            "compliance",
            "customer_data",
            "production_deploy",
        ],
    ),
    OperationalMode.MYCOSOFT: ModePolicy(
        mode=OperationalMode.MYCOSOFT,
        scope=[
            "operations",
            "projects",
            "finance",
            "repositories",
            "agents",
            "hr_process",
            "crm",
            "manufacturing",
            "lab_telemetry",
            "deployment",
            "compliance",
            "documentation",
            "infrastructure",
        ],
        memory_partition="mycosoft_enterprise",
        permission_level="enterprise",
        voice_style={
            "warmth": 0.7,
            "energy": 0.5,
            "formality": 0.4,
            "confidence": 0.85,
            "playfulness": 0.2,
        },
        description=(
            "Enterprise mode — professional, comprehensive operational "
            "support for Mycosoft. Access to all enterprise systems. "
            "More formal voice style with higher confidence."
        ),
        allowed_systems=[
            "orchestrator",
            "agents",
            "memory",
            "infrastructure",
            "repositories",
            "deployment",
            "monitoring",
            "lab",
            "financial",
            "hr",
            "documentation",
            "compliance",
        ],
        restricted_systems=[
            "morgan_personal_notes",
            "private_messages",
        ],
    ),
}


@dataclass
class ModeSwitchResult:
    """Result of a mode switch operation."""

    success: bool
    previous_mode: OperationalMode
    new_mode: OperationalMode
    switched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""


class OperationalModeManager:
    """
    Manages MYCA's operational context.

    Same coherent mind, same relationship layer.
    Different scopes, different policies.
    """

    def __init__(
        self,
        initial_mode: OperationalMode = OperationalMode.MYCOSOFT,
    ) -> None:
        self._current_mode = initial_mode
        self._switch_history: List[ModeSwitchResult] = []
        self._mode_durations: Dict[OperationalMode, float] = {
            OperationalMode.MORGAN: 0.0,
            OperationalMode.MYCOSOFT: 0.0,
        }
        self._last_switch_time = datetime.now(timezone.utc)

    async def switch_mode(
        self,
        target: OperationalMode,
        requester: str,
        reason: str = "",
    ) -> ModeSwitchResult:
        """
        Switch operational mode.

        Mode switching preserves the coherent identity and relationship
        layer while changing scope and policy.
        """
        previous = self._current_mode

        if target == previous:
            return ModeSwitchResult(
                success=True,
                previous_mode=previous,
                new_mode=target,
                reason="Already in requested mode",
            )

        # Track time in previous mode
        now = datetime.now(timezone.utc)
        elapsed = (now - self._last_switch_time).total_seconds()
        self._mode_durations[previous] += elapsed
        self._last_switch_time = now

        self._current_mode = target
        result = ModeSwitchResult(
            success=True,
            previous_mode=previous,
            new_mode=target,
            reason=reason or f"Switched by {requester}",
        )
        self._switch_history.append(result)

        logger.info(
            "Mode switched: %s → %s (by %s: %s)",
            previous.value,
            target.value,
            requester,
            reason,
        )

        return result

    def get_current_mode(self) -> OperationalMode:
        """Get the current operational mode."""
        return self._current_mode

    def get_policy(self) -> ModePolicy:
        """Get the policy for the current mode."""
        return _MODE_POLICIES[self._current_mode]

    def get_policy_for_mode(self, mode: OperationalMode) -> ModePolicy:
        """Get the policy for a specific mode."""
        return _MODE_POLICIES[mode]

    def is_system_allowed(self, system: str) -> bool:
        """Check if a system is allowed in the current mode."""
        policy = self.get_policy()
        if system in policy.restricted_systems:
            return False
        return system in policy.allowed_systems

    def get_voice_style(self) -> Dict[str, float]:
        """Get voice style parameters for the current mode."""
        return self.get_policy().voice_style

    def get_switch_history(self) -> List[ModeSwitchResult]:
        """Return mode switch history."""
        return list(self._switch_history)

    def get_mode_info(self) -> Dict[str, Any]:
        """Return information about all modes."""
        return {
            mode.value: {
                "description": policy.description,
                "scope": policy.scope,
                "permission_level": policy.permission_level,
                "allowed_systems": policy.allowed_systems,
                "restricted_systems": policy.restricted_systems,
                "voice_style": policy.voice_style,
                "current": mode == self._current_mode,
            }
            for mode, policy in _MODE_POLICIES.items()
        }
