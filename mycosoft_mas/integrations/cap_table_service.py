"""
Cap table persistence service.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import asyncpg
except Exception:  # pragma: no cover
    asyncpg = None


class CapTableService:
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = (
            database_url
            or os.getenv("DATABASE_URL")
            or os.getenv("MINDEX_DATABASE_URL")
        )
        self._pool: Optional["asyncpg.Pool"] = None

    async def initialize(self) -> None:
        if self._pool or not self._database_url:
            return
        if asyncpg is None:
            raise RuntimeError("asyncpg is required for cap table service")
        self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=4)
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE SCHEMA IF NOT EXISTS mindex;")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mindex.cap_table_entries (
                    id TEXT PRIMARY KEY,
                    stakeholder_id TEXT,
                    stakeholder_name TEXT NOT NULL,
                    instrument_type TEXT NOT NULL,
                    amount NUMERIC NOT NULL DEFAULT 0,
                    valuation_cap NUMERIC,
                    discount NUMERIC,
                    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    effective_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_cap_table_stakeholder
                    ON mindex.cap_table_entries (stakeholder_id);
                CREATE INDEX IF NOT EXISTS idx_cap_table_effective_at
                    ON mindex.cap_table_entries (effective_at DESC);
                """
            )

    async def record_safe_investment(self, agreement: Dict[str, Any]) -> str:
        await self.initialize()
        if not self._pool:
            raise RuntimeError("Cap table service unavailable")

        entry_id = f"cap-{agreement['agreement_id']}"
        effective_at = agreement.get("issue_date")
        try:
            effective_dt = datetime.fromisoformat(effective_at)
        except Exception:
            effective_dt = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.cap_table_entries (
                    id, stakeholder_id, stakeholder_name, instrument_type, amount,
                    valuation_cap, discount, metadata_json, effective_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
                ON CONFLICT (id) DO UPDATE SET
                    amount = EXCLUDED.amount,
                    valuation_cap = EXCLUDED.valuation_cap,
                    discount = EXCLUDED.discount,
                    metadata_json = EXCLUDED.metadata_json,
                    effective_at = EXCLUDED.effective_at
                """,
                entry_id,
                agreement.get("investor_id"),
                agreement.get("investor", "unknown"),
                "SAFE",
                agreement.get("amount", 0),
                agreement.get("valuation_cap"),
                agreement.get("discount"),
                json.dumps(agreement),
                effective_dt,
            )
        return entry_id
