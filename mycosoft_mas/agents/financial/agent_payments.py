"""
Agent Payments — x402 Payment Protocol Integration for MAS Agents
=================================================================

Integrates two x402-based payment approaches for agent-to-agent monetization:

1. **Ampersend SDK (A2A/Google ADK)** — Per-request micro-payments via
   ``make_x402_before_agent_callback`` for Google ADK agents converted to A2A apps.
2. **x402 FastAPI Middleware** — Route-level payment gating via ``require_payment``
   middleware for CrewAI-powered research endpoints.

Pricing is organized into "Tiger Tiers" — named after tiger subspecies — each
with distinct per-request costs, rate limits, and capability sets.

Pay-to address: 0xc432564C095FdAC424e4c07C4F9B5191A24441F9
Ampersend dashboard: https://app.ampersend.ai/agents/0xc432564C095FdAC424e4c07C4F9B5191A24441F9

Author: MYCA / Morgan Rockwell
Created: April 1, 2026
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

PAY_TO_ADDRESS = "0xc432564C095FdAC424e4c07C4F9B5191A24441F9"
PAYMENT_NETWORK = "base"
AMPERSEND_DASHBOARD = (
    f"https://app.ampersend.ai/agents/{PAY_TO_ADDRESS}"
)


# ============================================================================
# Tiger Tier Pricing — each subspecies is a pricing tier
# ============================================================================


class TigerTier(str, Enum):
    """Pricing tiers named after tiger subspecies."""

    # Living subspecies
    BENGAL = "bengal"              # Panthera tigris tigris — most common
    SIBERIAN = "siberian"          # Panthera tigris altaica — largest
    SUMATRAN = "sumatran"          # Panthera tigris sumatrae — smallest living
    INDOCHINESE = "indochinese"    # Panthera tigris corbetti
    MALAYAN = "malayan"            # Panthera tigris jacksoni
    SOUTH_CHINA = "south_china"    # Panthera tigris amoyensis — critically endangered

    # Extinct subspecies (premium/legacy tiers)
    CASPIAN = "caspian"            # Panthera tigris virgata — extinct ~1970s
    JAVAN = "javan"                # Panthera tigris sondaica — extinct ~1980s
    BALI = "bali"                  # Panthera tigris balica — extinct ~1950s


@dataclass
class TigerTierConfig:
    """Configuration for a single tiger pricing tier."""

    tier: TigerTier
    display_name: str
    subspecies: str
    price_per_request: str        # e.g. "$0.001"
    price_usd: float              # numeric for calculations
    daily_rate_limit: int
    capabilities: List[str]
    description: str
    conservation_status: str      # IUCN status of the real subspecies


# All nine tiger variety tiers
TIGER_TIERS: Dict[TigerTier, TigerTierConfig] = {
    TigerTier.BENGAL: TigerTierConfig(
        tier=TigerTier.BENGAL,
        display_name="Bengal Tiger",
        subspecies="Panthera tigris tigris",
        price_per_request="$0.001",
        price_usd=0.001,
        daily_rate_limit=10_000,
        capabilities=["search", "summarize"],
        description="Standard tier — high-volume, low-cost queries",
        conservation_status="Endangered",
    ),
    TigerTier.SIBERIAN: TigerTierConfig(
        tier=TigerTier.SIBERIAN,
        display_name="Siberian Tiger",
        subspecies="Panthera tigris altaica",
        price_per_request="$0.005",
        price_usd=0.005,
        daily_rate_limit=5_000,
        capabilities=["search", "summarize", "research", "analysis"],
        description="Professional tier — deeper analysis and research",
        conservation_status="Endangered",
    ),
    TigerTier.SUMATRAN: TigerTierConfig(
        tier=TigerTier.SUMATRAN,
        display_name="Sumatran Tiger",
        subspecies="Panthera tigris sumatrae",
        price_per_request="$0.01",
        price_usd=0.01,
        daily_rate_limit=2_000,
        capabilities=["search", "summarize", "research", "analysis", "crew_research"],
        description="Advanced tier — full CrewAI research capabilities",
        conservation_status="Critically Endangered",
    ),
    TigerTier.INDOCHINESE: TigerTierConfig(
        tier=TigerTier.INDOCHINESE,
        display_name="Indochinese Tiger",
        subspecies="Panthera tigris corbetti",
        price_per_request="$0.02",
        price_usd=0.02,
        daily_rate_limit=1_000,
        capabilities=["search", "summarize", "research", "analysis", "crew_research", "multi_agent"],
        description="Multi-agent tier — orchestrated agent crews",
        conservation_status="Endangered",
    ),
    TigerTier.MALAYAN: TigerTierConfig(
        tier=TigerTier.MALAYAN,
        display_name="Malayan Tiger",
        subspecies="Panthera tigris jacksoni",
        price_per_request="$0.05",
        price_usd=0.05,
        daily_rate_limit=500,
        capabilities=[
            "search", "summarize", "research", "analysis",
            "crew_research", "multi_agent", "priority_queue",
        ],
        description="Priority tier — guaranteed fast response with queue priority",
        conservation_status="Critically Endangered",
    ),
    TigerTier.SOUTH_CHINA: TigerTierConfig(
        tier=TigerTier.SOUTH_CHINA,
        display_name="South China Tiger",
        subspecies="Panthera tigris amoyensis",
        price_per_request="$0.10",
        price_usd=0.10,
        daily_rate_limit=200,
        capabilities=[
            "search", "summarize", "research", "analysis",
            "crew_research", "multi_agent", "priority_queue",
            "dedicated_compute",
        ],
        description="Dedicated tier — isolated compute with SLA guarantees",
        conservation_status="Critically Endangered (Functionally Extinct in Wild)",
    ),
    # Extinct subspecies = premium/legacy tiers
    TigerTier.CASPIAN: TigerTierConfig(
        tier=TigerTier.CASPIAN,
        display_name="Caspian Tiger",
        subspecies="Panthera tigris virgata",
        price_per_request="$0.25",
        price_usd=0.25,
        daily_rate_limit=100,
        capabilities=[
            "search", "summarize", "research", "analysis",
            "crew_research", "multi_agent", "priority_queue",
            "dedicated_compute", "custom_models",
        ],
        description="Legacy Premium — custom model selection, full orchestration",
        conservation_status="Extinct (~1970s)",
    ),
    TigerTier.JAVAN: TigerTierConfig(
        tier=TigerTier.JAVAN,
        display_name="Javan Tiger",
        subspecies="Panthera tigris sondaica",
        price_per_request="$0.50",
        price_usd=0.50,
        daily_rate_limit=50,
        capabilities=[
            "search", "summarize", "research", "analysis",
            "crew_research", "multi_agent", "priority_queue",
            "dedicated_compute", "custom_models", "white_glove",
        ],
        description="Enterprise — white-glove service, dedicated agent pool",
        conservation_status="Extinct (~1980s)",
    ),
    TigerTier.BALI: TigerTierConfig(
        tier=TigerTier.BALI,
        display_name="Bali Tiger",
        subspecies="Panthera tigris balica",
        price_per_request="$1.00",
        price_usd=1.00,
        daily_rate_limit=25,
        capabilities=[
            "search", "summarize", "research", "analysis",
            "crew_research", "multi_agent", "priority_queue",
            "dedicated_compute", "custom_models", "white_glove",
            "unlimited_context",
        ],
        description="Apex — unlimited context, all capabilities, highest priority",
        conservation_status="Extinct (~1950s)",
    ),
}

DEFAULT_TIER = TigerTier.BENGAL


# ============================================================================
# Payment Transaction Record
# ============================================================================


@dataclass
class PaymentTransaction:
    """Record of an x402 payment transaction."""

    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    client_address: str = ""
    tier: str = DEFAULT_TIER.value
    amount_usd: float = 0.0
    network: str = PAYMENT_NETWORK
    pay_to: str = PAY_TO_ADDRESS
    service_type: str = ""
    status: str = "pending"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Ampersend A2A Agent Factory
# ============================================================================


def create_ampersend_a2a_agent(
    tier: TigerTier = DEFAULT_TIER,
    model: str = "gemini-2.5-flash-lite",
    extra_tools: Optional[List[Any]] = None,
) -> Any:
    """
    Create a Google ADK agent with Ampersend x402 payment callback.

    This wraps the agent with ``make_x402_before_agent_callback`` so every
    incoming A2A request must include a valid x402 payment header.

    Args:
        tier: Tiger pricing tier to apply.
        model: Google ADK model to use.
        extra_tools: Additional tools beyond google_search.

    Returns:
        A Google ADK ``Agent`` instance with payment callback attached.
    """
    from ampersend_sdk.a2a.server import make_x402_before_agent_callback
    from google.adk import Agent
    from google.adk.tools import google_search

    tier_config = TIGER_TIERS[tier]
    tools = [google_search]
    if extra_tools:
        tools.extend(extra_tools)

    agent = Agent(
        name=f"mycosoft_{tier.value}_service",
        before_agent_callback=make_x402_before_agent_callback(
            price=tier_config.price_per_request,
            network=PAYMENT_NETWORK,
            pay_to_address=PAY_TO_ADDRESS,
        ),
        model=model,
        description=f"Mycosoft {tier_config.display_name} tier agent — {tier_config.description}",
        instruction=(
            f"You are a Mycosoft MAS agent operating at the {tier_config.display_name} tier. "
            f"Capabilities: {', '.join(tier_config.capabilities)}. "
            "Provide thorough, accurate responses. "
            "You are part of the Mycosoft Multi-Agent System with 158+ agents."
        ),
        tools=tools,
    )
    logger.info(
        "Created Ampersend A2A agent: tier=%s price=%s",
        tier.value,
        tier_config.price_per_request,
    )
    return agent


def create_ampersend_a2a_app(
    tier: TigerTier = DEFAULT_TIER,
    port: int = 8001,
    **kwargs: Any,
) -> Any:
    """
    Create a full A2A app from a Google ADK agent with x402 payment.

    Args:
        tier: Tiger pricing tier.
        port: Port for the A2A server.
        **kwargs: Passed to ``create_ampersend_a2a_agent``.

    Returns:
        An A2A ASGI app ready for ``uvicorn``.
    """
    from ampersend_sdk.a2a.server.to_a2a import to_a2a

    agent = create_ampersend_a2a_agent(tier=tier, **kwargs)
    a2a_app = to_a2a(agent, port=port)
    logger.info("Created A2A app on port %d for tier %s", port, tier.value)
    return a2a_app


# ============================================================================
# x402 FastAPI Middleware Factory (CrewAI)
# ============================================================================


def create_x402_payment_middleware(
    tier: TigerTier = DEFAULT_TIER,
    description: Optional[str] = None,
) -> Any:
    """
    Create x402 ``require_payment`` middleware for FastAPI routes.

    This is used to gate CrewAI research endpoints behind x402 payments.

    Args:
        tier: Tiger pricing tier.
        description: Human-readable description for the payment prompt.

    Returns:
        A FastAPI middleware callable.
    """
    from x402.fastapi import require_payment

    tier_config = TIGER_TIERS[tier]
    return require_payment(
        price=tier_config.price_per_request,
        pay_to_address=PAY_TO_ADDRESS,
        network=PAYMENT_NETWORK,
        description=description or f"Mycosoft {tier_config.display_name} — {tier_config.description}",
    )


def create_crewai_researcher(tier: TigerTier = DEFAULT_TIER) -> Any:
    """
    Create a CrewAI research agent configured for the given tier.

    Args:
        tier: Tiger pricing tier (determines agent backstory/capabilities).

    Returns:
        A CrewAI ``Agent`` instance.
    """
    from crewai import Agent as CrewAgent

    tier_config = TIGER_TIERS[tier]
    return CrewAgent(
        role="Research Analyst",
        goal=(
            f"Provide thorough, accurate research at the {tier_config.display_name} tier. "
            f"Available capabilities: {', '.join(tier_config.capabilities)}."
        ),
        backstory=(
            f"You are a Mycosoft MAS research analyst operating at the "
            f"{tier_config.display_name} ({tier_config.subspecies}) pricing tier. "
            f"You are part of a system with 158+ AI agents across 14 categories. "
            f"Conservation note: the real {tier_config.display_name} is "
            f"{tier_config.conservation_status}."
        ),
    )


async def run_crew_research(topic: str, tier: TigerTier = DEFAULT_TIER) -> str:
    """
    Execute a CrewAI research task for the given topic.

    Args:
        topic: Research topic string.
        tier: Tiger pricing tier.

    Returns:
        Research result as a string.
    """
    from crewai import Crew, Task

    researcher = create_crewai_researcher(tier=tier)
    task = Task(
        description=f"Research the following topic and provide a detailed summary: {topic}",
        expected_output="A concise, well-structured research summary.",
        agent=researcher,
    )
    crew = Crew(agents=[researcher], tasks=[task])
    result = crew.kickoff()
    return str(result)


# ============================================================================
# AgentPayments — BaseAgent integration
# ============================================================================


class AgentPaymentsAgent(BaseAgent):
    """
    Agent that manages x402 payment processing for MAS agent services.

    Integrates both Ampersend SDK (A2A/Google ADK) and x402 FastAPI middleware
    (CrewAI) payment flows. Tracks transactions, manages tier assignments,
    and provides payment analytics.

    Tiger Tiers (9 varieties):
        Bengal ($0.001) → Siberian ($0.005) → Sumatran ($0.01) →
        Indochinese ($0.02) → Malayan ($0.05) → South China ($0.10) →
        Caspian ($0.25) → Javan ($0.50) → Bali ($1.00)
    """

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.capabilities = [
            "x402_payments",
            "ampersend_a2a",
            "crewai_research",
            "tiger_tier_pricing",
            "payment_analytics",
        ]
        self.pay_to_address = config.get("pay_to_address", PAY_TO_ADDRESS)
        self.network = config.get("network", PAYMENT_NETWORK)
        self.default_tier = TigerTier(config.get("default_tier", DEFAULT_TIER.value))
        self.transactions: List[PaymentTransaction] = []
        self.client_tiers: Dict[str, TigerTier] = {}

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route payment tasks to the appropriate handler."""
        task_type = task.get("type", "")
        handlers = {
            "charge": self._handle_charge,
            "assign_tier": self._handle_assign_tier,
            "get_tiers": self._handle_get_tiers,
            "get_tier_info": self._handle_get_tier_info,
            "get_transactions": self._handle_get_transactions,
            "get_revenue": self._handle_get_revenue,
            "create_a2a_agent": self._handle_create_a2a,
            "crew_research": self._handle_crew_research,
        }
        handler = handlers.get(task_type)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown task type: {task_type}",
                "supported_types": list(handlers.keys()),
            }
        return await handler(task)

    async def _handle_charge(self, task: Dict[str, Any]) -> Dict[str, Any]:
        client_id = task.get("client_id", "")
        service_type = task.get("service_type", "query")
        tier = self._resolve_tier(client_id, task.get("tier"))

        tier_config = TIGER_TIERS[tier]
        txn = PaymentTransaction(
            client_address=client_id,
            tier=tier.value,
            amount_usd=tier_config.price_usd,
            service_type=service_type,
            status="completed",
            metadata=task.get("metadata", {}),
        )
        self.transactions.append(txn)
        logger.info("Charge: %s tier=%s amount=$%.4f", client_id, tier.value, tier_config.price_usd)
        return {
            "status": "success",
            "transaction_id": txn.transaction_id,
            "amount": tier_config.price_per_request,
            "tier": tier.value,
            "display_name": tier_config.display_name,
        }

    async def _handle_assign_tier(self, task: Dict[str, Any]) -> Dict[str, Any]:
        client_id = task.get("client_id", "")
        tier_name = task.get("tier", DEFAULT_TIER.value)
        try:
            tier = TigerTier(tier_name)
        except ValueError:
            return {"status": "error", "error": f"Unknown tier: {tier_name}"}
        self.client_tiers[client_id] = tier
        tier_config = TIGER_TIERS[tier]
        return {
            "status": "success",
            "client_id": client_id,
            "tier": tier.value,
            "display_name": tier_config.display_name,
            "price_per_request": tier_config.price_per_request,
        }

    async def _handle_get_tiers(self, task: Dict[str, Any]) -> Dict[str, Any]:
        tiers = []
        for tier_enum, cfg in TIGER_TIERS.items():
            tiers.append({
                "tier": cfg.tier.value,
                "display_name": cfg.display_name,
                "subspecies": cfg.subspecies,
                "price_per_request": cfg.price_per_request,
                "price_usd": cfg.price_usd,
                "daily_rate_limit": cfg.daily_rate_limit,
                "capabilities": cfg.capabilities,
                "description": cfg.description,
                "conservation_status": cfg.conservation_status,
            })
        return {"status": "success", "tiers": tiers, "count": len(tiers)}

    async def _handle_get_tier_info(self, task: Dict[str, Any]) -> Dict[str, Any]:
        tier_name = task.get("tier", DEFAULT_TIER.value)
        try:
            tier = TigerTier(tier_name)
        except ValueError:
            return {"status": "error", "error": f"Unknown tier: {tier_name}"}
        cfg = TIGER_TIERS[tier]
        return {
            "status": "success",
            "tier": cfg.tier.value,
            "display_name": cfg.display_name,
            "subspecies": cfg.subspecies,
            "price_per_request": cfg.price_per_request,
            "price_usd": cfg.price_usd,
            "daily_rate_limit": cfg.daily_rate_limit,
            "capabilities": cfg.capabilities,
            "description": cfg.description,
            "conservation_status": cfg.conservation_status,
        }

    async def _handle_get_transactions(self, task: Dict[str, Any]) -> Dict[str, Any]:
        client_id = task.get("client_id")
        limit = task.get("limit", 50)
        txns = self.transactions
        if client_id:
            txns = [t for t in txns if t.client_address == client_id]
        txns = txns[-limit:]
        return {
            "status": "success",
            "transactions": [
                {
                    "transaction_id": t.transaction_id,
                    "client_address": t.client_address,
                    "tier": t.tier,
                    "amount_usd": t.amount_usd,
                    "service_type": t.service_type,
                    "status": t.status,
                    "timestamp": t.timestamp,
                }
                for t in txns
            ],
            "count": len(txns),
        }

    async def _handle_get_revenue(self, task: Dict[str, Any]) -> Dict[str, Any]:
        completed = [t for t in self.transactions if t.status == "completed"]
        total = sum(t.amount_usd for t in completed)
        by_tier: Dict[str, float] = {}
        for t in completed:
            by_tier[t.tier] = by_tier.get(t.tier, 0.0) + t.amount_usd
        return {
            "status": "success",
            "total_revenue_usd": round(total, 6),
            "transaction_count": len(completed),
            "revenue_by_tier": {k: round(v, 6) for k, v in by_tier.items()},
            "pay_to_address": self.pay_to_address,
            "network": self.network,
            "dashboard": AMPERSEND_DASHBOARD,
        }

    async def _handle_create_a2a(self, task: Dict[str, Any]) -> Dict[str, Any]:
        tier_name = task.get("tier", DEFAULT_TIER.value)
        try:
            tier = TigerTier(tier_name)
        except ValueError:
            return {"status": "error", "error": f"Unknown tier: {tier_name}"}
        tier_config = TIGER_TIERS[tier]
        return {
            "status": "success",
            "message": (
                f"A2A agent ready for tier {tier_config.display_name}. "
                f"Call create_ampersend_a2a_app(tier=TigerTier.{tier.name}) to start."
            ),
            "tier": tier.value,
            "price": tier_config.price_per_request,
            "dashboard": AMPERSEND_DASHBOARD,
        }

    async def _handle_crew_research(self, task: Dict[str, Any]) -> Dict[str, Any]:
        topic = task.get("topic", "")
        if not topic:
            return {"status": "error", "error": "Missing 'topic' field"}
        tier_name = task.get("tier", TigerTier.SUMATRAN.value)
        try:
            tier = TigerTier(tier_name)
        except ValueError:
            return {"status": "error", "error": f"Unknown tier: {tier_name}"}
        tier_config = TIGER_TIERS[tier]
        if "crew_research" not in tier_config.capabilities:
            return {
                "status": "error",
                "error": f"Tier {tier.value} does not include crew_research capability. "
                         f"Minimum tier: sumatran ($0.01/request)",
            }
        # Record the charge
        txn = PaymentTransaction(
            client_address=task.get("client_id", "anonymous"),
            tier=tier.value,
            amount_usd=tier_config.price_usd,
            service_type="crew_research",
            status="completed",
            metadata={"topic": topic},
        )
        self.transactions.append(txn)

        result = await run_crew_research(topic=topic, tier=tier)
        return {
            "status": "success",
            "result": result,
            "transaction_id": txn.transaction_id,
            "tier": tier.value,
            "charged": tier_config.price_per_request,
        }

    def _resolve_tier(
        self, client_id: str, explicit_tier: Optional[str] = None
    ) -> TigerTier:
        if explicit_tier:
            try:
                return TigerTier(explicit_tier)
            except ValueError:
                pass
        return self.client_tiers.get(client_id, self.default_tier)

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "agent_id": self.agent_id,
            "name": self.name,
            "pay_to_address": self.pay_to_address,
            "network": self.network,
            "default_tier": self.default_tier.value,
            "total_transactions": len(self.transactions),
            "active_tiers": len(TIGER_TIERS),
            "dashboard": AMPERSEND_DASHBOARD,
        }
