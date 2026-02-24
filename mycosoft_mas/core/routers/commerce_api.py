"""
MAS Commerce API - February 17, 2026

UCP-first commerce orchestrator.
Website pricing/billing pages call this instead of ad-hoc flows.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.integrations.ucp_commerce_adapter import (
    get_ucp_commerce_adapter,
    RiskTier,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/commerce", tags=["commerce"])


class QuoteRequest(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    risk_tier: str = "low"
    approval_token: Optional[str] = None


class CheckoutRequest(BaseModel):
    quote_id: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    buyer: Optional[Dict[str, Any]] = None
    risk_tier: str = "medium"
    approval_token: Optional[str] = None


class OrderStatusRequest(BaseModel):
    order_id: str
    risk_tier: str = "low"
    approval_token: Optional[str] = None


def _parse_risk_tier(s: str) -> RiskTier:
    try:
        return RiskTier(s.lower())
    except ValueError:
        return RiskTier.LOW


def _log_protocol_event(protocol: str, tool_name: str, risk_tier: str, extra: Optional[Dict[str, Any]] = None):
    """Protocol telemetry - unified event logging for rollout observability."""
    risk_flags = [risk_tier] if risk_tier and risk_tier != "low" else []
    logger.info(
        "protocol_event protocol=%s tool_name=%s risk_flags=%s %s",
        protocol,
        tool_name,
        risk_flags,
        extra or {},
    )


@router.get("/discover")
async def commerce_discover(
    risk_tier: str = "low",
    approval_token: Optional[str] = None,
):
    """Discover merchants and capabilities."""
    _log_protocol_event("ucp", "discover", risk_tier)
    adapter = get_ucp_commerce_adapter()
    rt = _parse_risk_tier(risk_tier)
    result = await adapter.discover(risk_tier=rt, approval_token=approval_token)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "success": True,
        "merchants": result.merchants,
        "capabilities": result.capabilities,
    }


@router.post("/quote")
async def commerce_quote(body: QuoteRequest):
    """Get quote for items."""
    _log_protocol_event("ucp", "quote", body.risk_tier)
    adapter = get_ucp_commerce_adapter()
    rt = _parse_risk_tier(body.risk_tier)
    result = await adapter.quote(
        items=body.items,
        risk_tier=rt,
        approval_token=body.approval_token,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "success": True,
        "quote_id": result.quote_id,
        "line_items": result.line_items,
        "total": result.total,
        "currency": result.currency,
    }


@router.post("/checkout")
async def commerce_checkout(body: CheckoutRequest):
    """Initiate checkout."""
    _log_protocol_event("ucp", "checkout", body.risk_tier)
    adapter = get_ucp_commerce_adapter()
    rt = _parse_risk_tier(body.risk_tier)
    result = await adapter.checkout(
        quote_id=body.quote_id,
        items=body.items,
        buyer=body.buyer,
        risk_tier=rt,
        approval_token=body.approval_token,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "success": True,
        "checkout_id": result.checkout_id,
        "status": result.status,
        "redirect_url": result.redirect_url,
    }


@router.get("/order/{order_id}")
async def commerce_order_status(
    order_id: str,
    risk_tier: str = "low",
    approval_token: Optional[str] = None,
):
    """Get order status."""
    _log_protocol_event("ucp", "order-status", risk_tier, {"order_id": order_id})
    adapter = get_ucp_commerce_adapter()
    rt = _parse_risk_tier(risk_tier)
    result = await adapter.order_status(
        order_id=order_id,
        risk_tier=rt,
        approval_token=approval_token,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "success": True,
        "order_id": result.order_id,
        "status": result.status,
        "line_items": result.line_items,
        "fulfillment": result.fulfillment,
    }
