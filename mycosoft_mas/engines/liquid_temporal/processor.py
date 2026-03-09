"""
Liquid Temporal Processor — Adaptive Biosignal Processing for FCI Data

Processes continuous fungal biosignals with adaptive integration windows
inspired by Liquid Time-Constant (LTC) neural networks. Key properties:

  * Adaptive time constants: volatile signals get shorter tau (faster response),
    stable signals get longer tau (more smoothing, less compute).
  * Variable integration windows: edge-efficient — spend CPU on interesting
    signals, not on boring ones.
  * State transition detection: identifies when fungal network shifts between
    GFST states (e.g. baseline → active_growth → defense_activation).
  * Plugs into existing SDRPipeline for filtering + GFST pattern matching.

This is a bio-inspired processing heuristic. It does NOT implement actual
neural ODEs. When Liquid AI's LFM models become available for edge deployment,
this layer can be swapped out transparently.

Created: March 9, 2026
(c) 2026 Mycosoft Labs
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ProcessedStream:
    """Result of processing a continuous biosignal stream."""
    channel_id: str
    sample_count: int
    adaptive_tau: float
    integration_window_ms: float
    filtered_values: List[float]
    pattern_matches: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    signal_dynamics: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "sample_count": self.sample_count,
            "adaptive_tau": self.adaptive_tau,
            "integration_window_ms": self.integration_window_ms,
            "pattern_matches": self.pattern_matches,
            "confidence": self.confidence,
            "signal_dynamics": self.signal_dynamics,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StateTransition:
    """Detected transition between fungal network states."""
    transition_id: str
    channel_id: str
    from_state: str
    to_state: str
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = 0.0
    trigger_features: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "channel_id": self.channel_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "trigger_features": self.trigger_features,
        }


# ---------------------------------------------------------------------------
# Adaptive Time Constant
# ---------------------------------------------------------------------------

class AdaptiveTimeConstant:
    """
    Time constant that adapts based on signal dynamics.

    Inspired by LTC networks where tau adapts based on input:
      * High signal derivative / variance → shorter tau (more responsive)
      * Low signal derivative / variance  → longer tau (more smoothing)

    This is the core efficiency mechanism: boring signals cost less to process.
    """

    def __init__(
        self,
        tau_init: float = 50.0,
        tau_min: float = 5.0,
        tau_max: float = 500.0,
        sensitivity: float = 0.1,
    ):
        self.tau = tau_init
        self.tau_min = tau_min
        self.tau_max = tau_max
        self.sensitivity = sensitivity
        self._history: deque = deque(maxlen=100)

    def adapt(self, signal_derivative: float, signal_variance: float) -> float:
        """
        Adapt the time constant based on current signal dynamics.

        Returns the new tau value in milliseconds.
        """
        # Compute urgency: how much the signal is changing
        urgency = abs(signal_derivative) + math.sqrt(max(signal_variance, 0.0))

        # Map urgency to tau: more urgency → shorter tau
        # Uses a sigmoid-like mapping clamped to [tau_min, tau_max]
        if urgency > 0:
            target_tau = self.tau_max / (1.0 + self.sensitivity * urgency)
        else:
            target_tau = self.tau_max

        target_tau = max(self.tau_min, min(self.tau_max, target_tau))

        # Exponential moving average to prevent jitter
        alpha = 0.15
        self.tau = self.tau * (1 - alpha) + target_tau * alpha
        self._history.append(self.tau)
        return self.tau

    def get_integration_window_ms(self) -> float:
        """Return current integration window in milliseconds (= 2 * tau)."""
        return self.tau * 2.0

    def get_history(self) -> List[float]:
        """Return tau adaptation history."""
        return list(self._history)


# ---------------------------------------------------------------------------
# Channel State Tracker
# ---------------------------------------------------------------------------

class _ChannelState:
    """Internal state tracker for a single channel."""

    def __init__(self, channel_id: str, buffer_size: int = 2000):
        self.channel_id = channel_id
        self.atc = AdaptiveTimeConstant()
        self.buffer: deque = deque(maxlen=buffer_size)
        self.timestamps: deque = deque(maxlen=buffer_size)
        self.current_pattern: Optional[str] = None
        self.pattern_history: deque = deque(maxlen=50)
        self.transition_history: List[StateTransition] = []


# ---------------------------------------------------------------------------
# Liquid Temporal Processor
# ---------------------------------------------------------------------------

class LiquidTemporalProcessor:
    """
    Processes continuous fungal biosignals with adaptive integration windows.

    Architecture:
        Raw FCI samples
            → AdaptiveTimeConstant (determines integration window)
            → Variable-width windowed processing
            → SDRPipeline (filtering + GFST classification)
            → State transition detection
            → ProcessedStream output

    Designed for edge hardware (Jetson, ESP32):
        * Adaptive tau means stable signals use less CPU
        * No heavy matrix ops — simple running statistics
        * Memory-bounded buffers (deque with maxlen)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self._channels: Dict[str, _ChannelState] = {}
        self._buffer_size = config.get("buffer_size", 2000)
        self._min_samples_for_analysis = config.get("min_samples", 32)
        self._transition_confidence_threshold = config.get(
            "transition_confidence_threshold", 0.6
        )
        self._sdr_pipeline = None
        self._initialized = False
        logger.info("LiquidTemporalProcessor created")

    def _ensure_pipeline(self):
        """Lazy-init SDR pipeline to avoid import-time failures."""
        if self._sdr_pipeline is None:
            try:
                from mycosoft_mas.bio.sdr_pipeline import SDRPipeline
                self._sdr_pipeline = SDRPipeline(sample_rate=1000.0)
            except ImportError:
                logger.warning("SDRPipeline unavailable; pattern matching disabled")
        self._initialized = True

    def _get_channel(self, channel_id: str) -> _ChannelState:
        if channel_id not in self._channels:
            self._channels[channel_id] = _ChannelState(
                channel_id, self._buffer_size
            )
        return self._channels[channel_id]

    # ----- core processing ------------------------------------------------

    def process_continuous(
        self,
        channel_id: str,
        samples: List[float],
        timestamps: Optional[List[float]] = None,
    ) -> ProcessedStream:
        """
        Process a stream of samples with adaptive time constants.

        Args:
            channel_id: Electrode / channel identifier.
            samples: Raw signal values (mV).
            timestamps: Optional epoch-seconds per sample.

        Returns:
            ProcessedStream with adaptive_tau, patterns, confidence.
        """
        self._ensure_pipeline()
        ch = self._get_channel(channel_id)

        now = datetime.now(timezone.utc)
        ts_list = timestamps or [
            now.timestamp() + i / 1000.0 for i in range(len(samples))
        ]

        # 1. Append to buffer
        ch.buffer.extend(samples)
        ch.timestamps.extend(ts_list)

        # 2. Compute signal dynamics from recent buffer
        recent = list(ch.buffer)[-min(len(ch.buffer), 256):]
        dynamics = self._compute_dynamics(recent)

        # 3. Adapt time constant
        tau = ch.atc.adapt(
            dynamics["derivative"],
            dynamics["variance"],
        )
        window_ms = ch.atc.get_integration_window_ms()

        # 4. Process through SDR pipeline with variable window
        filtered_values: List[float] = []
        pattern_matches: List[Dict[str, Any]] = []

        if self._sdr_pipeline is not None and len(recent) >= self._min_samples_for_analysis:
            # Determine window size in samples (tau * 2 in ms, at 1kHz = tau * 2 samples)
            window_samples = max(
                self._min_samples_for_analysis,
                min(len(recent), int(window_ms)),
            )
            analysis_window = recent[-window_samples:]

            # Filter samples
            for s in analysis_window:
                ps = self._sdr_pipeline.process_sample(s)
                filtered_values.append(ps.filtered_value)

            # Spectrum + pattern classification
            spectrum = self._sdr_pipeline.compute_spectrum(filtered_values)
            rms = math.sqrt(sum(v * v for v in filtered_values) / max(len(filtered_values), 1))
            match = self._sdr_pipeline.classify_pattern(spectrum, rms)
            if match:
                pattern_matches.append({
                    "pattern": match.pattern_name,
                    "category": match.category,
                    "confidence": match.confidence,
                    "frequency": match.frequency,
                    "amplitude": match.amplitude,
                })

        # 5. Detect state transitions
        best_conf = pattern_matches[0]["confidence"] if pattern_matches else 0.0
        best_pattern = pattern_matches[0]["pattern"] if pattern_matches else None

        if best_pattern and best_pattern != ch.current_pattern:
            if best_conf >= self._transition_confidence_threshold:
                transition = StateTransition(
                    transition_id=uuid4().hex[:12],
                    channel_id=channel_id,
                    from_state=ch.current_pattern or "unknown",
                    to_state=best_pattern,
                    confidence=best_conf,
                    trigger_features=dynamics,
                )
                ch.transition_history.append(transition)
                ch.pattern_history.append(best_pattern)
                ch.current_pattern = best_pattern

        return ProcessedStream(
            channel_id=channel_id,
            sample_count=len(samples),
            adaptive_tau=tau,
            integration_window_ms=window_ms,
            filtered_values=filtered_values,
            pattern_matches=pattern_matches,
            confidence=best_conf,
            signal_dynamics=dynamics,
        )

    # ----- state transitions ----------------------------------------------

    def detect_state_transition(
        self, channel_id: str
    ) -> Optional[StateTransition]:
        """Return the most recent state transition for a channel, if any."""
        ch = self._channels.get(channel_id)
        if ch and ch.transition_history:
            return ch.transition_history[-1]
        return None

    def get_transition_history(
        self, channel_id: str
    ) -> List[StateTransition]:
        """Return full transition history for a channel."""
        ch = self._channels.get(channel_id)
        return list(ch.transition_history) if ch else []

    # ----- metrics --------------------------------------------------------

    def get_adaptation_metrics(self) -> Dict[str, Any]:
        """Return how time constants have adapted across all channels."""
        metrics: Dict[str, Any] = {}
        for cid, ch in self._channels.items():
            history = ch.atc.get_history()
            metrics[cid] = {
                "current_tau": ch.atc.tau,
                "tau_min_observed": min(history) if history else ch.atc.tau,
                "tau_max_observed": max(history) if history else ch.atc.tau,
                "tau_mean": sum(history) / len(history) if history else ch.atc.tau,
                "integration_window_ms": ch.atc.get_integration_window_ms(),
                "current_pattern": ch.current_pattern,
                "transitions_count": len(ch.transition_history),
                "buffer_size": len(ch.buffer),
                "adaptation_steps": len(history),
            }
        return {
            "channels": metrics,
            "total_channels": len(self._channels),
            "processor_initialized": self._initialized,
        }

    # ----- internal helpers -----------------------------------------------

    @staticmethod
    def _compute_dynamics(samples: List[float]) -> Dict[str, float]:
        """Compute signal dynamics: mean, variance, derivative, rate of change."""
        n = len(samples)
        if n == 0:
            return {"mean": 0.0, "variance": 0.0, "derivative": 0.0, "rate_of_change": 0.0}

        mean = sum(samples) / n
        variance = sum((s - mean) ** 2 for s in samples) / max(n - 1, 1)

        # First-order finite difference for derivative
        if n >= 2:
            derivatives = [samples[i] - samples[i - 1] for i in range(1, n)]
            derivative = sum(derivatives) / len(derivatives)
            rate_of_change = sum(abs(d) for d in derivatives) / len(derivatives)
        else:
            derivative = 0.0
            rate_of_change = 0.0

        return {
            "mean": mean,
            "variance": variance,
            "derivative": derivative,
            "rate_of_change": rate_of_change,
        }
