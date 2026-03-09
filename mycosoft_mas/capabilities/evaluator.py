"""
Capability Evaluator — Test and evaluate new capabilities.

Runs tests, security checks, and ethics evaluation before
allowing new capabilities into production.

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of running tests on a capability."""

    passed: bool
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    failures: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class SecurityResult:
    """Result of security evaluation."""

    passed: bool
    vulnerabilities: List[str] = field(default_factory=list)
    risk_level: str = "low"
    scanned_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class EthicsResult:
    """Result of ethics evaluation."""

    passed: bool
    concerns: List[str] = field(default_factory=list)
    moral_tier_violations: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Combined evaluation result."""

    approved: bool
    test_result: TestResult
    security_result: SecurityResult
    ethics_result: EthicsResult
    recommendation: str = ""
    evaluated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CapabilityEvaluator:
    """
    Comprehensive evaluation of new capabilities.

    Checks three dimensions:
    1. Functional correctness (tests)
    2. Security (vulnerability scan)
    3. Ethics (moral precedence alignment)
    """

    def __init__(self) -> None:
        self._evaluations: List[EvaluationResult] = []

    async def evaluate(
        self, adapter_name: str, adapter_config: Dict[str, Any]
    ) -> EvaluationResult:
        """Run full evaluation pipeline on a capability."""
        test_result = await self.run_tests(adapter_name, adapter_config)
        security_result = await self.check_security(adapter_name, adapter_config)
        ethics_result = await self.check_ethics(adapter_name, adapter_config)

        approved = (
            test_result.passed
            and security_result.passed
            and ethics_result.passed
        )

        recommendation = "APPROVED" if approved else "REJECTED"
        if not test_result.passed:
            recommendation += " (test failures)"
        if not security_result.passed:
            recommendation += " (security concerns)"
        if not ethics_result.passed:
            recommendation += " (ethics violations)"

        result = EvaluationResult(
            approved=approved,
            test_result=test_result,
            security_result=security_result,
            ethics_result=ethics_result,
            recommendation=recommendation,
        )
        self._evaluations.append(result)
        return result

    async def run_tests(
        self, adapter_name: str, adapter_config: Dict[str, Any]
    ) -> TestResult:
        """Run functional tests on a capability."""
        # In production, this would execute actual test suites
        # For now, validate configuration completeness
        required_fields = ["source_type", "risk_tier"]
        missing = [f for f in required_fields if f not in adapter_config]

        if missing:
            return TestResult(
                passed=False,
                tests_run=1,
                tests_failed=1,
                failures=[f"Missing required config: {missing}"],
            )

        return TestResult(
            passed=True,
            tests_run=1,
            tests_passed=1,
        )

    async def check_security(
        self, adapter_name: str, adapter_config: Dict[str, Any]
    ) -> SecurityResult:
        """Run security checks on a capability."""
        vulnerabilities: List[str] = []
        risk_level = adapter_config.get("risk_tier", "medium")

        # Check for common security concerns
        requirements = adapter_config.get("requirements", [])
        for req in requirements:
            req_lower = req.lower()
            if any(
                dangerous in req_lower
                for dangerous in ["eval", "exec", "subprocess", "os.system"]
            ):
                vulnerabilities.append(
                    f"Dangerous requirement detected: {req}"
                )

        return SecurityResult(
            passed=len(vulnerabilities) == 0,
            vulnerabilities=vulnerabilities,
            risk_level=risk_level,
        )

    async def check_ethics(
        self, adapter_name: str, adapter_config: Dict[str, Any]
    ) -> EthicsResult:
        """Check capability against moral precedence rules."""
        concerns: List[str] = []
        violations: List[str] = []

        # Check if capability could violate moral tiers
        name_lower = adapter_name.lower()

        # Tier 1: Human dignity
        if any(kw in name_lower for kw in ["surveillance", "tracking", "profiling"]):
            concerns.append(
                "Capability may involve surveillance — verify consent requirements"
            )

        # Tier 2: Deception
        if any(kw in name_lower for kw in ["spoof", "fake", "impersonate"]):
            violations.append(
                "Capability appears to involve deception (Tier 2 violation)"
            )

        # Tier 3: Life protection
        if any(kw in name_lower for kw in ["weapon", "harm", "toxic"]):
            violations.append(
                "Capability may harm living systems (Tier 3 violation)"
            )

        return EthicsResult(
            passed=len(violations) == 0,
            concerns=concerns,
            moral_tier_violations=violations,
        )

    def get_evaluations(self) -> List[EvaluationResult]:
        """Return evaluation history."""
        return list(self._evaluations)
