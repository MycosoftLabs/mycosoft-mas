"""
Tests for Recursive Self-Improvement Engine.

Validates:
  - Five-phase improvement cycle (observe → hypothesize → test → integrate → verify)
  - Bio-inspired adaptation rate modulation
  - Benchmark tracking
  - Hypothesis management
"""

import pytest

from mycosoft_mas.engines.recursive_improvement.engine import (
    BenchmarkRecord,
    ImprovementCycleResult,
    ImprovementHypothesis,
    RecursiveSelfImprovementEngine,
)


class TestImprovementHypothesis:
    """Test hypothesis data class."""

    def test_to_dict(self):
        h = ImprovementHypothesis(
            hypothesis_id="h1",
            category="accuracy",
            description="Test hypothesis",
            proposed_change="Change something",
            expected_improvement=0.1,
            confidence=0.8,
        )
        d = h.to_dict()
        assert d["hypothesis_id"] == "h1"
        assert d["category"] == "accuracy"
        assert d["status"] == "proposed"


class TestBenchmarkRecord:
    """Test benchmark data class."""

    def test_to_dict(self):
        b = BenchmarkRecord(
            benchmark_id="b1",
            metric_name="success_rate",
            value=0.85,
        )
        d = b.to_dict()
        assert d["benchmark_id"] == "b1"
        assert d["value"] == 0.85


