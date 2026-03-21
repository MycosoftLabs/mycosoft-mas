"""
Protocol UCP tests - February 17, 2026

UCP order-risk policy, commerce policy gate, and commerce adapter behavior.
CI gate: fail-fast on policy violations.
"""

from __future__ import annotations

import asyncio

import pytest

from mycosoft_mas.integrations.ucp_commerce_adapter import (
    ApprovalStatus,
    RiskTier,
    _policy_gate,
    get_ucp_commerce_adapter,
)


class TestUCPPolicyGate:
    """UCP order-risk policy - low allows bypass, medium+ requires approval."""

    def test_low_risk_allowed_without_approval(self):
        d = _policy_gate("discover", risk_tier=RiskTier.LOW)
        assert d.allowed is True
        assert d.approval_required is False
        assert d.approval_status == ApprovalStatus.BYPASSED

    def test_medium_risk_requires_approval(self):
        d = _policy_gate("checkout", risk_tier=RiskTier.MEDIUM)
        assert d.allowed is False
        assert d.approval_required is True
        assert d.approval_status == ApprovalStatus.PENDING
        assert "approval" in (d.reason or "").lower()

    def test_medium_risk_allowed_with_approval_token(self):
        d = _policy_gate("checkout", risk_tier=RiskTier.MEDIUM, approval_token="tok123")
        assert d.allowed is True
        assert d.approval_status == ApprovalStatus.APPROVED

    def test_high_risk_requires_approval(self):
        d = _policy_gate("checkout", risk_tier=RiskTier.HIGH)
        assert d.allowed is False
        assert d.approval_required is True

    def test_critical_risk_requires_approval(self):
        d = _policy_gate("checkout", risk_tier=RiskTier.CRITICAL)
        assert d.allowed is False
        assert d.approval_required is True


@pytest.fixture
def adapter():
    return get_ucp_commerce_adapter()


class TestUCPCommerceAdapter:
    """UCP commerce adapter - discover, quote, checkout, order-status."""

    def test_discover_returns_stub_when_ucp_disabled(self, adapter):
        r = asyncio.run(adapter.discover())
        assert r.success is True

    @pytest.mark.asyncio
    async def test_quote_low_risk_allowed(self, adapter):
        r = await adapter.quote(items=[], risk_tier=RiskTier.LOW)
        assert r.success is True

    @pytest.mark.asyncio
    async def test_quote_medium_risk_without_approval_blocked(self, adapter):
        r = await adapter.quote(items=[], risk_tier=RiskTier.MEDIUM)
        assert r.success is False
        assert "approval" in (r.error or "").lower()

    @pytest.mark.asyncio
    async def test_checkout_medium_risk_with_approval_allowed(self, adapter):
        r = await adapter.checkout(
            quote_id="q1",
            items=[],
            risk_tier=RiskTier.MEDIUM,
            approval_token="tok",
        )
        assert r.success is True

    @pytest.mark.asyncio
    async def test_order_status_read_only_allowed(self, adapter):
        r = await adapter.order_status(order_id="ord_123")
        assert r.success is True
