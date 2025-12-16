from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import Json
from prometheus_client import Counter

from .models import ToolAction


@dataclass
class ApprovalPolicy:
    """Simple approval policy that can be driven by configuration."""

    approval_required: bool = False
    guarded_categories: tuple[str, ...] = ("external_write", "system_change")

    def requires_approval(self, action: ToolAction) -> bool:
        if not self.approval_required:
            return False
        return action.category in self.guarded_categories


class ActionAuditLogger:
    ACTION_COUNTER = Counter("tool_action_events_total", "Tool action audit events", ["status", "category"])

    def __init__(self, database_url: Optional[str], policy: ApprovalPolicy):
        self.database_url = database_url
        self.policy = policy

    async def ensure_table(self) -> None:
        if not self.database_url:
            return
        await asyncio.to_thread(self._ensure_table_sync)

    async def record(
        self,
        action: ToolAction,
        *,
        status: str,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        if not self.database_url:
            return
        await asyncio.to_thread(
            self._record_sync,
            action,
            status,
            output or {},
            error,
            request_id,
        )

    def _ensure_table_sync(self) -> None:
        conn = psycopg2.connect(self.database_url)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS action_audit_log (
                id SERIAL PRIMARY KEY,
                action_type TEXT NOT NULL,
                category TEXT NOT NULL,
                actor TEXT,
                agent_id TEXT,
                run_id TEXT,
                request_id TEXT,
                inputs JSONB,
                metadata JSONB,
                output JSONB,
                status TEXT NOT NULL,
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT now()
            );
            """
        )
        cur.close()
        conn.close()

    def _record_sync(
        self,
        action: ToolAction,
        status: str,
        output: Dict[str, Any],
        error: Optional[str],
        request_id: Optional[str],
    ) -> None:
        conn = psycopg2.connect(self.database_url)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO action_audit_log (
                action_type, category, actor, agent_id, run_id, request_id,
                inputs, metadata, output, status, error
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                action.action,
                action.category,
                action.actor,
                action.agent_id,
                action.run_id,
                request_id,
                Json(action.redacted_inputs()),
                Json(action.metadata),
                Json(output),
                status,
                error,
            ),
        )
        cur.close()
        conn.close()
        try:
            self.ACTION_COUNTER.labels(status=status, category=action.category).inc()
        except Exception:
            # Metrics should never crash the flow
            pass
