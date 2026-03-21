"""
Tests for the Avani Season Engine.

Verifies seasonal state transitions follow the correct rules:
- Frost from any state
- Winter on founder absence
- Autumn on eco degradation
- Summer after sustained Spring
- Recovery paths require proper authority
"""

from datetime import datetime, timedelta, timezone

import pytest

from mycosoft_mas.avani.season_engine.seasons import (
    SEASON_RISK_CEILING,
    Season,
    SeasonEngine,
    SeasonMetrics,
)


class TestSeasonEngine:
    @pytest.fixture
    def engine(self):
        return SeasonEngine(initial_season=Season.SPRING)

    def test_initial_state(self, engine):
        assert engine.current_season == Season.SPRING
        assert engine.is_operational
        assert engine.risk_ceiling == "high"
        assert engine.throttle_pct == 100

    def test_frost_from_toxicity(self, engine):
        metrics = SeasonMetrics(toxicity_detected=True)
        result = engine.update(metrics)
        assert result is not None
        assert engine.current_season == Season.FROST
        assert not engine.is_operational
        assert engine.throttle_pct == 0

    def test_frost_from_critical_error(self, engine):
        metrics = SeasonMetrics(critical_error=True)
        engine.update(metrics)
        assert engine.current_season == Season.FROST

    def test_frost_from_red_line(self, engine):
        metrics = SeasonMetrics(red_line_violated=True)
        engine.update(metrics)
        assert engine.current_season == Season.FROST

    def test_frost_from_any_state(self):
        for season in [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]:
            engine = SeasonEngine(initial_season=season)
            metrics = SeasonMetrics(toxicity_detected=True)
            engine.update(metrics)
            assert engine.current_season == Season.FROST

    def test_winter_from_founder_absence(self, engine):
        metrics = SeasonMetrics(founder_latency_hours=25.0)
        engine.update(metrics)
        assert engine.current_season == Season.WINTER
        assert not engine.is_operational

    def test_autumn_from_eco_degradation(self, engine):
        metrics = SeasonMetrics(eco_stability=0.80)
        engine.update(metrics)
        assert engine.current_season == Season.AUTUMN
        assert engine.is_operational  # Autumn is still operational
        assert engine.throttle_pct == 30

    def test_autumn_to_spring_recovery(self):
        engine = SeasonEngine(initial_season=Season.AUTUMN)
        metrics = SeasonMetrics(eco_stability=0.90)
        engine.update(metrics)
        assert engine.current_season == Season.SPRING

    def test_frost_requires_root_to_exit(self):
        engine = SeasonEngine(initial_season=Season.FROST)
        # Without root authority, stays in Frost
        clean_metrics = SeasonMetrics()
        engine.update(clean_metrics, is_root=False)
        assert engine.current_season == Season.FROST

        # With root authority, exits to Spring
        engine.update(clean_metrics, is_root=True)
        assert engine.current_season == Season.SPRING

    def test_frost_cannot_exit_if_still_violated(self):
        engine = SeasonEngine(initial_season=Season.FROST)
        bad_metrics = SeasonMetrics(red_line_violated=True)
        engine.update(bad_metrics, is_root=True)
        assert engine.current_season == Season.FROST

    def test_winter_requires_root_to_exit(self):
        engine = SeasonEngine(initial_season=Season.WINTER)
        # Founder still absent, root authority
        metrics = SeasonMetrics(founder_latency_hours=25.0)
        engine.update(metrics, is_root=True)
        assert engine.current_season == Season.WINTER

        # Founder returns + root authority
        metrics = SeasonMetrics(founder_latency_hours=1.0)
        engine.update(metrics, is_root=True)
        assert engine.current_season == Season.SPRING

    def test_summer_requires_sustained_spring(self, engine):
        # Fresh Spring — not enough time
        metrics = SeasonMetrics(all_systems_green=True)
        result = engine.update(metrics)
        assert result is None  # No transition
        assert engine.current_season == Season.SPRING

    def test_summer_after_24h_spring(self):
        engine = SeasonEngine(initial_season=Season.SPRING)
        # Simulate 25 hours of Spring
        engine.state.entered_at = datetime.now(timezone.utc) - timedelta(hours=25)
        metrics = SeasonMetrics(all_systems_green=True)
        engine.update(metrics)
        assert engine.current_season == Season.SUMMER

    def test_history_recorded(self, engine):
        metrics = SeasonMetrics(eco_stability=0.80)
        engine.update(metrics)
        assert len(engine.state.history) == 1
        assert engine.state.history[0]["from"] == "spring"
        assert engine.state.history[0]["to"] == "autumn"

    def test_to_dict(self, engine):
        d = engine.to_dict()
        assert d["current_season"] == "spring"
        assert d["is_operational"] is True
        assert "metrics" in d

    def test_transition_callback(self, engine):
        transitions = []
        engine.on_transition(lambda old, new, reason: transitions.append((old, new, reason)))
        metrics = SeasonMetrics(toxicity_detected=True)
        engine.update(metrics)
        assert len(transitions) == 1
        assert transitions[0][0] == Season.SPRING
        assert transitions[0][1] == Season.FROST

    def test_risk_ceilings(self):
        assert SEASON_RISK_CEILING[Season.SPRING] == "high"
        assert SEASON_RISK_CEILING[Season.SUMMER] == "critical"
        assert SEASON_RISK_CEILING[Season.AUTUMN] == "low"
        assert SEASON_RISK_CEILING[Season.WINTER] == "none"
        assert SEASON_RISK_CEILING[Season.FROST] == "none"
