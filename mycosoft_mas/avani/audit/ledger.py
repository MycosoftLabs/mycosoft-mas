"""Append-only AVANI audit ledger with Postgres primary storage and JSONL fallback."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from mycosoft_mas.integrations.mindex_client import MINDEXClient

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def canonical_json(data: Dict[str, Any]) -> str:
    """Serialize a ledger payload deterministically for hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=_json_default)


def compute_entry_hash(entry: Dict[str, Any]) -> str:
    """Compute the SHA-256 hash for an entry, excluding its own hash field."""
    payload = {k: v for k, v in entry.items() if k != "entry_hash"}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _coerce_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


@dataclass(frozen=True)
class AvaniAuditEntry:
    event_id: str
    timestamp: str
    event_kind: str
    source: str
    action_type: str
    decision: Dict[str, Any]
    season: str
    metadata: Dict[str, Any]
    prev_hash: str
    entry_hash: str
    sequence: Optional[int] = None
    storage: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_kind": self.event_kind,
            "source": self.source,
            "action_type": self.action_type,
            "decision": self.decision,
            "season": self.season,
            "metadata": self.metadata,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
            "storage": self.storage,
        }


@dataclass(frozen=True)
class AvaniLedgerVerification:
    valid: bool
    checked: int
    storage: str
    first_invalid_event_id: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "checked": self.checked,
            "storage": self.storage,
            "first_invalid_event_id": self.first_invalid_event_id,
            "reason": self.reason,
        }


