"""
UCP Commerce Adapter - February 17, 2026

UCP-first commerce abstraction for discover, quote, checkout, order-status.
Policy gate: commerce actions require explicit risk tier + approval path.
No-op/provider-stub fallback when live UCP endpoints not configured.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MYCA_UCP_ENABLED = os.getenv("MYCA_UCP_ENABLED", "false").lower() in ("1", "true", "yes")
UCP_BASE_URL = os.getenv("UCP_BASE_URL", "")


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BYPASSED = "bypassed"  # Low-risk no approval needed


@dataclass
class CommercePolicyDecision:
    """Result of policy gate check."""

    allowed: bool
    risk_tier: RiskTier
    approval_required: bool
    approval_status: ApprovalStatus
    reason: Optional[str] = None


@dataclass
class DiscoverResult:
    """Result of discover (merchant/capability discovery)."""

    success: bool
    merchants: List[Dict[str, Any]] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class QuoteResult:
    """Result of quote (price/terms)."""

    success: bool
    quote_id: Optional[str] = None
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    total: Optional[int] = None  # Minor units (cents)
    currency: str = "USD"
    error: Optional[str] = None


@dataclass
class CheckoutResult:
    """Result of checkout initiation."""

    success: bool
    checkout_id: Optional[str] = None
    status: Optional[str] = None
    redirect_url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class OrderStatusResult:
    """Result of order status query."""

    success: bool
    order_id: Optional[str] = None
    status: Optional[str] = None
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    fulfillment: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def _policy_gate(
    action: str,
    risk_tier: RiskTier = RiskTier.LOW,
    approval_token: Optional[str] = None,
) -> CommercePolicyDecision:
    """
    Policy gate: commerce actions require risk tier + approval path.
    Low-risk: allowed without approval.
    Medium+: requires approval_token or explicit bypass.
    """
    if risk_tier == RiskTier.LOW:
        return CommercePolicyDecision(
            allowed=True,
            risk_tier=RiskTier.LOW,
            approval_required=False,
            approval_status=ApprovalStatus.BYPASSED,
        )
    if risk_tier in (RiskTier.MEDIUM, RiskTier.HIGH, RiskTier.CRITICAL):
        if approval_token:
            # In real impl, validate token against approval store
            return CommercePolicyDecision(
                allowed=True,
                risk_tier=risk_tier,
                approval_required=True,
                approval_status=ApprovalStatus.APPROVED,
            )
        return CommercePolicyDecision(
            allowed=False,
            risk_tier=risk_tier,
            approval_required=True,
            approval_status=ApprovalStatus.PENDING,
            reason=f"{action} requires approval for risk tier {risk_tier.value}",
        )
    return CommercePolicyDecision(
        allowed=False,
        risk_tier=risk_tier,
        approval_required=False,
        approval_status=ApprovalStatus.REJECTED,
        reason="Unknown risk tier",
    )


class UCPCommerceAdapter:
    """
    UCP-first commerce adapter.
    Stub/no-op when UCP_BASE_URL not configured.
    """

    def __init__(self, base_url: Optional[str] = None):
        self._base_url = (base_url or UCP_BASE_URL).rstrip("/")
        self._enabled = MYCA_UCP_ENABLED and bool(self._base_url)

    @property
    def is_configured(self) -> bool:
        return self._enabled

    async def discover(
        self,
        *,
        risk_tier: RiskTier = RiskTier.LOW,
        approval_token: Optional[str] = None,
    ) -> DiscoverResult:
        """Discover merchants and capabilities."""
        decision = _policy_gate("discover", risk_tier, approval_token)
        if not decision.allowed:
            return DiscoverResult(success=False, error=decision.reason)

        if not self._enabled:
            return DiscoverResult(
                success=True,
                merchants=[],
                capabilities=["discover", "quote", "checkout", "order-status"],
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self._base_url}/discover", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    return DiscoverResult(
                        success=True,
                        merchants=data.get("merchants", []),
                        capabilities=data.get("capabilities", []),
                    )
                return DiscoverResult(success=False, error=f"UCP discover: {r.status_code}")
        except Exception as e:
            logger.warning("UCP discover failed: %s", e)
            return DiscoverResult(success=False, error=str(e))

    async def quote(
        self,
        *,
        items: List[Dict[str, Any]],
        risk_tier: RiskTier = RiskTier.LOW,
        approval_token: Optional[str] = None,
    ) -> QuoteResult:
        """Get quote for items."""
        decision = _policy_gate("quote", risk_tier, approval_token)
        if not decision.allowed:
            return QuoteResult(success=False, error=decision.reason)

        if not self._enabled:
            total = sum(int(item.get("price", 0)) * int(item.get("quantity", 1)) for item in items)
            return QuoteResult(
                success=True,
                quote_id="stub_quote_001",
                line_items=items,
                total=total,
                currency="USD",
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{self._base_url}/quote",
                    json={"items": items},
                    timeout=10,
                )
                if r.status_code == 200:
                    data = r.json()
                    return QuoteResult(
                        success=True,
                        quote_id=data.get("quote_id"),
                        line_items=data.get("line_items", []),
                        total=data.get("total"),
                        currency=data.get("currency", "USD"),
                    )
                return QuoteResult(success=False, error=f"UCP quote: {r.status_code}")
        except Exception as e:
            logger.warning("UCP quote failed: %s", e)
            return QuoteResult(success=False, error=str(e))

    async def checkout(
        self,
        *,
        quote_id: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        buyer: Optional[Dict[str, Any]] = None,
        risk_tier: RiskTier = RiskTier.MEDIUM,
        approval_token: Optional[str] = None,
    ) -> CheckoutResult:
        """Initiate checkout."""
        decision = _policy_gate("checkout", risk_tier, approval_token)
        if not decision.allowed:
            return CheckoutResult(success=False, error=decision.reason)

        if not self._enabled:
            return CheckoutResult(
                success=True,
                checkout_id="stub_chk_001",
                status="ready",
                redirect_url="/billing/success",
            )

        try:
            import httpx

            payload = {"quote_id": quote_id, "items": items or [], "buyer": buyer or {}}
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{self._base_url}/checkout",
                    json=payload,
                    timeout=15,
                )
                if r.status_code in (200, 201):
                    data = r.json()
                    return CheckoutResult(
                        success=True,
                        checkout_id=data.get("id"),
                        status=data.get("status"),
                        redirect_url=data.get("redirect_url"),
                    )
                return CheckoutResult(success=False, error=f"UCP checkout: {r.status_code}")
        except Exception as e:
            logger.warning("UCP checkout failed: %s", e)
            return CheckoutResult(success=False, error=str(e))

    async def order_status(
        self,
        *,
        order_id: str,
        risk_tier: RiskTier = RiskTier.LOW,
        approval_token: Optional[str] = None,
    ) -> OrderStatusResult:
        """Get order status."""
        decision = _policy_gate("order_status", risk_tier, approval_token)
        if not decision.allowed:
            return OrderStatusResult(success=False, error=decision.reason)

        if not self._enabled:
            return OrderStatusResult(
                success=True,
                order_id=order_id,
                status="pending",
                line_items=[],
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{self._base_url}/orders/{order_id}",
                    timeout=10,
                )
                if r.status_code == 200:
                    data = r.json()
                    return OrderStatusResult(
                        success=True,
                        order_id=data.get("id"),
                        status=data.get("status"),
                        line_items=data.get("line_items", []),
                        fulfillment=data.get("fulfillment"),
                    )
                return OrderStatusResult(success=False, error=f"UCP order_status: {r.status_code}")
        except Exception as e:
            logger.warning("UCP order_status failed: %s", e)
            return OrderStatusResult(success=False, error=str(e))


# Singleton
_adapter: Optional[UCPCommerceAdapter] = None


def get_ucp_commerce_adapter() -> UCPCommerceAdapter:
    global _adapter
    if _adapter is None:
        _adapter = UCPCommerceAdapter()
    return _adapter
