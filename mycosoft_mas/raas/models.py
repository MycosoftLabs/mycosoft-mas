"""Shared Pydantic models for the RaaS Agent Service Platform.

Created: March 11, 2026
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent registration & account
# ---------------------------------------------------------------------------


class AgentRegistration(BaseModel):
    """Request body for registering a new external agent."""

    agent_name: str = Field(..., min_length=1, max_length=256)
    agent_url: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    payment_method: str = Field(default="stripe", pattern="^(stripe|crypto)$")


class AgentAccount(BaseModel):
    """Internal representation of a registered agent."""

    agent_id: str
    agent_name: str
    agent_url: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    tier: str = "agent"
    status: str = "pending_payment"
    credit_balance: int = 0
    payment_method: str = "stripe"
    stripe_customer_id: Optional[str] = None
    crypto_wallet_address: Optional[str] = None
    registered_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None


class AgentRegistrationResponse(BaseModel):
    """Returned after successful registration."""

    agent_id: str
    api_key: str
    status: str
    signup_payment_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Credits & packages
# ---------------------------------------------------------------------------


class CreditPackage(BaseModel):
    """A purchasable credit package."""

    package_id: str
    name: str
    credits: int
    price_usd: float
    bonus_credits: int = 0


class CreditBalance(BaseModel):
    """Current credit state for an agent."""

    agent_id: str
    balance: int
    total_purchased: int
    total_used: int


class CreditTransaction(BaseModel):
    """A single credit ledger entry."""

    id: str
    agent_id: str
    amount: int
    type: str  # purchase, usage, bonus, refund
    description: Optional[str] = None
    service_id: Optional[str] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Service catalog
# ---------------------------------------------------------------------------


class ServiceDefinition(BaseModel):
    """A single service offered via RaaS."""

    service_id: str
    name: str
    description: str
    category: str
    credit_cost: int
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    rate_limit_per_minute: int = 60


class ServiceCategory(BaseModel):
    """Grouping of services."""

    category_id: str
    name: str
    description: str
    services: List[ServiceDefinition] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Invocation
# ---------------------------------------------------------------------------


class InvokeResponse(BaseModel):
    """Standard response wrapper for metered service invocations."""

    request_id: str
    service_id: str
    result: Any
    credits_used: int
    credits_remaining: int
    latency_ms: float


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


class StripeCheckoutRequest(BaseModel):
    """Create a Stripe checkout for signup or credit purchase."""

    agent_id: str
    package_id: str  # "signup" or a credit package id


class StripeCheckoutResponse(BaseModel):
    """Stripe payment intent details."""

    payment_intent_id: str
    client_secret: str
    amount: int  # cents
    currency: str = "usd"


class CryptoInvoiceRequest(BaseModel):
    """Create a crypto payment invoice."""

    agent_id: str
    package_id: str  # "signup" or a credit package id
    currency: str = Field(..., pattern="^(USDC|SOL|ETH|BTC|USDT|AVE)$")


class CryptoInvoiceResponse(BaseModel):
    """Crypto invoice details for the agent to pay."""

    invoice_id: str
    wallet_address: str
    amount: float
    currency: str
    reference: str
    expires_at: datetime


class CryptoVerifyRequest(BaseModel):
    """Verify an on-chain payment."""

    invoice_id: str
    tx_signature: str


class PaymentHistoryItem(BaseModel):
    """A payment record."""

    invoice_id: str
    agent_id: str
    amount_usd: float
    amount_crypto: Optional[float] = None
    currency: str
    package_id: Optional[str] = None
    type: str
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# NLM invoke
# ---------------------------------------------------------------------------


class NLMInvokeRequest(BaseModel):
    """Request body for NLM inference via RaaS."""

    query: str
    query_type: str = "general"
    max_tokens: int = 1024
    temperature: float = 0.7


# ---------------------------------------------------------------------------
# CREP invoke
# ---------------------------------------------------------------------------


class CREPInvokeRequest(BaseModel):
    """Request body for CREP data query via RaaS."""

    data_type: str = Field(..., pattern="^(aviation|maritime|satellite|weather)$")
    filters: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Earth2 invoke
# ---------------------------------------------------------------------------


class Earth2InvokeRequest(BaseModel):
    """Request body for Earth2 simulation via RaaS."""

    forecast_type: str = Field(
        default="medium_range",
        pattern="^(medium_range|short_range|spore_dispersal|ensemble)$",
    )
    location: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Device invoke
# ---------------------------------------------------------------------------


class DeviceInvokeRequest(BaseModel):
    """Request body for device telemetry query via RaaS."""

    device_id: Optional[str] = None
    query_type: str = "list"
    filters: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# MINDEX data invoke
# ---------------------------------------------------------------------------


class DataInvokeRequest(BaseModel):
    """Request body for MINDEX data query via RaaS."""

    query_type: str = Field(
        default="species",
        pattern="^(species|taxonomy|compound|knowledge_graph)$",
    )
    query: str = ""
    filters: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Agent task invoke
# ---------------------------------------------------------------------------


class AgentInvokeRequest(BaseModel):
    """Request body for agent task execution via RaaS."""

    agent_type: str
    task_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Memory invoke
# ---------------------------------------------------------------------------


class MemoryInvokeRequest(BaseModel):
    """Request body for memory/search query via RaaS."""

    query: str
    search_type: str = Field(
        default="semantic", pattern="^(semantic|fulltext|graph)$"
    )
    limit: int = Field(default=10, ge=1, le=100)


# ---------------------------------------------------------------------------
# Simulation invoke
# ---------------------------------------------------------------------------


class SimulationInvokeRequest(BaseModel):
    """Request body for simulation run via RaaS."""

    sim_type: str = Field(
        default="petri", pattern="^(petri|mycelium|physics)$"
    )
    parameters: Dict[str, Any] = Field(default_factory=dict)