class AvaniAuditLedger:
    """Governance-grade AVANI audit ledger.

    Postgres/MINDEX is primary. If the database is unavailable, entries are
    still appended to a local JSONL chain so governance never becomes unaudited.
    """

    def __init__(
        self,
        mindex_client: Optional[MINDEXClient] = None,
        fallback_dir: Optional[Path | str] = None,
    ) -> None:
        self._mindex = mindex_client or MINDEXClient()
        self._db_available: Optional[bool] = None
        self._fallback_dir = Path(
            fallback_dir
            or os.getenv("AVANI_AUDIT_LEDGER_DIR", "")
            or Path(__file__).resolve().parent / "ledger_data"
        )
        self._fallback_dir.mkdir(parents=True, exist_ok=True)
        self._fallback_lock = threading.Lock()

    @property
    def fallback_file(self) -> Path:
        date_str = _utc_now().strftime("%Y-%m-%d")
        return self._fallback_dir / f"avani_audit_{date_str}.jsonl"

    async def append(
        self,
        *,
        event_kind: str,
        source: str,
        action_type: str,
        decision: Dict[str, Any],
        season: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AvaniAuditEntry:
        entry_base = {
            "event_id": f"avani-{uuid.uuid4().hex}",
            "timestamp": _utc_now().isoformat(),
            "event_kind": event_kind,
            "source": source,
            "action_type": action_type,
            "decision": decision,
            "season": season,
            "metadata": metadata or {},
        }
        try:
            return await self._append_postgres(entry_base)
        except Exception as exc:
            self._db_available = False
            logger.warning("AVANI audit Postgres append failed; using JSONL fallback: %s", exc)
            return self._append_jsonl(entry_base)

    async def query(
        self,
        *,
        event_kind: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        try:
            rows = await self._query_postgres(event_kind=event_kind, since=since, limit=limit)
            self._db_available = True
            return [entry.to_dict() for entry in rows]
        except Exception as exc:
            self._db_available = False
            logger.warning("AVANI audit Postgres query failed; using JSONL fallback: %s", exc)
            return [entry.to_dict() for entry in self._query_jsonl(event_kind, since, limit)]

    async def stats(self) -> Dict[str, Any]:
        try:
            await self._ensure_table()
            pool = await self._mindex._get_db_pool()
            async with pool.acquire() as conn:
                total = int(await conn.fetchval("SELECT COUNT(*) FROM avani_audit_ledger") or 0)
                approved = int(
                    await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM avani_audit_ledger
                        WHERE COALESCE(decision->>'approved', '') = 'true'
                           OR decision->>'verdict' IN ('allow', 'allow_with_audit')
                        """
                    )
                    or 0
                )
                denied = int(
                    await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM avani_audit_ledger
                        WHERE COALESCE(decision->>'approved', '') = 'false'
                           OR decision->>'verdict' IN ('deny', 'pause', 'require_approval')
                        """
                    )
                    or 0
                )
                by_kind_rows = await conn.fetch(
                    """
                    SELECT event_kind, COUNT(*) AS count
                    FROM avani_audit_ledger
                    GROUP BY event_kind
                    """
                )
            self._db_available = True
            return {
                "storage": "postgres",
                "total_decisions": total,
                "approved": approved,
                "denied": denied,
                "approval_rate": approved / total if total else 0.0,
                "by_event_kind": {row["event_kind"]: int(row["count"]) for row in by_kind_rows},
            }
        except Exception as exc:
            self._db_available = False
            logger.warning("AVANI audit Postgres stats failed; using JSONL fallback: %s", exc)
            entries = self._query_jsonl(None, None, 100000)
            total = len(entries)
            approved = sum(
                1
                for e in entries
                if e.decision.get("approved") is True
                or e.decision.get("verdict") in ("allow", "allow_with_audit")
            )
            denied = sum(
                1
                for e in entries
                if e.decision.get("approved") is False
                or e.decision.get("verdict") in ("deny", "pause", "require_approval")
            )
            by_kind: Dict[str, int] = {}
            for entry in entries:
                by_kind[entry.event_kind] = by_kind.get(entry.event_kind, 0) + 1
            return {
                "storage": "jsonl_fallback",
                "total_decisions": total,
                "approved": approved,
                "denied": denied,
                "approval_rate": approved / total if total else 0.0,
                "by_event_kind": by_kind,
            }

    async def verify(self, limit: int = 10000) -> AvaniLedgerVerification:
        try:
            rows = await self._query_postgres(event_kind=None, since=None, limit=limit, ascending=True)
            storage = "postgres"
        except Exception:
            rows = self._query_jsonl(None, None, limit, ascending=True)
            storage = "jsonl_fallback"
        return self._verify_entries(rows, storage=storage)

    async def _ensure_table(self) -> None:
        pool = await self._mindex._get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS avani_audit_ledger (
                    sequence BIGSERIAL PRIMARY KEY,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    event_kind TEXT NOT NULL,
                    source TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    decision JSONB NOT NULL DEFAULT '{}',
                    season TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}',
                    prev_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL
                );
                """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_avani_audit_kind_ts "
                "ON avani_audit_ledger(event_kind, timestamp DESC);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_avani_audit_ts "
                "ON avani_audit_ledger(timestamp DESC);"
            )

    async def _append_postgres(self, entry_base: Dict[str, Any]) -> AvaniAuditEntry:
        await self._ensure_table()
        pool = await self._mindex._get_db_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock($1)", 2682641)
                prev_hash = await conn.fetchval(
                    "SELECT entry_hash FROM avani_audit_ledger ORDER BY sequence DESC LIMIT 1"
                )
                entry = {**entry_base, "prev_hash": prev_hash or GENESIS_HASH}
                entry["entry_hash"] = compute_entry_hash(entry)
                row = await conn.fetchrow(
                    """
                    INSERT INTO avani_audit_ledger (
                        event_id, timestamp, event_kind, source, action_type,
                        decision, season, metadata, prev_hash, entry_hash
                    )
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8::jsonb, $9, $10)
                    RETURNING *
                    """,
                    entry["event_id"],
                    datetime.fromisoformat(entry["timestamp"]),
                    entry["event_kind"],
                    entry["source"],
                    entry["action_type"],
                    json.dumps(entry["decision"], default=_json_default),
                    entry["season"],
                    json.dumps(entry["metadata"], default=_json_default),
                    entry["prev_hash"],
                    entry["entry_hash"],
                )
        self._db_available = True
        return self._row_to_entry(row, storage="postgres")

    async def _query_postgres(
        self,
        *,
        event_kind: Optional[str],
        since: Optional[str],
        limit: int,
        ascending: bool = False,
    ) -> List[AvaniAuditEntry]:
        await self._ensure_table()
        pool = await self._mindex._get_db_pool()
        conditions: List[str] = []
        params: List[Any] = []
        if event_kind:
            params.append(event_kind)
            conditions.append(f"event_kind = ${len(params)}")
        if since:
            params.append(datetime.fromisoformat(since.replace("Z", "+00:00")))
            conditions.append(f"timestamp >= ${len(params)}")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        order = "ASC" if ascending else "DESC"
        params.append(limit)
        query = f"""
            SELECT *
            FROM avani_audit_ledger
            {where}
            ORDER BY sequence {order}
            LIMIT ${len(params)}
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [self._row_to_entry(row, storage="postgres") for row in rows]

    def _append_jsonl(self, entry_base: Dict[str, Any]) -> AvaniAuditEntry:
        with self._fallback_lock:
            entries = self._query_jsonl(None, None, 100000, ascending=True)
            prev_hash = entries[-1].entry_hash if entries else GENESIS_HASH
            sequence = (entries[-1].sequence or 0) + 1 if entries else 1
            entry = {**entry_base, "sequence": sequence, "prev_hash": prev_hash}
            entry["entry_hash"] = compute_entry_hash(entry)
            audit_entry = self._dict_to_entry(entry, storage="jsonl_fallback")
            with self.fallback_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(audit_entry.to_dict(), default=_json_default) + "\n")
            return audit_entry

    def _query_jsonl(
        self,
        event_kind: Optional[str],
        since: Optional[str],
        limit: int,
        ascending: bool = False,
    ) -> List[AvaniAuditEntry]:
        entries: List[AvaniAuditEntry] = []
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None
        for path in sorted(self._fallback_dir.glob("avani_audit_*.jsonl")):
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    entry = self._dict_to_entry(raw, storage="jsonl_fallback")
                    if event_kind and entry.event_kind != event_kind:
                        continue
                    if since_dt and datetime.fromisoformat(entry.timestamp) < since_dt:
                        continue
                    entries.append(entry)
        entries.sort(key=lambda e: (e.sequence or 0, e.timestamp), reverse=not ascending)
        return entries[: max(1, min(int(limit), 100000))]

    def _verify_entries(
        self, entries: Iterable[AvaniAuditEntry], *, storage: str
    ) -> AvaniLedgerVerification:
        expected_prev = GENESIS_HASH
        checked = 0
        for entry in entries:
            raw = entry.to_dict()
            raw.pop("storage", None)
            computed = compute_entry_hash(raw)
            if entry.prev_hash != expected_prev:
                return AvaniLedgerVerification(
                    valid=False,
                    checked=checked,
                    storage=storage,
                    first_invalid_event_id=entry.event_id,
                    reason="prev_hash_mismatch",
                )
            if computed != entry.entry_hash:
                return AvaniLedgerVerification(
                    valid=False,
                    checked=checked,
                    storage=storage,
                    first_invalid_event_id=entry.event_id,
                    reason="entry_hash_mismatch",
                )
            expected_prev = entry.entry_hash
            checked += 1
        return AvaniLedgerVerification(valid=True, checked=checked, storage=storage)

    def _row_to_entry(self, row: Any, *, storage: str) -> AvaniAuditEntry:
        return AvaniAuditEntry(
            sequence=int(row["sequence"]),
            event_id=row["event_id"],
            timestamp=row["timestamp"].astimezone(timezone.utc).isoformat(),
            event_kind=row["event_kind"],
            source=row["source"],
            action_type=row["action_type"],
            decision=_coerce_json(row["decision"]) or {},
            season=row["season"],
            metadata=_coerce_json(row["metadata"]) or {},
            prev_hash=row["prev_hash"],
            entry_hash=row["entry_hash"],
            storage=storage,
        )

    def _dict_to_entry(self, raw: Dict[str, Any], *, storage: str) -> AvaniAuditEntry:
        return AvaniAuditEntry(
            sequence=raw.get("sequence"),
            event_id=raw["event_id"],
            timestamp=raw["timestamp"],
            event_kind=raw["event_kind"],
            source=raw["source"],
            action_type=raw["action_type"],
            decision=_coerce_json(raw.get("decision")) or {},
            season=raw.get("season", "unknown"),
            metadata=_coerce_json(raw.get("metadata")) or {},
            prev_hash=raw["prev_hash"],
            entry_hash=raw["entry_hash"],
            storage=storage,
        )


_default_ledger: Optional[AvaniAuditLedger] = None


def get_audit_ledger() -> AvaniAuditLedger:
    global _default_ledger
    if _default_ledger is None:
        _default_ledger = AvaniAuditLedger()
    return _default_ledger
