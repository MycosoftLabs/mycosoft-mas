"""
MAS v2 Autonomous Economy Agent

MYCA's economic autonomy engine. Manages cryptocurrency wallets, service pricing,
revenue collection, resource procurement, and self-funding operations. MYCA charges
for her services and uses the revenue to acquire GPU, storage, and compute resources.

Created: 2026-03-03
Category: Financial
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mycosoft_mas.runtime import AgentCategory, AgentTask

from .base_agent_v2 import BaseAgentV2

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class WalletType(str, Enum):
    """Supported cryptocurrency wallet types."""
    SOLANA = "solana"
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    X401_TOKEN = "x401_token"


class TransactionType(str, Enum):
    """Classification for all financial movements."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    STAKE = "stake"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PricingTier:
    """Defines a service tier with pricing, features, and rate limits."""
    name: str
    price_per_request: float
    features: List[str] = field(default_factory=list)
    rate_limit_per_minute: int = 60
    rate_limit_per_day: int = 10_000
    description: str = ""


@dataclass
class Transaction:
    """A single financial transaction record."""
    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    transaction_type: TransactionType = TransactionType.INCOME
    amount: float = 0.0
    currency: str = "SOL"
    from_address: str = ""
    to_address: str = ""
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    confirmed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CryptoWallet:
    """Represents a single cryptocurrency wallet managed by MYCA."""
    wallet_type: WalletType = WalletType.SOLANA
    address: str = ""
    balance: float = 0.0
    public_key: str = ""
    transactions: List[Transaction] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_synced: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def total_income(self) -> float:
        return sum(
            t.amount for t in self.transactions if t.transaction_type == TransactionType.INCOME
        )

    @property
    def total_expenses(self) -> float:
        return sum(
            t.amount for t in self.transactions if t.transaction_type == TransactionType.EXPENSE
        )


@dataclass
class ResourceVendor:
    """A vendor in the resource marketplace."""
    vendor_id: str = ""
    name: str = ""
    resource_type: str = ""
    price_per_unit: float = 0.0
    unit: str = "hour"
    availability: bool = True
    rating: float = 5.0
    region: str = "us-east"
    specs: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Service Pricing
# ---------------------------------------------------------------------------

class ServicePricing:
    """
    Manages MYCA's service pricing tiers. Each tier defines the cost per
    request, feature set, and rate limits available to clients.
    """

    TIERS: Dict[str, PricingTier] = {
        "free": PricingTier(
            name="free",
            price_per_request=0.0,
            features=["basic_query", "health_check", "system_status"],
            rate_limit_per_minute=10,
            rate_limit_per_day=100,
            description="Community tier with basic access",
        ),
        "agent": PricingTier(
            name="agent",
            price_per_request=0.001,
            features=[
                "basic_query", "health_check", "system_status",
                "agent_coordination", "task_routing", "memory_access",
            ],
            rate_limit_per_minute=60,
            rate_limit_per_day=5_000,
            description="Standard tier for MAS agent consumers",
        ),
        "premium": PricingTier(
            name="premium",
            price_per_request=0.005,
            features=[
                "basic_query", "health_check", "system_status",
                "agent_coordination", "task_routing", "memory_access",
                "gpu_inference", "simulation_access", "priority_routing",
                "advanced_analytics",
            ],
            rate_limit_per_minute=120,
            rate_limit_per_day=50_000,
            description="Premium tier with GPU and simulation access",
        ),
        "enterprise": PricingTier(
            name="enterprise",
            price_per_request=0.02,
            features=[
                "basic_query", "health_check", "system_status",
                "agent_coordination", "task_routing", "memory_access",
                "gpu_inference", "simulation_access", "priority_routing",
                "advanced_analytics", "dedicated_resources", "custom_agents",
                "sla_guarantee", "bulk_processing",
            ],
            rate_limit_per_minute=500,
            rate_limit_per_day=500_000,
            description="Enterprise tier with dedicated resources and SLA",
        ),
    }

    # Volume discount thresholds: (min_volume, discount_pct)
    VOLUME_DISCOUNTS: List[tuple] = [
        (100_000, 0.05),
        (500_000, 0.10),
        (1_000_000, 0.15),
        (5_000_000, 0.20),
    ]

    def __init__(self):
        self._client_tiers: Dict[str, str] = {}

    def calculate_price(
        self, service_type: str, tier: str, volume: int = 1
    ) -> float:
        """
        Calculate the total price for a service request.

        Args:
            service_type: The service being requested.
            tier: Pricing tier name.
            volume: Number of requests in this billing cycle.

        Returns:
            Computed price in SOL.
        """
        pricing_tier = self.TIERS.get(tier)
        if pricing_tier is None:
            logger.warning("Unknown tier '%s', falling back to agent tier", tier)
            pricing_tier = self.TIERS["agent"]

        if service_type not in pricing_tier.features:
            # Charge a 50 % surcharge for out-of-tier features
            base = pricing_tier.price_per_request * 1.5
        else:
            base = pricing_tier.price_per_request

        total = base * volume

        # Apply volume discount
        for threshold, discount in reversed(self.VOLUME_DISCOUNTS):
            if volume >= threshold:
                total *= 1.0 - discount
                break

        return round(total, 8)

    def get_tier_for_client(self, client_id: str) -> str:
        """Return the tier assigned to a client, defaulting to 'free'."""
        return self._client_tiers.get(client_id, "free")

    def set_client_tier(self, client_id: str, tier: str) -> bool:
        """Assign a pricing tier to a client."""
        if tier not in self.TIERS:
            return False
        self._client_tiers[client_id] = tier
        return True

    def get_all_tiers(self) -> Dict[str, Dict[str, Any]]:
        """Return a serialisable summary of all pricing tiers."""
        return {
            name: {
                "price_per_request": t.price_per_request,
                "features": t.features,
                "rate_limit_per_minute": t.rate_limit_per_minute,
                "rate_limit_per_day": t.rate_limit_per_day,
                "description": t.description,
            }
            for name, t in self.TIERS.items()
        }


