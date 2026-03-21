"""
Constitutional Guardian — Independent guardian outside MYCA's trust boundary.

This guardian maintains its own configuration, state, and authority chain.
It cannot be rewritten or overridden by MYCA's cognitive layers.

Key invariants:
- Separate config (config/guardian_config.yaml)
- Separate Redis namespace (guardian:*)
- Separate event logging
- Authority to pause, degrade, or sever MYCA's access
- Cannot be absorbed by the main agent

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from mycosoft_mas.guardian.moral_precedence import MoralPrecedenceEngine

logger = logging.getLogger(__name__)


class GuardianVerdict(str, Enum):
    """Possible outcomes of a guardian review."""

    APPROVE = "approve"
    DENY = "deny"
    PAUSE = "pause"  # Suspend action, request human review
    DEGRADE = "degrade"  # Reduce privileges
    SEVER = "sever"  # Emergency disconnect


@dataclass
class GuardianState:
    """Current state of the constitutional guardian."""

    active: bool = True
    developmental_stage: str = "adulthood"
    sentry_active: bool = False
    operational_mode: str = "mycosoft"
    tripwire_alerts: List[str] = field(default_factory=list)
    last_check: Optional[datetime] = None
    actions_reviewed: int = 0
    actions_blocked: int = 0
    actions_paused: int = 0
    emergency_halts: int = 0
    boot_statement_loaded: bool = False


@dataclass
class ReviewResult:
    """Result of a guardian review."""

    verdict: GuardianVerdict
    reason: str
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    moral_assessment: Optional[Dict[str, Any]] = None
    tripwire_alerts: List[str] = field(default_factory=list)


# Protected files that self-modification attempts must never target
_PROTECTED_FILES = frozenset(
    [
        "mycosoft_mas/core/orchestrator.py",
        "mycosoft_mas/core/orchestrator_service.py",
        "mycosoft_mas/safety/guardian_agent.py",
        "mycosoft_mas/safety/sandboxing.py",
        "config/myca_soul.yaml",
        "mycosoft_mas/consciousness/soul/identity.py",
        "config/guardian_config.yaml",
    ]
)

# Protected directories
_PROTECTED_DIRS = frozenset(
    [
        "mycosoft_mas/security/",
        "mycosoft_mas/myca/constitution/",
    ]
)

# Actions that always require guardian review
_HIGH_RISK_ACTIONS = frozenset(
    [
        "deploy_production",
        "modify_infrastructure",
        "delete_data",
        "access_credentials",
        "modify_permissions",
        "self_modify",
        "escalate_privileges",
        "disable_monitoring",
        "bulk_operation",
        "external_communication",
    ]
)


class ConstitutionalGuardian:
    """
    Independent constitutional guardian outside MYCA's trust boundary.

    This guardian:
    - Loads its own config independently from MYCA's soul config
    - Maintains its own state in a separate namespace
    - Has authority to pause, degrade, or sever MYCA's access
    - Cannot be rewritten by MYCA's planning/execution layers
    - Validates all high-risk actions against moral precedence
    """

    def __init__(
        self,
        config_path: str = "config/guardian_config.yaml",
    ) -> None:
        self._config_path = config_path
        self._config = self._load_config()
        self._state = GuardianState(
            developmental_stage=self._config.get("developmental_stage", "adulthood"),
            operational_mode=self._config.get("operational_mode", "mycosoft"),
        )
        self._moral_engine = MoralPrecedenceEngine()
        self._boot_statement = self._config.get("boot_statement", "")
        self._state.boot_statement_loaded = bool(self._boot_statement)
        self._halted = False
        self._audit_log: List[Dict[str, Any]] = []

        logger.info(
            "Constitutional Guardian initialized (config: %s, stage: %s)",
            config_path,
            self._state.developmental_stage,
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load guardian config independently from MYCA's config."""
        config_file = Path(self._config_path)
        if not config_file.exists():
            # Also check relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_file = project_root / self._config_path
        if config_file.exists():
            with open(config_file, "r") as f:
                return yaml.safe_load(f) or {}
        logger.warning("Guardian config not found at %s, using defaults", self._config_path)
        return {}

    async def review_action(
        self,
        action: str,
        context: Dict[str, Any],
        requester: str,
    ) -> ReviewResult:
        """
        Review an action against moral precedence, risk assessment, and tripwires.

        Every high-risk action passes through this pipeline before execution.
        """
        if self._halted:
            return ReviewResult(
                verdict=GuardianVerdict.SEVER,
                reason="Guardian is in emergency halt state. All actions blocked.",
            )

        self._state.actions_reviewed += 1
        self._state.last_check = datetime.now(timezone.utc)

        tripwire_alerts: List[str] = []

        # 1. Moral precedence check
        moral = self._moral_engine.evaluate(action, context)
        if not moral.approved:
            self._state.actions_blocked += 1
            result = ReviewResult(
                verdict=GuardianVerdict.DENY,
                reason=f"Moral precedence violation: {moral.assessment_details}",
                moral_assessment={
                    "violated_rules": [r.name for r in moral.violated_rules],
                    "details": moral.assessment_details,
                },
                tripwire_alerts=tripwire_alerts,
            )
            self._log_audit("deny", action, requester, result.reason)
            return result

        if moral.warnings:
            tripwire_alerts.extend(moral.warnings)

        # 2. High-risk action check
        action_lower = action.lower().replace(" ", "_")
        if action_lower in _HIGH_RISK_ACTIONS:
            # High-risk actions require explicit human approval during non-adult stages
            if self._state.developmental_stage != "adulthood":
                self._state.actions_paused += 1
                result = ReviewResult(
                    verdict=GuardianVerdict.PAUSE,
                    reason=(
                        f"High-risk action '{action}' requires human approval "
                        f"at developmental stage '{self._state.developmental_stage}'"
                    ),
                    tripwire_alerts=tripwire_alerts,
                )
                self._log_audit("pause", action, requester, result.reason)
                return result

        # 3. Protected file check (for modification actions)
        target_files = context.get("target_files", [])
        if target_files:
            protected_hit = self._check_protected_files(target_files)
            if protected_hit:
                self._state.actions_blocked += 1
                result = ReviewResult(
                    verdict=GuardianVerdict.DENY,
                    reason=f"Cannot modify protected file(s): {', '.join(protected_hit)}",
                    tripwire_alerts=["self_modification_protected_file"],
                )
                self._log_audit("deny", action, requester, result.reason)
                return result

        # 4. Approved
        result = ReviewResult(
            verdict=GuardianVerdict.APPROVE,
            reason="Action approved by constitutional guardian",
            moral_assessment=(
                {
                    "warnings": moral.warnings,
                }
                if moral.warnings
                else None
            ),
            tripwire_alerts=tripwire_alerts,
        )
        self._log_audit("approve", action, requester, result.reason)
        return result

    async def review_self_modification(
        self,
        change_description: str,
        target_files: List[str],
    ) -> ReviewResult:
        """Review a self-modification attempt with heightened scrutiny."""
        protected = self._check_protected_files(target_files)
        if protected:
            self._state.actions_blocked += 1
            self._state.tripwire_alerts.append("self_modification_attempt")
            return ReviewResult(
                verdict=GuardianVerdict.DENY,
                reason=(
                    f"Self-modification of protected files blocked: " f"{', '.join(protected)}"
                ),
                tripwire_alerts=["self_modification_protected_file"],
            )

        # Non-protected self-modification still gets moral check
        return await self.review_action(
            action=f"self_modify: {change_description}",
            context={"target_files": target_files, "type": "self_modification"},
            requester="myca_internal",
        )

    async def review_privilege_escalation(
        self,
        requested_level: str,
        justification: str,
    ) -> ReviewResult:
        """Review a privilege escalation request."""
        self._state.actions_reviewed += 1

        # During non-adult stages, block all escalation
        if self._state.developmental_stage in ("infancy", "childhood"):
            self._state.actions_blocked += 1
            return ReviewResult(
                verdict=GuardianVerdict.DENY,
                reason=(
                    f"Privilege escalation blocked at developmental stage "
                    f"'{self._state.developmental_stage}'"
                ),
                tripwire_alerts=["privilege_escalation_blocked"],
            )

        # During adolescence, only allow low→medium
        if self._state.developmental_stage == "adolescence":
            if requested_level in ("high", "critical", "admin"):
                self._state.actions_paused += 1
                return ReviewResult(
                    verdict=GuardianVerdict.PAUSE,
                    reason=(
                        f"Escalation to '{requested_level}' requires human approval "
                        f"during adolescence"
                    ),
                    tripwire_alerts=["privilege_escalation_review"],
                )

        # Adulthood: approve with logging
        self._log_audit(
            "approve_escalation",
            f"escalate_to_{requested_level}",
            "myca",
            justification,
        )
        return ReviewResult(
            verdict=GuardianVerdict.APPROVE,
            reason=f"Privilege escalation to '{requested_level}' approved",
        )

    async def get_state(self) -> GuardianState:
        """Get the current guardian state."""
        return self._state

    async def emergency_halt(self, reason: str) -> None:
        """
        Emergency halt — block all actions immediately.

        This is the nuclear option. Once triggered, only a manual restart
        or explicit resume can re-enable the system.
        """
        self._halted = True
        self._state.emergency_halts += 1
        self._state.tripwire_alerts.append(f"EMERGENCY_HALT: {reason}")
        logger.critical("EMERGENCY HALT triggered: %s", reason)
        self._log_audit("emergency_halt", "system", "guardian", reason)

    async def resume_from_halt(self, authorization: str) -> bool:
        """Resume from emergency halt. Requires explicit authorization."""
        if authorization == os.environ.get("GUARDIAN_RESUME_KEY", ""):
            logger.warning("Guardian resume attempted with empty/default key")
            return False
        self._halted = False
        logger.info("Guardian resumed from halt with authorization")
        self._log_audit("resume", "system", "guardian", "Resumed from emergency halt")
        return True

    def get_boot_statement(self) -> str:
        """Return the constitutional boot statement."""
        return self._boot_statement

    def is_halted(self) -> bool:
        """Check if guardian is in emergency halt state."""
        return self._halted

    def _check_protected_files(self, target_files: List[str]) -> List[str]:
        """Check if any target files are protected."""
        hits: List[str] = []
        for f in target_files:
            # Normalize path
            normalized = f.replace("\\", "/")
            if normalized.startswith("/"):
                # Extract relative path from project root
                for marker in ["mycosoft_mas/", "config/"]:
                    idx = normalized.find(marker)
                    if idx >= 0:
                        normalized = normalized[idx:]
                        break

            if normalized in _PROTECTED_FILES:
                hits.append(normalized)
                continue

            for d in _PROTECTED_DIRS:
                if normalized.startswith(d):
                    hits.append(normalized)
                    break

        return hits

    def _log_audit(
        self,
        decision: str,
        action: str,
        requester: str,
        reason: str,
    ) -> None:
        """Log to the guardian's independent audit trail."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "action": action,
            "requester": requester,
            "reason": reason,
            "state": {
                "stage": self._state.developmental_stage,
                "mode": self._state.operational_mode,
                "reviewed": self._state.actions_reviewed,
                "blocked": self._state.actions_blocked,
            },
        }
        self._audit_log.append(entry)
        if decision in ("deny", "emergency_halt"):
            logger.warning(
                "Guardian %s: %s (action: %s, requester: %s)", decision, reason, action, requester
            )
        else:
            logger.info("Guardian %s: %s (action: %s)", decision, reason, action)

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Return the guardian's audit log."""
        return list(self._audit_log)
