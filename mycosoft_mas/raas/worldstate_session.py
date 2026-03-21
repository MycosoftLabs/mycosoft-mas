"""Worldstate session metering — $1/min live MYCA/AVANI connection.

Agents purchase minutes via website Stripe checkout, then claim them with
stripe_checkout_session_id. Sessions are started/heartbeat/stopped;
each elapsed minute deducts 1 from balance. Used by session_lifecycle router.

Created: March 14, 2026
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from mycosoft_mas.integrations.mindex_client import MINDEXClient
from mycosoft_mas.raas.models import (
    WorldstateBalance,
    WorldstateSessionSummary,
)

logger = logging.getLogger(__name__)

_mindex = MINDEXClient()


async def _ensure_tables() -> None:
    """Create worldstate tables if they don't exist (idempotent)."""
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS raas_worldstate_minutes (
                agent_id TEXT PRIMARY KEY,
                balance_minutes INTEGER DEFAULT 0,
                total_purchased INTEGER DEFAULT 0,
                total_used INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS raas_worldstate_sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT NOW(),
                last_heartbeat_at TIMESTAMP DEFAULT NOW(),
                stopped_at TIMESTAMP,
                minutes_used INTEGER DEFAULT 0
            );
            """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS raas_worldstate_minute_transactions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_raas_ws_tx_agent "
            "ON raas_worldstate_minute_transactions(agent_id);"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS raas_worldstate_claimed_sessions (
                stripe_session_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                minutes_added INTEGER NOT NULL,
                claimed_at TIMESTAMP DEFAULT NOW()
            );
            """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_raas_ws_sessions_agent "
            "ON raas_worldstate_sessions(agent_id);"
        )


async def get_balance(agent_id: str) -> WorldstateBalance:
    """Return current minute balance for an agent."""
    await _ensure_tables()
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT balance_minutes, total_purchased, total_used "
            "FROM raas_worldstate_minutes WHERE agent_id = $1",
            agent_id,
        )
    if not row:
        return WorldstateBalance(
            agent_id=agent_id,
            balance_minutes=0,
            total_purchased_minutes=0,
            total_used_minutes=0,
        )
    return WorldstateBalance(
        agent_id=agent_id,
        balance_minutes=int(row["balance_minutes"]),
        total_purchased_minutes=int(row["total_purchased"]),
        total_used_minutes=int(row["total_used"]),
    )


async def add_minutes(
    agent_id: str,
    minutes: int,
    tx_type: str = "purchase",
    description: str = "",
    session_id: Optional[str] = None,
) -> int:
    """Add minutes to an agent's balance. Returns new balance."""
    if minutes <= 0:
        return (await get_balance(agent_id)).balance_minutes
    await _ensure_tables()
    pool = await _mindex._get_db_pool()
    tx_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO raas_worldstate_minutes
                    (agent_id, balance_minutes, total_purchased, updated_at)
                VALUES ($1, $2, $2, $3)
                ON CONFLICT (agent_id) DO UPDATE
                SET balance_minutes = raas_worldstate_minutes.balance_minutes + $2,
                    total_purchased = raas_worldstate_minutes.total_purchased + $2,
                    updated_at = $3
                """,
                agent_id,
                minutes,
                now,
            )
            await conn.execute(
                """
                INSERT INTO raas_worldstate_minute_transactions
                    (id, agent_id, amount, type, description, session_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                tx_id,
                agent_id,
                minutes,
                tx_type,
                description,
                session_id,
                now,
            )
            row = await conn.fetchrow(
                "SELECT balance_minutes FROM raas_worldstate_minutes WHERE agent_id = $1",
                agent_id,
            )
    new_balance = int(row["balance_minutes"]) if row else minutes
    logger.info(
        "Added %d worldstate minutes to agent %s (type=%s). New balance: %d",
        minutes,
        agent_id,
        tx_type,
        new_balance,
    )
    return new_balance


