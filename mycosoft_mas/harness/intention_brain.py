"""Persistent intention stack — goals, tasks, hypotheses (SQLite)."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

GoalStatus = Literal["pending", "active", "done", "blocked"]


@dataclass
class Goal:
    goal_id: str
    description: str
    status: GoalStatus


class IntentionBrain:
    """Stores goals and streams signals from NLM / Nemotron."""

    def __init__(self, db_path: str) -> None:
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _init_db(self) -> None:
        with self._connect() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS goals (
                  id TEXT PRIMARY KEY,
                  description TEXT NOT NULL,
                  status TEXT NOT NULL,
                  updated_ts REAL NOT NULL,
                  meta_json TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                  id TEXT PRIMARY KEY,
                  source TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  ts REAL NOT NULL
                )
                """
            )

    def update_goal(self, goal_id: str, status: GoalStatus) -> None:
        with self._connect() as c:
            c.execute(
                "UPDATE goals SET status = ?, updated_ts = ? WHERE id = ?",
                (status, time.time(), goal_id),
            )

    def add_goal(self, description: str, status: GoalStatus = "pending") -> str:
        gid = str(uuid.uuid4())
        with self._connect() as c:
            c.execute(
                "INSERT INTO goals (id, description, status, updated_ts, meta_json) VALUES (?,?,?,?,?)",
                (gid, description, status, time.time(), "{}"),
            )
        return gid

    def get_next_task(self) -> Goal | None:
        with self._connect() as c:
            row = c.execute(
                "SELECT id, description, status FROM goals WHERE status IN ('pending','active') ORDER BY updated_ts ASC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        return Goal(goal_id=row[0], description=row[1], status=row[2])  # type: ignore[arg-type]

    def ingest_signal(self, source: str, payload: dict[str, Any]) -> None:
        sid = str(uuid.uuid4())
        with self._connect() as c:
            c.execute(
                "INSERT INTO signals (id, source, payload_json, ts) VALUES (?,?,?,?)",
                (sid, source, json.dumps(payload), time.time()),
            )
        # Escalate if NLM anomaly score high
        if source == "nlm" and float(payload.get("anomaly_score", 0)) > 0.85:
            self.add_goal("Safety escalation: high NLM anomaly", status="active")
