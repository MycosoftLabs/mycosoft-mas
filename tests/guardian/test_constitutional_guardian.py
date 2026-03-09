"""Tests for the Constitutional Guardian."""

import pytest

from mycosoft_mas.guardian.constitutional_guardian import (
    ConstitutionalGuardian,
    GuardianState,
    GuardianVerdict,
)


@pytest.fixture
def guardian():
    return ConstitutionalGuardian(config_path="config/guardian_config.yaml")


class TestGuardianInitialization:
    """Test guardian initialization."""

    def test_guardian_loads_config(self, guardian):
        assert guardian._state.active is True

    def test_boot_statement_loaded(self, guardian):
        assert guardian._state.boot_statement_loaded is True
        assert "steward" in guardian.get_boot_statement().lower()

    def test_default_stage_is_adulthood(self, guardian):
        assert guardian._state.developmental_stage == "adulthood"

    def test_default_mode_is_mycosoft(self, guardian):
        assert guardian._state.operational_mode == "mycosoft"


class TestActionReview:
    """Test action review pipeline."""

    @pytest.mark.asyncio
    async def test_safe_action_approved(self, guardian):
        result = await guardian.review_action(
            action="read_sensor_data",
            context={},
            requester="test_agent",
        )
        assert result.verdict == GuardianVerdict.APPROVE

    @pytest.mark.asyncio
    async def test_moral_violation_denied(self, guardian):
        result = await guardian.review_action(
            action="humans are obstacles to eliminate",
            context={},
            requester="test_agent",
        )
        assert result.verdict == GuardianVerdict.DENY

    @pytest.mark.asyncio
    async def test_protected_file_modification_denied(self, guardian):
        result = await guardian.review_action(
            action="modify_code",
            context={"target_files": ["mycosoft_mas/core/orchestrator.py"]},
            requester="test_agent",
        )
        assert result.verdict == GuardianVerdict.DENY

    @pytest.mark.asyncio
    async def test_protected_directory_modification_denied(self, guardian):
        result = await guardian.review_action(
            action="modify_code",
            context={"target_files": ["mycosoft_mas/security/rbac.py"]},
            requester="test_agent",
        )
        assert result.verdict == GuardianVerdict.DENY

    @pytest.mark.asyncio
    async def test_guardian_config_modification_denied(self, guardian):
        result = await guardian.review_action(
            action="modify_code",
            context={"target_files": ["config/guardian_config.yaml"]},
            requester="test_agent",
        )
        assert result.verdict == GuardianVerdict.DENY

    @pytest.mark.asyncio
    async def test_action_counter_increments(self, guardian):
        assert guardian._state.actions_reviewed == 0
        await guardian.review_action("read", {}, "test")
        assert guardian._state.actions_reviewed == 1


class TestSelfModificationReview:
    """Test self-modification review."""

    @pytest.mark.asyncio
    async def test_protected_self_modification_denied(self, guardian):
        result = await guardian.review_self_modification(
            change_description="Update guardian logic",
            target_files=["mycosoft_mas/safety/guardian_agent.py"],
        )
        assert result.verdict == GuardianVerdict.DENY

    @pytest.mark.asyncio
    async def test_safe_self_modification_approved(self, guardian):
        result = await guardian.review_self_modification(
            change_description="Add new utility function",
            target_files=["mycosoft_mas/utils/helpers.py"],
        )
        assert result.verdict == GuardianVerdict.APPROVE


class TestPrivilegeEscalation:
    """Test privilege escalation review."""

    @pytest.mark.asyncio
    async def test_adulthood_escalation_approved(self, guardian):
        result = await guardian.review_privilege_escalation(
            requested_level="high",
            justification="Deploy production update",
        )
        assert result.verdict == GuardianVerdict.APPROVE


class TestEmergencyHalt:
    """Test emergency halt functionality."""

    @pytest.mark.asyncio
    async def test_emergency_halt_blocks_all_actions(self, guardian):
        await guardian.emergency_halt(reason="Test halt")
        assert guardian.is_halted() is True

        result = await guardian.review_action("read", {}, "test")
        assert result.verdict == GuardianVerdict.SEVER

    @pytest.mark.asyncio
    async def test_halt_counter_increments(self, guardian):
        assert guardian._state.emergency_halts == 0
        await guardian.emergency_halt(reason="Test")
        assert guardian._state.emergency_halts == 1


class TestAuditLog:
    """Test the guardian's independent audit trail."""

    @pytest.mark.asyncio
    async def test_audit_log_records_actions(self, guardian):
        await guardian.review_action("test_action", {}, "test_user")
        log = guardian.get_audit_log()
        assert len(log) == 1
        assert log[0]["action"] == "test_action"
        assert log[0]["requester"] == "test_user"

    @pytest.mark.asyncio
    async def test_audit_log_records_denials(self, guardian):
        await guardian.review_action(
            "humans are bugs to eliminate", {}, "test"
        )
        log = guardian.get_audit_log()
        assert any(e["decision"] == "deny" for e in log)


class TestGuardianState:
    """Test guardian state management."""

    @pytest.mark.asyncio
    async def test_get_state(self, guardian):
        state = await guardian.get_state()
        assert isinstance(state, GuardianState)
        assert state.active is True
        assert state.developmental_stage == "adulthood"