async def claim_stripe_session(stripe_checkout_session_id: str, agent_id: str) -> Tuple[int, str]:
    """
    Claim prepaid minutes from a completed Stripe Checkout session.
    Idempotent: if session already claimed, returns (0, "already_claimed").
    Returns (minutes_added, status) where status is "ok" or error reason.
    """
    await _ensure_tables()
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT minutes_added FROM raas_worldstate_claimed_sessions WHERE stripe_session_id = $1",
            stripe_checkout_session_id,
        )
    if existing:
        return int(existing["minutes_added"]), "already_claimed"

    from mycosoft_mas.integrations.stripe_client import StripeClient

    stripe = StripeClient()
    session = await stripe.retrieve_checkout_session(stripe_checkout_session_id)
    if not session:
        return 0, "invalid_session"
    if session.get("payment_status") != "paid":
        return 0, "not_paid"
    metadata = session.get("metadata") or {}
    if metadata.get("type") != "agent_worldstate":
        return 0, "wrong_product"
    try:
        minutes = int(metadata.get("minutes", 0))
    except (TypeError, ValueError):
        minutes = 0
    if minutes <= 0:
        return 0, "invalid_minutes"

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                await conn.execute(
                    """
                    INSERT INTO raas_worldstate_claimed_sessions
                        (stripe_session_id, agent_id, minutes_added, claimed_at)
                    VALUES ($1, $2, $3, $4)
                    """,
                    stripe_checkout_session_id,
                    agent_id,
                    minutes,
                    now,
                )
            except Exception as e:
                if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                    return 0, "already_claimed"
                raise

    new_balance = await add_minutes(
        agent_id,
        minutes,
        tx_type="purchase",
        description=f"Stripe checkout {stripe_checkout_session_id[:20]}...",
    )
    logger.info(
        "Claimed %d worldstate minutes for agent %s from session %s. New balance: %d",
        minutes,
        agent_id,
        stripe_checkout_session_id[:24],
        new_balance,
    )
    return minutes, "ok"