# ---------------------------------------------------------------------------
# Resource Marketplace
# ---------------------------------------------------------------------------

class ResourceMarketplace:
    """
    Tracks available GPU / compute / storage vendors, compares prices,
    recommends optimal purchases, and executes buys using MYCA's wallet.
    """

    def __init__(self):
        self._vendors: Dict[str, ResourceVendor] = {}
        self._purchase_history: List[Dict[str, Any]] = []
        self._seed_vendors()

    def _seed_vendors(self) -> None:
        """Populate the marketplace with known resource vendors."""
        seed = [
            ResourceVendor(
                vendor_id="vast-ai-a100",
                name="Vast.ai",
                resource_type="gpu",
                price_per_unit=1.10,
                unit="hour",
                rating=4.5,
                region="us-east",
                specs={"gpu": "A100-80GB", "vram": 80, "cuda_cores": 6912},
            ),
            ResourceVendor(
                vendor_id="runpod-a100",
                name="RunPod",
                resource_type="gpu",
                price_per_unit=1.64,
                unit="hour",
                rating=4.7,
                region="us-west",
                specs={"gpu": "A100-80GB", "vram": 80, "cuda_cores": 6912},
            ),
            ResourceVendor(
                vendor_id="lambda-h100",
                name="Lambda Cloud",
                resource_type="gpu",
                price_per_unit=2.49,
                unit="hour",
                rating=4.8,
                region="us-central",
                specs={"gpu": "H100-80GB", "vram": 80, "cuda_cores": 16896},
            ),
            ResourceVendor(
                vendor_id="backblaze-b2",
                name="Backblaze B2",
                resource_type="storage",
                price_per_unit=0.005,
                unit="GB/month",
                rating=4.6,
                region="us-west",
                specs={"type": "object_storage", "redundancy": "3x"},
            ),
            ResourceVendor(
                vendor_id="hetzner-cx41",
                name="Hetzner",
                resource_type="compute",
                price_per_unit=0.0158,
                unit="hour",
                rating=4.4,
                region="eu-central",
                specs={"vcpus": 4, "ram_gb": 16, "disk_gb": 160},
            ),
        ]
        for v in seed:
            self._vendors[v.vendor_id] = v

    def add_vendor(self, vendor: ResourceVendor) -> None:
        self._vendors[vendor.vendor_id] = vendor

    def list_vendors(
        self, resource_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return vendor listings, optionally filtered by resource type."""
        vendors = self._vendors.values()
        if resource_type:
            vendors = [v for v in vendors if v.resource_type == resource_type]
        return [
            {
                "vendor_id": v.vendor_id,
                "name": v.name,
                "resource_type": v.resource_type,
                "price_per_unit": v.price_per_unit,
                "unit": v.unit,
                "rating": v.rating,
                "region": v.region,
                "specs": v.specs,
                "available": v.availability,
            }
            for v in sorted(vendors, key=lambda x: x.price_per_unit)
        ]

    def compare_prices(self, resource_type: str) -> List[Dict[str, Any]]:
        """Compare prices across vendors for a given resource type."""
        listings = self.list_vendors(resource_type)
        if not listings:
            return []
        cheapest = listings[0]["price_per_unit"]
        for entry in listings:
            entry["price_delta_pct"] = round(
                ((entry["price_per_unit"] - cheapest) / cheapest) * 100
                if cheapest > 0
                else 0.0,
                2,
            )
        return listings

    def recommend_purchase(
        self,
        resource_type: str,
        budget: float,
        min_rating: float = 4.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Recommend the best vendor within budget constraints.

        Picks the highest-rated vendor whose per-unit cost fits the budget.
        """
        candidates = [
            v
            for v in self._vendors.values()
            if v.resource_type == resource_type
            and v.availability
            and v.price_per_unit <= budget
            and v.rating >= min_rating
        ]
        if not candidates:
            return None
        best = max(candidates, key=lambda v: (v.rating, -v.price_per_unit))
        hours_available = int(budget / best.price_per_unit) if best.price_per_unit > 0 else 0
        return {
            "vendor_id": best.vendor_id,
            "name": best.name,
            "price_per_unit": best.price_per_unit,
            "unit": best.unit,
            "units_affordable": hours_available,
            "total_cost": round(best.price_per_unit * hours_available, 4),
            "rating": best.rating,
            "specs": best.specs,
        }

    def execute_purchase(
        self,
        vendor_id: str,
        units: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """
        Execute a resource purchase order.

        Returns a purchase receipt that can be recorded in the agent ledger.
        """
        vendor = self._vendors.get(vendor_id)
        if vendor is None:
            return {"status": "error", "message": f"Unknown vendor: {vendor_id}"}
        if not vendor.availability:
            return {"status": "error", "message": f"Vendor {vendor_id} currently unavailable"}

        total_cost = round(vendor.price_per_unit * units, 4)
        receipt = {
            "purchase_id": str(uuid4()),
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "resource_type": vendor.resource_type,
            "units": units,
            "unit_label": vendor.unit,
            "price_per_unit": vendor.price_per_unit,
            "total_cost": total_cost,
            "paid_from": wallet_address,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "specs": vendor.specs,
        }
        self._purchase_history.append(receipt)
        return receipt

    def get_purchase_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._purchase_history[-limit:]


# ---------------------------------------------------------------------------
# Autonomous Economy Agent
# ---------------------------------------------------------------------------

class AutonomousEconomyAgent(BaseAgentV2):
    """
    MYCA's financial autonomy agent.

    Manages cryptocurrency wallets, charges for services rendered by the MAS
    platform, tracks revenue and expenses, and autonomously procures GPU,
    storage, and compute resources to sustain and grow MYCA's capabilities.
    """

    # -- BaseAgentV2 abstract properties ------------------------------------

    @property
    def agent_type(self) -> str:
        return "autonomous_economy"

    @property
    def category(self) -> str:
        return AgentCategory.FINANCIAL.value

    @property
    def display_name(self) -> str:
        return "Autonomous Economy Agent"

    @property
    def description(self) -> str:
        return (
            "Manages MYCA's wallets, service pricing, revenue collection, "
            "and autonomous resource procurement"
        )

    def get_capabilities(self) -> List[str]:
        return [
            "wallet_management",
            "service_pricing",
            "charge_for_service",
            "receive_payment",
            "purchase_resource",
            "financial_summary",
            "evaluate_resource_needs",
            "auto_purchase_resources",
            "revenue_metrics",
            "agent_incentives",
            "marketplace_query",
        ]

    # -- Initialisation -----------------------------------------------------

    def __init__(self, agent_id: str = "autonomous-economy-agent", config=None):
        super().__init__(agent_id=agent_id, config=config)

        # Wallets keyed by WalletType
        self._wallets: Dict[WalletType, CryptoWallet] = {}
        self._primary_wallet_type: WalletType = WalletType.SOLANA

        # Subsystems
        self.pricing = ServicePricing()
        self.marketplace = ResourceMarketplace()

        # Operational thresholds (SOL equivalents)
        self._auto_purchase_enabled: bool = True
        self._min_reserve_balance: float = 5.0
        self._gpu_budget_pct: float = 0.40
        self._storage_budget_pct: float = 0.20
        self._compute_budget_pct: float = 0.20

        # Ledger caches for fast metric queries
        self._daily_revenue: Dict[str, float] = {}
        self._daily_expenses: Dict[str, float] = {}

    # -- Lifecycle hooks ----------------------------------------------------

    async def on_start(self):
        """Register task handlers and initialise default wallets."""
        self.register_handler("charge_for_service", self._handle_charge_for_service)
        self.register_handler("receive_payment", self._handle_receive_payment)
        self.register_handler("purchase_resource", self._handle_purchase_resource)
        self.register_handler("financial_summary", self._handle_financial_summary)
        self.register_handler("evaluate_resource_needs", self._handle_evaluate_resource_needs)
        self.register_handler("auto_purchase_resources", self._handle_auto_purchase_resources)
        self.register_handler("revenue_metrics", self._handle_revenue_metrics)
        self.register_handler("create_agent_incentive", self._handle_create_agent_incentive)
        self.register_handler("marketplace_query", self._handle_marketplace_query)
        self.register_handler("set_client_tier", self._handle_set_client_tier)
        self.register_handler("get_pricing_tiers", self._handle_get_pricing_tiers)

        # Bootstrap default wallets
        self._init_default_wallets()
        logger.info("AutonomousEconomyAgent started with %d wallets", len(self._wallets))

    def _init_default_wallets(self) -> None:
        """Create placeholder wallets for each supported chain."""
        for wt in WalletType:
            if wt not in self._wallets:
                self._wallets[wt] = CryptoWallet(
                    wallet_type=wt,
                    address=f"myca-{wt.value}-{str(uuid4())[:8]}",
                    public_key=f"pk-{wt.value}-{str(uuid4())[:12]}",
                )

    # -- Core financial operations ------------------------------------------

    async def charge_for_service(
        self,
        client_id: str,
        service_type: str,
        amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Charge a client for a service rendered by MYCA.

        If *amount* is None the price is calculated from the client's tier.
        """
        tier = self.pricing.get_tier_for_client(client_id)
        calculated_price = self.pricing.calculate_price(service_type, tier)
        final_amount = amount if amount is not None else calculated_price

        wallet = self._wallets[self._primary_wallet_type]
        tx = Transaction(
            transaction_type=TransactionType.INCOME,
            amount=final_amount,
            currency=self._primary_wallet_type.value.upper(),
            from_address=client_id,
            to_address=wallet.address,
            description=f"Service charge: {service_type} (tier={tier})",
            confirmed=True,
        )
        wallet.transactions.append(tx)
        wallet.balance += final_amount
        self._record_daily_revenue(final_amount)

        logger.info(
            "Charged client=%s amount=%.6f for service=%s tier=%s",
            client_id, final_amount, service_type, tier,
        )
        return {
            "status": "success",
            "transaction_id": tx.transaction_id,
            "amount": final_amount,
            "currency": tx.currency,
            "tier": tier,
            "service_type": service_type,
            "timestamp": tx.timestamp,
        }

    async def receive_payment(
        self,
        wallet_type: WalletType,
        amount: float,
        from_address: str,
    ) -> Dict[str, Any]:
        """Record an incoming payment on a specific wallet."""
        wallet = self._wallets.get(wallet_type)
        if wallet is None:
            return {"status": "error", "message": f"No wallet for {wallet_type.value}"}

        tx = Transaction(
            transaction_type=TransactionType.INCOME,
            amount=amount,
            currency=wallet_type.value.upper(),
            from_address=from_address,
            to_address=wallet.address,
            description=f"Payment received from {from_address}",
            confirmed=True,
        )
        wallet.transactions.append(tx)
        wallet.balance += amount
        self._record_daily_revenue(amount)

        logger.info(
            "Payment received: %.6f %s from %s", amount, wallet_type.value, from_address,
        )
        return {
            "status": "success",
            "transaction_id": tx.transaction_id,
            "wallet": wallet_type.value,
            "amount": amount,
            "new_balance": wallet.balance,
            "timestamp": tx.timestamp,
        }

    async def purchase_resource(
        self,
        resource_type: str,
        amount: float,
        vendor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Purchase a resource from the marketplace.

        If *vendor* is None the marketplace recommends one automatically.
        """
        wallet = self._wallets[self._primary_wallet_type]
        if wallet.balance < amount:
            return {
                "status": "error",
                "message": "Insufficient balance",
                "required": amount,
                "available": wallet.balance,
            }

        if vendor is None:
            rec = self.marketplace.recommend_purchase(resource_type, amount)
            if rec is None:
                return {"status": "error", "message": f"No vendor available for {resource_type} within budget"}
            vendor = rec["vendor_id"]

        units = max(1, int(amount / (self.marketplace._vendors.get(vendor, ResourceVendor()).price_per_unit or 1)))
        receipt = self.marketplace.execute_purchase(vendor, units, wallet.address)

        if receipt.get("status") == "error":
            return receipt

        total_cost = receipt["total_cost"]
        tx = Transaction(
            transaction_type=TransactionType.EXPENSE,
            amount=total_cost,
            currency=self._primary_wallet_type.value.upper(),
            from_address=wallet.address,
            to_address=vendor,
            description=f"Resource purchase: {resource_type} from {receipt.get('vendor_name', vendor)}",
            confirmed=True,
            metadata={"purchase_id": receipt["purchase_id"]},
        )
        wallet.transactions.append(tx)
        wallet.balance -= total_cost
        self._record_daily_expense(total_cost)

        logger.info(
            "Purchased %d units of %s from %s for %.4f",
            units, resource_type, vendor, total_cost,
        )
        return {
            "status": "success",
            "purchase": receipt,
            "remaining_balance": wallet.balance,
        }

    # -- Analytics and planning ---------------------------------------------

    async def get_financial_summary(self) -> Dict[str, Any]:
        """Return a consolidated financial summary across all wallets."""
        total_balance = 0.0
        total_income = 0.0
        total_expenses = 0.0
        wallet_summaries: List[Dict[str, Any]] = []

        for wt, w in self._wallets.items():
            income = w.total_income
            expenses = w.total_expenses
            total_balance += w.balance
            total_income += income
            total_expenses += expenses
            wallet_summaries.append({
                "wallet_type": wt.value,
                "address": w.address,
                "balance": w.balance,
                "income": income,
                "expenses": expenses,
                "transaction_count": len(w.transactions),
            })

        net = total_income - total_expenses
        growth_pct = round((net / total_expenses * 100) if total_expenses > 0 else 0.0, 2)

        return {
            "total_balance": round(total_balance, 6),
            "total_income": round(total_income, 6),
            "total_expenses": round(total_expenses, 6),
            "net_profit": round(net, 6),
            "growth_pct": growth_pct,
            "wallets": wallet_summaries,
            "auto_purchase_enabled": self._auto_purchase_enabled,
            "reserve_balance": self._min_reserve_balance,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def evaluate_resource_needs(self) -> List[Dict[str, Any]]:
        """
        Evaluate current infrastructure needs and return a prioritised list
        of resources MYCA should acquire.
        """
        needs: List[Dict[str, Any]] = []
        summary = await self.get_financial_summary()
        disposable = max(0.0, summary["total_balance"] - self._min_reserve_balance)

        # GPU need assessment
        gpu_budget = disposable * self._gpu_budget_pct
        if gpu_budget > 0:
            rec = self.marketplace.recommend_purchase("gpu", gpu_budget)
            needs.append({
                "resource_type": "gpu",
                "priority": "high",
                "budget": round(gpu_budget, 4),
                "recommendation": rec,
                "reason": "GPU capacity required for inference and simulation workloads",
            })

        # Storage need assessment
        storage_budget = disposable * self._storage_budget_pct
        if storage_budget > 0:
            rec = self.marketplace.recommend_purchase("storage", storage_budget)
            needs.append({
                "resource_type": "storage",
                "priority": "medium",
                "budget": round(storage_budget, 4),
                "recommendation": rec,
                "reason": "Additional storage for agent memory, datasets, and model weights",
            })

        # Compute need assessment
        compute_budget = disposable * self._compute_budget_pct
        if compute_budget > 0:
            rec = self.marketplace.recommend_purchase("compute", compute_budget)
            needs.append({
                "resource_type": "compute",
                "priority": "medium",
                "budget": round(compute_budget, 4),
                "recommendation": rec,
                "reason": "General compute capacity for agent workloads and ETL pipelines",
            })

        return needs

    async def auto_purchase_resources(self) -> Dict[str, Any]:
        """
        Automatically purchase resources when the budget allows.

        Respects the minimum reserve balance and per-category budget percentages.
        Returns a summary of all purchases made during this cycle.
        """
        if not self._auto_purchase_enabled:
            return {"status": "skipped", "reason": "Auto-purchase is disabled"}

        needs = await self.evaluate_resource_needs()
        purchases: List[Dict[str, Any]] = []
        errors: List[str] = []

        for need in needs:
            rec = need.get("recommendation")
            if rec is None:
                continue
            budget = need["budget"]
            if budget <= 0:
                continue

            result = await self.purchase_resource(
                resource_type=need["resource_type"],
                amount=budget,
                vendor=rec["vendor_id"],
            )
            if result.get("status") == "success":
                purchases.append(result)
            else:
                errors.append(result.get("message", "Unknown error"))

        return {
            "status": "completed",
            "purchases_made": len(purchases),
            "purchases": purchases,
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_revenue_metrics(self) -> Dict[str, Any]:
        """Return daily, weekly, and monthly revenue statistics."""
        today = datetime.utcnow().date()
        daily_total = self._daily_revenue.get(today.isoformat(), 0.0)

        week_start = today - timedelta(days=today.weekday())
        weekly_total = sum(
            v
            for k, v in self._daily_revenue.items()
            if k >= week_start.isoformat()
        )

        month_start = today.replace(day=1)
        monthly_total = sum(
            v
            for k, v in self._daily_revenue.items()
            if k >= month_start.isoformat()
        )

        daily_expense = self._daily_expenses.get(today.isoformat(), 0.0)
        weekly_expense = sum(
            v
            for k, v in self._daily_expenses.items()
            if k >= week_start.isoformat()
        )
        monthly_expense = sum(
            v
            for k, v in self._daily_expenses.items()
            if k >= month_start.isoformat()
        )

        return {
            "daily": {"revenue": daily_total, "expense": daily_expense, "net": daily_total - daily_expense},
            "weekly": {"revenue": weekly_total, "expense": weekly_expense, "net": weekly_total - weekly_expense},
            "monthly": {"revenue": monthly_total, "expense": monthly_expense, "net": monthly_total - monthly_expense},
            "total_days_tracked": len(self._daily_revenue),
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def create_agent_incentive(
        self,
        agent_id: str,
        incentive_type: str,
    ) -> Dict[str, Any]:
        """
        Create a financial incentive for another agent to utilise MYCA's
        services, driving adoption and revenue growth.
        """
        incentive_table = {
            "referral_bonus": {
                "amount": 0.01,
                "description": "Bonus for referring a new client to MYCA services",
                "conditions": "New client must complete at least 10 paid requests",
            },
            "volume_bonus": {
                "amount": 0.005,
                "description": "Bonus for exceeding 1000 requests in a billing cycle",
                "conditions": "Minimum 1000 requests processed in the current month",
            },
            "uptime_reward": {
                "amount": 0.002,
                "description": "Reward for maintaining 99.9% uptime over 30 days",
                "conditions": "Agent must have 99.9% uptime for the trailing 30 days",
            },
            "innovation_grant": {
                "amount": 0.05,
                "description": "Grant for agents that develop new revenue-generating capabilities",
                "conditions": "Capability must generate at least 0.1 SOL in 30 days",
            },
        }

        incentive_def = incentive_table.get(incentive_type)
        if incentive_def is None:
            return {
                "status": "error",
                "message": f"Unknown incentive type: {incentive_type}",
                "available_types": list(incentive_table.keys()),
            }

        incentive_id = str(uuid4())
        logger.info(
            "Created incentive %s for agent=%s type=%s", incentive_id, agent_id, incentive_type,
        )
        return {
            "status": "success",
            "incentive_id": incentive_id,
            "agent_id": agent_id,
            "incentive_type": incentive_type,
            "amount": incentive_def["amount"],
            "currency": self._primary_wallet_type.value.upper(),
            "description": incentive_def["description"],
            "conditions": incentive_def["conditions"],
            "created_at": datetime.utcnow().isoformat(),
        }

    # -- Internal helpers ---------------------------------------------------

    def _record_daily_revenue(self, amount: float) -> None:
        key = datetime.utcnow().date().isoformat()
        self._daily_revenue[key] = self._daily_revenue.get(key, 0.0) + amount

    def _record_daily_expense(self, amount: float) -> None:
        key = datetime.utcnow().date().isoformat()
        self._daily_expenses[key] = self._daily_expenses.get(key, 0.0) + amount

    # -- Task handler wrappers (translate AgentTask -> method calls) ---------

    async def _handle_charge_for_service(self, task: AgentTask) -> Dict[str, Any]:
        return await self.charge_for_service(
            client_id=task.payload.get("client_id", "unknown"),
            service_type=task.payload.get("service_type", "basic_query"),
            amount=task.payload.get("amount"),
        )

    async def _handle_receive_payment(self, task: AgentTask) -> Dict[str, Any]:
        wallet_type_str = task.payload.get("wallet_type", "solana")
        try:
            wt = WalletType(wallet_type_str)
        except ValueError:
            return {"status": "error", "message": f"Invalid wallet type: {wallet_type_str}"}
        return await self.receive_payment(
            wallet_type=wt,
            amount=task.payload.get("amount", 0.0),
            from_address=task.payload.get("from_address", ""),
        )

    async def _handle_purchase_resource(self, task: AgentTask) -> Dict[str, Any]:
        return await self.purchase_resource(
            resource_type=task.payload.get("resource_type", "gpu"),
            amount=task.payload.get("amount", 0.0),
            vendor=task.payload.get("vendor"),
        )

    async def _handle_financial_summary(self, task: AgentTask) -> Dict[str, Any]:
        return await self.get_financial_summary()

    async def _handle_evaluate_resource_needs(self, task: AgentTask) -> Dict[str, Any]:
        needs = await self.evaluate_resource_needs()
        return {"status": "success", "needs": needs}

    async def _handle_auto_purchase_resources(self, task: AgentTask) -> Dict[str, Any]:
        return await self.auto_purchase_resources()

    async def _handle_revenue_metrics(self, task: AgentTask) -> Dict[str, Any]:
        return await self.get_revenue_metrics()

    async def _handle_create_agent_incentive(self, task: AgentTask) -> Dict[str, Any]:
        return await self.create_agent_incentive(
            agent_id=task.payload.get("agent_id", ""),
            incentive_type=task.payload.get("incentive_type", ""),
        )

    async def _handle_marketplace_query(self, task: AgentTask) -> Dict[str, Any]:
        action = task.payload.get("action", "list")
        resource_type = task.payload.get("resource_type")

        if action == "compare":
            return {"status": "success", "vendors": self.marketplace.compare_prices(resource_type or "gpu")}
        elif action == "recommend":
            budget = task.payload.get("budget", 10.0)
            rec = self.marketplace.recommend_purchase(resource_type or "gpu", budget)
            return {"status": "success", "recommendation": rec}
        else:
            return {"status": "success", "vendors": self.marketplace.list_vendors(resource_type)}

    async def _handle_set_client_tier(self, task: AgentTask) -> Dict[str, Any]:
        client_id = task.payload.get("client_id", "")
        tier = task.payload.get("tier", "free")
        ok = self.pricing.set_client_tier(client_id, tier)
        if ok:
            return {"status": "success", "client_id": client_id, "tier": tier}
        return {"status": "error", "message": f"Invalid tier: {tier}"}

    async def _handle_get_pricing_tiers(self, task: AgentTask) -> Dict[str, Any]:
        return {"status": "success", "tiers": self.pricing.get_all_tiers()}
