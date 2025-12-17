import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VoiceFeedback:
    feedback_id: str
    created_at: str
    conversation_id: str | None
    agent_name: str | None
    transcript: str | None
    response_text: str | None
    rating: int | None
    success: bool | None
    notes: str | None


class VoiceFeedbackStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS voice_feedback (
                      feedback_id TEXT PRIMARY KEY,
                      created_at TEXT NOT NULL,
                      conversation_id TEXT NULL,
                      agent_name TEXT NULL,
                      transcript TEXT NULL,
                      response_text TEXT NULL,
                      rating INTEGER NULL,
                      success INTEGER NULL,
                      notes TEXT NULL
                    );
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_voice_feedback_created_at ON voice_feedback(created_at);"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_voice_feedback_conversation_id ON voice_feedback(conversation_id);"
                )

    def add_feedback(
        self,
        *,
        conversation_id: str | None,
        agent_name: str | None,
        transcript: str | None,
        response_text: str | None,
        rating: int | None,
        success: bool | None,
        notes: str | None,
    ) -> VoiceFeedback:
        feedback_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        rating_norm = None
        if rating is not None:
            rating_norm = max(1, min(5, int(rating)))

        success_int = None
        if success is not None:
            success_int = 1 if bool(success) else 0

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO voice_feedback (
                      feedback_id, created_at, conversation_id, agent_name,
                      transcript, response_text, rating, success, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        feedback_id,
                        created_at,
                        conversation_id,
                        agent_name,
                        transcript,
                        response_text,
                        rating_norm,
                        success_int,
                        notes,
                    ),
                )

        return VoiceFeedback(
            feedback_id=feedback_id,
            created_at=created_at,
            conversation_id=conversation_id,
            agent_name=agent_name,
            transcript=transcript,
            response_text=response_text,
            rating=rating_norm,
            success=success,
            notes=notes,
        )

    def list_recent(self, *, limit: int = 25) -> list[VoiceFeedback]:
        limit = max(1, min(200, int(limit)))
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM voice_feedback
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        results: list[VoiceFeedback] = []
        for r in rows:
            results.append(
                VoiceFeedback(
                    feedback_id=str(r["feedback_id"]),
                    created_at=str(r["created_at"]),
                    conversation_id=r["conversation_id"],
                    agent_name=r["agent_name"],
                    transcript=r["transcript"],
                    response_text=r["response_text"],
                    rating=r["rating"],
                    success=(None if r["success"] is None else bool(r["success"])),
                    notes=r["notes"],
                )
            )
        return results

    def summary(self) -> dict[str, Any]:
        with self._lock:
            with self._connect() as conn:
                total = conn.execute("SELECT COUNT(*) AS c FROM voice_feedback").fetchone()["c"]
                avg = conn.execute(
                    "SELECT AVG(rating) AS avg_rating FROM voice_feedback WHERE rating IS NOT NULL"
                ).fetchone()["avg_rating"]
                succ = conn.execute(
                    "SELECT AVG(success) AS avg_success FROM voice_feedback WHERE success IS NOT NULL"
                ).fetchone()["avg_success"]

        return {
            "total": int(total or 0),
            "avg_rating": (None if avg is None else float(avg)),
            "avg_success": (None if succ is None else float(succ)),
        }

    def prompt_hint(self, *, limit: int = 10) -> str:
        """Small, non-sensitive hint string for the orchestrator system prompt."""
        items = self.list_recent(limit=limit)
        rated = [i.rating for i in items if i.rating is not None]
        if not rated:
            return "No user feedback captured yet."
        avg = sum(rated) / len(rated)
        return f"Recent feedback: avg rating {avg:.2f}/5 across last {len(rated)} rated interactions." 
