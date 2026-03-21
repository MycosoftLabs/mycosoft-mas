"""
Economy API - MYCA's Autonomous Economic System Endpoints
=========================================================

Provides API endpoints for MYCA's self-funded economy:
- Service pricing and charging
- Wallet management
- Revenue tracking
- Resource purchasing
- Agent monetization and incentives

Author: MYCA / Morgan Rockwell
Created: March 3, 2026
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.core.persistence import economy_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/economy", tags=["economy"])

RECORDED_PURCHASES_CAP = 50

RESOURCE_NEEDS_NO_FORECAST_MESSAGE = (
    "Resource needs forecasts are not returned without a real planning source "
    "(budget, capex plan, or inventory-linked forecast). "
    "Recorded historical purchases and current wallet balances are provided below."
)


# ============================================================================
# Request/Response Models
# ============================================================================


class ChargeRequest(BaseModel):
    """Request to charge for a service."""

    client_id: str
    service_type: str
    amount: Optional[float] = None
    currency: str = "SOL"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChargeResponse(BaseModel):
    """Response from a charge operation."""

    transaction_id: str
    client_id: str
    amount: float
    currency: str
    status: str
    timestamp: str


class WalletInfo(BaseModel):
    """Wallet information."""

    wallet_type: str
    address: str
    balance: float
    currency: str
    last_updated: str


class RevenueMetrics(BaseModel):
    """Revenue metrics from completed transactions; period sums are UTC bucket totals."""

    daily_revenue: float
    weekly_revenue: float
    monthly_revenue: float
    total_revenue: float
    active_clients: int
    agent_clients: int
    human_clients: int
    avg_revenue_per_client: float
    period_metrics_available: bool
    currency: str = "USD"


class ResourcePurchaseRequest(BaseModel):
    """Request to purchase a resource."""

    resource_type: str  # "gpu", "storage", "compute", "memory"
    quantity: int
    max_price: float
    currency: str = "USD"
    vendor_preference: Optional[str] = None


class PricingTierInfo(BaseModel):
    """Information about a pricing tier."""

    tier: str
    price_per_request: float
    daily_limit: int
    features: List[str]
    currency: str = "USD"


class IncentiveRequest(BaseModel):
    """Request to create an agent incentive."""

    agent_id: str
    incentive_type: str  # "discount", "bonus", "free_tier", "referral"
    value: float
    duration_days: int = 30
    description: str = ""


# ============================================================================
# STORAGE: economy_store (Supabase when configured, else in-memory)
# ============================================================================


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/health")
async def economy_health():
    """Check economy system health."""
    state = economy_store.get_state()
    return {
        "status": "healthy",
        "wallets_active": len(state["wallets"]),
        "total_revenue": state["total_revenue"],
        "active_clients": len(state["active_clients"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/wallets")
async def list_wallets() -> List[WalletInfo]:
    """List MYCA's cryptocurrency wallets."""
    state = economy_store.get_state()
    wallets = []
    for wtype, wdata in state["wallets"].items():
        wallets.append(
            WalletInfo(
                wallet_type=wtype,
                address=wdata["address"],
                balance=wdata["balance"],
                currency=wdata["currency"],
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
        )
    return wallets


@router.get("/wallets/{wallet_type}")
async def get_wallet(wallet_type: str) -> WalletInfo:
    """Get a specific wallet's information."""
    state = economy_store.get_state()
    if wallet_type not in state["wallets"]:
        raise HTTPException(status_code=404, detail=f"Wallet type '{wallet_type}' not found")
    wdata = state["wallets"][wallet_type]
    return WalletInfo(
        wallet_type=wallet_type,
        address=wdata["address"],
        balance=wdata["balance"],
        currency=wdata["currency"],
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/charge")
async def charge_for_service(request: ChargeRequest) -> ChargeResponse:
    """Charge a client for a MYCA service."""
    state = economy_store.get_state()
    # Look up client tier
    client_tier = state["active_clients"].get(request.client_id, {}).get("tier", "agent")
    tier_pricing = state["pricing_tiers"].get(client_tier, state["pricing_tiers"]["agent"])

    amount = request.amount or tier_pricing["price_per_request"]

    # Record transaction
    tx_id = f"tx_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{request.client_id[:8]}"
    economy_store.record_charge(
        transaction_id=tx_id,
        client_id=request.client_id,
        amount=amount,
        currency=request.currency,
        service_type=request.service_type,
    )

    logger.info(
        "Charged %s %.6f %s for %s",
        request.client_id,
        amount,
        request.currency,
        request.service_type,
    )

    return ChargeResponse(
        transaction_id=tx_id,
        client_id=request.client_id,
        amount=amount,
        currency=request.currency,
        status="completed",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/revenue")
async def get_revenue_metrics() -> RevenueMetrics:
    """Revenue from completed transactions only; UTC daily/weekly/monthly from parseable timestamps."""
    state = economy_store.get_state()
    clients = state["active_clients"]
    agent_count = sum(1 for c in clients.values() if c.get("type") == "agent")
    human_count = sum(1 for c in clients.values() if c.get("type") == "human")
    n_clients = len(clients)
    periods = economy_store.get_revenue_period_totals()

    avg_per_client = 0.0 if n_clients == 0 else float(state["total_revenue"]) / n_clients

    return RevenueMetrics(
        daily_revenue=float(periods["daily_revenue"]),
        weekly_revenue=float(periods["weekly_revenue"]),
        monthly_revenue=float(periods["monthly_revenue"]),
        total_revenue=float(state["total_revenue"]),
        active_clients=n_clients,
        agent_clients=agent_count,
        human_clients=human_count,
        avg_revenue_per_client=avg_per_client,
        period_metrics_available=bool(periods["period_metrics_available"]),
    )


@router.get("/pricing")
async def get_pricing_tiers() -> Dict[str, PricingTierInfo]:
    """Get available pricing tiers."""
    state = economy_store.get_state()
    tiers = {}
    for tier_name, tier_data in state["pricing_tiers"].items():
        tiers[tier_name] = PricingTierInfo(
            tier=tier_name,
            price_per_request=tier_data["price_per_request"],
            daily_limit=tier_data["daily_limit"],
            features=tier_data["features"],
        )
    return tiers


@router.post("/resources/purchase")
async def purchase_resource(request: ResourcePurchaseRequest) -> Dict[str, Any]:
    """Purchase a resource (GPU, storage, compute) with MYCA's funds."""
    state = economy_store.get_state()
    # Check if we have sufficient funds
    total_cost = request.quantity * request.max_price
    total_balance = sum(w["balance"] for w in state["wallets"].values())

    if total_balance < total_cost:
        return {
            "status": "insufficient_funds",
            "required": total_cost,
            "available": total_balance,
            "message": "Need more revenue to purchase this resource",
        }

    economy_store.add_resource_purchase(
        resource_type=request.resource_type,
        quantity=request.quantity,
        total_cost=total_cost,
        vendor=request.vendor_preference or "auto_selected",
        status="pending",
    )
    purchase = {
        "resource_type": request.resource_type,
        "quantity": request.quantity,
        "total_cost": total_cost,
        "vendor": request.vendor_preference or "auto_selected",
        "status": "pending",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "Resource purchase initiated: %d x %s at $%.2f",
        request.quantity,
        request.resource_type,
        total_cost,
    )

    return {
        "status": "purchase_initiated",
        "purchase": purchase,
        "message": f"Purchasing {request.quantity} {request.resource_type} units",
    }


@router.get("/resources/needs")
async def evaluate_resource_needs() -> Dict[str, Any]:
    """
    No speculative resource forecasts: empty needs, null cost totals.
    Returns wallet-derived current_balance and a capped list of recorded purchases.
    """
    state = economy_store.get_state()
    current_balance = float(sum(w["balance"] for w in state["wallets"].values()))
    purchases = list(state.get("resource_purchases") or [])
    recorded_purchases = purchases[-RECORDED_PURCHASES_CAP:]
    return {
        "status": "success",
        "needs": [],
        "total_estimated_cost": None,
        "revenue_needed": None,
        "current_balance": current_balance,
        "recorded_purchases": recorded_purchases,
        "message": RESOURCE_NEEDS_NO_FORECAST_MESSAGE,
    }


@router.post("/incentives")
async def create_agent_incentive(request: IncentiveRequest) -> Dict[str, Any]:
    """Create an incentive for an agent to use MYCA's services."""
    economy_store.add_incentive(
        agent_id=request.agent_id,
        incentive_type=request.incentive_type,
        value=request.value,
        duration_days=request.duration_days,
        description=request.description,
    )
    incentive = {
        "agent_id": request.agent_id,
        "type": request.incentive_type,
        "value": request.value,
        "duration_days": request.duration_days,
        "description": request.description,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "Created incentive for %s: %s (%.2f)",
        request.agent_id,
        request.incentive_type,
        request.value,
    )

    return {"status": "success", "incentive": incentive}


@router.get("/incentives")
async def list_incentives() -> Dict[str, Any]:
    """List all active incentives."""
    state = economy_store.get_state()
    return {
        "status": "success",
        "incentives": state["incentives"],
        "total_active": len([i for i in state["incentives"] if i.get("status") == "active"]),
    }


@router.get("/summary")
async def get_economic_summary() -> Dict[str, Any]:
    """Get a full economic summary of MYCA's autonomous economy."""
    state = economy_store.get_state()
    return {
        "status": "success",
        "wallets": {
            k: {"balance": v["balance"], "currency": v["currency"]}
            for k, v in state["wallets"].items()
        },
        "total_revenue": state["total_revenue"],
        "total_transactions": len(state["transactions"]),
        "active_clients": len(state["active_clients"]),
        "resource_purchases": len(state["resource_purchases"]),
        "active_incentives": len([i for i in state["incentives"] if i.get("status") == "active"]),
        "pricing_tiers": list(state["pricing_tiers"].keys()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# x402-style metering, settlement, and authorization
# ============================================================================


class MeterRequest(BaseModel):
    """Request to record usage for billing (x402-style metering)."""

    client_id: str
    service_type: str
    units: float = 1.0
    unit_price: Optional[float] = None
    currency: str = "X401"


class SettleRequest(BaseModel):
    """Request to settle a metered usage to a charge."""

    usage_id: str


@router.post("/meter")
async def meter_usage(request: MeterRequest) -> Dict[str, Any]:
    """Record usage for x402-style request metering. Creates a meter record for later settlement."""
    state = economy_store.get_state()
    client_tier = state["active_clients"].get(request.client_id, {}).get("tier", "agent")
    tier_pricing = state["pricing_tiers"].get(client_tier, state["pricing_tiers"]["agent"])
    unit_price = (
        request.unit_price if request.unit_price is not None else tier_pricing["price_per_request"]
    )
    usage_id = (
        f"usage_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{request.client_id[:8]}"
    )
    economy_store.record_meter(
        usage_id=usage_id,
        client_id=request.client_id,
        service_type=request.service_type,
        units=request.units,
        unit_price=unit_price,
        currency=request.currency,
    )
    amount = request.units * unit_price
    return {
        "status": "metered",
        "usage_id": usage_id,
        "client_id": request.client_id,
        "service_type": request.service_type,
        "units": request.units,
        "unit_price": unit_price,
        "amount": amount,
        "currency": request.currency,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/settle")
async def settle_usage(request: SettleRequest) -> Dict[str, Any]:
    """Settle a metered usage into a completed charge (agent settlement)."""
    tx_id = f"tx_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_settle"
    ok = economy_store.settle_metered(usage_id=request.usage_id, transaction_id=tx_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"Metered usage '{request.usage_id}' not found or already settled",
        )
    return {
        "status": "settled",
        "usage_id": request.usage_id,
        "transaction_id": tx_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/authorize")
async def authorize_payment(
    client_id: str,
    service_type: str = "api_request",
    estimated_amount: Optional[float] = None,
    currency: str = "X401",
) -> Dict[str, Any]:
    """Check if client/agent can pay for a service (tier limits, balance). Used before serving paid requests."""
    state = economy_store.get_state()
    client_tier = state["active_clients"].get(client_id, {}).get("tier", "agent")
    tier_pricing = state["pricing_tiers"].get(client_tier, state["pricing_tiers"]["agent"])
    amount = estimated_amount if estimated_amount is not None else tier_pricing["price_per_request"]
    result = economy_store.can_authorize(
        client_id=client_id,
        service_type=service_type,
        estimated_amount=amount,
        currency=currency,
    )
    return {
        "authorized": result["authorized"],
        "reason": result["reason"],
        "tier": result["tier"],
        "balance": result["balance"],
        "daily_limit": result["daily_limit"],
        "estimated_amount": result["estimated_amount"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/clients/register")
async def register_client(
    client_id: str, client_type: str = "agent", tier: str = "agent"
) -> Dict[str, Any]:
    """Register a new client (agent or human) in the economy."""
    economy_store.register_client(client_id=client_id, client_type=client_type, tier=tier)
    logger.info("New client registered: %s (type=%s, tier=%s)", client_id, client_type, tier)
    return {
        "status": "success",
        "client_id": client_id,
        "tier": tier,
        "message": f"Welcome to MYCA's economy. Your tier: {tier}",
    }
