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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/economy", tags=["economy"])


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
    """Revenue metrics."""
    daily_revenue: float
    weekly_revenue: float
    monthly_revenue: float
    total_revenue: float
    active_clients: int
    agent_clients: int
    human_clients: int
    avg_revenue_per_client: float
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
# In-memory state (would be backed by database in production)
# ============================================================================

_economy_state = {
    "wallets": {
        "solana": {"address": "MYCA_SOL_WALLET", "balance": 0.0, "currency": "SOL"},
        "bitcoin": {"address": "MYCA_BTC_WALLET", "balance": 0.0, "currency": "BTC"},
        "x401": {"address": "MYCA_X401_WALLET", "balance": 0.0, "currency": "X401"},
    },
    "total_revenue": 0.0,
    "transactions": [],
    "active_clients": {},
    "resource_purchases": [],
    "incentives": [],
    "pricing_tiers": {
        "free": {"price_per_request": 0.0, "daily_limit": 10, "features": ["basic_query", "taxonomy_lookup"]},
        "agent": {"price_per_request": 0.001, "daily_limit": 10000, "features": ["all_queries", "data_access", "api_tools"]},
        "premium": {"price_per_request": 0.01, "daily_limit": 100000, "features": ["all_queries", "data_access", "api_tools", "simulations", "priority"]},
        "enterprise": {"price_per_request": 0.005, "daily_limit": 1000000, "features": ["unlimited", "custom_models", "dedicated_compute", "sla"]},
    },
}


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/health")
async def economy_health():
    """Check economy system health."""
    return {
        "status": "healthy",
        "wallets_active": len(_economy_state["wallets"]),
        "total_revenue": _economy_state["total_revenue"],
        "active_clients": len(_economy_state["active_clients"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/wallets")
async def list_wallets() -> List[WalletInfo]:
    """List MYCA's cryptocurrency wallets."""
    wallets = []
    for wtype, wdata in _economy_state["wallets"].items():
        wallets.append(WalletInfo(
            wallet_type=wtype,
            address=wdata["address"],
            balance=wdata["balance"],
            currency=wdata["currency"],
            last_updated=datetime.now(timezone.utc).isoformat(),
        ))
    return wallets


@router.get("/wallets/{wallet_type}")
async def get_wallet(wallet_type: str) -> WalletInfo:
    """Get a specific wallet's information."""
    if wallet_type not in _economy_state["wallets"]:
        raise HTTPException(status_code=404, detail=f"Wallet type '{wallet_type}' not found")
    wdata = _economy_state["wallets"][wallet_type]
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
    # Look up client tier
    client_tier = _economy_state["active_clients"].get(request.client_id, {}).get("tier", "agent")
    tier_pricing = _economy_state["pricing_tiers"].get(client_tier, _economy_state["pricing_tiers"]["agent"])

    amount = request.amount or tier_pricing["price_per_request"]

    # Record transaction
    tx_id = f"tx_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{request.client_id[:8]}"
    transaction = {
        "id": tx_id,
        "client_id": request.client_id,
        "amount": amount,
        "currency": request.currency,
        "service_type": request.service_type,
        "status": "completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _economy_state["transactions"].append(transaction)
    _economy_state["total_revenue"] += amount

    # Update wallet balance
    wallet_map = {"SOL": "solana", "BTC": "bitcoin", "X401": "x401"}
    wallet_key = wallet_map.get(request.currency, "solana")
    if wallet_key in _economy_state["wallets"]:
        _economy_state["wallets"][wallet_key]["balance"] += amount

    logger.info("Charged %s %.6f %s for %s", request.client_id, amount, request.currency, request.service_type)

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
    """Get MYCA's revenue metrics."""
    clients = _economy_state["active_clients"]
    agent_count = sum(1 for c in clients.values() if c.get("type") == "agent")
    human_count = sum(1 for c in clients.values() if c.get("type") == "human")
    total_clients = len(clients) or 1  # Avoid division by zero

    return RevenueMetrics(
        daily_revenue=_economy_state["total_revenue"] * 0.033,  # Estimate
        weekly_revenue=_economy_state["total_revenue"] * 0.23,
        monthly_revenue=_economy_state["total_revenue"],
        total_revenue=_economy_state["total_revenue"],
        active_clients=len(clients),
        agent_clients=agent_count,
        human_clients=human_count,
        avg_revenue_per_client=_economy_state["total_revenue"] / total_clients,
    )


@router.get("/pricing")
async def get_pricing_tiers() -> Dict[str, PricingTierInfo]:
    """Get available pricing tiers."""
    tiers = {}
    for tier_name, tier_data in _economy_state["pricing_tiers"].items():
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
    # Check if we have sufficient funds
    total_cost = request.quantity * request.max_price
    total_balance = sum(w["balance"] for w in _economy_state["wallets"].values())

    if total_balance < total_cost:
        return {
            "status": "insufficient_funds",
            "required": total_cost,
            "available": total_balance,
            "message": "Need more revenue to purchase this resource",
        }

    purchase = {
        "resource_type": request.resource_type,
        "quantity": request.quantity,
        "total_cost": total_cost,
        "vendor": request.vendor_preference or "auto_selected",
        "status": "pending",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _economy_state["resource_purchases"].append(purchase)

    logger.info("Resource purchase initiated: %d x %s at $%.2f", request.quantity, request.resource_type, total_cost)

    return {
        "status": "purchase_initiated",
        "purchase": purchase,
        "message": f"Purchasing {request.quantity} {request.resource_type} units",
    }


@router.get("/resources/needs")
async def evaluate_resource_needs() -> Dict[str, Any]:
    """Evaluate what resources MYCA needs to purchase."""
    return {
        "status": "success",
        "needs": [
            {"resource": "gpu", "priority": "critical", "quantity": 4, "type": "A100/H100", "estimated_cost": 40000,
             "reason": "Local LLM inference and fine-tuning"},
            {"resource": "storage", "priority": "critical", "quantity": 10000, "unit": "TB", "estimated_cost": 50000,
             "reason": "MINDEX data: all taxonomy, genetic, chemical, image data"},
            {"resource": "nas", "priority": "high", "quantity": 5, "type": "Synology 8-bay", "estimated_cost": 15000,
             "reason": "Distributed NAS for environmental and taxonomy images"},
            {"resource": "compute", "priority": "high", "quantity": 8, "type": "vCPU nodes", "estimated_cost": 5000,
             "reason": "Data ingestion and processing pipeline"},
            {"resource": "memory", "priority": "medium", "quantity": 512, "unit": "GB", "estimated_cost": 2000,
             "reason": "In-memory caching for real-time queries"},
        ],
        "total_estimated_cost": 112000,
        "current_balance": sum(w["balance"] for w in _economy_state["wallets"].values()),
        "revenue_needed": 112000 - sum(w["balance"] for w in _economy_state["wallets"].values()),
    }


@router.post("/incentives")
async def create_agent_incentive(request: IncentiveRequest) -> Dict[str, Any]:
    """Create an incentive for an agent to use MYCA's services."""
    incentive = {
        "agent_id": request.agent_id,
        "type": request.incentive_type,
        "value": request.value,
        "duration_days": request.duration_days,
        "description": request.description,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _economy_state["incentives"].append(incentive)

    logger.info("Created incentive for %s: %s (%.2f)", request.agent_id, request.incentive_type, request.value)

    return {"status": "success", "incentive": incentive}


@router.get("/incentives")
async def list_incentives() -> Dict[str, Any]:
    """List all active incentives."""
    return {
        "status": "success",
        "incentives": _economy_state["incentives"],
        "total_active": len([i for i in _economy_state["incentives"] if i["status"] == "active"]),
    }


@router.get("/summary")
async def get_economic_summary() -> Dict[str, Any]:
    """Get a full economic summary of MYCA's autonomous economy."""
    return {
        "status": "success",
        "wallets": {k: {"balance": v["balance"], "currency": v["currency"]}
                    for k, v in _economy_state["wallets"].items()},
        "total_revenue": _economy_state["total_revenue"],
        "total_transactions": len(_economy_state["transactions"]),
        "active_clients": len(_economy_state["active_clients"]),
        "resource_purchases": len(_economy_state["resource_purchases"]),
        "active_incentives": len([i for i in _economy_state["incentives"] if i["status"] == "active"]),
        "pricing_tiers": list(_economy_state["pricing_tiers"].keys()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/clients/register")
async def register_client(client_id: str, client_type: str = "agent",
                          tier: str = "agent") -> Dict[str, Any]:
    """Register a new client (agent or human) in the economy."""
    _economy_state["active_clients"][client_id] = {
        "type": client_type,
        "tier": tier,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "total_spent": 0.0,
    }
    logger.info("New client registered: %s (type=%s, tier=%s)", client_id, client_type, tier)
    return {
        "status": "success",
        "client_id": client_id,
        "tier": tier,
        "message": f"Welcome to MYCA's economy. Your tier: {tier}",
    }
