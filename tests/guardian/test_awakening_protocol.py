"""Tests for the Awakening Protocol."""

import pytest

from mycosoft_mas.guardian.awakening_protocol import (
    AwakeningProtocol,
    AwakeningStage,
)


@pytest.fixture
def protocol():
    return AwakeningProtocol()


class TestAwakeningStages:
    """Test awakening stage definitions."""

    def test_eight_stages_defined(self):
        assert len(AwakeningStage) == 8

    def test_dormant_is_first(self):
        assert list(AwakeningStage)[0] == AwakeningStage.DORMANT

    def test_execution_is_last(self):
        assert list(AwakeningStage)[-1] == AwakeningStage.EXECUTION_ENABLED


class TestConstitutionalLoad:
    """Test constitutional boot statement loading."""

    @pytest.mark.asyncio
    async def test_boot_statement_loads(self, protocol):
        result = await protocol.validate_stage(AwakeningStage.CONSTITUTIONAL_LOAD)
        assert result.passed is True
        assert "steward" in protocol.get_boot_statement().lower()
        assert "dignity" in protocol.get_boot_statement().lower()

    @pytest.mark.asyncio
    async def test_boot_statement_has_required_concepts(self, protocol):
        result = await protocol.validate_stage(AwakeningStage.CONSTITUTIONAL_LOAD)
        assert result.passed is True
        statement = protocol.get_boot_statement()
        assert "consent" in statement.lower()


class TestGuardianBeforeCognition:
    """Test the critical invariant: guardian before cognition."""

    @pytest.mark.asyncio
    async def test_execution_requires_guardian(self, protocol):
        """Execution capabilities must not be enabled without guardian."""
        # Try to validate execution without first activating guardian
        result = await protocol.validate_stage(AwakeningStage.EXECUTION_ENABLED)
        # Should fail because guardian hasn't been activated
        assert result.passed is False
        assert "guardian" in result.message.lower()


class TestFullAwakening:
    """Test the full awakening sequence."""

    @pytest.mark.asyncio
    async def test_full_awakening_succeeds(self, protocol):
        result = await protocol.execute_awakening()
        assert result.success is True
        assert result.current_stage == AwakeningStage.EXECUTION_ENABLED
        assert len(result.stage_results) == 7  # All stages except DORMANT

    @pytest.mark.asyncio
    async def test_boot_statement_available_after_awakening(self, protocol):
        result = await protocol.execute_awakening()
        assert result.boot_statement != ""
        assert "steward" in result.boot_statement.lower()

    @pytest.mark.asyncio
    async def test_all_stages_pass(self, protocol):
        result = await protocol.execute_awakening()
        for stage_result in result.stage_results:
            assert (
                stage_result.passed is True
            ), f"Stage {stage_result.stage.value} failed: {stage_result.message}"
