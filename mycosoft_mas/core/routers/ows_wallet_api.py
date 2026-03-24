"""
OWS (Open Wallet Standard) Wallet API.

Multi-chain wallet management for internal MAS agents and external
customer agents. Includes treasury dashboard, A2A payment bus, and
onboarding wallet creation.

Endpoints:
    Internal (MAS agents):
        POST   /api/wallet/ows/create
        GET    /api/wallet/ows/{agent_id}
        GET    /api/wallet/ows/{agent_id}/balance
        POST   /api/wallet/ows/transfer
        GET    /api/wallet/ows/{agent_id}/history
        POST   /api/wallet/ows/sign
        GET    /api/wallet/ows/treasury

    External (customer agents):
        POST   /api/wallet/ows/onboard
        POST   /api/wallet/ows/fund
        GET    /api/wallet/ows/fund/status/{tx_id}
        POST   /api/wallet/ows/pay

Created: March 24, 2026
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wallet/ows", tags=["ows-wallet", "crypto", "payments"])


# ---------------------------------------------------------------------------
# CEO auth dependency (lazy import to avoid circular deps at module load)
# ---------------------------------------------------------------------------


async def _require_ceo_auth_dep(request: Request) -> str:
    """FastAPI dependency wrapper for CEO treasury auth."""
    from mycosoft_mas.security.treasury_auth import require_ceo_auth

    return await require_ceo_auth(request)


# Lazy singletons
_ows_agent = None
_mindex = None


def _get_ows_agent():
    global _ows_agent
    if _ows_agent is None:
        try:
            from mycosoft_mas.agents.crypto.ows_wallet_agent import OWSWalletAgent

            _ows_agent = OWSWalletAgent()
        except ImportError:
            logger.warning("OWSWalletAgent not available")
    return _ows_agent


def _get_mindex():
    global _mindex
    if _mindex is None:
        try:
            from mycosoft_mas.integrations.mindex_client import MINDEXClient

            _mindex = MINDEXClient()
        except ImportError:
            logger.warning("MINDEXClient not available")
    return _mindex


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class CreateWalletRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    wallet_name: Optional[str] = None
    wallet_type: str = Field(default="internal", pattern="^(internal|external|treasury)$")


class CreateWalletResponse(BaseModel):
    agent_id: str
    wallet_name: str
    wallet_type: str
    chains: Dict[str, str] = Field(default_factory=dict)
    status: str


class TransferRequest(BaseModel):
    from_agent_id: str = Field(..., min_length=1)
    to_agent_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="SOL", pattern="^(SOL|USDC|ETH|BTC)$")


class TransferResponse(BaseModel):
    tx_id: str
    from_agent_id: str
    to_agent_id: str
    amount: float
    fee: float
    currency: str
    status: str


class FundRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    chain: str = Field(default="solana")


class FundResponse(BaseModel):
    agent_id: str
    chain: str
    deposit_address: Optional[str] = None
    supported_currencies: List[str] = Field(default_factory=list)


class PayRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    service_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="SOL")


class SignRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    chain: str = Field(default="solana:mainnet")
    tx_data: Dict[str, Any] = Field(default_factory=dict)


class OnboardWalletRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    agent_name: Optional[str] = None


class BalanceResponse(BaseModel):
    agent_id: str
    balances: Dict[str, float] = Field(default_factory=dict)
    total_usd_estimate: Optional[float] = None


class TreasuryResponse(BaseModel):
    wallet_name: str = "myca-treasury"
    balances: Dict[str, float] = Field(default_factory=dict)
    total_received_24h: float = 0.0
    total_transactions_24h: int = 0
    active_wallets: int = 0
    by_agent_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    by_chain_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    supported_chains: List[str] = Field(default_factory=list)
    withdrawal_addresses: Dict[str, str] = Field(default_factory=dict)
    treasury_fee_percent: float = 5.0


class TreasurySettingsUpdate(BaseModel):
    """Update treasury withdrawal addresses and settings.

    Only include fields you want to change. Omitted fields stay as-is.
    """
    withdrawal_address_solana: Optional[str] = None
    withdrawal_address_ethereum: Optional[str] = None
    withdrawal_address_bitcoin: Optional[str] = None
    treasury_fee_percent: Optional[float] = Field(None, ge=0, le=50)
    auto_sweep_enabled: Optional[bool] = None
    auto_sweep_threshold_sol: Optional[float] = Field(None, ge=0)
    auto_sweep_threshold_eth: Optional[float] = Field(None, ge=0)
    auto_sweep_threshold_btc: Optional[float] = Field(None, ge=0)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
async def ows_wallet_health() -> Dict[str, Any]:
    """Check OWS wallet system health."""
    agent = _get_ows_agent()
    if not agent:
        return {"status": "unavailable", "error": "OWSWalletAgent not loaded"}
    health = await agent._check_services_health()
    return {"status": "healthy", "ows": health}


# ---------------------------------------------------------------------------
# Internal Endpoints
# ---------------------------------------------------------------------------


@router.post("/create", response_model=CreateWalletResponse)
async def create_wallet(body: CreateWalletRequest) -> CreateWalletResponse:
    """Create a new OWS wallet for an agent."""
    agent = _get_ows_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="OWS wallet system unavailable")

    wallet_name = body.wallet_name or f"agent-{body.agent_id}"
    passphrase = secrets.token_urlsafe(32)

    result = await agent.process_task(
        {
            "type": "create_wallet",
            "agent_id": body.agent_id,
            "wallet_name": wallet_name,
            "passphrase": passphrase,
            "wallet_type": body.wallet_type,
        }
    )

    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("error", "Wallet creation failed"))

    return CreateWalletResponse(
        agent_id=body.agent_id,
        wallet_name=wallet_name,
        wallet_type=body.wallet_type,
        chains=result.get("chains", {}),
        status="active",
    )


@router.get("/{agent_id}")
async def get_wallet_info(agent_id: str) -> Dict[str, Any]:
    """Get full wallet info for an agent."""
    agent = _get_ows_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="OWS wallet system unavailable")

    result = await agent.process_task({"type": "get_wallet_info", "agent_id": agent_id})
    if result.get("status") != "success":
        raise HTTPException(status_code=404, detail=result.get("error", "Wallet not found"))
    return result


@router.get("/{agent_id}/balance", response_model=BalanceResponse)
async def get_balance(agent_id: str) -> BalanceResponse:
    """Get balance for an agent (on-chain + internal ledger)."""
    agent = _get_ows_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="OWS wallet system unavailable")

    result = await agent.process_task({"type": "get_balance", "agent_id": agent_id})
    return BalanceResponse(
        agent_id=agent_id,
        balances=result.get("balances", {}),
    )


@router.post("/transfer", response_model=TransferResponse)
async def transfer(body: TransferRequest) -> TransferResponse:
    """Internal agent-to-agent transfer with 5% treasury fee."""
    agent = _get_ows_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="OWS wallet system unavailable")

    result = await agent.process_task(
        {
            "type": "transfer",
            "from_agent_id": body.from_agent_id,
            "to_agent_id": body.to_agent_id,
            "amount": body.amount,
            "currency": body.currency,
        }
    )

    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("error", "Transfer failed"))

    return TransferResponse(
        tx_id=result["tx_id"],
        from_agent_id=body.from_agent_id,
        to_agent_id=body.to_agent_id,
        amount=result["amount"],
        fee=result["fee"],
        currency=body.currency,
        status="confirmed",
    )


@router.get("/{agent_id}/history")
async def get_transaction_history(
    agent_id: str, limit: int = 50, offset: int = 0
) -> Dict[str, Any]:
    """Get transaction history for an agent."""
    mindex = _get_mindex()
    if not mindex:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tx_id, from_agent_id, to_agent_id, amount, currency,
                       chain, tx_type, tx_hash, status, metadata, created_at
                FROM ows_transactions
                WHERE from_agent_id = $1 OR to_agent_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                agent_id,
                limit,
                offset,
            )
            total = await conn.fetchval(
                """SELECT COUNT(*) FROM ows_transactions
                   WHERE from_agent_id = $1 OR to_agent_id = $1""",
                agent_id,
            )
        transactions = [
            {
                "tx_id": str(r["tx_id"]),
                "from_agent_id": r["from_agent_id"],
                "to_agent_id": r["to_agent_id"],
                "amount": float(r["amount"]),
                "currency": r["currency"],
                "chain": r["chain"],
                "tx_type": r["tx_type"],
                "tx_hash": r["tx_hash"],
                "status": r["status"],
                "metadata": r["metadata"] or {},
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
        return {
            "agent_id": agent_id,
            "transactions": transactions,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sign")
async def sign_transaction(body: SignRequest) -> Dict[str, Any]:
    """Sign a transaction for an agent."""
    agent = _get_ows_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="OWS wallet system unavailable")

    result = await agent.process_task(
        {
            "type": "sign_transaction",
            "agent_id": body.agent_id,
            "chain": body.chain,
            "tx_data": body.tx_data,
            "passphrase": "",  # Retrieved from secure store
        }
    )
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("error", "Signing failed"))
    return result


# ---------------------------------------------------------------------------
# Treasury
# ---------------------------------------------------------------------------


@router.get("/treasury", response_model=TreasuryResponse)
async def get_treasury_status() -> TreasuryResponse:
    """Get MYCA treasury wallet status and analytics."""
    from mycosoft_mas.agents.crypto.ows_wallet_agent import TREASURY_AGENT_ID
    from mycosoft_mas.integrations.ows_client import SUPPORTED_CHAINS, CHAIN_DISPLAY_NAMES

    mindex = _get_mindex()
    if not mindex:
        return TreasuryResponse(supported_chains=[CHAIN_DISPLAY_NAMES.get(c, c) for c in SUPPORTED_CHAINS])

    try:
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            # Treasury balances
            bal_row = await conn.fetchrow(
                "SELECT * FROM ows_balances WHERE agent_id = $1", TREASURY_AGENT_ID
            )
            balances = {}
            if bal_row:
                balances = {
                    "SOL": float(bal_row.get("sol_balance", 0)),
                    "USDC": float(bal_row.get("usdc_balance", 0)),
                    "ETH": float(bal_row.get("eth_balance", 0)),
                    "BTC": float(bal_row.get("btc_balance", 0)),
                }

            # 24h metrics
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            from datetime import timedelta

            day_ago = now - timedelta(hours=24)

            total_24h = await conn.fetchval(
                """SELECT COALESCE(SUM(amount), 0) FROM ows_transactions
                   WHERE to_agent_id = $1 AND created_at >= $2 AND status = 'confirmed'""",
                TREASURY_AGENT_ID,
                day_ago,
            )
            tx_count_24h = await conn.fetchval(
                """SELECT COUNT(*) FROM ows_transactions
                   WHERE to_agent_id = $1 AND created_at >= $2 AND status = 'confirmed'""",
                TREASURY_AGENT_ID,
                day_ago,
            )
            active_wallets = await conn.fetchval(
                "SELECT COUNT(*) FROM ows_wallets WHERE status = 'active'"
            )

            # Top paying agents
            top_agents = await conn.fetch(
                """SELECT from_agent_id, SUM(amount) as total_paid
                   FROM ows_transactions
                   WHERE to_agent_id = $1 AND status = 'confirmed'
                   GROUP BY from_agent_id
                   ORDER BY total_paid DESC
                   LIMIT 10""",
                TREASURY_AGENT_ID,
            )
            by_agent = [
                {"agent_id": r["from_agent_id"], "total_paid": float(r["total_paid"])}
                for r in top_agents
            ]

            # By chain breakdown
            by_chain_rows = await conn.fetch(
                """SELECT chain, SUM(amount) as total
                   FROM ows_transactions
                   WHERE to_agent_id = $1 AND status = 'confirmed'
                   GROUP BY chain""",
                TREASURY_AGENT_ID,
            )
            by_chain = [
                {"chain": r["chain"], "total": float(r["total"])} for r in by_chain_rows
            ]

            # Load treasury config (withdrawal addresses etc.)
            config_rows = await conn.fetch("SELECT config_key, config_value FROM ows_treasury_config")
            config = {r["config_key"]: r["config_value"] for r in config_rows}

        withdrawal_addrs = {}
        for chain in ["solana", "ethereum", "bitcoin"]:
            addr = config.get(f"withdrawal_address_{chain}", "")
            if addr:
                withdrawal_addrs[chain] = addr

        fee_pct = float(config.get("treasury_fee_percent", "5.0"))

        return TreasuryResponse(
            balances=balances,
            total_received_24h=float(total_24h) if total_24h else 0.0,
            total_transactions_24h=tx_count_24h or 0,
            active_wallets=active_wallets or 0,
            by_agent_breakdown=by_agent,
            by_chain_breakdown=by_chain,
            supported_chains=[CHAIN_DISPLAY_NAMES.get(c, c) for c in SUPPORTED_CHAINS],
            withdrawal_addresses=withdrawal_addrs,
            treasury_fee_percent=fee_pct,
        )
    except Exception as e:
        logger.error("Treasury status failed: %s", e)
        return TreasuryResponse()


# ---------------------------------------------------------------------------
# Treasury Auth Init (one-time setup)
# ---------------------------------------------------------------------------


class InitAuthRequest(BaseModel):
    """Set the CEO master key for treasury operations."""
    master_key: str = Field(..., min_length=16, description="Your secret key (16+ chars). Store it safely — cannot be recovered.")


@router.post("/treasury/init-auth")
async def init_treasury_auth(body: InitAuthRequest, request: Request) -> Dict[str, Any]:
    """One-time setup: Set your CEO master key for treasury access.

    This key protects ALL treasury settings — withdrawal addresses,
    fee changes, fund sweeps. Store it somewhere only you control.

    After setting this, all treasury mutation endpoints require
    the header: X-Treasury-Key: <your-master-key>

    To rotate: call this again with the old key in X-Treasury-Key
    and the new key in the body.
    """
    from mycosoft_mas.security.treasury_auth import (
        _get_ceo_key_hash,
        _get_client_ip,
        _record_audit,
        init_ceo_master_key,
        _hash_key,
    )

    ip = _get_client_ip(request)

    # If key already exists, require the current key to rotate
    existing_hash = await _get_ceo_key_hash()
    if existing_hash:
        old_key = request.headers.get("x-treasury-key", "").strip()
        if not old_key or _hash_key(old_key) != existing_hash:
            await _record_audit("key_rotation_denied", False, ip, {"reason": "invalid_current_key"})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CEO key already set. To rotate, provide current key in X-Treasury-Key header.",
            )
        await _record_audit("key_rotation", True, ip)

    result = await init_ceo_master_key(body.master_key)
    await _record_audit("key_init", True, ip)
    return result


# ---------------------------------------------------------------------------
# Treasury Settings (CEO-controlled, auth required)
# ---------------------------------------------------------------------------


@router.get("/treasury/settings")
async def get_treasury_settings(ceo: str = Depends(_require_ceo_auth_dep)) -> Dict[str, Any]:
    """Get all treasury configuration settings.

    Requires X-Treasury-Key header.
    Returns withdrawal addresses, fee percentage, auto-sweep settings.
    These are the addresses YOU control where funds get sent.
    """
    mindex = _get_mindex()
    if not mindex:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT config_key, config_value, updated_at, updated_by FROM ows_treasury_config")
        settings = {}
        for r in rows:
            settings[r["config_key"]] = {
                "value": r["config_value"],
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
                "updated_by": r["updated_by"],
            }
        return {"status": "ok", "settings": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/treasury/settings")
async def update_treasury_settings(
    body: TreasurySettingsUpdate,
    ceo: str = Depends(_require_ceo_auth_dep),
) -> Dict[str, Any]:
    """Update treasury settings. CEO key required.

    **Address changes use two-phase confirmation:**
    1. New addresses go to PENDING state with a cooldown timer (default 24h)
    2. Sweeps ONLY use CONFIRMED addresses — pending addresses are never used
    3. After cooldown expires, call POST /treasury/settings/confirm to activate
    4. If system crashes during this process, pending stays pending — funds safe

    Non-address settings (fee %, thresholds) apply immediately.

    Example:
        PUT /api/wallet/ows/treasury/settings
        Headers: X-Treasury-Key: <your-key>
        {"withdrawal_address_solana": "YourNewAddress"}
        -> Response: address staged as PENDING, confirm after cooldown
    """
    from mycosoft_mas.security.treasury_auth import _record_audit

    mindex = _get_mindex()
    if not mindex:
        raise HTTPException(status_code=503, detail="Database unavailable")

    # Separate address changes (two-phase) from other settings (immediate)
    address_updates: Dict[str, str] = {}
    immediate_updates: Dict[str, str] = {}

    for chain in ["solana", "ethereum", "bitcoin"]:
        val = getattr(body, f"withdrawal_address_{chain}", None)
        if val is not None:
            address_updates[chain] = val

    if body.treasury_fee_percent is not None:
        immediate_updates["treasury_fee_percent"] = str(body.treasury_fee_percent)
    if body.auto_sweep_enabled is not None:
        immediate_updates["auto_sweep_enabled"] = str(body.auto_sweep_enabled).lower()
    if body.auto_sweep_threshold_sol is not None:
        immediate_updates["auto_sweep_threshold_sol"] = str(body.auto_sweep_threshold_sol)
    if body.auto_sweep_threshold_eth is not None:
        immediate_updates["auto_sweep_threshold_eth"] = str(body.auto_sweep_threshold_eth)
    if body.auto_sweep_threshold_btc is not None:
        immediate_updates["auto_sweep_threshold_btc"] = str(body.auto_sweep_threshold_btc)

    if not address_updates and not immediate_updates:
        return {"status": "no_changes", "message": "No fields provided to update"}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    from datetime import timedelta

    try:
        pool = await mindex._get_db_pool()
        audit_changes = []

        async with pool.acquire() as conn:
            # All changes in one transaction — atomic, crash-safe
            async with conn.transaction():
                # Apply immediate (non-address) settings
                for key, value in immediate_updates.items():
                    old_row = await conn.fetchrow(
                        "SELECT config_value FROM ows_treasury_config WHERE config_key = $1", key
                    )
                    old_value = old_row["config_value"] if old_row else "(not set)"
                    await conn.execute(
                        """INSERT INTO ows_treasury_config (config_key, config_value, updated_at, updated_by)
                           VALUES ($1, $2, $3, 'ceo')
                           ON CONFLICT (config_key) DO UPDATE
                           SET config_value = $2, updated_at = $3, updated_by = 'ceo'""",
                        key, value, now,
                    )
                    audit_changes.append({"field": key, "old": old_value, "new": value, "status": "applied"})

                # Stage address changes as PENDING (not yet active)
                if address_updates:
                    # Lock sweeps while address change is pending
                    await conn.execute(
                        """INSERT INTO ows_treasury_config (config_key, config_value, updated_at, updated_by)
                           VALUES ('sweep_locked', 'true', $1, 'system')
                           ON CONFLICT (config_key) DO UPDATE
                           SET config_value = 'true', updated_at = $1, updated_by = 'system'""",
                        now,
                    )

                    # Get cooldown hours
                    cooldown_row = await conn.fetchrow(
                        "SELECT config_value FROM ows_treasury_config WHERE config_key = 'address_change_cooldown_hours'"
                    )
                    cooldown_hours = int(cooldown_row["config_value"]) if cooldown_row and cooldown_row["config_value"] else 24
                    expires_at = now + timedelta(hours=cooldown_hours)

                    for chain, addr in address_updates.items():
                        old_row = await conn.fetchrow(
                            "SELECT config_value FROM ows_treasury_config WHERE config_key = $1",
                            f"withdrawal_address_{chain}",
                        )
                        old_value = old_row["config_value"] if old_row else "(not set)"

                        # Write to pending slot
                        await conn.execute(
                            """INSERT INTO ows_treasury_config (config_key, config_value, updated_at, updated_by)
                               VALUES ($1, $2, $3, 'ceo')
                               ON CONFLICT (config_key) DO UPDATE
                               SET config_value = $2, updated_at = $3, updated_by = 'ceo'""",
                            f"pending_address_{chain}", addr, now,
                        )
                        audit_changes.append({
                            "field": f"withdrawal_address_{chain}",
                            "old": old_value,
                            "new": addr,
                            "status": "pending",
                            "confirms_after": expires_at.isoformat(),
                        })

                    # Record when pending expires
                    await conn.execute(
                        """INSERT INTO ows_treasury_config (config_key, config_value, updated_at, updated_by)
                           VALUES ('pending_address_expires_at', $1, $2, 'ceo')
                           ON CONFLICT (config_key) DO UPDATE
                           SET config_value = $1, updated_at = $2, updated_by = 'ceo'""",
                        expires_at.isoformat(), now,
                    )

        await _record_audit("settings_update", True, "api", {"changes": audit_changes})
        logger.info("Treasury settings updated: %s", [c["field"] for c in audit_changes])

        result: Dict[str, Any] = {
            "status": "updated",
            "changes": audit_changes,
            "timestamp": now.isoformat(),
        }
        if address_updates:
            result["address_change_note"] = (
                f"Address changes are PENDING for {cooldown_hours}h. "
                f"Sweeps are LOCKED until you confirm. "
                f"Confirm after {expires_at.isoformat()} via POST /api/wallet/ows/treasury/settings/confirm"
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/treasury/settings/confirm")
async def confirm_pending_addresses(
    ceo: str = Depends(_require_ceo_auth_dep),
) -> Dict[str, Any]:
    """Confirm pending address changes after cooldown has elapsed.

    CEO key required. Will refuse if cooldown hasn't expired yet.
    On confirmation:
      - Pending addresses become the active confirmed addresses
      - Sweep lock is released
      - Old addresses are overwritten (audit trail preserves them)
    """
    from mycosoft_mas.security.treasury_auth import _record_audit

    mindex = _get_mindex()
    if not mindex:
        raise HTTPException(status_code=503, detail="Database unavailable")

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            # Check if there are pending changes
            expires_row = await conn.fetchrow(
                "SELECT config_value FROM ows_treasury_config WHERE config_key = 'pending_address_expires_at'"
            )
            if not expires_row or not expires_row["config_value"]:
                return {"status": "nothing_pending", "message": "No pending address changes to confirm"}

            expires_at_str = expires_row["config_value"]
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if expires_at.tzinfo:
                    expires_at = expires_at.replace(tzinfo=None)
            except ValueError:
                return {"status": "error", "message": "Invalid pending expiry timestamp"}

            if now < expires_at:
                remaining = expires_at - now
                hours_left = remaining.total_seconds() / 3600
                return {
                    "status": "cooldown_active",
                    "message": f"Cooldown has not expired. {hours_left:.1f} hours remaining.",
                    "expires_at": expires_at.isoformat(),
                }

            # Cooldown expired — promote pending → confirmed (atomic)
            confirmed = []
            async with conn.transaction():
                for chain in ["solana", "ethereum", "bitcoin"]:
                    pending_row = await conn.fetchrow(
                        "SELECT config_value FROM ows_treasury_config WHERE config_key = $1",
                        f"pending_address_{chain}",
                    )
                    pending_addr = (pending_row["config_value"] or "").strip() if pending_row else ""
                    if not pending_addr:
                        continue

                    # Get old confirmed address for audit
                    old_row = await conn.fetchrow(
                        "SELECT config_value FROM ows_treasury_config WHERE config_key = $1",
                        f"withdrawal_address_{chain}",
                    )
                    old_addr = old_row["config_value"] if old_row else ""

                    # Promote: pending → confirmed
                    await conn.execute(
                        """INSERT INTO ows_treasury_config (config_key, config_value, updated_at, updated_by)
                           VALUES ($1, $2, $3, 'ceo')
                           ON CONFLICT (config_key) DO UPDATE
                           SET config_value = $2, updated_at = $3, updated_by = 'ceo'""",
                        f"withdrawal_address_{chain}", pending_addr, now,
                    )
                    # Clear pending
                    await conn.execute(
                        """UPDATE ows_treasury_config SET config_value = '', updated_at = $2
                           WHERE config_key = $1""",
                        f"pending_address_{chain}", now,
                    )
                    confirmed.append({
                        "chain": chain,
                        "old_address": old_addr,
                        "new_address": pending_addr,
                    })

                # Clear expiry and unlock sweeps
                await conn.execute(
                    "UPDATE ows_treasury_config SET config_value = '' WHERE config_key = 'pending_address_expires_at'"
                )
                await conn.execute(
                    """UPDATE ows_treasury_config SET config_value = 'false', updated_at = $1
                       WHERE config_key = 'sweep_locked'""",
                    now,
                )

        await _record_audit("address_confirmed", True, "api", {"confirmed": confirmed})

        if not confirmed:
            return {"status": "nothing_to_confirm", "message": "No pending addresses had values"}

        return {
            "status": "confirmed",
            "confirmed_addresses": confirmed,
            "sweep_unlocked": True,
            "timestamp": now.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/treasury/settings/cancel")
async def cancel_pending_addresses(
    ceo: str = Depends(_require_ceo_auth_dep),
) -> Dict[str, Any]:
    """Cancel pending address changes and unlock sweeps.

    Use this if you made a mistake or want to abort an address change.
    """
    from mycosoft_mas.security.treasury_auth import _record_audit

    mindex = _get_mindex()
    if not mindex:
        raise HTTPException(status_code=503, detail="Database unavailable")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                for chain in ["solana", "ethereum", "bitcoin"]:
                    await conn.execute(
                        "UPDATE ows_treasury_config SET config_value = '', updated_at = $2 WHERE config_key = $1",
                        f"pending_address_{chain}", now,
                    )
                await conn.execute(
                    "UPDATE ows_treasury_config SET config_value = '' WHERE config_key = 'pending_address_expires_at'"
                )
                await conn.execute(
                    "UPDATE ows_treasury_config SET config_value = 'false', updated_at = $1 WHERE config_key = 'sweep_locked'",
                    now,
                )

        await _record_audit("address_change_cancelled", True, "api")
        return {"status": "cancelled", "sweep_unlocked": True, "timestamp": now.isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/treasury/sweep")
async def sweep_treasury_to_owner(
    ceo: str = Depends(_require_ceo_auth_dep),
) -> Dict[str, Any]:
    """Manually sweep treasury funds to your CONFIRMED withdrawal addresses.

    Requires X-Treasury-Key header (CEO only).

    Safety guarantees:
    - ONLY uses confirmed addresses (never pending)
    - Refuses to sweep if an address change is pending (sweep_locked)
    - Each chain sweep is an atomic DB transaction
    - If crash mid-sweep, unswept chains keep their balance
    """
    from mycosoft_mas.security.treasury_auth import _record_audit

    mindex = _get_mindex()
    agent = _get_ows_agent()
    if not mindex or not agent:
        raise HTTPException(status_code=503, detail="System unavailable")

    from mycosoft_mas.agents.crypto.ows_wallet_agent import TREASURY_AGENT_ID

    try:
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            # Get config
            config_rows = await conn.fetch("SELECT config_key, config_value FROM ows_treasury_config")
            config = {r["config_key"]: r["config_value"] for r in config_rows}

            # CHECK: Is sweep locked due to pending address change?
            if config.get("sweep_locked", "false").lower() == "true":
                pending_expires = config.get("pending_address_expires_at", "")
                await _record_audit("sweep_blocked", False, "api", {"reason": "sweep_locked", "pending_expires": pending_expires})
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Sweep is LOCKED — an address change is pending. "
                        f"Either confirm it (POST /treasury/settings/confirm) "
                        f"or cancel it (POST /treasury/settings/cancel) first. "
                        f"Pending expires: {pending_expires}"
                    ),
                )

            # Get treasury balances
            bal_row = await conn.fetchrow(
                "SELECT * FROM ows_balances WHERE agent_id = $1", TREASURY_AGENT_ID
            )

        if not bal_row:
            return {"status": "no_balance", "message": "Treasury has no balance record"}

        sweeps = []
        chain_map = {
            "solana": ("sol_balance", "SOL", "solana:mainnet"),
            "ethereum": ("eth_balance", "ETH", "eip155:1"),
            "bitcoin": ("btc_balance", "BTC", "bip122:000000000019d6689c085ae165831e93"),
        }

        for chain_name, (col, currency, chain_id) in chain_map.items():
            # ONLY use confirmed addresses — never pending
            addr = config.get(f"withdrawal_address_{chain_name}", "").strip()
            balance = float(bal_row.get(col, 0))
            if not addr or balance <= 0:
                continue

            result = await agent.process_task(
                {
                    "type": "withdraw",
                    "agent_id": TREASURY_AGENT_ID,
                    "amount": balance,
                    "currency": currency,
                    "chain": chain_id,
                    "to_address": addr,
                }
            )
            sweeps.append({
                "chain": chain_name,
                "amount": balance,
                "currency": currency,
                "to_address": addr,
                "result": result.get("status"),
                "tx_id": result.get("tx_id"),
            })

        if not sweeps:
            return {
                "status": "nothing_to_sweep",
                "message": "No chains have both a confirmed withdrawal address and a positive balance",
            }

        await _record_audit("sweep_executed", True, "api", {"sweeps": sweeps})
        return {"status": "swept", "sweeps": sweeps}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/treasury/audit")
async def get_treasury_audit_log(
    limit: int = 50,
    ceo: str = Depends(_require_ceo_auth_dep),
) -> Dict[str, Any]:
    """View the treasury access audit log.

    Requires X-Treasury-Key header (CEO only).
    Shows every access attempt — successful and failed — with IP, timestamp, details.
    """
    mindex = _get_mindex()
    if not mindex:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT audit_id, action, success, ip_address, details, created_at
                   FROM ows_treasury_audit
                   ORDER BY created_at DESC
                   LIMIT $1""",
                limit,
            )
        entries = [
            {
                "id": r["audit_id"],
                "action": r["action"],
                "success": r["success"],
                "ip": r["ip_address"],
                "details": r["details"] or {},
                "timestamp": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
        return {"audit_entries": entries, "total_returned": len(entries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# External Agent Endpoints
# ---------------------------------------------------------------------------


@router.post("/onboard")
async def onboard_agent_wallet(body: OnboardWalletRequest) -> Dict[str, Any]:
    """Create a wallet during external agent onboarding."""
    agent = _get_ows_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="OWS wallet system unavailable")

    wallet_name = f"ext-{body.agent_id}"
    passphrase = secrets.token_urlsafe(32)

    result = await agent.process_task(
        {
            "type": "create_wallet",
            "agent_id": body.agent_id,
            "wallet_name": wallet_name,
            "passphrase": passphrase,
            "wallet_type": "external",
        }
    )

    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("error", "Onboarding failed"))

    chains = result.get("chains", {})
    deposit_addresses = {}
    from mycosoft_mas.integrations.ows_client import CHAIN_DISPLAY_NAMES

    for chain_id, addr in chains.items():
        display = CHAIN_DISPLAY_NAMES.get(chain_id, chain_id)
        deposit_addresses[display.lower()] = addr

    return {
        "status": "success",
        "agent_id": body.agent_id,
        "wallet_name": wallet_name,
        "deposit_addresses": deposit_addresses,
        "supported_chains": list(deposit_addresses.keys()),
        "next_steps": [
            "Fund your wallet by sending crypto to any deposit address above",
            "Check balance: GET /api/wallet/ows/{agent_id}/balance",
            "Pay for services: POST /api/wallet/ows/pay",
        ],
    }


@router.post("/fund", response_model=FundResponse)
async def get_fund_address(body: FundRequest) -> FundResponse:
    """Get deposit address for funding a wallet."""
    from mycosoft_mas.integrations.ows_client import CHAIN_ALIASES, CHAIN_DISPLAY_NAMES

    mindex = _get_mindex()
    if not mindex:
        raise HTTPException(status_code=503, detail="Database unavailable")

    chain_id = CHAIN_ALIASES.get(body.chain.lower(), body.chain)

    try:
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT chains FROM ows_wallets WHERE agent_id = $1", body.agent_id
            )
            if not row:
                raise HTTPException(status_code=404, detail="Wallet not found")

            chains = row["chains"] or {}
            if isinstance(chains, str):
                chains = __import__("json").loads(chains)

            address = chains.get(chain_id)

        currencies_map = {
            "solana:mainnet": ["SOL", "USDC"],
            "eip155:1": ["ETH", "USDC"],
            "bip122:000000000019d6689c085ae165831e93": ["BTC"],
        }

        return FundResponse(
            agent_id=body.agent_id,
            chain=CHAIN_DISPLAY_NAMES.get(chain_id, chain_id),
            deposit_address=address,
            supported_currencies=currencies_map.get(chain_id, []),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fund/status/{tx_id}")
async def get_funding_status(tx_id: str) -> Dict[str, Any]:
    """Check status of a funding transaction."""
    mindex = _get_mindex()
    if not mindex:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ows_transactions WHERE tx_id = $1", uuid.UUID(tx_id)
            )
            if not row:
                raise HTTPException(status_code=404, detail="Transaction not found")

        return {
            "tx_id": tx_id,
            "status": row["status"],
            "amount": float(row["amount"]),
            "currency": row["currency"],
            "chain": row["chain"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pay")
async def pay_for_service(body: PayRequest) -> Dict[str, Any]:
    """Pay for an API service from wallet (debits agent, credits treasury)."""
    from mycosoft_mas.agents.crypto.ows_wallet_agent import TREASURY_AGENT_ID

    agent = _get_ows_agent()
    if not agent:
        raise HTTPException(status_code=503, detail="OWS wallet system unavailable")

    result = await agent.process_task(
        {
            "type": "transfer",
            "from_agent_id": body.agent_id,
            "to_agent_id": TREASURY_AGENT_ID,
            "amount": body.amount,
            "currency": body.currency,
        }
    )

    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("error", "Payment failed"))

    return {
        "status": "success",
        "tx_id": result["tx_id"],
        "agent_id": body.agent_id,
        "service_id": body.service_id,
        "amount_paid": result["amount"],
        "fee": result["fee"],
        "currency": body.currency,
    }