class TestRecursiveSelfImprovementEngine:
    """Test the improvement engine."""

    def test_init(self):
        engine = RecursiveSelfImprovementEngine()
        assert engine._cycle_count == 0
        assert engine._improvement_rate == 0.5
        assert len(engine._hypotheses) == 0

    def test_observe_no_services(self):
        """Observe without connected services should return empty observation."""
        engine = RecursiveSelfImprovementEngine()
        obs = engine.observe()
        assert "timestamp" in obs
        assert obs["agent_performance"] == {}

    def test_observe_with_learning_feedback(self):
        """Observe with learning feedback service should pull data."""
        from mycosoft_mas.services.learning_feedback import LearningFeedbackService

        lfs = LearningFeedbackService()
        lfs.record_outcome("test_task", "agent1", True, 1.0)
        lfs.record_outcome("test_task", "agent1", False, 2.0, error_message="fail")

        engine = RecursiveSelfImprovementEngine(learning_feedback=lfs)
        obs = engine.observe()
        assert "agent1" in obs["agent_performance"]

    def test_hypothesize_from_low_success_rate(self):
        """Should generate hypothesis for agent with low success rate."""
        engine = RecursiveSelfImprovementEngine()
        obs = {
            "agent_performance": {
                "bad_agent": {"total_tasks": 10, "success_rate": 0.3, "avg_duration": 5.0}
            },
            "common_errors": [],
            "drift_alerts": [],
            "improvement_suggestions": [],
        }
        hypotheses = engine.hypothesize(obs)
        assert len(hypotheses) >= 1
        assert hypotheses[0].category == "accuracy"
        assert "bad_agent" in hypotheses[0].description

    def test_hypothesize_from_recurring_errors(self):
        """Should generate hypothesis for recurring errors."""
        engine = RecursiveSelfImprovementEngine()
        obs = {
            "agent_performance": {},
            "common_errors": [{"error": "Connection timeout", "count": 5}],
            "drift_alerts": [],
            "improvement_suggestions": [],
        }
        hypotheses = engine.hypothesize(obs)
        assert len(hypotheses) >= 1
        assert hypotheses[0].category == "robustness"

    def test_hypothesize_from_drift(self):
        """Should generate hypothesis for drift alerts."""
        engine = RecursiveSelfImprovementEngine()
        obs = {
            "agent_performance": {},
            "common_errors": [],
            "drift_alerts": [
                {"stream_key": "sensor_temp", "severity": "high"}
            ],
            "improvement_suggestions": [],
        }
        hypotheses = engine.hypothesize(obs)
        assert len(hypotheses) >= 1
        assert hypotheses[0].category == "adaptation"

    def test_test_phase(self):
        """Test phase should record baseline and create benchmark."""
        engine = RecursiveSelfImprovementEngine()
        h = ImprovementHypothesis(
            hypothesis_id="h1",
            category="accuracy",
            description="test",
            proposed_change="test",
            expected_improvement=0.1,
            confidence=0.5,
            source="test",
        )
        benchmark = engine.test(h)
        assert h.status == "testing"
        assert h.baseline_metric is not None
        assert isinstance(benchmark, BenchmarkRecord)
        assert len(engine._benchmarks) == 1

    def test_integrate_insufficient_improvement(self):
        """Should reject hypothesis with insufficient improvement."""
        engine = RecursiveSelfImprovementEngine()
        h = ImprovementHypothesis(
            hypothesis_id="h1",
            category="accuracy",
            description="test",
            proposed_change="test",
            expected_improvement=0.1,
            confidence=0.5,
        )
        h.baseline_metric = 0.8
        h.result_metric = 0.81  # Only 1.25% improvement, below 5% threshold

        b = BenchmarkRecord(benchmark_id="b1", metric_name="test", value=0.81)
        result = engine.integrate(h, b)
        assert result is False
        assert h.status == "rejected"

    def test_integrate_sufficient_improvement(self):
        """Should accept hypothesis with sufficient improvement."""
        engine = RecursiveSelfImprovementEngine()
        h = ImprovementHypothesis(
            hypothesis_id="h1",
            category="accuracy",
            description="test",
            proposed_change="test",
            expected_improvement=0.2,
            confidence=0.8,
        )
        h.baseline_metric = 0.5
        h.result_metric = 0.7  # 40% improvement

        b = BenchmarkRecord(benchmark_id="b1", metric_name="test", value=0.7)
        result = engine.integrate(h, b)
        assert result is True
        assert h.status == "integrated"

    def test_run_cycle_empty(self):
        """Full cycle with no data should complete without errors."""
        engine = RecursiveSelfImprovementEngine()
        result = engine.run_cycle()
        assert isinstance(result, ImprovementCycleResult)
        assert result.cycle_number == 1
        assert len(result.errors) == 0

    def test_run_cycle_increments(self):
        """Each cycle should increment the counter."""
        engine = RecursiveSelfImprovementEngine()
        engine.run_cycle()
        engine.run_cycle()
        assert engine._cycle_count == 2

    def test_adapt_improvement_rate_success(self):
        """High success should increase improvement rate."""
        engine = RecursiveSelfImprovementEngine()
        initial_rate = engine._improvement_rate
        engine.adapt_improvement_rate(0.8)
        assert engine._improvement_rate > initial_rate

    def test_adapt_improvement_rate_failure(self):
        """Low success should decrease improvement rate."""
        engine = RecursiveSelfImprovementEngine()
        initial_rate = engine._improvement_rate
        engine.adapt_improvement_rate(0.1)
        assert engine._improvement_rate < initial_rate

    def test_adapt_rate_bounds(self):
        """Rate should stay within bounds."""
        engine = RecursiveSelfImprovementEngine()
        # Drive rate up
        for _ in range(50):
            engine.adapt_improvement_rate(1.0)
        assert engine._improvement_rate <= engine._max_improvement_rate

        # Drive rate down
        for _ in range(50):
            engine.adapt_improvement_rate(0.0)
        assert engine._improvement_rate >= engine._min_improvement_rate

    def test_get_summary(self):
        """Summary should include all key fields."""
        engine = RecursiveSelfImprovementEngine()
        engine.run_cycle()
        summary = engine.get_summary()
        assert summary["cycle_count"] == 1
        assert "improvement_rate" in summary
        assert "hypotheses_by_status" in summary

    def test_get_hypotheses_filtered(self):
        """Should filter hypotheses by status."""
        engine = RecursiveSelfImprovementEngine()
        engine._hypotheses.append(
            ImprovementHypothesis(
                hypothesis_id="h1",
                category="accuracy",
                description="a",
                proposed_change="b",
                expected_improvement=0.1,
                confidence=0.5,
                status="verified",
            )
        )
        engine._hypotheses.append(
            ImprovementHypothesis(
                hypothesis_id="h2",
                category="accuracy",
                description="c",
                proposed_change="d",
                expected_improvement=0.1,
                confidence=0.5,
                status="rejected",
            )
        )

        verified = engine.get_hypotheses(status="verified")
        assert len(verified) == 1
        assert verified[0]["hypothesis_id"] == "h1"

    def test_improvement_history(self):
        """History should track all cycles."""
        engine = RecursiveSelfImprovementEngine()
        engine.run_cycle()
        engine.run_cycle()
        history = engine.get_improvement_history()
        assert len(history) == 2
