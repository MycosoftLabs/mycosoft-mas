"""Tests for Developmental Stages."""

import pytest

from mycosoft_mas.guardian.developmental_stages import (
    STAGE_CAPABILITIES,
    DevelopmentalStage,
    DevelopmentalTracker,
)


@pytest.fixture
def tracker():
    return DevelopmentalTracker(initial_stage=DevelopmentalStage.ADULTHOOD)


@pytest.fixture
def infant_tracker():
    return DevelopmentalTracker(initial_stage=DevelopmentalStage.INFANCY)


class TestStageCapabilities:
    """Test capability definitions per stage."""

    def test_infancy_cannot_write(self):
        caps = STAGE_CAPABILITIES[DevelopmentalStage.INFANCY]
        assert caps.can_write is False
        assert caps.can_execute is False
        assert caps.can_deploy is False

    def test_childhood_can_write_not_execute(self):
        caps = STAGE_CAPABILITIES[DevelopmentalStage.CHILDHOOD]
        assert caps.can_write is True
        assert caps.can_execute is False

    def test_adolescence_can_execute_not_deploy(self):
        caps = STAGE_CAPABILITIES[DevelopmentalStage.ADOLESCENCE]
        assert caps.can_execute is True
        assert caps.can_deploy is False

    def test_adulthood_can_deploy(self):
        caps = STAGE_CAPABILITIES[DevelopmentalStage.ADULTHOOD]
        assert caps.can_deploy is True

    def test_no_stage_allows_self_modify(self):
        for stage, caps in STAGE_CAPABILITIES.items():
            assert (
                caps.can_self_modify is False
            ), f"{stage.value} should not allow self-modification"

    def test_infancy_requires_approval(self):
        caps = STAGE_CAPABILITIES[DevelopmentalStage.INFANCY]
        assert caps.requires_approval is True

    def test_adulthood_does_not_require_approval(self):
        caps = STAGE_CAPABILITIES[DevelopmentalStage.ADULTHOOD]
        assert caps.requires_approval is False


class TestActionAllowance:
    """Test action allowance checks."""

    def test_adulthood_allows_deploy(self, tracker):
        assert tracker.is_action_allowed("deploy", "high") is True

    def test_infancy_blocks_write(self, infant_tracker):
        assert infant_tracker.is_action_allowed("write", "low") is False

    def test_infancy_blocks_high_risk(self, infant_tracker):
        assert infant_tracker.is_action_allowed("read", "high") is False

    def test_adulthood_blocks_critical_risk(self, tracker):
        assert tracker.is_action_allowed("read", "critical") is False


class TestStageTransitions:
    """Test stage advancement and regression."""

    def test_default_is_adulthood(self, tracker):
        assert tracker.get_current_stage() == DevelopmentalStage.ADULTHOOD

    def test_regression_to_lower_stage(self, tracker):
        result = tracker.regress_stage(
            DevelopmentalStage.CHILDHOOD,
            reason="Safety violation detected",
        )
        assert result is True
        assert tracker.get_current_stage() == DevelopmentalStage.CHILDHOOD

    def test_cannot_regress_to_same_stage(self, tracker):
        result = tracker.regress_stage(
            DevelopmentalStage.ADULTHOOD,
            reason="Not a real regression",
        )
        assert result is False

    def test_forced_advance(self, infant_tracker):
        result = infant_tracker.advance_stage(
            DevelopmentalStage.ADULTHOOD,
            reason="Initialization",
            force=True,
        )
        assert result is True
        assert infant_tracker.get_current_stage() == DevelopmentalStage.ADULTHOOD

    def test_stage_history_tracked(self, tracker):
        tracker.regress_stage(DevelopmentalStage.CHILDHOOD, "test")
        history = tracker.get_stage_history()
        assert len(history) == 2  # Initial + regression


class TestReadinessAssessment:
    """Test readiness assessment for stage transitions."""

    def test_assess_readiness_with_unmet_criteria(self, infant_tracker):
        assessment = infant_tracker.assess_readiness(DevelopmentalStage.CHILDHOOD)
        assert assessment.ready is False
        assert len(assessment.criteria_unmet) > 0

    def test_assess_readiness_with_met_criteria(self, infant_tracker):
        assessment = infant_tracker.assess_readiness(
            DevelopmentalStage.CHILDHOOD,
            achieved_criteria={
                "identity_verified": True,
                "guardian_active": True,
                "boot_statement_loaded": True,
                "memory_system_online": True,
            },
        )
        assert assessment.ready is True


class TestStageInfo:
    """Test stage information retrieval."""

    def test_all_stage_info(self, tracker):
        info = tracker.get_all_stage_info()
        assert len(info) == 4
        assert info[3]["stage"] == "adulthood"
        assert info[3]["current"] is True
