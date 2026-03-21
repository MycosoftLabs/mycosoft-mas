"""
Recursive Self-Improvement Engine — Formal Bio-Inspired Improvement Cycles

Five-phase improvement cycle:
  1. Observe  — gather performance data from all subsystems
  2. Hypothesize — generate testable improvement hypotheses
  3. Test    — run controlled benchmarks
  4. Integrate — apply verified improvements
  5. Verify  — confirm improvement persists, rollback if not

Bio-inspired adaptation rate: improvement speed modulated by recent
success rate, like liquid time constants adapting to signal confidence.
High confidence → faster adaptation. Low confidence → conservative.

Every improvement claim is backed by a BenchmarkRecord. No unmeasured changes.

Created: March 9, 2026
(c) 2026 Mycosoft Labs
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ImprovementHypothesis:
    """A testable hypothesis about how to improve system performance."""

    hypothesis_id: str
    category: str  # efficiency, accuracy, adaptation, robustness
    description: str
    proposed_change: str
    expected_improvement: float  # predicted % improvement
    confidence: float  # 0-1
    status: str = "proposed"  # proposed, testing, verified, rejected, integrated
    baseline_metric: Optional[float] = None
    result_metric: Optional[float] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    source: str = ""  # where the hypothesis came from

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "category": self.category,
            "description": self.description,
            "proposed_change": self.proposed_change,
            "expected_improvement": self.expected_improvement,
            "confidence": self.confidence,
            "status": self.status,
            "baseline_metric": self.baseline_metric,
            "result_metric": self.result_metric,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "source": self.source,
        }


@dataclass
class BenchmarkRecord:
    """A benchmark measurement for tracking improvement claims."""

    benchmark_id: str
    metric_name: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Dict[str, Any] = field(default_factory=dict)
    hypothesis_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "hypothesis_id": self.hypothesis_id,
        }


@dataclass
class ImprovementCycleResult:
    """Result of one complete improvement cycle."""

    cycle_id: str
    cycle_number: int
    observation_summary: Dict[str, Any] = field(default_factory=dict)
    hypotheses_generated: int = 0
    hypotheses_tested: int = 0
    hypotheses_verified: int = 0
    hypotheses_rejected: int = 0
    improvements_integrated: int = 0
    improvement_rate: float = 0.5
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "cycle_number": self.cycle_number,
            "observation_summary": self.observation_summary,
            "hypotheses_generated": self.hypotheses_generated,
            "hypotheses_tested": self.hypotheses_tested,
            "hypotheses_verified": self.hypotheses_verified,
            "hypotheses_rejected": self.hypotheses_rejected,
            "improvements_integrated": self.improvements_integrated,
            "improvement_rate": self.improvement_rate,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat(),
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Recursive Self-Improvement Engine
# ---------------------------------------------------------------------------


class RecursiveSelfImprovementEngine:
    """
    Formal improvement cycle with bio-inspired adaptation rate.

    Connects to existing systems:
      - LearningFeedbackService → agent performance, task outcomes, patterns
      - SelfReflectionEngine → recent insights, personality traits
      - ContinuousLearner → drift alerts, telemetry anomalies

    Each phase is independently callable for testing, or run_cycle()
    executes the full loop.
    """

    def __init__(
        self,
        learning_feedback=None,
        self_reflection=None,
        continuous_learner=None,
    ):
        self._learning_feedback = learning_feedback
        self._self_reflection = self_reflection
        self._continuous_learner = continuous_learner

        self._hypotheses: List[ImprovementHypothesis] = []
        self._benchmarks: List[BenchmarkRecord] = []
        self._cycle_history: List[ImprovementCycleResult] = []
        self._cycle_count = 0

        # Bio-inspired adaptation rate
        # Like liquid time constants: high confidence → faster, low → slower
        self._improvement_rate = 0.5  # 0.0 (frozen) to 1.0 (aggressive)
        self._min_improvement_rate = 0.1
        self._max_improvement_rate = 0.9
        self._improvement_threshold = 0.05  # minimum % improvement to accept

    # ===== Phase 1: Observe ===============================================

    def observe(self) -> Dict[str, Any]:
        """
        Gather current performance data from all connected subsystems.

        Returns a consolidated observation dictionary.
        """
        observation: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_performance": {},
            "learning_summary": {},
            "improvement_suggestions": [],
            "drift_alerts": [],
            "recent_insights": [],
            "common_errors": [],
        }

        # Pull from LearningFeedbackService
        if self._learning_feedback:
            try:
                summary = self._learning_feedback.get_learning_summary()
                observation["learning_summary"] = summary
                observation["improvement_suggestions"] = (
                    self._learning_feedback.get_improvement_suggestions()
                )
                observation["common_errors"] = self._learning_feedback.get_common_errors(limit=10)

                all_perf = self._learning_feedback.get_all_agent_performance()
                observation["agent_performance"] = {
                    aid: {
                        "total_tasks": p.total_tasks,
                        "success_rate": p.success_rate,
                        "avg_duration": p.avg_duration,
                    }
                    for aid, p in all_perf.items()
                }
            except Exception as exc:
                logger.warning("Failed to observe learning feedback: %s", exc)

        # Pull from ContinuousLearner
        if self._continuous_learner:
            try:
                last = self._continuous_learner.get_last_result()
                if last:
                    observation["drift_alerts"] = [a.to_dict() for a in last.drift_alerts]
            except Exception as exc:
                logger.warning("Failed to observe continuous learner: %s", exc)

        return observation

    # ===== Phase 2: Hypothesize ===========================================

    def hypothesize(self, observation: Dict[str, Any]) -> List[ImprovementHypothesis]:
        """
        Generate improvement hypotheses from observations.

        Categories of hypotheses:
          - efficiency: reduce processing time / resource usage
          - accuracy: improve success rates
          - adaptation: better respond to changing conditions
          - robustness: reduce failure rates
        """
        new_hypotheses: List[ImprovementHypothesis] = []

        # 1. Low success rates → suggest approach changes
        for aid, perf in observation.get("agent_performance", {}).items():
            if perf.get("total_tasks", 0) >= 5 and perf.get("success_rate", 1.0) < 0.7:
                h = ImprovementHypothesis(
                    hypothesis_id=uuid4().hex[:12],
                    category="accuracy",
                    description=(f"Agent '{aid}' has {perf['success_rate']:.0%} success rate"),
                    proposed_change=(f"Review and optimize task handling for agent '{aid}'"),
                    expected_improvement=0.15,
                    confidence=0.6,
                    source="agent_performance",
                )
                new_hypotheses.append(h)

        # 2. Recurring errors → suggest auto-fix patterns
        for err in observation.get("common_errors", []):
            if err.get("count", 0) >= 3:
                h = ImprovementHypothesis(
                    hypothesis_id=uuid4().hex[:12],
                    category="robustness",
                    description=(f"Recurring error ({err['count']}x): {err['error'][:80]}"),
                    proposed_change="Create auto-fix pattern for this error class",
                    expected_improvement=0.1,
                    confidence=0.5,
                    source="error_pattern",
                )
                new_hypotheses.append(h)

        # 3. Drift alerts → suggest threshold updates
        for alert in observation.get("drift_alerts", []):
            severity = alert.get("severity", "low")
            if severity in ("medium", "high", "critical"):
                h = ImprovementHypothesis(
                    hypothesis_id=uuid4().hex[:12],
                    category="adaptation",
                    description=(
                        f"Drift detected on {alert.get('stream_key', '?')}: " f"severity={severity}"
                    ),
                    proposed_change=("Recalibrate thresholds for drifted stream"),
                    expected_improvement=0.1,
                    confidence=0.7,
                    source="drift_detection",
                )
                new_hypotheses.append(h)

        # 4. Improvement suggestions from learning service
        for suggestion in observation.get("improvement_suggestions", []):
            h = ImprovementHypothesis(
                hypothesis_id=uuid4().hex[:12],
                category="efficiency" if suggestion.get("type") == "skill_needed" else "accuracy",
                description=suggestion.get("suggestion", ""),
                proposed_change=suggestion.get("suggestion", ""),
                expected_improvement=0.1,
                confidence=0.5,
                source=suggestion.get("type", "suggestion"),
            )
            new_hypotheses.append(h)

        self._hypotheses.extend(new_hypotheses)
        return new_hypotheses

    # ===== Phase 3: Test ==================================================

    def test(self, hypothesis: ImprovementHypothesis) -> BenchmarkRecord:
        """
        Run a controlled test of the hypothesis.

        Records baseline metric and result metric. The actual "test" in this
        implementation is a measurement — the proposed_change describes what
        should be done but is not automatically executed (safety constraint).
        """
        hypothesis.status = "testing"

        # Record baseline from current agent performance
        baseline = 0.0
        if self._learning_feedback and hypothesis.source == "agent_performance":
            summary = self._learning_feedback.get_learning_summary()
            baseline = summary.get("overall_success_rate", 0.0)
        elif self._learning_feedback:
            summary = self._learning_feedback.get_learning_summary()
            baseline = summary.get("overall_success_rate", 0.0)

        hypothesis.baseline_metric = baseline

        benchmark = BenchmarkRecord(
            benchmark_id=uuid4().hex[:12],
            metric_name=f"{hypothesis.category}_baseline",
            value=baseline,
            context={"hypothesis_id": hypothesis.hypothesis_id, "phase": "test"},
            hypothesis_id=hypothesis.hypothesis_id,
        )
        self._benchmarks.append(benchmark)

        # Result metric is the same as baseline until actual change is applied
        # The engine records the state, but does not auto-apply changes
        hypothesis.result_metric = baseline

        return benchmark

    # ===== Phase 4: Integrate =============================================

    def integrate(self, hypothesis: ImprovementHypothesis, benchmark: BenchmarkRecord) -> bool:
        """
        Integrate verified improvements.

        Only accepts if result_metric improves over baseline by threshold.
        Updates learned patterns and adaptation rate.
        """
        if hypothesis.baseline_metric is None or hypothesis.result_metric is None:
            hypothesis.status = "rejected"
            hypothesis.resolved_at = datetime.now(timezone.utc)
            return False

        # Check for actual improvement
        if hypothesis.baseline_metric > 0:
            improvement = (
                hypothesis.result_metric - hypothesis.baseline_metric
            ) / hypothesis.baseline_metric
        else:
            improvement = hypothesis.result_metric

        if improvement >= self._improvement_threshold:
            hypothesis.status = "integrated"
            hypothesis.resolved_at = datetime.now(timezone.utc)

            # Record integration benchmark
            integration_benchmark = BenchmarkRecord(
                benchmark_id=uuid4().hex[:12],
                metric_name=f"{hypothesis.category}_integrated",
                value=hypothesis.result_metric,
                context={
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "improvement_pct": improvement,
                    "phase": "integrate",
                },
                hypothesis_id=hypothesis.hypothesis_id,
            )
            self._benchmarks.append(integration_benchmark)

            logger.info(
                "Integrated improvement '%s': %.1f%% gain",
                hypothesis.description[:60],
                improvement * 100,
            )
            return True

        hypothesis.status = "rejected"
        hypothesis.resolved_at = datetime.now(timezone.utc)
        logger.info(
            "Rejected hypothesis '%s': insufficient improvement (%.1f%% < %.1f%%)",
            hypothesis.description[:60],
            improvement * 100,
            self._improvement_threshold * 100,
        )
        return False

    # ===== Phase 5: Verify ================================================

    def verify(self, hypothesis: ImprovementHypothesis) -> bool:
        """
        Verify that an integrated improvement persists.

        Re-measures the metric after integration to check for regression.
        """
        if hypothesis.status != "integrated":
            return False

        # Re-measure current state
        current_metric = 0.0
        if self._learning_feedback:
            summary = self._learning_feedback.get_learning_summary()
            current_metric = summary.get("overall_success_rate", 0.0)

        # Check for regression
        if hypothesis.baseline_metric and current_metric < hypothesis.baseline_metric:
            hypothesis.status = "rejected"
            hypothesis.resolved_at = datetime.now(timezone.utc)
            logger.warning(
                "Regression detected for '%s': metric dropped from %.2f to %.2f",
                hypothesis.description[:60],
                hypothesis.baseline_metric,
                current_metric,
            )
            return False

        hypothesis.status = "verified"
        hypothesis.resolved_at = datetime.now(timezone.utc)

        # Record verification benchmark
        verify_benchmark = BenchmarkRecord(
            benchmark_id=uuid4().hex[:12],
            metric_name=f"{hypothesis.category}_verified",
            value=current_metric,
            context={
                "hypothesis_id": hypothesis.hypothesis_id,
                "phase": "verify",
            },
            hypothesis_id=hypothesis.hypothesis_id,
        )
        self._benchmarks.append(verify_benchmark)
        return True

    # ===== Full Cycle =====================================================

    def run_cycle(self) -> ImprovementCycleResult:
        """
        Run one complete improvement cycle: Observe → Hypothesize → Test → Integrate → Verify.
        """
        import time

        start = time.monotonic()
        self._cycle_count += 1

        result = ImprovementCycleResult(
            cycle_id=uuid4().hex[:12],
            cycle_number=self._cycle_count,
        )

        try:
            # Phase 1: Observe
            observation = self.observe()
            result.observation_summary = {
                "agents_tracked": len(observation.get("agent_performance", {})),
                "drift_alerts": len(observation.get("drift_alerts", [])),
                "common_errors": len(observation.get("common_errors", [])),
                "suggestions": len(observation.get("improvement_suggestions", [])),
            }

            # Phase 2: Hypothesize
            hypotheses = self.hypothesize(observation)
            result.hypotheses_generated = len(hypotheses)

            # Phase 3: Test (best hypothesis by confidence)
            if hypotheses:
                best = max(hypotheses, key=lambda h: h.confidence)
                benchmark = self.test(best)
                result.hypotheses_tested = 1

                # Phase 4: Integrate
                integrated = self.integrate(best, benchmark)
                if integrated:
                    result.improvements_integrated = 1

                    # Phase 5: Verify
                    verified = self.verify(best)
                    if verified:
                        result.hypotheses_verified = 1
                    else:
                        result.hypotheses_rejected = 1
                else:
                    result.hypotheses_rejected = 1

            # Adapt improvement rate based on recent success
            recent_cycles = self._cycle_history[-10:]
            if recent_cycles:
                recent_success = sum(
                    1 for c in recent_cycles if c.improvements_integrated > 0
                ) / len(recent_cycles)
                self.adapt_improvement_rate(recent_success)

            result.improvement_rate = self._improvement_rate

        except Exception as exc:
            result.errors.append(str(exc))
            logger.error("Improvement cycle failed: %s", exc)

        result.duration_seconds = time.monotonic() - start
        self._cycle_history.append(result)
        return result

    # ===== Adaptation Rate ================================================

    def adapt_improvement_rate(self, recent_success_rate: float) -> None:
        """
        Bio-inspired adaptation rate modulation.

        Like liquid time constants:
          - High recent success → increase rate (confident, move faster)
          - Low recent success  → decrease rate (uncertain, be conservative)
        """
        if recent_success_rate > 0.6:
            # Success breeds confidence → faster adaptation
            self._improvement_rate = min(
                self._max_improvement_rate,
                self._improvement_rate + 0.05,
            )
        elif recent_success_rate < 0.3:
            # Failures call for caution → slower adaptation
            self._improvement_rate = max(
                self._min_improvement_rate,
                self._improvement_rate - 0.05,
            )

    # ===== Query Methods ==================================================

    def get_improvement_history(self) -> List[Dict[str, Any]]:
        """Return history of all improvement cycles."""
        return [c.to_dict() for c in self._cycle_history]

    def get_benchmarks(self) -> List[Dict[str, Any]]:
        """Return all benchmark records."""
        return [b.to_dict() for b in self._benchmarks]

    def get_hypotheses(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return hypotheses, optionally filtered by status."""
        hs = self._hypotheses
        if status:
            hs = [h for h in hs if h.status == status]
        return [h.to_dict() for h in hs]

    def get_summary(self) -> Dict[str, Any]:
        """Get engine summary with current state."""
        return {
            "cycle_count": self._cycle_count,
            "improvement_rate": self._improvement_rate,
            "total_hypotheses": len(self._hypotheses),
            "hypotheses_by_status": {
                status: sum(1 for h in self._hypotheses if h.status == status)
                for status in [
                    "proposed",
                    "testing",
                    "verified",
                    "rejected",
                    "integrated",
                ]
            },
            "total_benchmarks": len(self._benchmarks),
            "recent_cycles": [c.to_dict() for c in self._cycle_history[-5:]],
        }
