"""Tests for Sentry Mode."""

import pytest

from mycosoft_mas.guardian.sentry_mode import (
    AlertSeverity,
    SentryMode,
    SentryProfile,
    SentryState,
)


@pytest.fixture
def sentry():
    return SentryMode()


class TestSentryActivation:
    """Test sentry mode activation/deactivation."""

    @pytest.mark.asyncio
    async def test_default_inactive(self, sentry):
        assert sentry.is_active() is False

    @pytest.mark.asyncio
    async def test_activate_default(self, sentry):
        status = await sentry.activate()
        assert status.state == SentryState.ACTIVE
        assert sentry.is_active() is True

    @pytest.mark.asyncio
    async def test_activate_named_profile(self, sentry):
        status = await sentry.activate(profile_name="lab")
        assert status.profile.name == "lab"
        assert "sensors" in status.watch_targets_active

    @pytest.mark.asyncio
    async def test_activate_infrastructure_profile(self, sentry):
        status = await sentry.activate(profile_name="infrastructure")
        assert status.profile.name == "infrastructure"
        assert "vm_health" in status.watch_targets_active

    @pytest.mark.asyncio
    async def test_deactivate(self, sentry):
        await sentry.activate()
        status = await sentry.deactivate()
        assert status.state == SentryState.INACTIVE
        assert sentry.is_active() is False

    @pytest.mark.asyncio
    async def test_unknown_profile_raises(self, sentry):
        with pytest.raises(ValueError, match="Unknown sentry profile"):
            await sentry.activate(profile_name="nonexistent")


class TestBoundedActions:
    """Test that sentry mode enforces bounded actions."""

    @pytest.mark.asyncio
    async def test_monitor_allowed(self, sentry):
        await sentry.activate()
        assert sentry.is_action_allowed("monitor") is True

    @pytest.mark.asyncio
    async def test_alert_allowed(self, sentry):
        await sentry.activate()
        assert sentry.is_action_allowed("alert") is True

    @pytest.mark.asyncio
    async def test_attack_forbidden(self, sentry):
        await sentry.activate()
        assert sentry.is_action_allowed("attack") is False

    @pytest.mark.asyncio
    async def test_escalate_privileges_forbidden(self, sentry):
        await sentry.activate()
        assert sentry.is_action_allowed("escalate_privileges") is False

    @pytest.mark.asyncio
    async def test_modify_infrastructure_forbidden(self, sentry):
        await sentry.activate()
        assert sentry.is_action_allowed("modify_infrastructure") is False

    @pytest.mark.asyncio
    async def test_forbidden_actions_in_profile_rejected(self, sentry):
        with pytest.raises(ValueError, match="forbidden actions"):
            bad_profile = SentryProfile(
                name="bad",
                watch_targets=["network"],
                bounded_actions=["monitor", "attack"],
            )
            await sentry.activate(profile=bad_profile)


class TestAlertProcessing:
    """Test alert processing during sentry mode."""

    @pytest.mark.asyncio
    async def test_process_info_alert(self, sentry):
        await sentry.activate(profile_name="lab")
        alert = await sentry.process_alert({
            "source": "temperature_sensor",
            "description": "Temperature slightly elevated",
            "severity": "info",
        })
        assert alert.severity == AlertSeverity.INFO

    @pytest.mark.asyncio
    async def test_critical_alert_escalates(self, sentry):
        await sentry.activate(profile_name="lab")
        alert = await sentry.process_alert({
            "source": "biosafety",
            "description": "Critical biological_risk_detected",
            "severity": "critical",
        })
        assert alert.escalated is True

    @pytest.mark.asyncio
    async def test_inactive_sentry_rejects_alerts(self, sentry):
        with pytest.raises(RuntimeError, match="inactive"):
            await sentry.process_alert({"source": "test", "description": "test"})


class TestSentryProfiles:
    """Test predefined sentry profiles."""

    def test_available_profiles(self, sentry):
        profiles = sentry.get_available_profiles()
        assert "lab" in profiles
        assert "infrastructure" in profiles
        assert "personal" in profiles
