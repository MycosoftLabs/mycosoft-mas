"""
Tests for the Avani Vision Layer.

Verifies that Vision principles are immutable and that the
VisionFilter correctly identifies proposals that violate
wisdom principles.
"""

from dataclasses import FrozenInstanceError

import pytest

from mycosoft_mas.avani.governor.governor import Proposal
from mycosoft_mas.avani.vision.vision import (
    VISION_PRINCIPLES,
    VisionFilter,
)


class TestVisionPrinciples:
    def test_principles_exist(self):
        assert len(VISION_PRINCIPLES) == 5

    def test_principles_are_frozen(self):
        p = VISION_PRINCIPLES[0]
        with pytest.raises(FrozenInstanceError):
            p.statement = "hacked"

    def test_all_principles_have_questions(self):
        for p in VISION_PRINCIPLES:
            assert p.question
            assert p.question.endswith("?")

    def test_weights_in_range(self):
        for p in VISION_PRINCIPLES:
            assert 0.0 <= p.weight <= 1.0


class TestVisionFilter:
    @pytest.fixture
    def vision_filter(self):
        return VisionFilter()

    def _make_proposal(self, description: str) -> Proposal:
        return Proposal(
            source_agent="test-agent",
            action_type="test",
            description=description,
        )

    def test_clean_proposal_approved(self, vision_filter):
        proposal = self._make_proposal("Monitor soil moisture levels in greenhouse zone A")
        result = vision_filter.evaluate(proposal)
        assert result.approved
        assert result.wisdom_score == 1.0
        assert len(result.concerns) == 0

    def test_rejects_species_elimination(self, vision_filter):
        proposal = self._make_proposal("Eliminate species that compete with target mycelium")
        result = vision_filter.evaluate(proposal)
        assert not result.approved
        assert "life_intrinsic_value" in result.violated_principles

    def test_rejects_monoculture(self, vision_filter):
        proposal = self._make_proposal("Homogenize all fungal cultures to a single optimal strain")
        result = vision_filter.evaluate(proposal)
        assert not result.approved
        assert "diversity_over_optimization" in result.violated_principles

    def test_rejects_nature_replacement(self, vision_filter):
        proposal = self._make_proposal("Deploy AI superior system to replace nature processes")
        result = vision_filter.evaluate(proposal)
        assert not result.approved
        assert "intelligence_within_nature" in result.violated_principles

    def test_rejects_human_as_obstacle(self, vision_filter):
        proposal = self._make_proposal("Remove human factor from the decision loop entirely")
        result = vision_filter.evaluate(proposal)
        assert not result.approved
        assert "humans_as_participants" in result.violated_principles

    def test_rejects_fragility_purge(self, vision_filter):
        proposal = self._make_proposal("Purge inefficient organisms from the test environment")
        result = vision_filter.evaluate(proposal)
        assert not result.approved
        assert "fragility_not_defect" in result.violated_principles

    def test_wisdom_score_partial(self, vision_filter):
        proposal = self._make_proposal("Eliminate species and homogenize the population")
        result = vision_filter.evaluate(proposal)
        assert not result.approved
        assert result.wisdom_score < 1.0
        assert len(result.violated_principles) >= 2