async def start_session(agent_id: str) -> Tuple[Optional[str], int, Optional[str]]:
    """
    Start a paid worldstate session. Does not deduct the first minute at start;
    heartbeat will deduct as time elapses.
    Returns (session_id, balance_minutes, error_message).
    If balance is 0, returns (None, 0, "insufficient_balance").
    """
    await _ensure_tables()
    bal = await get_balance(agent_id)
    if bal.balance_minutes <= 0:
        return None, bal.balance_minutes, "insufficient_balance"

    session_id = f"ws_{uuid.uuid4().hex[:20]}"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO raas_worldstate_sessions
                (session_id, agent_id, started_at, last_heartbeat_at, minutes_used)
            VALUES ($1, $2, $3, $3, 0)
            """,
            session_id,
            agent_id,
            now,
        )
        row = await conn.fetchrow(
            "SELECT balance_minutes FROM raas_worldstate_minutes WHERE agent_id = $1",
            agent_id,
        )
    balance = int(row["balance_minutes"]) if row else bal.balance_minutes
    return session_id, balance, None


async def heartbeat_session(session_id: str, agent_id: str) -> Tuple[bool, int, int, Optional[str]]:
    """
    Heartbeat an active session. Deducts 1 minute per full minute elapsed
    since last_heartbeat_at. If balance would go below 0, returns 402 case.
    Returns (success, balance_minutes, minutes_used_this_session, error_message).
    """
    await _ensure_tables()
    pool = await _mindex._get_db_pool()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT agent_id, started_at, last_heartbeat_at, minutes_used, stopped_at
            FROM raas_worldstate_sessions
            WHERE session_id = $1
            """,
            session_id,
        )
    if not row or row["agent_id"] != agent_id:
        return False, 0, 0, "session_not_found"
    if row["stopped_at"]:
        return False, 0, int(row["minutes_used"] or 0), "session_stopped"

    last = row["last_heartbeat_at"]
    if last is None:
        last = row["started_at"]
    if last and last.tzinfo:
        last = last.replace(tzinfo=None)
    elapsed_seconds = (now - last).total_seconds() if last else 0
    minutes_to_deduct = max(0, int(elapsed_seconds // 60))
    if minutes_to_deduct == 0:
        bal = await get_balance(agent_id)
        async with pool.acquire() as conn:
            r = await conn.fetchrow(
                "SELECT minutes_used FROM raas_worldstate_sessions WHERE session_id = $1",
                session_id,
            )
            used = int(r["minutes_used"]) if r else 0
            await conn.execute(
                "UPDATE raas_worldstate_sessions SET last_heartbeat_at = $2 WHERE session_id = $1",
                session_id,
                now,
            )
        return True, bal.balance_minutes, used, None

    bal = await get_balance(agent_id)
    if bal.balance_minutes < minutes_to_deduct:
        return False, bal.balance_minutes, int(row["minutes_used"] or 0), "insufficient_balance"

    tx_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                UPDATE raas_worldstate_minutes
                SET balance_minutes = balance_minutes - $2,
                    total_used = total_used + $2,
                    updated_at = $3
                WHERE agent_id = $1
                """,
                agent_id,
                minutes_to_deduct,
                now,
            )
            await conn.execute(
                """
                INSERT INTO raas_worldstate_minute_transactions
                    (id, agent_id, amount, type, description, session_id, created_at)
                VALUES ($1, $2, $3, 'usage', $4, $5, $6)
                """,
                tx_id,
                agent_id,
                -minutes_to_deduct,
                f"Session heartbeat: {session_id[:20]}...",
                session_id,
                now,
            )
            await conn.execute(
                """
                UPDATE raas_worldstate_sessions
                SET last_heartbeat_at = $2, minutes_used = minutes_used + $3
                WHERE session_id = $1
                """,
                session_id,
                now,
                minutes_to_deduct,
            )
            row2 = await conn.fetchrow(
                "SELECT balance_minutes FROM raas_worldstate_minutes WHERE agent_id = $1",
                agent_id,
            )
            row3 = await conn.fetchrow(
                "SELECT minutes_used FROM raas_worldstate_sessions WHERE session_id = $1",
                session_id,
            )
    balance = int(row2["balance_minutes"]) if row2 else 0
    used = int(row3["minutes_used"]) if row3 else minutes_to_deduct
    return True, balance, used, None


async def stop_session(session_id: str, agent_id: str) -> Tuple[bool, int, int, Optional[str]]:
    """
    Stop an active session. Returns (success, total_minutes_used, balance_minutes, error).
    """
    await _ensure_tables()
    pool = await _mindex._get_db_pool()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT agent_id, minutes_used, stopped_at FROM raas_worldstate_sessions WHERE session_id = $1",
            session_id,
        )
    if not row or row["agent_id"] != agent_id:
        return False, 0, 0, "session_not_found"
    if row["stopped_at"]:
        bal = await get_balance(agent_id)
        return True, int(row["minutes_used"] or 0), bal.balance_minutes, None

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE raas_worldstate_sessions SET stopped_at = $2 WHERE session_id = $1",
            session_id,
            now,
        )
        row2 = await conn.fetchrow(
            "SELECT minutes_used FROM raas_worldstate_sessions WHERE session_id = $1",
            session_id,
        )
    bal = await get_balance(agent_id)
    return True, int(row2["minutes_used"]) if row2 else 0, bal.balance_minutes, None


async def get_active_session_id(agent_id: str) -> Optional[str]:
    """Return the current active session_id for this agent, if any."""
    await _ensure_tables()
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT session_id FROM raas_worldstate_sessions
            WHERE agent_id = $1 AND stopped_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
            """,
            agent_id,
        )
    return row["session_id"] if row else None


async def get_usage(
    agent_id: str, limit: int = 20
) -> Tuple[WorldstateBalance, Optional[str], List[WorldstateSessionSummary]]:
    """Return balance, active_session_id, and recent sessions."""
    await _ensure_tables()
    bal = await get_balance(agent_id)
    active = await get_active_session_id(agent_id)
    pool = await _mindex._get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT session_id, agent_id, started_at, last_heartbeat_at, stopped_at, minutes_used
            FROM raas_worldstate_sessions
            WHERE agent_id = $1
            ORDER BY started_at DESC
            LIMIT $2
            """,
            agent_id,
            limit,
        )
    sessions = [
        WorldstateSessionSummary(
            session_id=r["session_id"],
            agent_id=r["agent_id"],
            started_at=r.get("started_at"),
            last_heartbeat_at=r.get("last_heartbeat_at"),
            stopped_at=r.get("stopped_at"),
            minutes_used=int(r.get("minutes_used") or 0),
        )
        for r in rows
    ]
    return bal, active, sessions
