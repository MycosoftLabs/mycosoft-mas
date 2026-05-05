"""Base harness agent for Agent100 — Worldview smoke + treasury debits."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Any

from mycosoft_mas.agent100.treasury import debit
from mycosoft_mas.agent100.types import AgentRow, CallRecord
from mycosoft_mas.agent100.worldview_client import WorldviewClient


class BaseAgent100(ABC):
    """One internal paying persona: optional Worldview ping + archetype-specific work."""

    def __init__(self, row: AgentRow) -> None:
        self.row = row
        key = os.environ.get(row.api_key_env, "") if row.api_key_env else ""
        self._wv = WorldviewClient(api_key=key or None)

    def close(self) -> None:
        self._wv.close()

    @abstractmethod
    def run_cycle(self, mode: str) -> list[CallRecord]:
        """Execute one validation cycle for this agent."""

    def ping_worldview_health(self) -> CallRecord:
        status, body, ms = self._wv.health()
        err = None if status == 200 else f"http_{status}"
        return CallRecord(
            agent_id=self.row.id,
            archetype=self.row.archetype,
            framework=self.row.framework,
            dataset_id=None,
            mode="health",
            request_path="/api/worldview/v1/health",
            status_code=status,
            latency_ms=int(ms),
            cache=None,
            cost_debited=None,
            rate_weight=None,
            bytes=None,
            schema_valid=isinstance(body, dict) if body is not None else None,
            freshness_ok=True if status == 200 else False,
            error_class=err,
            request_id=None,
            envelope_ok=True if status == 200 else False,
        )

    def maybe_debit(self, amount_cents: int, ref: str, meta: dict[str, Any] | None = None) -> bool:
        return debit(self.row.id, amount_cents, ref, meta)

    def sleep_paced(self, min_interval_s: float = 2.0) -> None:
        time.sleep(min_interval_s)
