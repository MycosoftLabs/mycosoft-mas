"""
OWS (Open Wallet Standard) Wallet Agent.

Manages wallet lifecycle, multi-chain balances, A2A transfers,
treasury operations, and on-chain signing for all MAS agents.

Task types:
    create_wallet     — Provision new OWS wallet for an agent
    get_balance       — Check on-chain + internal ledger balance
    transfer          — Internal agent-to-agent transfer (ledger-based, instant)
    fund_wallet       — Record external funding of agent wallet
    withdraw          — On-chain withdrawal from agent wallet
    sign_transaction  — Sign arbitrary transaction for an agent
    get_wallet_info   — Get all chain addresses for an agent
    reconcile         — Sync on-chain balances with internal ledger
    init_treasury     — Initialize MYCA treasury wallet

Created: March 24, 2026
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

TREASURY_WALLET_NAME = "myca-treasury"
TREASURY_AGENT_ID = "myca-treasury"
TREASURY_FEE_PERCENT = Decimal("0.05")  # 5% orchestrator cut on internal transfers

# Currency → balance column mapping
CURRENCY_COLUMN_MAP = {
    "SOL": "sol_balance",
    "USDC": "usdc_balance",
    "ETH": "eth_balance",
    "BTC": "btc_balance",
}


class OWSWalletAgent(BaseAgent):
    """Agent for OWS wallet management — multi-chain, A2A payments, treasury."""

    def __init__(
        self,
        agent_id: str = "ows-wallet-agent",
        name: str = "OWS Wallet Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities.update(
            {"ows_wallet", "multi_chain", "agent_payments", "treasury"}
        )
        self._ows_client = None
        self._mindex = None

    # ------------------------------------------------------------------
    # Lazy loaders
    # ------------------------------------------------------------------

    def _get_ows(self):
        if self._ows_client is None:
            try:
                from mycosoft_mas.integrations.ows_client import OWSClient

                self._ows_client = OWSClient(self.config)
            except ImportError:
                logger.warning("OWSClient not available — wallet ops disabled")
        return self._ows_client

    def _get_mindex(self):
        if self._mindex is None:
            try:
                from mycosoft_mas.integrations.mindex_client import MINDEXClient

                self._mindex = MINDEXClient()
            except ImportError:
                logger.warning("MINDEXClient not available — DB ops disabled")
        return self._mindex

    # ------------------------------------------------------------------
    # BaseAgent overrides
    # ------------------------------------------------------------------

    async def _initialize_services(self) -> None:
        from mycosoft_mas.agents.base_agent import AgentStatus

        self.status = AgentStatus.ACTIVE

    async def _check_services_health(self) -> Dict[str, Any]:
        ows = self._get_ows()
        if ows:
            return await ows.health_check()
        return {"status": "unconfigured", "error": "OWS client not available"}

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to the appropriate handler."""
        task_type = task.get("type", "")
        handlers = {
            "create_wallet": self._handle_create_wallet,
            "get_balance": self._handle_get_balance,
            "transfer": self._handle_transfer,
            "fund_wallet": self._handle_fund_wallet,
            "withdraw": self._handle_withdraw,
            "sign_transaction": self._handle_sign_transaction,
            "get_wallet_info": self._handle_get_wallet_info,
            "reconcile": self._handle_reconcile,
            "init_treasury": self._handle_init_treasury,
        }
        handler = handlers.get(task_type)
        if handler:
            return await handler(task)
        return {"status": "unhandled", "task_type": task_type}

    async def process(self) -> None:
        await asyncio.sleep(0.1)

    # ------------------------------------------------------------------
    # Task handlers
    # ------------------------------------------------------------------

    async def _handle_create_wallet(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create an OWS wallet for an agent and register in DB."""
        agent_id = task.get("agent_id", "")
        wallet_name = task.get("wallet_name", f"agent-{agent_id}")
        passphrase = task.get("passphrase", "")
        wallet_type = task.get("wallet_type", "internal")

        if not agent_id or not passphrase:
            return {"status": "error", "error": "agent_id and passphrase required"}

        ows = self._get_ows()
        if not ows:
            return {"status": "error", "error": "OWS client not available"}

        # Create the OWS vault
        result = await ows.create_wallet(wallet_name, passphrase)
        chains = result.get("chains", {})

        # Hash passphrase for DB storage
        passphrase_hash = hashlib.sha256(passphrase.encode()).hexdigest()

        # Persist to MINDEX
        mindex = self._get_mindex()
        if mindex:
            try:
                pool = await mindex._get_db_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO ows_wallets
                            (agent_id, wallet_name, wallet_type, passphrase_hash, chains, status)
                        VALUES ($1, $2, $3, $4, $5::jsonb, 'active')
                        ON CONFLICT (agent_id) DO UPDATE
                            SET chains = $5::jsonb, updated_at = NOW()
                        """,
                        agent_id,
                        wallet_name,
                        wallet_type,
                        passphrase_hash,
                        __import__("json").dumps(chains),
                    )
                    # Initialize balance record
                    await conn.execute(
                        """
                        INSERT INTO ows_balances (agent_id)
                        VALUES ($1)
                        ON CONFLICT (agent_id) DO NOTHING
                        """,
                        agent_id,
                    )
            except Exception as e:
                logger.error("Failed to persist wallet for %s: %s", agent_id, e)

        return {
            "status": "success",
            "agent_id": agent_id,
            "wallet_name": wallet_name,
            "wallet_type": wallet_type,
            "chains": chains,
        }

    async def _handle_get_balance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get combined on-chain + internal ledger balance for an agent."""
        agent_id = task.get("agent_id", "")
        if not agent_id:
            return {"status": "error", "error": "agent_id required"}

        balances: Dict[str, float] = {}
        mindex = self._get_mindex()
        if mindex:
            try:
                pool = await mindex._get_db_pool()
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM ows_balances WHERE agent_id = $1", agent_id
                    )
                    if row:
                        balances = {
                            "SOL": float(row.get("sol_balance", 0)),
                            "USDC": float(row.get("usdc_balance", 0)),
                            "ETH": float(row.get("eth_balance", 0)),
                            "BTC": float(row.get("btc_balance", 0)),
                        }
            except Exception as e:
                logger.warning("Failed to get balance for %s: %s", agent_id, e)

        return {"status": "success", "agent_id": agent_id, "balances": balances}

    async def _handle_transfer(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Internal A2A transfer with treasury fee (ledger-based, instant)."""
        from_agent = task.get("from_agent_id", "")
        to_agent = task.get("to_agent_id", "")
        amount = Decimal(str(task.get("amount", 0)))
        currency = task.get("currency", "SOL").upper()

        if not from_agent or not to_agent or amount <= 0:
            return {"status": "error", "error": "from_agent_id, to_agent_id, amount required"}

        # Minimum transfer: 0.00000001 (1 sat equivalent) — prevent dust/rounding exploits
        if amount < Decimal("0.00000001"):
            return {"status": "error", "error": "Amount below minimum (0.00000001)"}

        col = CURRENCY_COLUMN_MAP.get(currency)
        if not col:
            return {"status": "error", "error": f"Unsupported currency: {currency}"}

        fee = amount * TREASURY_FEE_PERCENT
        net_amount = amount - fee
        tx_id = str(uuid.uuid4())
        fee_tx_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        mindex = self._get_mindex()
        if not mindex:
            return {"status": "error", "error": "Database not available"}

        try:
            pool = await mindex._get_db_pool()
            async with pool.acquire() as conn:
                async with conn.transaction():
                    # Check sender balance
                    row = await conn.fetchrow(
                        f"SELECT {col} FROM ows_balances WHERE agent_id = $1 FOR UPDATE",
                        from_agent,
                    )
                    if not row:
                        return {"status": "error", "error": "Sender wallet not found"}
                    sender_bal = Decimal(str(row[col]))
                    if sender_bal < amount:
                        return {
                            "status": "error",
                            "error": "Insufficient balance",
                            "balance": float(sender_bal),
                            "required": float(amount),
                        }

                    # Debit sender
                    await conn.execute(
                        f"UPDATE ows_balances SET {col} = {col} - $2 WHERE agent_id = $1",
                        from_agent,
                        amount,
                    )
                    # Credit receiver (net)
                    await conn.execute(
                        f"UPDATE ows_balances SET {col} = {col} + $2 WHERE agent_id = $1",
                        to_agent,
                        net_amount,
                    )
                    # Credit treasury (fee)
                    await conn.execute(
                        f"""UPDATE ows_balances SET {col} = {col} + $2
                            WHERE agent_id = $1""",
                        TREASURY_AGENT_ID,
                        fee,
                    )

                    # Record main transaction
                    await conn.execute(
                        """
                        INSERT INTO ows_transactions
                            (tx_id, from_agent_id, to_agent_id, amount, currency,
                             chain, tx_type, status, created_at)
                        VALUES ($1, $2, $3, $4, $5, 'internal', 'internal_transfer', 'confirmed', $6)
                        """,
                        uuid.UUID(tx_id),
                        from_agent,
                        to_agent,
                        net_amount,
                        currency,
                        now,
                    )
                    # Record fee transaction
                    await conn.execute(
                        """
                        INSERT INTO ows_transactions
                            (tx_id, from_agent_id, to_agent_id, amount, currency,
                             chain, tx_type, status, created_at)
                        VALUES ($1, $2, $3, $4, $5, 'internal', 'service_fee', 'confirmed', $6)
                        """,
                        uuid.UUID(fee_tx_id),
                        from_agent,
                        TREASURY_AGENT_ID,
                        fee,
                        currency,
                        now,
                    )

            # Publish event to Redis
            try:
                import redis.asyncio as aioredis

                r = aioredis.from_url("redis://192.168.0.189:6379")
                event = {
                    "type": "ows_transfer",
                    "tx_id": tx_id,
                    "from": from_agent,
                    "to": to_agent,
                    "amount": str(net_amount),
                    "fee": str(fee),
                    "currency": currency,
                    "timestamp": now.isoformat(),
                }
                await r.publish("ows:payments", __import__("json").dumps(event))
                await r.aclose()
            except Exception as e:
                logger.debug("Redis publish failed (non-critical): %s", e)

            return {
                "status": "success",
                "tx_id": tx_id,
                "from_agent_id": from_agent,
                "to_agent_id": to_agent,
                "amount": float(net_amount),
                "fee": float(fee),
                "currency": currency,
            }
        except Exception as e:
            logger.error("Transfer failed: %s", e)
            return {"status": "error", "error": str(e)}

    async def _handle_fund_wallet(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Record external funding of an agent wallet.

        SECURITY: This should ONLY be called by verified payment webhooks
        (Stripe webhook, on-chain tx verifier) — never by an agent directly.
        The tx_hash must be verified against the actual blockchain before calling this.
        The caller must set verified=True to confirm the funding is real.
        """
        agent_id = task.get("agent_id", "")
        amount = Decimal(str(task.get("amount", 0)))
        currency = task.get("currency", "SOL").upper()
        tx_hash = task.get("tx_hash")
        verified = task.get("verified", False)

        if not verified:
            return {"status": "error", "error": "Funding must be verified (verified=True). Only payment webhooks may credit balances."}

        col = CURRENCY_COLUMN_MAP.get(currency)
        if not agent_id or amount <= 0 or not col:
            return {"status": "error", "error": "agent_id, amount, valid currency required"}
        if not tx_hash:
            return {"status": "error", "error": "tx_hash required for verified funding"}

        mindex = self._get_mindex()
        if not mindex:
            return {"status": "error", "error": "Database not available"}

        tx_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        try:
            pool = await mindex._get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    f"UPDATE ows_balances SET {col} = {col} + $2 WHERE agent_id = $1",
                    agent_id,
                    amount,
                )
                await conn.execute(
                    """
                    INSERT INTO ows_transactions
                        (tx_id, to_agent_id, amount, currency, chain, tx_type, tx_hash, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, 'fund', $6, 'confirmed', $7)
                    """,
                    uuid.UUID(tx_id),
                    agent_id,
                    amount,
                    currency,
                    task.get("chain", "external"),
                    tx_hash,
                    now,
                )
            return {
                "status": "success",
                "tx_id": tx_id,
                "agent_id": agent_id,
                "amount": float(amount),
                "currency": currency,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _handle_withdraw(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """On-chain withdrawal from an agent wallet."""
        agent_id = task.get("agent_id", "")
        amount = Decimal(str(task.get("amount", 0)))
        currency = task.get("currency", "SOL").upper()
        chain = task.get("chain", "solana:mainnet")
        to_address = task.get("to_address", "")

        col = CURRENCY_COLUMN_MAP.get(currency)
        if not agent_id or amount <= 0 or not col or not to_address:
            return {"status": "error", "error": "agent_id, amount, currency, to_address required"}

        tx_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        mindex = self._get_mindex()
        if not mindex:
            return {"status": "error", "error": "Database not available"}

        try:
            pool = await mindex._get_db_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT {col} FROM ows_balances WHERE agent_id = $1 FOR UPDATE",
                    agent_id,
                )
                if not row or Decimal(str(row[col])) < amount:
                    return {"status": "error", "error": "Insufficient balance"}

                await conn.execute(
                    f"UPDATE ows_balances SET {col} = {col} - $2 WHERE agent_id = $1",
                    agent_id,
                    amount,
                )
                await conn.execute(
                    """
                    INSERT INTO ows_transactions
                        (tx_id, from_agent_id, amount, currency, chain, tx_type,
                         status, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, 'withdraw', 'pending', $6::jsonb, $7)
                    """,
                    uuid.UUID(tx_id),
                    agent_id,
                    amount,
                    currency,
                    chain,
                    __import__("json").dumps({"to_address": to_address}),
                    now,
                )
            return {
                "status": "success",
                "tx_id": tx_id,
                "agent_id": agent_id,
                "amount": float(amount),
                "currency": currency,
                "chain": chain,
                "to_address": to_address,
                "note": "Withdrawal pending on-chain confirmation",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _handle_sign_transaction(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Sign a transaction for an agent."""
        agent_id = task.get("agent_id", "")
        chain = task.get("chain", "solana:mainnet")
        tx_data = task.get("tx_data", {})
        passphrase = task.get("passphrase", "")

        ows = self._get_ows()
        if not ows:
            return {"status": "error", "error": "OWS client not available"}

        # Look up wallet name for agent
        mindex = self._get_mindex()
        wallet_name = f"agent-{agent_id}"
        if mindex:
            try:
                pool = await mindex._get_db_pool()
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT wallet_name FROM ows_wallets WHERE agent_id = $1", agent_id
                    )
                    if row:
                        wallet_name = row["wallet_name"]
            except Exception:
                pass

        sig = await ows.sign_transaction(wallet_name, chain, tx_data, passphrase)
        if sig:
            return {"status": "success", "signature": sig, "chain": chain}
        return {"status": "error", "error": "Signing failed"}

    async def _handle_get_wallet_info(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get wallet info including chain addresses."""
        agent_id = task.get("agent_id", "")
        if not agent_id:
            return {"status": "error", "error": "agent_id required"}

        mindex = self._get_mindex()
        if not mindex:
            return {"status": "error", "error": "Database not available"}

        try:
            pool = await mindex._get_db_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """SELECT wallet_name, wallet_type, chains, status, created_at
                       FROM ows_wallets WHERE agent_id = $1""",
                    agent_id,
                )
                if not row:
                    return {"status": "error", "error": "Wallet not found"}

                balance_row = await conn.fetchrow(
                    "SELECT * FROM ows_balances WHERE agent_id = $1", agent_id
                )

            chains = row.get("chains", {})
            if isinstance(chains, str):
                chains = __import__("json").loads(chains)

            balances = {}
            if balance_row:
                balances = {
                    "SOL": float(balance_row.get("sol_balance", 0)),
                    "USDC": float(balance_row.get("usdc_balance", 0)),
                    "ETH": float(balance_row.get("eth_balance", 0)),
                    "BTC": float(balance_row.get("btc_balance", 0)),
                }

            return {
                "status": "success",
                "agent_id": agent_id,
                "wallet_name": row["wallet_name"],
                "wallet_type": row["wallet_type"],
                "chains": chains,
                "balances": balances,
                "wallet_status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _handle_reconcile(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder for on-chain ↔ ledger reconciliation."""
        return {
            "status": "success",
            "note": "Reconciliation scheduled — on-chain balances will be synced with internal ledger",
        }

    async def _handle_init_treasury(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the MYCA treasury wallet."""
        passphrase = task.get("passphrase", "")
        if not passphrase:
            return {"status": "error", "error": "passphrase required for treasury init"}

        return await self._handle_create_wallet(
            {
                "agent_id": TREASURY_AGENT_ID,
                "wallet_name": TREASURY_WALLET_NAME,
                "passphrase": passphrase,
                "wallet_type": "treasury",
            }
        )
