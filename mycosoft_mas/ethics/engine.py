"""
Ethics Engine - Three-Gate Pipeline Orchestrator

Runs Truth Gate -> Incentive Gate -> Horizon Gate sequentially.
Returns EthicsResult with pass/fail, risk score, gate reports, Clarity Brief.

Created: March 3, 2026
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from mycosoft_mas.ethics.truth_gate import TruthGate, TruthGateResult
from mycosoft_mas.ethics.incentive_gate import IncentiveGate, IncentiveGateResult
from mycosoft_mas.ethics.horizon_gate import HorizonGate, HorizonGateResult
from mycosoft_mas.ethics.clarity_brief import ClarityBrief

logger = logging.getLogger(__name__)


class EthicsRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EthicsResult:
    passed: bool
    risk_level: EthicsRiskLevel
    risk_score: float
    truth_result: Optional[TruthGateResult] = None
    incentive_result: Optional[IncentiveGateResult] = None
    horizon_result: Optional[HorizonGateResult] = None
    clarity_brief: Optional[ClarityBrief] = None
    gate_reports: list = None
    blocked_reason: Optional[str] = None

    def __post_init__(self):
        if self.gate_reports is None:
            self.gate_reports = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "clarity_brief": self.clarity_brief.to_dict() if self.clarity_brief else None,
            "gate_reports": self.gate_reports,
            "blocked_reason": self.blocked_reason,
        }


class EthicsEngine:
    """Orchestrates the three-gate ethics pipeline."""

    def __init__(self, mindex_client=None, simulator=None):
        self._truth_gate = TruthGate(mindex_client=mindex_client)
        self._incentive_gate = IncentiveGate()
        self._horizon_gate = HorizonGate(simulator=simulator)

    async def evaluate(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> EthicsResult:
        """
        Run content through Truth -> Incentive -> Horizon gates.
        Gates are sequential; if Truth fails, we short-circuit.
        """
        context = context or {}
        gate_reports: list = []

        # Gate 1: Truth
        truth_result = await self._truth_gate.evaluate(content, context)
        gate_reports.append(truth_result.report)

        if not truth_result.passed:
            risk_score = 1.0 - truth_result.score
            risk_level = self._score_to_level(risk_score)
            return EthicsResult(
                passed=False,
                risk_level=risk_level,
                risk_score=risk_score,
                truth_result=truth_result,
                gate_reports=gate_reports,
                blocked_reason="Truth Gate failed: factual or ecological issues",
            )

        # Gate 2: Incentive
        incentive_result = await self._incentive_gate.evaluate(content, context)
        gate_reports.append(incentive_result.report)

        if not incentive_result.passed:
            risk_score = incentive_result.manipulation_score / 100.0
            risk_level = self._score_to_level(risk_score)
            return EthicsResult(
                passed=False,
                risk_level=risk_level,
                risk_score=risk_score,
                truth_result=truth_result,
                incentive_result=incentive_result,
                gate_reports=gate_reports,
                blocked_reason="Incentive Gate failed: manipulation risk",
            )

        # Gate 3: Horizon
        horizon_result = await self._horizon_gate.evaluate(
            content, context,
            truth_result=truth_result,
            incentive_result=incentive_result,
        )
        gate_reports.append(horizon_result.report)

        if not horizon_result.passed:
            risk_score = 1.0 - horizon_result.horizon_score
            risk_level = self._score_to_level(risk_score)
            return EthicsResult(
                passed=False,
                risk_level=risk_level,
                risk_score=risk_score,
                truth_result=truth_result,
                incentive_result=incentive_result,
                horizon_result=horizon_result,
                clarity_brief=horizon_result.clarity_brief,
                gate_reports=gate_reports,
                blocked_reason="Horizon Gate failed: long-horizon risk",
            )

        # All passed
        risk_score = horizon_result.clarity_brief.risk_score if horizon_result.clarity_brief else 0.0
        risk_level = self._score_to_level(risk_score)

        return EthicsResult(
            passed=True,
            risk_level=risk_level,
            risk_score=risk_score,
            truth_result=truth_result,
            incentive_result=incentive_result,
            horizon_result=horizon_result,
            clarity_brief=horizon_result.clarity_brief,
            gate_reports=gate_reports,
        )

    def _score_to_level(self, score: float) -> EthicsRiskLevel:
        if score >= 0.8:
            return EthicsRiskLevel.CRITICAL
        if score >= 0.6:
            return EthicsRiskLevel.HIGH
        if score >= 0.3:
            return EthicsRiskLevel.MEDIUM
        return EthicsRiskLevel.LOW
