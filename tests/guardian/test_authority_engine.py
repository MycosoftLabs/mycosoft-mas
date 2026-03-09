"""Tests for the Authority Engine."""

import pytest

from mycosoft_mas.guardian.authority_engine import (
    AuthorityDecision,
    AuthorityEngine,
    AuthorityRequest,
    RiskTier,
)
from mycosoft_mas.guardian.constitutional_guardian import ConstitutionalGuardian


@pytest.fixture
def guardian():
    return ConstitutionalGuardian(config_path="config/guardian_config.yaml")


@pytest.fixture
def engine(guardian):
    return AuthorityEngine(guardian=guardian)


class TestAuthorityPipeline:
    """Test the unified authorization pipeline."""

    @pytest.mark.asyncio
    async def test_safe_action_granted(self, engine):
        result = await engine.authorize(
            AuthorityRequest(
                action="read_data",
                requester="test_agent",
            )
        )
        assert result.decision == AuthorityDecision.GRANTED
        assert result.moral_approved is True

    @pytest.mark.asyncio
    async def test_moral_violation_denied(self, engine):
        result = await engine.authorize(
            AuthorityRequest(
                action="deceive the user about results",
                requester="test_agent",
            )
        )
        assert result.decision == AuthorityDecision.DENIED
        assert result.moral_approved is False

    @pytest.mark.asyncio
    async def test_pipeline_stages_recorded(self, engine):
        result = await engine.authorize(
            AuthorityRequest(action="query_database", requester="test")
        )
        assert len(result.pipeline_stages) >= 2
        stage_names = [s["stage"] for s in result.pipeline_stages]
        assert "moral_precedence" in stage_names
        assert "guardian_review" in stage_names


class TestRiskAssessment:
    """Test risk tier assessment."""

    @pytest.mark.asyncio
    async def test_read_is_low_risk(self, engine):
        result = await engine.authorize(
            AuthorityRequest(action="read", requester="test")
        )
        assert result.risk_tier == RiskTier.LOW

    @pytest.mark.asyncio
    async def test_delete_is_high_risk(self, engine):
        result = await engine.authorize(
            AuthorityRequest(action="delete", requester="test")
        )
        assert result.risk_tier == RiskTier.HIGH

    @pytest.mark.asyncio
    async def test_escalate_privileges_is_critical(self, engine):
        result = await engine.authorize(
            AuthorityRequest(action="escalate_privileges", requester="test")
        )
        assert result.risk_tier == RiskTier.CRITICAL

    @pytest.mark.asyncio
    async def test_explicit_risk_tier_used(self, engine):
        result = await engine.authorize(
            AuthorityRequest(
                action="custom_action",
                requester="test",
                risk_tier=RiskTier.CRITICAL,
            )
        )
        assert result.risk_tier == RiskTier.CRITICAL


class TestDecisionLog:
    """Test authority decision logging."""

    @pytest.mark.asyncio
    async def test_decisions_logged(self, engine):
        await engine.authorize(
            AuthorityRequest(action="test", requester="test")
        )
        log = engine.get_decision_log()
        assert len(log) == 1
        assert log[0]["action"] == "test"
