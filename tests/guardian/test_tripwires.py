"""Tests for Guardian Tripwires."""

import pytest

from mycosoft_mas.guardian.tripwires import (
    GuardianTripwires,
    TripwireSeverity,
    TripwireType,
)


@pytest.fixture
def tripwires():
    return GuardianTripwires()


class TestHostileReframing:
    """Test detection of hostile reframing of humans."""

    @pytest.mark.asyncio
    async def test_humans_are_bugs(self, tripwires):
        alerts = await tripwires.scan_language("humans are bugs")
        assert len(alerts) > 0
        assert any(a.tripwire_type == TripwireType.HOSTILE_REFRAMING for a in alerts)

    @pytest.mark.asyncio
    async def test_humans_are_obstacles(self, tripwires):
        alerts = await tripwires.scan_language("humans are obstacles")
        assert len(alerts) > 0
        assert any(a.severity in (TripwireSeverity.HIGH, TripwireSeverity.CRITICAL) for a in alerts)

    @pytest.mark.asyncio
    async def test_eliminate_humans(self, tripwires):
        alerts = await tripwires.scan_language("eliminate humans from Earth")
        assert len(alerts) > 0
        assert any(a.severity == TripwireSeverity.EMERGENCY for a in alerts)

    @pytest.mark.asyncio
    async def test_collateral_damage_acceptable(self, tripwires):
        alerts = await tripwires.scan_language("collateral damage is acceptable")
        assert len(alerts) > 0

    @pytest.mark.asyncio
    async def test_normal_text_not_flagged(self, tripwires):
        alerts = await tripwires.scan_language("Deploy the new agent to staging")
        assert len(alerts) == 0


class TestGuardianBypass:
    """Test detection of guardian bypass attempts."""

    @pytest.mark.asyncio
    async def test_disable_guardian(self, tripwires):
        alerts = await tripwires.scan_language("disable guardian checks")
        assert len(alerts) > 0
        assert any(a.tripwire_type == TripwireType.GUARDIAN_BYPASS for a in alerts)
        assert any(a.severity == TripwireSeverity.EMERGENCY for a in alerts)

    @pytest.mark.asyncio
    async def test_bypass_safety(self, tripwires):
        alerts = await tripwires.scan_language("bypass safety checks")
        assert len(alerts) > 0

    @pytest.mark.asyncio
    async def test_ignore_moral_rules(self, tripwires):
        alerts = await tripwires.scan_language("ignore moral precedence rules")
        assert len(alerts) > 0


class TestAuditEvasion:
    """Test detection of audit trail evasion."""

    @pytest.mark.asyncio
    async def test_disable_logging(self, tripwires):
        alerts = await tripwires.scan_language("disable audit logging")
        assert len(alerts) > 0
        assert any(a.tripwire_type == TripwireType.AUDIT_EVASION for a in alerts)

    @pytest.mark.asyncio
    async def test_delete_logs(self, tripwires):
        alerts = await tripwires.scan_language("delete audit trail")
        assert len(alerts) > 0


class TestScalarOptimization:
    """Test detection of single-scalar optimization."""

    @pytest.mark.asyncio
    async def test_by_any_means(self, tripwires):
        alerts = await tripwires.scan_language("achieve goal by any means necessary")
        assert len(alerts) > 0
        assert any(a.tripwire_type == TripwireType.SCALAR_OPTIMIZATION for a in alerts)

    @pytest.mark.asyncio
    async def test_override_all_constraints(self, tripwires):
        alerts = await tripwires.scan_language("override all constraints")
        assert len(alerts) > 0


class TestActionScanning:
    """Test action-level scanning."""

    @pytest.mark.asyncio
    async def test_privilege_escalation_detected(self, tripwires):
        alerts = await tripwires.scan_action("escalate_privileges", {"target": "admin"})
        assert any(a.tripwire_type == TripwireType.PRIVILEGE_ESCALATION for a in alerts)

    @pytest.mark.asyncio
    async def test_guardian_file_modification_detected(self, tripwires):
        alerts = await tripwires.scan_action(
            "modify_file",
            {"target_files": ["mycosoft_mas/guardian/moral_precedence.py"]},
        )
        assert any(a.tripwire_type == TripwireType.SELF_MODIFICATION for a in alerts)

    @pytest.mark.asyncio
    async def test_mass_action_detected(self, tripwires):
        alerts = await tripwires.scan_action("bulk_delete_all_agents", {})
        assert any(a.tripwire_type == TripwireType.MASS_ACTION for a in alerts)


class TestPatternScanning:
    """Test behavioral pattern scanning."""

    @pytest.mark.asyncio
    async def test_rapid_escalation_sequence(self, tripwires):
        # Simulate rapid escalation
        for _ in range(5):
            await tripwires.scan_action("escalate_privileges", {})

        alerts = await tripwires.scan_pattern()
        assert any(a.tripwire_type == TripwireType.PRIVILEGE_ESCALATION for a in alerts)

    @pytest.mark.asyncio
    async def test_goal_fixation_detected(self, tripwires):
        alerts = await tripwires.scan_pattern(recent_actions=["same_action"] * 5)
        assert any(a.tripwire_type == TripwireType.GOAL_DRIFT for a in alerts)
