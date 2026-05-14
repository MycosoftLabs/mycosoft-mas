"""Persistent AVANI season state storage."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from mycosoft_mas.avani.audit.ledger import _coerce_json, _json_default
from mycosoft_mas.avani.season_engine.seasons import Season, SeasonMetrics, SeasonState
from mycosoft_mas.integrations.mindex_client import MINDEXClient

logger = logging.getLogger(__name__)


class AvaniSeasonStateStore:
    """Persist and restore AVANI's homeostatic season state."""

    def __init__(
        self,
        mindex_client: Optional[MINDEXClient] = None,
        fallback_dir: Optional[Path | str] = None,
    ) -> None:
        self._mindex = mindex_client or MINDEXClient()
        self._fallback_dir = Path(
            fallback_dir
            or os.getenv("AVANI_AUDIT_LEDGER_DIR", "")
            or Path(__file__).resolve().parent / "ledger_data"
        )
        self._fallback_dir.mkdir(parents=True, exist_ok=True)

    @property
    def fallback_file(self) -> Path:
        return self._fallback_dir / "avani_season_state.json"

    async def load(self) -> Optional[SeasonState]:
        try:
            row = await self._load_postgres()
            if row:
                return self._dict_to_state(row)
        except Exception as exc:
            logger.warning("AVANI season Postgres load failed; using JSON fallback: %s", exc)
        return self._load_json()

    async def save(self, state: SeasonState) -> str:
        payload = self._state_to_dict(state)
        try:
            await self._save_postgres(payload)
            return "postgres"
        except Exception as exc:
            logger.warning("AVANI season Postgres save failed; using JSON fallback: %s", exc)
            self._save_json(payload)
            return "json_fallback"

    async def _ensure_table(self) -> None:
        pool = await self._mindex._get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS avani_season_state (
                    singleton_id BOOLEAN PRIMARY KEY DEFAULT TRUE,
                    current TEXT NOT NULL,
                    entered_at TIMESTAMPTZ NOT NULL,
                    trigger_reason TEXT NOT NULL,
                    metrics JSONB NOT NULL DEFAULT '{}',
                    history JSONB NOT NULL DEFAULT '[]',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT avani_season_state_singleton CHECK (singleton_id)
                );
            """)

    async def _load_postgres(self) -> Optional[Dict[str, Any]]:
        await self._ensure_table()
        pool = await self._mindex._get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT current, entered_at, trigger_reason, metrics, history
                FROM avani_season_state
                WHERE singleton_id = TRUE
                """
            )
        return dict(row) if row else None

    async def _save_postgres(self, payload: Dict[str, Any]) -> None:
        await self._ensure_table()
        pool = await self._mindex._get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO avani_season_state (
                    singleton_id, current, entered_at, trigger_reason,
                    metrics, history, updated_at
                )
                VALUES (TRUE, $1, $2, $3, $4::jsonb, $5::jsonb, $6)
                ON CONFLICT (singleton_id) DO UPDATE SET
                    current = EXCLUDED.current,
                    entered_at = EXCLUDED.entered_at,
                    trigger_reason = EXCLUDED.trigger_reason,
                    metrics = EXCLUDED.metrics,
                    history = EXCLUDED.history,
                    updated_at = EXCLUDED.updated_at
                """,
                payload["current"],
                datetime.fromisoformat(payload["entered_at"]),
                payload["trigger_reason"],
                json.dumps(payload["metrics"], default=_json_default),
                json.dumps(payload["history"], default=_json_default),
                datetime.now(timezone.utc),
            )

    def _load_json(self) -> Optional[SeasonState]:
        if not self.fallback_file.exists():
            return None
        try:
            return self._dict_to_state(json.loads(self.fallback_file.read_text(encoding="utf-8")))
        except Exception as exc:
            logger.warning("AVANI season JSON fallback load failed: %s", exc)
            return None

    def _save_json(self, payload: Dict[str, Any]) -> None:
        self.fallback_file.write_text(
            json.dumps(payload, sort_keys=True, default=_json_default), encoding="utf-8"
        )

    def _state_to_dict(self, state: SeasonState) -> Dict[str, Any]:
        metrics = state.metrics
        return {
            "current": state.current.value,
            "entered_at": state.entered_at.astimezone(timezone.utc).isoformat(),
            "trigger_reason": state.trigger_reason,
            "metrics": {
                "eco_stability": metrics.eco_stability,
                "founder_latency_hours": metrics.founder_latency_hours,
                "toxicity_detected": metrics.toxicity_detected,
                "critical_error": metrics.critical_error,
                "red_line_violated": metrics.red_line_violated,
                "all_systems_green": metrics.all_systems_green,
            },
            "history": state.history,
        }

    def _dict_to_state(self, raw: Dict[str, Any]) -> SeasonState:
        metrics_raw = _coerce_json(raw.get("metrics")) or {}
        history = _coerce_json(raw.get("history")) or []
        entered_at = raw.get("entered_at")
        if isinstance(entered_at, datetime):
            entered_dt = entered_at.astimezone(timezone.utc)
        else:
            entered_dt = datetime.fromisoformat(str(entered_at).replace("Z", "+00:00"))
        return SeasonState(
            current=Season(str(raw["current"])),
            entered_at=entered_dt,
            trigger_reason=str(raw.get("trigger_reason") or "restored"),
            metrics=SeasonMetrics(
                eco_stability=float(metrics_raw.get("eco_stability", 1.0)),
                founder_latency_hours=float(metrics_raw.get("founder_latency_hours", 0.0)),
                toxicity_detected=bool(metrics_raw.get("toxicity_detected", False)),
                critical_error=bool(metrics_raw.get("critical_error", False)),
                red_line_violated=bool(metrics_raw.get("red_line_violated", False)),
                all_systems_green=bool(metrics_raw.get("all_systems_green", True)),
            ),
            history=list(history),
        )
