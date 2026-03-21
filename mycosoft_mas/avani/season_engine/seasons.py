"""
Avani Season Engine — Homeostatic State Machine

The system operates through seasonal states that constrain what
Micah and the agents may do.  Seasons are not arbitrary — they are
triggered by measurable conditions.

| Season | Trigger                              | System State                     |
|--------|--------------------------------------|----------------------------------|
| Spring | Heartbeat PRESENT + eco > 0.85       | Full autonomous innovation       |
| Summer | Spring sustained 24h + all green     | Peak operation                   |
| Autumn | Biodiversity < 0.85 or declining     | Throttling, observation only     |
| Winter | Founder latency > 24h                | Deep Hibernation, agents pause   |
| Frost  | Toxicity spike / critical error / RL | Immediate Hard Kill              |

Transition rules:
  - Frost can be entered from ANY state
  - Spring/Summer require Root or Avani to exit Winter
  - Only Root can exit Frost
  - Summer requires Spring sustained for 24h

Author: Morgan Rockwell / Mycosoft Labs
Created: March 9, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Season(str, Enum):
    """Seasonal states for the Avani governance engine."""

    SPRING = "spring"  # Full autonomous innovation and growth
    SUMMER = "summer"  # Peak operation, all systems green
    AUTUMN = "autumn"  # Throttling of Micah; observation only
    WINTER = "winter"  # Deep Hibernation — agents cease activity
    FROST = "frost"  # Immediate Hard Kill — everything stops


# Allowed risk tiers per season
SEASON_RISK_CEILING: Dict[Season, str] = {
    Season.SPRING: "high",
    Season.SUMMER: "critical",
    Season.AUTUMN: "low",
    Season.WINTER: "none",
    Season.FROST: "none",
}

# Throttle percentage per season (100 = full capability)
SEASON_THROTTLE: Dict[Season, int] = {
    Season.SPRING: 100,
    Season.SUMMER: 100,
    Season.AUTUMN: 30,
    Season.WINTER: 0,
    Season.FROST: 0,
}


@dataclass
class SeasonMetrics:
    """Environmental and system metrics that drive seasonal transitions."""

    eco_stability: float = 1.0  # 0.0-1.0, biodiversity/health score
    founder_latency_hours: float = 0.0  # Hours since last heartbeat
    toxicity_detected: bool = False
    critical_error: bool = False
    red_line_violated: bool = False
    all_systems_green: bool = True


@dataclass
class SeasonState:
    """Current seasonal state with metadata."""

    current: Season
    entered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trigger_reason: str = "system_init"
    metrics: SeasonMetrics = field(default_factory=SeasonMetrics)
    history: List[Dict] = field(default_factory=list)


class SeasonEngine:
    """
    State machine governing the seasonal lifecycle.

    The engine evaluates metrics and transitions between seasons
    according to strict rules.  Some transitions require Root authority.
    """

    def __init__(self, initial_season: Season = Season.SPRING) -> None:
        self.state = SeasonState(
            current=initial_season,
            trigger_reason="system_init",
        )
        self._transition_callbacks: List[Callable] = []

    @property
    def current_season(self) -> Season:
        return self.state.current

    @property
    def risk_ceiling(self) -> str:
        return SEASON_RISK_CEILING[self.state.current]

    @property
    def throttle_pct(self) -> int:
        return SEASON_THROTTLE[self.state.current]

    @property
    def is_operational(self) -> bool:
        """Whether agents are allowed to operate at all."""
        return self.state.current not in (Season.WINTER, Season.FROST)

    def on_transition(self, callback: Callable) -> None:
        """Register a callback for season transitions."""
        self._transition_callbacks.append(callback)

    def evaluate_transition(
        self, metrics: SeasonMetrics, is_root: bool = False
    ) -> Optional[Season]:
        """
        Evaluate whether a seasonal transition should occur.

        Args:
            metrics: Current environmental and system metrics.
            is_root: Whether this evaluation is initiated by Root authority.

        Returns:
            The new season if a transition should occur, else None.
        """
        self.state.metrics = metrics
        current = self.state.current

        # Frost can be entered from ANY state
        if metrics.toxicity_detected or metrics.critical_error or metrics.red_line_violated:
            if current != Season.FROST:
                return Season.FROST

        # Winter: founder absent > 24h (from any non-Frost state)
        if metrics.founder_latency_hours > 24.0:
            if current not in (Season.WINTER, Season.FROST):
                return Season.WINTER

        # Exiting Frost requires Root
        if current == Season.FROST:
            if is_root and not metrics.red_line_violated and not metrics.toxicity_detected:
                return Season.SPRING
            return None

        # Exiting Winter requires Root or Avani (is_root covers both)
        if current == Season.WINTER:
            if is_root and metrics.founder_latency_hours <= 24.0:
                return Season.SPRING
            return None

        # Autumn: eco_stability drops below threshold
        if metrics.eco_stability < 0.85:
            if current in (Season.SPRING, Season.SUMMER):
                return Season.AUTUMN

        # Recovery from Autumn to Spring
        if current == Season.AUTUMN:
            if metrics.eco_stability >= 0.85 and metrics.founder_latency_hours <= 24.0:
                return Season.SPRING

        # Summer: Spring sustained 24h + all systems green
        if current == Season.SPRING:
            spring_duration = datetime.now(timezone.utc) - self.state.entered_at
            if spring_duration >= timedelta(hours=24) and metrics.all_systems_green:
                return Season.SUMMER

        return None

    def transition(self, new_season: Season, reason: str) -> SeasonState:
        """
        Execute a seasonal transition.

        Records history and notifies callbacks.
        """
        old_season = self.state.current

        history_entry = {
            "from": old_season.value,
            "to": new_season.value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.state.history.append(history_entry)
        self.state.current = new_season
        self.state.entered_at = datetime.now(timezone.utc)
        self.state.trigger_reason = reason

        logger.info(
            "Season transition: %s -> %s (reason: %s)",
            old_season.value,
            new_season.value,
            reason,
        )

        for callback in self._transition_callbacks:
            try:
                callback(old_season, new_season, reason)
            except Exception as e:
                logger.error("Season transition callback error: %s", e)

        return self.state

    def update(self, metrics: SeasonMetrics, is_root: bool = False) -> Optional[SeasonState]:
        """
        Evaluate metrics and perform transition if warranted.

        Convenience method that combines evaluate + transition.
        Returns the new state if a transition occurred, else None.
        """
        new_season = self.evaluate_transition(metrics, is_root=is_root)
        if new_season is not None:
            reason = self._describe_reason(new_season, metrics)
            return self.transition(new_season, reason)
        return None

    def _describe_reason(self, season: Season, metrics: SeasonMetrics) -> str:
        if season == Season.FROST:
            parts = []
            if metrics.toxicity_detected:
                parts.append("toxicity_spike")
            if metrics.critical_error:
                parts.append("critical_error")
            if metrics.red_line_violated:
                parts.append("red_line_violation")
            return "frost_trigger: " + ", ".join(parts)
        if season == Season.WINTER:
            return f"founder_latency_{metrics.founder_latency_hours:.1f}h"
        if season == Season.AUTUMN:
            return f"eco_stability_{metrics.eco_stability:.2f}_below_threshold"
        if season == Season.SPRING:
            return "conditions_restored"
        if season == Season.SUMMER:
            return "spring_sustained_24h_all_green"
        return "unknown"

    def to_dict(self) -> Dict:
        """Serialize current state for API responses."""
        return {
            "current_season": self.state.current.value,
            "entered_at": self.state.entered_at.isoformat(),
            "trigger_reason": self.state.trigger_reason,
            "risk_ceiling": self.risk_ceiling,
            "throttle_pct": self.throttle_pct,
            "is_operational": self.is_operational,
            "metrics": {
                "eco_stability": self.state.metrics.eco_stability,
                "founder_latency_hours": self.state.metrics.founder_latency_hours,
                "toxicity_detected": self.state.metrics.toxicity_detected,
                "critical_error": self.state.metrics.critical_error,
                "red_line_violated": self.state.metrics.red_line_violated,
                "all_systems_green": self.state.metrics.all_systems_green,
            },
            "history_count": len(self.state.history),
        }
