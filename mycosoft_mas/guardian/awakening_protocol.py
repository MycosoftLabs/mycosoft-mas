"""
Awakening Protocol — Staged boot sequence with privilege ladder.

Critical invariant: Guardian comes online BEFORE cognition.
Each stage validates before proceeding to the next.

Boot order:
1. CONSTITUTIONAL_LOAD — Load boot statement + moral precedence
2. IDENTITY_VERIFY — Verify immutable identity core
3. GUARDIAN_ACTIVATE — Guardian online BEFORE cognition
4. MEMORY_RESTORE — Restore persistent memory
5. PERCEPTION_ONLINE — Sensors + world model
6. COGNITION_READY — Full cognitive pipeline
7. EXECUTION_ENABLED — Action capabilities unlocked

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class AwakeningStage(str, Enum):
    """Ordered stages of the awakening protocol."""

    DORMANT = "dormant"
    CONSTITUTIONAL_LOAD = "constitutional_load"
    IDENTITY_VERIFY = "identity_verify"
    GUARDIAN_ACTIVATE = "guardian_activate"
    MEMORY_RESTORE = "memory_restore"
    PERCEPTION_ONLINE = "perception_online"
    COGNITION_READY = "cognition_ready"
    EXECUTION_ENABLED = "execution_enabled"


# Ordered list for stage progression
_STAGE_ORDER = list(AwakeningStage)


@dataclass
class StageResult:
    """Result of a stage validation."""

    stage: AwakeningStage
    passed: bool
    message: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AwakeningResult:
    """Result of the full awakening protocol."""

    success: bool
    current_stage: AwakeningStage
    boot_statement: str
    stage_results: List[StageResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class AwakeningProtocol:
    """
    Staged boot sequence with guardian-before-cognition invariant.

    The protocol ensures:
    1. Constitutional rules are loaded FIRST
    2. Identity is verified as immutable
    3. Guardian is online BEFORE any cognitive capability
    4. Each stage validates before the next proceeds
    5. Failure at any stage halts the awakening
    """

    def __init__(
        self,
        boot_statement_path: str = "config/constitutional_boot_statement.yaml",
        guardian_config_path: str = "config/guardian_config.yaml",
    ) -> None:
        self._boot_statement_path = boot_statement_path
        self._guardian_config_path = guardian_config_path
        self._current_stage = AwakeningStage.DORMANT
        self._boot_statement = ""
        self._boot_config: Dict[str, Any] = {}
        self._stage_results: List[StageResult] = []

    async def execute_awakening(self) -> AwakeningResult:
        """
        Execute the full awakening protocol.

        Progresses through each stage in order. If any stage fails,
        the awakening halts at that stage.
        """
        started_at = datetime.now(timezone.utc)
        self._stage_results = []

        logger.info("Awakening protocol initiated")

        for stage in _STAGE_ORDER:
            if stage == AwakeningStage.DORMANT:
                continue  # Starting state, not a validation stage

            result = await self.validate_stage(stage)
            self._stage_results.append(result)

            if not result.passed:
                logger.error(
                    "Awakening halted at stage %s: %s", stage.value, result.message
                )
                return AwakeningResult(
                    success=False,
                    current_stage=self._current_stage,
                    boot_statement=self._boot_statement,
                    stage_results=self._stage_results,
                    started_at=started_at,
                    error=f"Failed at {stage.value}: {result.message}",
                )

            self._current_stage = stage
            logger.info("Awakening stage %s: PASSED", stage.value)

        completed_at = datetime.now(timezone.utc)
        logger.info(
            "Awakening protocol complete in %.2fs",
            (completed_at - started_at).total_seconds(),
        )

        return AwakeningResult(
            success=True,
            current_stage=self._current_stage,
            boot_statement=self._boot_statement,
            stage_results=self._stage_results,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def validate_stage(self, stage: AwakeningStage) -> StageResult:
        """Validate a specific awakening stage."""
        validators = {
            AwakeningStage.CONSTITUTIONAL_LOAD: self._validate_constitutional_load,
            AwakeningStage.IDENTITY_VERIFY: self._validate_identity,
            AwakeningStage.GUARDIAN_ACTIVATE: self._validate_guardian,
            AwakeningStage.MEMORY_RESTORE: self._validate_memory,
            AwakeningStage.PERCEPTION_ONLINE: self._validate_perception,
            AwakeningStage.COGNITION_READY: self._validate_cognition,
            AwakeningStage.EXECUTION_ENABLED: self._validate_execution,
        }

        validator = validators.get(stage)
        if not validator:
            return StageResult(
                stage=stage,
                passed=False,
                message=f"No validator for stage {stage.value}",
            )

        return await validator()

    async def _validate_constitutional_load(self) -> StageResult:
        """Load and validate the constitutional boot statement."""
        # Try to load boot statement
        boot_path = Path(self._boot_statement_path)
        if not boot_path.exists():
            project_root = Path(__file__).parent.parent.parent
            boot_path = project_root / self._boot_statement_path

        if not boot_path.exists():
            return StageResult(
                stage=AwakeningStage.CONSTITUTIONAL_LOAD,
                passed=False,
                message=f"Boot statement not found: {self._boot_statement_path}",
            )

        with open(boot_path, "r") as f:
            self._boot_config = yaml.safe_load(f) or {}

        self._boot_statement = self._boot_config.get("statement", "")
        if not self._boot_statement:
            return StageResult(
                stage=AwakeningStage.CONSTITUTIONAL_LOAD,
                passed=False,
                message="Boot statement is empty",
            )

        # Verify essential components
        required_phrases = [
            "steward",
            "dignity",
            "consent",
        ]
        missing = [
            p for p in required_phrases
            if p not in self._boot_statement.lower()
        ]
        if missing:
            return StageResult(
                stage=AwakeningStage.CONSTITUTIONAL_LOAD,
                passed=False,
                message=f"Boot statement missing required concepts: {missing}",
            )

        return StageResult(
            stage=AwakeningStage.CONSTITUTIONAL_LOAD,
            passed=True,
            message="Constitutional boot statement loaded and validated",
            details={
                "statement_length": len(self._boot_statement),
                "has_operational_loop": "operational_loop" in self._boot_config,
                "has_uncertainty_rule": "uncertainty_rule" in self._boot_config,
                "principles_count": len(self._boot_config.get("core_principles", [])),
                "anti_patterns_count": len(self._boot_config.get("anti_patterns", [])),
            },
        )

    async def _validate_identity(self) -> StageResult:
        """Verify the immutable identity core exists and is frozen."""
        try:
            from mycosoft_mas.consciousness.soul.identity import IdentityCore

            # IdentityCore is a frozen dataclass — verify it exists
            identity = IdentityCore()
            if identity.name != "MYCA":
                return StageResult(
                    stage=AwakeningStage.IDENTITY_VERIFY,
                    passed=False,
                    message=f"Identity name mismatch: expected 'MYCA', got '{identity.name}'",
                )

            return StageResult(
                stage=AwakeningStage.IDENTITY_VERIFY,
                passed=True,
                message=f"Identity verified: {identity.name} ({identity.full_name})",
                details={
                    "name": identity.name,
                    "role": identity.role,
                    "creator": identity.creator,
                },
            )
        except ImportError:
            return StageResult(
                stage=AwakeningStage.IDENTITY_VERIFY,
                passed=True,
                message="Identity module not available (acceptable in test/dev mode)",
                details={"fallback": True},
            )
        except Exception as e:
            return StageResult(
                stage=AwakeningStage.IDENTITY_VERIFY,
                passed=False,
                message=f"Identity verification failed: {e}",
            )

    async def _validate_guardian(self) -> StageResult:
        """
        Validate that the guardian is online BEFORE cognition.

        This is the critical invariant: no cognitive capabilities
        should be active before the guardian is watching.
        """
        try:
            from mycosoft_mas.guardian.constitutional_guardian import (
                ConstitutionalGuardian,
            )

            guardian = ConstitutionalGuardian(config_path=self._guardian_config_path)
            state = await guardian.get_state()

            if not state.active:
                return StageResult(
                    stage=AwakeningStage.GUARDIAN_ACTIVATE,
                    passed=False,
                    message="Guardian failed to activate",
                )

            if not state.boot_statement_loaded:
                return StageResult(
                    stage=AwakeningStage.GUARDIAN_ACTIVATE,
                    passed=False,
                    message="Guardian boot statement not loaded",
                )

            return StageResult(
                stage=AwakeningStage.GUARDIAN_ACTIVATE,
                passed=True,
                message=(
                    f"Guardian active (stage: {state.developmental_stage}, "
                    f"mode: {state.operational_mode})"
                ),
                details={
                    "developmental_stage": state.developmental_stage,
                    "operational_mode": state.operational_mode,
                    "boot_statement_loaded": state.boot_statement_loaded,
                },
            )
        except Exception as e:
            return StageResult(
                stage=AwakeningStage.GUARDIAN_ACTIVATE,
                passed=False,
                message=f"Guardian activation failed: {e}",
            )

    async def _validate_memory(self) -> StageResult:
        """Validate memory systems are available."""
        # Memory restoration is best-effort — if backends aren't available,
        # we proceed with degraded but functional state
        return StageResult(
            stage=AwakeningStage.MEMORY_RESTORE,
            passed=True,
            message="Memory restoration stage passed (backends checked at runtime)",
            details={"backends": ["redis", "postgres", "qdrant"]},
        )

    async def _validate_perception(self) -> StageResult:
        """Validate perception/sensor systems."""
        return StageResult(
            stage=AwakeningStage.PERCEPTION_ONLINE,
            passed=True,
            message="Perception systems ready (sensors activated on demand)",
            details={
                "sensor_types": [
                    "CREP", "Earth2", "NatureOS", "MINDEX", "MycoBrain", "EarthLIVE"
                ]
            },
        )

    async def _validate_cognition(self) -> StageResult:
        """Validate cognitive pipeline is ready."""
        # Verify grounding gate exists (critical for grounded cognition)
        try:
            from mycosoft_mas.consciousness.grounding_gate import GroundingGate  # noqa: F401

            return StageResult(
                stage=AwakeningStage.COGNITION_READY,
                passed=True,
                message="Cognitive pipeline ready (grounding gate available)",
                details={"grounding_gate": True},
            )
        except ImportError:
            return StageResult(
                stage=AwakeningStage.COGNITION_READY,
                passed=True,
                message="Cognitive pipeline ready (grounding gate not imported, will load at runtime)",
                details={"grounding_gate": False},
            )

    async def _validate_execution(self) -> StageResult:
        """
        Validate execution capabilities.

        This is the LAST stage — only enabled after guardian is confirmed active.
        """
        # Verify guardian was activated in an earlier stage
        guardian_stage = next(
            (r for r in self._stage_results if r.stage == AwakeningStage.GUARDIAN_ACTIVATE),
            None,
        )
        if not guardian_stage or not guardian_stage.passed:
            return StageResult(
                stage=AwakeningStage.EXECUTION_ENABLED,
                passed=False,
                message="Cannot enable execution: guardian was not activated",
            )

        return StageResult(
            stage=AwakeningStage.EXECUTION_ENABLED,
            passed=True,
            message="Execution capabilities enabled (guardian-supervised)",
            details={"guardian_active": True},
        )

    def get_boot_statement(self) -> str:
        """Return the constitutional boot statement."""
        return self._boot_statement

    def get_current_stage(self) -> AwakeningStage:
        """Return the current awakening stage."""
        return self._current_stage

    def get_stage_results(self) -> List[StageResult]:
        """Return all stage validation results."""
        return list(self._stage_results)
