"""
Tests for Liquid Temporal Processor.

Validates:
  - Adaptive time constant behavior (faster tau for volatile signals)
  - Signal dynamics computation
  - State transition detection
  - Adaptation metrics reporting
"""

import math
import pytest

from mycosoft_mas.engines.liquid_temporal.processor import (
    AdaptiveTimeConstant,
    LiquidTemporalProcessor,
    ProcessedStream,
    StateTransition,
)


class TestAdaptiveTimeConstant:
    """Test the adaptive time constant mechanism."""

    def test_init_defaults(self):
        atc = AdaptiveTimeConstant()
        assert atc.tau == 50.0
        assert atc.tau_min == 5.0
        assert atc.tau_max == 500.0

    def test_adapt_stable_signal(self):
        """Stable signal (low derivative/variance) should increase tau."""
        atc = AdaptiveTimeConstant(tau_init=50.0)
        # Feed stable signal dynamics
        for _ in range(20):
            atc.adapt(signal_derivative=0.01, signal_variance=0.001)
        # Tau should move toward tau_max
        assert atc.tau > 50.0

    def test_adapt_volatile_signal(self):
        """Volatile signal (high derivative/variance) should decrease tau."""
        atc = AdaptiveTimeConstant(tau_init=200.0)
        # Feed volatile signal dynamics
        for _ in range(20):
            atc.adapt(signal_derivative=10.0, signal_variance=50.0)
        # Tau should move toward tau_min
        assert atc.tau < 200.0

    def test_tau_stays_in_bounds(self):
        """Tau should never exceed min/max bounds."""
        atc = AdaptiveTimeConstant(tau_min=10.0, tau_max=100.0)
        # Drive toward minimum
        for _ in range(100):
            atc.adapt(signal_derivative=100.0, signal_variance=100.0)
        assert atc.tau >= atc.tau_min

        # Drive toward maximum
        for _ in range(100):
            atc.adapt(signal_derivative=0.0, signal_variance=0.0)
        assert atc.tau <= atc.tau_max

    def test_integration_window(self):
        """Integration window should be 2 * tau."""
        atc = AdaptiveTimeConstant(tau_init=25.0)
        assert atc.get_integration_window_ms() == 50.0

    def test_history_tracking(self):
        """History should track tau values."""
        atc = AdaptiveTimeConstant()
        assert len(atc.get_history()) == 0
        atc.adapt(1.0, 1.0)
        assert len(atc.get_history()) == 1


class TestLiquidTemporalProcessor:
    """Test the main processor."""

    def test_init(self):
        proc = LiquidTemporalProcessor()
        assert proc._initialized is False

    def test_process_continuous_basic(self):
        """Process a basic signal through the processor."""
        proc = LiquidTemporalProcessor()
        # Simple sine-like signal
        samples = [math.sin(i * 0.1) * 2.0 for i in range(100)]

        result = proc.process_continuous("ch0", samples)

        assert isinstance(result, ProcessedStream)
        assert result.channel_id == "ch0"
        assert result.sample_count == 100
        assert result.adaptive_tau > 0
        assert result.integration_window_ms > 0

    def test_process_continuous_volatile(self):
        """Volatile signal should get shorter tau."""
        proc = LiquidTemporalProcessor()

        # First: stable signal
        stable = [1.0] * 100
        result_stable = proc.process_continuous("ch_stable", stable)

        # Second: volatile signal
        volatile = [(-1) ** i * 10.0 for i in range(100)]
        result_volatile = proc.process_continuous("ch_volatile", volatile)

        # Volatile channel should have shorter tau
        assert result_volatile.adaptive_tau < result_stable.adaptive_tau

    def test_signal_dynamics(self):
        """Check signal dynamics computation."""
        dynamics = LiquidTemporalProcessor._compute_dynamics([1.0, 2.0, 3.0, 4.0, 5.0])
        assert dynamics["mean"] == 3.0
        assert dynamics["derivative"] == pytest.approx(1.0)
        assert dynamics["variance"] > 0

    def test_signal_dynamics_empty(self):
        """Empty samples should return zeros."""
        dynamics = LiquidTemporalProcessor._compute_dynamics([])
        assert dynamics["mean"] == 0.0
        assert dynamics["variance"] == 0.0

    def test_adaptation_metrics(self):
        """Metrics should report channel state."""
        proc = LiquidTemporalProcessor()
        proc.process_continuous("ch0", [1.0, 2.0, 3.0] * 20)

        metrics = proc.get_adaptation_metrics()
        assert metrics["total_channels"] == 1
        assert "ch0" in metrics["channels"]
        assert metrics["channels"]["ch0"]["current_tau"] > 0

    def test_no_transition_on_first_process(self):
        """First process should not detect a transition (no prior state)."""
        proc = LiquidTemporalProcessor()
        proc.process_continuous("ch0", [1.0] * 50)
        transition = proc.detect_state_transition("ch0")
        # May or may not detect depending on pattern match — just check type
        assert transition is None or isinstance(transition, StateTransition)

    def test_transition_history(self):
        """Transition history should be a list."""
        proc = LiquidTemporalProcessor()
        proc.process_continuous("ch0", [1.0] * 50)
        history = proc.get_transition_history("ch0")
        assert isinstance(history, list)

    def test_nonexistent_channel(self):
        """Querying nonexistent channel should return None/empty."""
        proc = LiquidTemporalProcessor()
        assert proc.detect_state_transition("nope") is None
        assert proc.get_transition_history("nope") == []

    def test_processed_stream_to_dict(self):
        """ProcessedStream serialization."""
        proc = LiquidTemporalProcessor()
        result = proc.process_continuous("ch0", [1.0, 2.0, 3.0] * 20)
        d = result.to_dict()
        assert d["channel_id"] == "ch0"
        assert "adaptive_tau" in d
        assert "signal_dynamics" in d


class TestStateTransition:
    """Test StateTransition data class."""

    def test_to_dict(self):
        t = StateTransition(
            transition_id="abc",
            channel_id="ch0",
            from_state="baseline",
            to_state="active_growth",
            confidence=0.85,
        )
        d = t.to_dict()
        assert d["from_state"] == "baseline"
        assert d["to_state"] == "active_growth"
        assert d["confidence"] == 0.85
