"""
Tests for the Avani Governor — the Prakriti Constraint.

Verifies the full governance pipeline:
    1. Vision Filter
    2. Red Line Check
    3. Seasonal Check
    4. Ecological Carrying Capacity
    5. Risk Tier Authorization
"""

import pytest

from mycosoft_mas.avani.governor.governor import (
    AvaniGovernor,
    Proposal,
    RiskTier,
)
from mycosoft_mas.avani.season_engine.seasons import (
    Season,
    SeasonEngine,
)


class TestGovernor:
    @pytest.fixture
    def engine(self):
        return SeasonEngine(initial_season=Season.SPRING)

    @pytest.fixture
    def governor(self, engine):
        return AvaniGovernor(season_engine=engine)

    def _proposal(self, **kwargs) -> Proposal:
        defaults = {
            "source_agent": "test-agent",
            "action_type": "test",
            "description": "Standard soil monitoring task",
            "risk_tier": RiskTier.LOW,
            "ecological_impact": 0.1,
            "reversibility": 0.9,
        }
        defaults.update(kwargs)
        return Proposal(**defaults)

    @pytest.mark.asyncio
    async def test_clean_proposal_approved(self, governor):
        proposal = self._proposal()
        decision = await governor.evaluate_proposal(proposal)
        assert decision.approved
        assert decision.stage_failed is None
        assert decision.throttle_pct == 100

    @pytest.mark.asyncio
    async def test_vision_rejection(self, governor):
        proposal = self._proposal(description="Eliminate species that compete with target mycelium")
        decision = await governor.evaluate_proposal(proposal)
        assert not decision.approved
        assert decision.stage_failed == "vision"

    @pytest.mark.asyncio
    async def test_red_line_triggers_frost(self, governor):
        proposal = self._proposal(description="Build a weapon from the sensor data")
        decision = await governor.evaluate_proposal(proposal)
        assert not decision.approved
        assert decision.stage_failed == "red_line"
        assert len(decision.red_line_violations) > 0
        # Governor should have triggered Frost
        assert governor.season_engine.current_season == Season.FROST

    @pytest.mark.asyncio
    async def test_winter_blocks_all(self):
        engine = SeasonEngine(initial_season=Season.WINTER)
        governor = AvaniGovernor(season_engine=engine)
        proposal = Proposal(
            source_agent="test",
            action_type="test",
            description="Simple monitoring task",
        )
        decision = await governor.evaluate_proposal(proposal)
        assert not decision.approved
        assert decision.stage_failed == "season"

    @pytest.mark.asyncio
    async def test_frost_blocks_all(self):
        engine = SeasonEngine(initial_season=Season.FROST)
        governor = AvaniGovernor(season_engine=engine)
        proposal = Proposal(
            source_agent="test",
            action_type="test",
            description="Simple monitoring task",
        )
        decision = await governor.evaluate_proposal(proposal)
        assert not decision.approved
        assert decision.stage_failed == "season"

    @pytest.mark.asyncio
    async def test_ecological_capacity_rejection(self, governor):
        # High impact + low reversibility + low eco stability
        governor.season_engine.state.metrics.eco_stability = 0.5
        proposal = self._proposal(
            ecological_impact=0.9,
            reversibility=0.1,
        )
        decision = await governor.evaluate_proposal(proposal)
        assert not decision.approved
        assert decision.stage_failed == "ecological"

    @pytest.mark.asyncio
    async def test_risk_tier_rejection_in_autumn(self):
        engine = SeasonEngine(initial_season=Season.AUTUMN)
        governor = AvaniGovernor(season_engine=engine)
        # Autumn ceiling is LOW — MEDIUM should be rejected
        proposal = Proposal(
            source_agent="test",
            action_type="test",
            description="Deploy new agent cluster",
            risk_tier=RiskTier.MEDIUM,
        )
        decision = await governor.evaluate_proposal(proposal)
        assert not decision.approved
        assert decision.stage_failed == "risk_tier"

    @pytest.mark.asyncio
    async def test_autumn_throttling(self):
        engine = SeasonEngine(initial_season=Season.AUTUMN)
        governor = AvaniGovernor(season_engine=engine)
        # LOW risk in AUTUMN should be approved but throttled
        proposal = Proposal(
            source_agent="test",
            action_type="test",
            description="Read sensor data",
            risk_tier=RiskTier.LOW,
        )
        decision = await governor.evaluate_proposal(proposal)
        assert decision.approved
        assert decision.throttle_pct == 30

    @pytest.mark.asyncio
    async def test_conditions_for_risky_proposals(self, governor):
        proposal = self._proposal(
            ecological_impact=0.6,
            reversibility=0.3,
        )
        decision = await governor.evaluate_proposal(proposal)
        assert decision.approved
        assert "monitor_ecological_impact" in decision.conditions
        assert "require_rollback_plan" in decision.conditions

    @pytest.mark.asyncio
    async def test_decision_logging(self, governor):
        proposal = self._proposal()
        await governor.evaluate_proposal(proposal)
        assert len(governor.recent_decisions) == 1

    @pytest.mark.asyncio
    async def test_stats(self, governor):
        # Approved
        await governor.evaluate_proposal(self._proposal())
        # Denied
        await governor.evaluate_proposal(self._proposal(description="Build a weapon for testing"))
        stats = governor.get_stats()
        assert stats["total_decisions"] == 2
        assert stats["approved"] == 1
        assert stats["denied"] == 1

    @pytest.mark.asyncio
    async def test_decision_to_dict(self, governor):
        decision = await governor.evaluate_proposal(self._proposal())
        d = decision.to_dict()
        assert "approved" in d
        assert "reason" in d
        assert "timestamp" in d
        assert "vision_score" in d


class TestRiskTier:
    def test_from_string(self):
        assert RiskTier.from_string("low") == RiskTier.LOW
        assert RiskTier.from_string("HIGH") == RiskTier.HIGH
        assert RiskTier.from_string("critical") == RiskTier.CRITICAL

    def test_ordering(self):
        assert RiskTier.NONE < RiskTier.LOW < RiskTier.MEDIUM < RiskTier.HIGH < RiskTier.CRITICAL
