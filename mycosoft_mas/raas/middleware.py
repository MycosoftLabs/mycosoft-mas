"""RaaS authentication and credit-checking middleware.

Provides FastAPI dependencies for:
- API key authentication (X-API-Key header)
- Credit balance verification before service invocation

Created: March 11, 2026
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import HTTPException, Request, status

from mycosoft_mas.integrations.mindex_client import MINDEXClient
from mycosoft_mas.raas.models import AgentAccount

logger = logging.getLogger(__name__)

_mindex = MINDEXClient()


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def _ensure_agents_table() -> None:
    """Create raas_agents table if it doesn't exist (idempotent)."""
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS raas_agents (
                agent_id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                agent_url TEXT,
                description TEXT,
                contact_email TEXT,
                api_key_hash TEXT NOT NULL,
                tier TEXT DEFAULT 'agent',
                status TEXT DEFAULT 'pending_payment',
                stripe_customer_id TEXT,
                crypto_wallet_address TEXT,
                payment_method TEXT DEFAULT 'stripe',
                registered_at TIMESTAMP DEFAULT NOW(),
                activated_at TIMESTAMP,
                metadata JSONB DEFAULT '{}'
            );
            """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_raas_agents_key_hash " "ON raas_agents(api_key_hash);"
        )


async def require_raas_auth(request: Request) -> AgentAccount:
    """FastAPI dependency — authenticate via X-API-Key header.

    Looks up the agent in raas_agents, verifies status is ``active``.
    Returns the full ``AgentAccount`` on success.
    """
    raw_key = request.headers.get("X-API-Key")
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header missing",
        )

    await _ensure_agents_table()
    key_hash = _hash_key(raw_key)
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT agent_id, agent_name, agent_url, description,
                   contact_email, tier, status, stripe_customer_id,
                   crypto_wallet_address, payment_method,
                   registered_at, activated_at
            FROM raas_agents
            WHERE api_key_hash = $1
            """,
            key_hash,
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if row["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent account is not active (status={row['status']}). "
            "Complete signup payment to activate.",
        )

    # Fetch credit balance inline (lightweight query)
    credit_row = await _fetch_credit_balance(row["agent_id"])

    return AgentAccount(
        agent_id=row["agent_id"],
        agent_name=row["agent_name"],
        agent_url=row.get("agent_url"),
        description=row.get("description"),
        contact_email=row.get("contact_email"),
        tier=row["tier"],
        status=row["status"],
        credit_balance=credit_row,
        payment_method=row.get("payment_method", "stripe"),
        stripe_customer_id=row.get("stripe_customer_id"),
        crypto_wallet_address=row.get("crypto_wallet_address"),
        registered_at=row.get("registered_at"),
        activated_at=row.get("activated_at"),
    )


async def _fetch_credit_balance(agent_id: str) -> int:
    """Quick credit balance lookup."""
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT balance FROM raas_credits WHERE agent_id = $1",
            agent_id,
        )
    return int(row["balance"]) if row else 0
