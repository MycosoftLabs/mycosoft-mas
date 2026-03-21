"""Credit system for RaaS — PostgreSQL-backed balance management.

Each API call costs credits. Agents purchase credit packages and credits
are atomically deducted on every metered invocation.

Created: March 11, 2026
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from mycosoft_mas.integrations.mindex_client import MINDEXClient
from mycosoft_mas.raas.models import CreditBalance, CreditPackage, CreditTransaction

logger = logging.getLogger(__name__)

_mindex = MINDEXClient()

# ---------------------------------------------------------------------------
# Credit packages
# ---------------------------------------------------------------------------

CREDIT_PACKAGES: Dict[str, CreditPackage] = {
    "signup": CreditPackage(
        package_id="signup",
        name="Signup Bonus",
        credits=100,
        price_usd=1.00,
        bonus_credits=0,
    ),
    "starter": CreditPackage(
        package_id="starter",
        name="Starter",
        credits=5000,
        price_usd=5.00,
        bonus_credits=0,
    ),
    "growth": CreditPackage(
        package_id="growth",
        name="Growth",
        credits=25000,
        price_usd=25.00,
        bonus_credits=5000,
    ),
    "scale": CreditPackage(
        package_id="scale",
        name="Scale",
        credits=100000,
        price_usd=100.00,
        bonus_credits=50000,
    ),
    "enterprise": CreditPackage(
        package_id="enterprise",
        name="Enterprise",
        credits=500000,
        price_usd=500.00,
        bonus_credits=500000,
    ),
}

# ---------------------------------------------------------------------------
# Service costs (credits per invocation)
# ---------------------------------------------------------------------------

CREDIT_COSTS: Dict[str, int] = {
    "nlm_inference": 10,
    "crep_query": 5,
    "crep_stream_minute": 20,
    "earth2_forecast": 25,
    "earth2_nowcast": 15,
    "device_telemetry": 5,
    "agent_task": 50,
    "mindex_query": 3,
    "knowledge_graph": 5,
    "memory_search": 5,
    "simulation": 25,
    "data_export": 100,
}


# ---------------------------------------------------------------------------
# Table setup
# ---------------------------------------------------------------------------


async def _ensure_tables() -> None:
    """Create credit tables if they don't exist (idempotent)."""
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS raas_credits (
                agent_id TEXT PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                total_purchased INTEGER DEFAULT 0,
                total_used INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS raas_credit_transactions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                service_id TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_raas_credit_tx_agent "
            "ON raas_credit_transactions(agent_id);"
        )


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


async def get_balance(agent_id: str) -> CreditBalance:
    """Return current credit balance for an agent."""
    await _ensure_tables()
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT balance, total_purchased, total_used " "FROM raas_credits WHERE agent_id = $1",
            agent_id,
        )
    if not row:
        return CreditBalance(agent_id=agent_id, balance=0, total_purchased=0, total_used=0)
    return CreditBalance(
        agent_id=agent_id,
        balance=int(row["balance"]),
        total_purchased=int(row["total_purchased"]),
        total_used=int(row["total_used"]),
    )


async def add_credits(
    agent_id: str,
    amount: int,
    tx_type: str = "purchase",
    description: str = "",
) -> int:
    """Add credits to an agent's balance. Returns new balance."""
    await _ensure_tables()
    pool = await _mindex._get_db_pool()
    tx_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Upsert credit balance
            await conn.execute(
                """
                INSERT INTO raas_credits (agent_id, balance, total_purchased, updated_at)
                VALUES ($1, $2, $2, $3)
                ON CONFLICT (agent_id) DO UPDATE
                SET balance = raas_credits.balance + $2,
                    total_purchased = raas_credits.total_purchased + $2,
                    updated_at = $3
                """,
                agent_id,
                amount,
                now,
            )
            # Record transaction
            await conn.execute(
                """
                INSERT INTO raas_credit_transactions
                    (id, agent_id, amount, type, description, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                tx_id,
                agent_id,
                amount,
                tx_type,
                description,
                now,
            )
            row = await conn.fetchrow(
                "SELECT balance FROM raas_credits WHERE agent_id = $1",
                agent_id,
            )
    new_balance = int(row["balance"]) if row else amount
    logger.info(
        "Added %d credits to agent %s (type=%s). New balance: %d",
        amount,
        agent_id,
        tx_type,
        new_balance,
    )
    return new_balance


async def deduct_credits(agent_id: str, amount: int, service_id: str) -> Tuple[bool, int]:
    """Atomically deduct credits. Returns (success, remaining_balance)."""
    await _ensure_tables()
    pool = await _mindex._get_db_pool()
    tx_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT balance FROM raas_credits WHERE agent_id = $1 FOR UPDATE",
                agent_id,
            )
            if not row or int(row["balance"]) < amount:
                current = int(row["balance"]) if row else 0
                return False, current

            await conn.execute(
                """
                UPDATE raas_credits
                SET balance = balance - $2,
                    total_used = total_used + $2,
                    updated_at = $3
                WHERE agent_id = $1
                """,
                agent_id,
                amount,
                now,
            )
            await conn.execute(
                """
                INSERT INTO raas_credit_transactions
                    (id, agent_id, amount, type, description, service_id, created_at)
                VALUES ($1, $2, $3, 'usage', $4, $5, $6)
                """,
                tx_id,
                agent_id,
                -amount,
                f"Service invocation: {service_id}",
                service_id,
                now,
            )
            row2 = await conn.fetchrow(
                "SELECT balance FROM raas_credits WHERE agent_id = $1",
                agent_id,
            )
    remaining = int(row2["balance"]) if row2 else 0
    return True, remaining


async def get_transactions(agent_id: str, limit: int = 50) -> List[CreditTransaction]:
    """Return recent credit transactions for an agent."""
    await _ensure_tables()
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, agent_id, amount, type, description, service_id, created_at
            FROM raas_credit_transactions
            WHERE agent_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            agent_id,
            limit,
        )
    return [
        CreditTransaction(
            id=str(r["id"]),
            agent_id=r["agent_id"],
            amount=int(r["amount"]),
            type=r["type"],
            description=r.get("description"),
            service_id=r.get("service_id"),
            created_at=r["created_at"],
        )
        for r in rows
    ]
