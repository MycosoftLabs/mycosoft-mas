"""Tests for the Capability Foundry."""

import pytest

from mycosoft_mas.capabilities.foundry import (
    CapabilityFoundry,
    CapabilityRequest,
    CapabilityStatus,
    DeployTarget,
)


@pytest.fixture
def foundry():
    return CapabilityFoundry()


class TestCapabilityDetection:
    """Test missing capability detection."""

    @pytest.mark.asyncio
    async def test_detect_stripe(self, foundry):
        result = await foundry.detect_missing(
            {"description": "Process a Stripe payment"}
        )
        assert result == "payment_processing"

    @pytest.mark.asyncio
    async def test_detect_email(self, foundry):
        result = await foundry.detect_missing(
            {"description": "Send an email notification"}
        )
        assert result == "email_management"

    @pytest.mark.asyncio
    async def test_detect_custom(self, foundry):
        result = await foundry.detect_missing(
            {"description": "Custom unknown task"}
        )
        assert result is not None
        assert result.startswith("custom_")

    @pytest.mark.asyncio
    async def test_empty_description_returns_none(self, foundry):
        result = await foundry.detect_missing({"description": ""})
        assert result is None


class TestSecurityScan:
    """Test security scanning of capabilities."""

    @pytest.mark.asyncio
    async def test_clean_code_passes(self, foundry):
        from mycosoft_mas.capabilities.foundry import CapabilityAdapter, CapabilityCandidate

        adapter = CapabilityAdapter(
            adapter_id="test",
            name="test",
            description="test",
            source_candidate=CapabilityCandidate(
                source="test", name="test", description="test", source_type="test"
            ),
            code="def hello(): return 'world'",
        )
        result = await foundry.security_scan(adapter)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_eval_code_fails(self, foundry):
        from mycosoft_mas.capabilities.foundry import CapabilityAdapter, CapabilityCandidate

        adapter = CapabilityAdapter(
            adapter_id="test",
            name="test",
            description="test",
            source_candidate=CapabilityCandidate(
                source="test", name="test", description="test", source_type="test"
            ),
            code="result = eval(user_input)",
        )
        result = await foundry.security_scan(adapter)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_subprocess_code_fails(self, foundry):
        from mycosoft_mas.capabilities.foundry import CapabilityAdapter, CapabilityCandidate

        adapter = CapabilityAdapter(
            adapter_id="test",
            name="test",
            description="test",
            source_candidate=CapabilityCandidate(
                source="test", name="test", description="test", source_type="test"
            ),
            code="import subprocess; subprocess.run(['rm', '-rf', '/'])",
        )
        result = await foundry.security_scan(adapter)
        assert result.passed is False


class TestPolicyCheck:
    """Test policy checking."""

    @pytest.mark.asyncio
    async def test_medium_risk_passes(self, foundry):
        from mycosoft_mas.capabilities.foundry import CapabilityAdapter, CapabilityCandidate

        adapter = CapabilityAdapter(
            adapter_id="test",
            name="test",
            description="test",
            source_candidate=CapabilityCandidate(
                source="test", name="test", description="test", source_type="test"
            ),
            config={"risk_tier": "medium"},
        )
        result = await foundry.policy_check(adapter)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_critical_risk_requires_approval(self, foundry):
        from mycosoft_mas.capabilities.foundry import CapabilityAdapter, CapabilityCandidate

        adapter = CapabilityAdapter(
            adapter_id="test",
            name="test",
            description="test",
            source_candidate=CapabilityCandidate(
                source="test", name="test", description="test", source_type="test"
            ),
            config={"risk_tier": "critical"},
        )
        result = await foundry.policy_check(adapter)
        assert result.passed is False


class TestDeployTarget:
    """Test deployment target determination."""

    def test_low_risk_goes_to_production(self, foundry):
        assert foundry._determine_deploy_target("low") == DeployTarget.PRODUCTION

    def test_medium_risk_goes_to_staging(self, foundry):
        assert foundry._determine_deploy_target("medium") == DeployTarget.STAGING

    def test_high_risk_goes_to_sandbox(self, foundry):
        assert foundry._determine_deploy_target("high") == DeployTarget.SANDBOX
