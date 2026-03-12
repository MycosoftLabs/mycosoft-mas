"""RaaS Agent Onboarding — registration, activation, account management.

External agents register here, pay the $1 signup fee, get an API key,
and start consuming MYCA services.

Created: March 11, 2026
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from mycosoft_mas.integrations.mindex_client import MINDEXClient
from mycosoft_mas.raas import credits as credit_system
from mycosoft_mas.raas.middleware import _ensure_agents_table, require_raas_auth
from mycosoft_mas.raas.models import (
    AgentAccount,
    AgentRegistration,
    AgentRegistrationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/raas/agents", tags=["RaaS - Agent Onboarding"])

_mindex = MINDEXClient()


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", response_model=AgentRegistrationResponse)
async def register_agent(body: AgentRegistration) -> AgentRegistrationResponse:
    """Register a new external agent.

    Returns an API key and instructions for completing the $1 signup payment.
    The agent account remains ``pending_payment`` until the fee is confirmed.
    """
    await _ensure_agents_table()

    agent_id = f"agent_{uuid.uuid4().hex[:16]}"
    raw_key = f"myca_raas_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO raas_agents
                (agent_id, agent_name, agent_url, description, contact_email,
                 api_key_hash, tier, status, payment_method, registered_at)
            VALUES ($1, $2, $3, $4, $5, $6, 'agent', 'pending_payment', $7, $8)
            """,
            agent_id,
            body.agent_name,
            body.agent_url,
            body.description,
            body.contact_email,
            key_hash,
            body.payment_method,
            now,
        )

    # Initialize credit record (zero balance)
    await credit_system._ensure_tables()

    signup_url = None
    if body.payment_method == "stripe":
        signup_url = f"/api/raas/payments/stripe/checkout?agent_id={agent_id}&package_id=signup"
    else:
        signup_url = f"/api/raas/payments/crypto/invoice?agent_id={agent_id}&package_id=signup"

    logger.info(
        "Registered agent %s (%s) via %s", agent_id, body.agent_name, body.payment_method
    )

    return AgentRegistrationResponse(
        agent_id=agent_id,
        api_key=raw_key,
        status="pending_payment",
        signup_payment_url=signup_url,
    )


@router.post("/activate")
async def activate_agent(agent_id: str) -> Dict[str, Any]:
    """Activate an agent after signup payment is confirmed.

    Called internally by payment webhook / crypto verification.
    Adds 100 bonus credits on activation.
    """
    await _ensure_agents_table()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE raas_agents
            SET status = 'active', activated_at = $2
            WHERE agent_id = $1 AND status = 'pending_payment'
            """,
            agent_id,
            now,
        )

    if result.split(" ")[-1] == "0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or already active",
        )

    # Award signup bonus credits
    new_balance = await credit_system.add_credits(
        agent_id, 100, tx_type="bonus", description="Signup bonus"
    )

    logger.info("Activated agent %s with 100 bonus credits", agent_id)

    return {
        "status": "activated",
        "agent_id": agent_id,
        "credit_balance": new_balance,
        "message": "Welcome! Your agent account is now active with 100 bonus credits.",
    }


@router.get("/me")
async def get_my_account(
    agent: AgentAccount = Depends(require_raas_auth),
) -> Dict[str, Any]:
    """Get current agent account info including credit balance."""
    balance = await credit_system.get_balance(agent.agent_id)
    return {
        "status": "ok",
        "agent": {
            "agent_id": agent.agent_id,
            "agent_name": agent.agent_name,
            "tier": agent.tier,
            "status": agent.status,
            "payment_method": agent.payment_method,
            "registered_at": agent.registered_at.isoformat() if agent.registered_at else None,
            "activated_at": agent.activated_at.isoformat() if agent.activated_at else None,
        },
        "credits": balance.model_dump(),
    }


@router.get("/me/usage")
async def get_my_usage(
    agent: AgentAccount = Depends(require_raas_auth),
    limit: int = 50,
) -> Dict[str, Any]:
    """Get recent credit usage history."""
    transactions = await credit_system.get_transactions(agent.agent_id, limit=limit)
    balance = await credit_system.get_balance(agent.agent_id)

    # Group by service
    by_service: Dict[str, int] = {}
    for tx in transactions:
        if tx.type == "usage" and tx.service_id:
            by_service[tx.service_id] = by_service.get(tx.service_id, 0) + abs(tx.amount)

    return {
        "status": "ok",
        "balance": balance.model_dump(),
        "usage_by_service": by_service,
        "recent_transactions": [tx.model_dump() for tx in transactions],
    }
