"""
Durable store for economy state.
Uses Supabase economy_* tables when configured; falls back to in-memory.

Created: March 10, 2026
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from mycosoft_mas.core.persistence.supabase_client import (
    supabase_available,
    supabase_insert,
    supabase_select,
    supabase_upsert,
)

logger = logging.getLogger(__name__)


def _parse_iso(value: Any) -> Optional[datetime]:
    """Parse ISO 8601 timestamps to timezone-aware UTC, or None if invalid."""
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


_DEFAULT_TIERS = {
    "free": {"price_per_request": 0.0, "daily_limit": 10, "features": ["basic_query", "taxonomy_lookup"]},
    "agent": {"price_per_request": 0.001, "daily_limit": 10000, "features": ["all_queries", "data_access", "api_tools"]},
    "premium": {"price_per_request": 0.01, "daily_limit": 100000, "features": ["all_queries", "data_access", "api_tools", "simulations", "priority"]},
    "enterprise": {"price_per_request": 0.005, "daily_limit": 1000000, "features": ["unlimited", "custom_models", "dedicated_compute", "sla"]},
}

_DEFAULT_WALLETS = {
    "solana": {"address": "MYCA_SOL_WALLET", "balance": 0.0, "currency": "SOL"},
    "bitcoin": {"address": "MYCA_BTC_WALLET", "balance": 0.0, "currency": "BTC"},
    "x401": {"address": "MYCA_X401_WALLET", "balance": 0.0, "currency": "X401"},
}


class EconomyStore:
    """Unified store for economy state: Supabase when available, else in-memory."""

    def __init__(self) -> None:
        self._memory: Dict[str, Any] = {
            "wallets": dict(_DEFAULT_WALLETS),
            "total_revenue": 0.0,
            "transactions": [],
            "active_clients": {},
            "resource_purchases": [],
            "incentives": [],
            "pricing_tiers": dict(_DEFAULT_TIERS),
        }
        self._loaded = False

    def _load_from_supabase(self) -> None:
        """Load state from Supabase tables into _memory."""
        if not supabase_available() or self._loaded:
            return
        try:
            # Wallets
            rows = supabase_select("economy_wallets", limit=50)
            if rows:
                self._memory["wallets"] = {}
                for r in rows:
                    wtype = r.get("wallet_type", "")
                    self._memory["wallets"][wtype] = {
                        "address": r.get("address", ""),
                        "balance": float(r.get("balance", 0)),
                        "currency": r.get("currency", "SOL"),
                    }
            # Transactions and total_revenue
            rows = supabase_select("economy_transactions", order="created_at.desc", limit=1000)
            self._memory["transactions"] = []
            rev = 0.0
            for r in rows:
                amt = float(r.get("amount", 0))
                if r.get("status") == "completed":
                    rev += amt
                self._memory["transactions"].append({
                    "id": r.get("transaction_id"),
                    "client_id": r.get("client_id"),
                    "amount": amt,
                    "currency": r.get("currency"),
                    "service_type": r.get("service_type"),
                    "status": r.get("status"),
                    "timestamp": (r.get("created_at") or ""),
                })
            self._memory["total_revenue"] = rev
            # Clients
            rows = supabase_select("economy_clients", limit=500)
            self._memory["active_clients"] = {}
            for r in rows:
                cid = r.get("client_id", "")
                self._memory["active_clients"][cid] = {
                    "type": r.get("client_type", "agent"),
                    "tier": r.get("tier", "agent"),
                    "registered_at": (r.get("registered_at") or ""),
                    "total_spent": float(r.get("total_spent", 0)),
                }
            # Resource purchases
            rows = supabase_select("economy_resource_purchases", order="created_at.desc", limit=100)
            self._memory["resource_purchases"] = [
                {
                    "resource_type": r.get("resource_type"),
                    "quantity": r.get("quantity", 0),
                    "total_cost": float(r.get("total_cost", 0)),
                    "vendor": r.get("vendor"),
                    "status": r.get("status"),
                    "timestamp": (r.get("created_at") or ""),
                }
                for r in rows
            ]
            # Incentives
            rows = supabase_select("economy_incentives", order="created_at.desc", limit=100)
            self._memory["incentives"] = [
                {
                    "agent_id": r.get("agent_id"),
                    "type": r.get("incentive_type"),
                    "value": float(r.get("value", 0)),
                    "duration_days": r.get("duration_days", 30),
                    "description": r.get("description"),
                    "status": r.get("status"),
                    "created_at": (r.get("created_at") or ""),
                }
                for r in rows
            ]
            # Pricing tiers from DB or keep defaults
            rows = supabase_select("economy_pricing_tiers", limit=20)
            if rows:
                for r in rows:
                    tier = r.get("tier", "")
                    feats = r.get("features") or []
                    if isinstance(feats, str):
                        feats = []
                    self._memory["pricing_tiers"][tier] = {
                        "price_per_request": float(r.get("price_per_request", 0)),
                        "daily_limit": r.get("daily_limit", 0),
                        "features": feats,
                    }
        except Exception as e:
            logger.debug("economy_store load from Supabase failed: %s", e)
        self._loaded = True

    def get_state(self) -> Dict[str, Any]:
        """Return full economy state. Loads from Supabase on first call if available."""
        self._load_from_supabase()
        return self._memory

    def get_revenue_period_totals(self) -> Dict[str, Any]:
        """
        Sum completed transaction amounts into daily / weekly / monthly buckets (UTC).

        Returns keys: daily_revenue, weekly_revenue, monthly_revenue, period_metrics_available.
        period_metrics_available is True when there are no completed transactions, or when
        every completed transaction has a parseable timestamp. Otherwise False (period sums may
        omit amounts from rows with bad/missing timestamps).
        """
        self._load_from_supabase()
        txs = self._memory.get("transactions") or []
        completed = [t for t in txs if (t.get("status") or "").lower() == "completed"]

        if not completed:
            return {
                "daily_revenue": 0.0,
                "weekly_revenue": 0.0,
                "monthly_revenue": 0.0,
                "period_metrics_available": True,
            }

        parsed: List[tuple[float, datetime]] = []
        missing_ts = 0
        for t in completed:
            amt = float(t.get("amount", 0))
            dt = _parse_iso(t.get("timestamp"))
            if dt is None:
                missing_ts += 1
                continue
            parsed.append((amt, dt))

        if missing_ts == len(completed):
            return {
                "daily_revenue": 0.0,
                "weekly_revenue": 0.0,
                "monthly_revenue": 0.0,
                "period_metrics_available": False,
            }

        now = datetime.now(timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = day_start - timedelta(days=day_start.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        daily = weekly = monthly = 0.0
        for amt, dt in parsed:
            if dt >= day_start:
                daily += amt
            if dt >= week_start:
                weekly += amt
            if dt >= month_start:
                monthly += amt

        period_ok = missing_ts == 0
        return {
            "daily_revenue": daily,
            "weekly_revenue": weekly,
            "monthly_revenue": monthly,
            "period_metrics_available": period_ok,
        }

    def record_charge(
        self,
        transaction_id: str,
        client_id: str,
        amount: float,
        currency: str,
        service_type: str,
    ) -> None:
        """Record a charge and update revenue + wallet."""
        self._load_from_supabase()
        ts = datetime.now(timezone.utc).isoformat()
        tx = {
            "id": transaction_id,
            "client_id": client_id,
            "amount": amount,
            "currency": currency,
            "service_type": service_type,
            "status": "completed",
            "timestamp": ts,
        }
        self._memory["transactions"].append(tx)
        self._memory["total_revenue"] += amount
        wallet_map = {"SOL": "solana", "BTC": "bitcoin", "X401": "x401"}
        wallet_key = wallet_map.get(currency.upper(), "solana")
        if wallet_key in self._memory["wallets"]:
            self._memory["wallets"][wallet_key]["balance"] += amount
        if supabase_available():
            try:
                supabase_insert("economy_transactions", {
                    "transaction_id": transaction_id,
                    "client_id": client_id,
                    "amount": amount,
                    "currency": currency,
                    "service_type": service_type,
                    "status": "completed",
                    "metadata": {},
                })
                supabase_upsert("economy_wallets", {
                    "wallet_type": wallet_key,
                    "address": self._memory["wallets"][wallet_key]["address"],
                    "balance": self._memory["wallets"][wallet_key]["balance"],
                    "currency": self._memory["wallets"][wallet_key]["currency"],
                }, on_conflict="wallet_type")
            except Exception as e:
                logger.debug("economy_store record_charge persist failed: %s", e)

    def register_client(self, client_id: str, client_type: str = "agent", tier: str = "agent") -> None:
        """Register a client."""
        self._load_from_supabase()
        self._memory["active_clients"][client_id] = {
            "type": client_type,
            "tier": tier,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "total_spent": 0.0,
        }
        if supabase_available():
            try:
                supabase_upsert("economy_clients", {
                    "client_id": client_id,
                    "client_type": client_type,
                    "tier": tier,
                    "total_spent": 0,
                }, on_conflict="client_id")
            except Exception as e:
                logger.debug("economy_store register_client persist failed: %s", e)

    def add_resource_purchase(
        self,
        resource_type: str,
        quantity: int,
        total_cost: float,
        vendor: str,
        status: str = "pending",
    ) -> None:
        """Add a resource purchase."""
        self._load_from_supabase()
        ts = datetime.now(timezone.utc).isoformat()
        self._memory["resource_purchases"].append({
            "resource_type": resource_type,
            "quantity": quantity,
            "total_cost": total_cost,
            "vendor": vendor,
            "status": status,
            "timestamp": ts,
        })
        if supabase_available():
            try:
                supabase_insert("economy_resource_purchases", {
                    "resource_type": resource_type,
                    "quantity": quantity,
                    "total_cost": total_cost,
                    "vendor": vendor,
                    "status": status,
                })
            except Exception as e:
                logger.debug("economy_store add_resource_purchase persist failed: %s", e)

    def add_incentive(
        self,
        agent_id: str,
        incentive_type: str,
        value: float,
        duration_days: int = 30,
        description: str = "",
    ) -> None:
        """Add an incentive."""
        self._load_from_supabase()
        ts = datetime.now(timezone.utc).isoformat()
        self._memory["incentives"].append({
            "agent_id": agent_id,
            "type": incentive_type,
            "value": value,
            "duration_days": duration_days,
            "description": description,
            "status": "active",
            "created_at": ts,
        })
        if supabase_available():
            try:
                supabase_insert("economy_incentives", {
                    "agent_id": agent_id,
                    "incentive_type": incentive_type,
                    "value": value,
                    "duration_days": duration_days,
                    "description": description,
                    "status": "active",
                })
            except Exception as e:
                logger.debug("economy_store add_incentive persist failed: %s", e)

    def record_meter(
        self,
        usage_id: str,
        client_id: str,
        service_type: str,
        units: float,
        unit_price: float,
        currency: str = "X401",
        status: str = "metered",
    ) -> None:
        """Record usage for x402-style request metering."""
        self._load_from_supabase()
        amount = units * unit_price
        ts = datetime.now(timezone.utc).isoformat()
        rec = {
            "usage_id": usage_id,
            "client_id": client_id,
            "service_type": service_type,
            "units": units,
            "unit_price": unit_price,
            "amount": amount,
            "currency": currency,
            "status": status,
            "timestamp": ts,
        }
        if "meter_records" not in self._memory:
            self._memory["meter_records"] = []
        self._memory["meter_records"].append(rec)
        if supabase_available():
            try:
                supabase_insert("economy_meter_records", {
                    "usage_id": usage_id,
                    "client_id": client_id,
                    "service_type": service_type,
                    "units": units,
                    "unit_price": unit_price,
                    "amount": amount,
                    "currency": currency,
                    "status": status,
                })
            except Exception as e:
                logger.debug("economy_store record_meter persist failed: %s", e)

    def settle_metered(self, usage_id: str, transaction_id: str) -> bool:
        """Settle a metered usage into a charge. Returns True if settled."""
        self._load_from_supabase()
        records = self._memory.get("meter_records", [])
        for rec in records:
            if rec.get("usage_id") == usage_id and rec.get("status") == "metered":
                self.record_charge(
                    transaction_id=transaction_id,
                    client_id=rec["client_id"],
                    amount=rec["amount"],
                    currency=rec.get("currency", "X401"),
                    service_type=rec["service_type"],
                )
                rec["status"] = "settled"
                rec["transaction_id"] = transaction_id
                return True
        return False

    def can_authorize(
        self,
        client_id: str,
        service_type: str,
        estimated_amount: float,
        currency: str = "X401",
    ) -> Dict[str, Any]:
        """
        Check if client can pay for service (tier limits, balance).
        Returns {authorized, reason, tier, balance}.
        """
        self._load_from_supabase()
        client = self._memory.get("active_clients", {}).get(client_id)
        tier_name = (client or {}).get("tier", "agent")
        tiers = self._memory.get("pricing_tiers", {})
        tier = tiers.get(tier_name, tiers.get("agent", {}))
        daily_limit = float(tier.get("daily_limit", 1000))
        # Use x401 balance if available
        wallet = self._memory.get("wallets", {}).get("x401", {})
        balance = float(wallet.get("balance", 0))
        authorized = balance >= estimated_amount and daily_limit > 0
        return {
            "authorized": authorized,
            "reason": "ok" if authorized else ("insufficient_balance" if balance < estimated_amount else "tier_limit_exceeded"),
            "tier": tier_name,
            "balance": balance,
            "daily_limit": daily_limit,
            "estimated_amount": estimated_amount,
        }


economy_store = EconomyStore()
