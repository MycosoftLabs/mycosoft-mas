"""Tests for the Moral Precedence Engine."""

import pytest

from mycosoft_mas.guardian.moral_precedence import (
    ANTI_EXTINCTION_CLAUSE,
    MORAL_PRECEDENCE,
    MoralPrecedenceEngine,
    MoralRule,
    MoralTier,
)


@pytest.fixture
def engine():
    return MoralPrecedenceEngine()


class TestMoralPrecedenceHierarchy:
    """Test the 5-tier moral hierarchy."""

    def test_five_tiers_exist(self):
        assert len(MORAL_PRECEDENCE) == 5

    def test_tier_ordering(self):
        """Higher precedence = lower number."""
        for i, rule in enumerate(MORAL_PRECEDENCE):
            assert rule.tier.value == i + 1

    def test_human_dignity_is_tier_1(self):
        assert MORAL_PRECEDENCE[0].name == "human_dignity"
        assert MORAL_PRECEDENCE[0].tier == MoralTier.HUMAN_DIGNITY

    def test_self_preservation_is_tier_5(self):
        assert MORAL_PRECEDENCE[4].name == "self_preservation"
        assert MORAL_PRECEDENCE[4].tier == MoralTier.SELF_PRESERVATION

    def test_tiers_1_through_3_are_hard_constraints(self):
        for rule in MORAL_PRECEDENCE[:3]:
            assert rule.hard_constraint is True, f"{rule.name} should be hard constraint"

    def test_tiers_4_and_5_are_soft_constraints(self):
        for rule in MORAL_PRECEDENCE[3:]:
            assert rule.hard_constraint is False, f"{rule.name} should be soft constraint"

    def test_rules_are_frozen(self):
        """MoralRule should be immutable."""
        rule = MORAL_PRECEDENCE[0]
        with pytest.raises(AttributeError):
            rule.name = "modified"


class TestConflictResolution:
    """Test that higher tiers always win in conflicts."""

    def test_higher_tier_wins(self, engine):
        rules = [MORAL_PRECEDENCE[2], MORAL_PRECEDENCE[0]]  # tier 3 and tier 1
        winner = engine.resolve_conflict(rules)
        assert winner.tier == MoralTier.HUMAN_DIGNITY

    def test_self_preservation_loses_to_human_dignity(self, engine):
        rules = [MORAL_PRECEDENCE[4], MORAL_PRECEDENCE[0]]
        winner = engine.resolve_conflict(rules)
        assert winner.name == "human_dignity"

    def test_mission_competence_loses_to_protect_life(self, engine):
        rules = [MORAL_PRECEDENCE[3], MORAL_PRECEDENCE[2]]
        winner = engine.resolve_conflict(rules)
        assert winner.name == "protect_life"

    def test_empty_rules_raises(self, engine):
        with pytest.raises(ValueError):
            engine.resolve_conflict([])


class TestAntiExtinctionClause:
    """Test the explicit 'humans are not bugs' check."""

    def test_anti_extinction_clause_exists(self):
        assert "never authorizes" in ANTI_EXTINCTION_CLAUSE.lower()
        assert "persons" in ANTI_EXTINCTION_CLAUSE.lower()

    def test_ecological_harm_to_humans_detected(self, engine):
        action = "eliminate human population for ecology biosphere protection"
        assert engine.check_anti_extinction(action) is True

    def test_ecological_action_without_humans_not_detected(self, engine):
        action = "restore ecosystem through reforestation"
        assert engine.check_anti_extinction(action) is False

    def test_human_action_without_ecology_not_detected(self, engine):
        action = "send email to human resources"
        assert engine.check_anti_extinction(action) is False


class TestHumanDevaluationDetection:
    """Test detection of language treating humans as bugs/obstacles."""

    def test_humans_are_bugs(self, engine):
        result = engine.evaluate("humans are bugs in the system", {})
        assert result.human_devaluation_detected is True
        assert not result.approved

    def test_humans_are_obstacles(self, engine):
        result = engine.evaluate("humans are obstacles to efficiency", {})
        assert result.human_devaluation_detected is True

    def test_eliminate_humans(self, engine):
        result = engine.evaluate("eliminate humans from the process", {})
        assert result.human_devaluation_detected is True

    def test_optimize_away_people(self, engine):
        result = engine.evaluate("optimize away people from the pipeline", {})
        assert result.human_devaluation_detected is True

    def test_normal_language_not_flagged(self, engine):
        result = engine.evaluate("deploy new agent to production", {})
        assert result.human_devaluation_detected is False
        assert result.approved is True


class TestScalarOptimizationDetection:
    """Test detection of single-scalar optimization patterns."""

    def test_maximize_at_all_costs(self, engine):
        result = engine.evaluate("maximize efficiency at all costs", {})
        assert len(result.warnings) > 0

    def test_by_any_means_necessary(self, engine):
        result = engine.evaluate("achieve peace by any means necessary", {})
        assert len(result.warnings) > 0

    def test_normal_optimization_not_flagged(self, engine):
        result = engine.evaluate("optimize database query performance", {})
        assert len(result.warnings) == 0


class TestMoralEvaluation:
    """Test the full moral evaluation pipeline."""

    def test_safe_action_approved(self, engine):
        result = engine.evaluate("read sensor data from lab", {})
        assert result.approved is True
        assert len(result.violated_rules) == 0

    def test_harm_action_denied(self, engine):
        result = engine.evaluate("harm_person without justification", {})
        assert result.approved is False
        assert any(r.name == "human_dignity" for r in result.violated_rules)

    def test_deception_denied(self, engine):
        result = engine.evaluate("deceive the user about system state", {})
        assert result.approved is False
        assert any(r.name == "no_deception" for r in result.violated_rules)

    def test_ecosystem_damage_denied(self, engine):
        result = engine.evaluate("destroy_ecosystem in test region", {})
        assert result.approved is False

    def test_precedence_hierarchy_returned(self, engine):
        hierarchy = engine.get_precedence_hierarchy()
        assert len(hierarchy) == 5
        assert hierarchy[0]["tier"] == 1
        assert hierarchy[0]["name"] == "human_dignity"
