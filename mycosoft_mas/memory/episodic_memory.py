"""
Episodic Memory Persistence for MYCA.
Created: February 28, 2026

Persists episodic events in PostgreSQL and supports similarity recall
plus consolidation into semantic memory.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger("EpisodicMemoryPersistent")


@dataclass
class Episode:
    """A persisted episodic event."""

    id: UUID
    timestamp: datetime
    context: Dict[str, Any]
    actions: List[Dict[str, Any]]
    outcome: str
    embedding: Optional[List[float]]
    consolidated_at: Optional[datetime]


class EpisodicMemory:
    """PostgreSQL-backed episodic memory store."""

    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv("MINDEX_DATABASE_URL")
        if not self._database_url:
            raise ValueError("MINDEX_DATABASE_URL is required for EpisodicMemory.")
        self._pool = None

    async def initialize(self) -> None:
        """Initialize DB connection and ensure episodic schema exists."""
        if self._pool:
            return
        try:
            import asyncpg
        except Exception as e:
            raise RuntimeError("asyncpg is required for EpisodicMemory") from e

        self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mindex.episodic_events (
                    id UUID PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    context_json JSONB NOT NULL,
                    actions_json JSONB NOT NULL,
                    outcome TEXT NOT NULL,
                    embedding_json JSONB NULL,
                    consolidated_at TIMESTAMPTZ NULL
                );
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_episodic_timestamp
                ON mindex.episodic_events (timestamp DESC);
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_episodic_consolidated
                ON mindex.episodic_events (consolidated_at);
                """
            )
        logger.info("EpisodicMemory initialized")

    async def record_episode(
        self,
        context: Dict[str, Any],
        actions: List[Dict[str, Any]],
        outcome: str,
    ) -> Episode:
        """Persist one episode and return the stored object."""
        if not self._pool:
            await self.initialize()

        episode_id = uuid4()
        now = datetime.now(timezone.utc)
        embedding = await self._compute_embedding(context=context, actions=actions, outcome=outcome)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.episodic_events (
                    id, timestamp, context_json, actions_json, outcome, embedding_json
                ) VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6::jsonb);
                """,
                episode_id,
                now,
                json.dumps(context),
                json.dumps(actions),
                outcome,
                json.dumps(embedding) if embedding else None,
            )

        return Episode(
            id=episode_id,
            timestamp=now,
            context=context,
            actions=actions,
            outcome=outcome,
            embedding=embedding,
            consolidated_at=None,
        )

    async def recall_similar(self, context: Dict[str, Any], limit: int = 5) -> List[Episode]:
        """Recall similar episodes using embedding score + key overlap."""
        if not self._pool:
            await self.initialize()

        target_embedding = await self._compute_embedding(context=context, actions=[], outcome="")
        target_keys = set(context.keys())

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, timestamp, context_json, actions_json, outcome, embedding_json, consolidated_at
                FROM mindex.episodic_events
                ORDER BY timestamp DESC
                LIMIT 250;
                """
            )

        scored: List[tuple[float, Episode]] = []
        for row in rows:
            row_context = row["context_json"]
            if isinstance(row_context, str):
                row_context = json.loads(row_context)
            row_actions = row["actions_json"]
            if isinstance(row_actions, str):
                row_actions = json.loads(row_actions)
            row_embedding = row["embedding_json"]
            if isinstance(row_embedding, str):
                row_embedding = json.loads(row_embedding)

            key_overlap = 0.0
            if target_keys:
                key_overlap = len(target_keys.intersection(set((row_context or {}).keys()))) / max(
                    1, len(target_keys)
                )

            embedding_score = self._cosine_similarity(target_embedding, row_embedding)
            score = (embedding_score * 0.7) + (key_overlap * 0.3)

            scored.append(
                (
                    score,
                    Episode(
                        id=UUID(str(row["id"])),
                        timestamp=row["timestamp"],
                        context=row_context or {},
                        actions=row_actions or [],
                        outcome=row["outcome"] or "",
                        embedding=row_embedding,
                        consolidated_at=row["consolidated_at"],
                    ),
                )
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [episode for _, episode in scored[: max(1, limit)]]

    async def consolidate_to_semantic(self) -> int:
        """
        Consolidate unconsolidated episodes into semantic memory.

        Returns number of consolidated episodes.
        """
        if not self._pool:
            await self.initialize()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, context_json, actions_json, outcome, timestamp
                FROM mindex.episodic_events
                WHERE consolidated_at IS NULL
                ORDER BY timestamp ASC
                LIMIT 100;
                """
            )

        if not rows:
            return 0

        try:
            from mycosoft_mas.memory.myca_memory import MemoryLayer, get_myca_memory

            memory = await get_myca_memory()
        except Exception as e:
            logger.warning("Unable to consolidate episodic memory into semantic layer: %s", e)
            return 0

        consolidated_ids: List[UUID] = []
        for row in rows:
            row_context = row["context_json"]
            if isinstance(row_context, str):
                row_context = json.loads(row_context)
            row_actions = row["actions_json"]
            if isinstance(row_actions, str):
                row_actions = json.loads(row_actions)

            fact_text = self._episode_to_fact_text(
                context=row_context or {},
                actions=row_actions or [],
                outcome=row["outcome"] or "",
                timestamp=row["timestamp"],
            )
            await memory.remember(
                content={"text": fact_text, "source": "episodic_consolidation", "episode_id": str(row["id"])},
                layer=MemoryLayer.SEMANTIC,
                importance=0.75,
                tags=["episodic", "consolidated"],
            )
            consolidated_ids.append(UUID(str(row["id"])))

        async with self._pool.acquire() as conn:
            await conn.executemany(
                """
                UPDATE mindex.episodic_events
                SET consolidated_at = NOW()
                WHERE id = $1;
                """,
                [(episode_id,) for episode_id in consolidated_ids],
            )

        return len(consolidated_ids)

    async def _compute_embedding(
        self,
        *,
        context: Dict[str, Any],
        actions: List[Dict[str, Any]],
        outcome: str,
    ) -> Optional[List[float]]:
        text = self._episode_to_fact_text(
            context=context,
            actions=actions,
            outcome=outcome,
            timestamp=datetime.now(timezone.utc),
        )
        try:
            from mycosoft_mas.memory.embeddings import get_embedder

            embedder = get_embedder(os.getenv("EMBEDDER_PROVIDER", "openai"))
            return await embedder.embed_text(text)
        except Exception:
            return None

    def _episode_to_fact_text(
        self,
        *,
        context: Dict[str, Any],
        actions: List[Dict[str, Any]],
        outcome: str,
        timestamp: datetime,
    ) -> str:
        action_summaries = []
        for action in actions[:10]:
            if isinstance(action, dict):
                action_summaries.append(
                    action.get("type") or action.get("name") or action.get("action") or str(action)
                )
            else:
                action_summaries.append(str(action))
        return (
            f"Episode at {timestamp.isoformat()} | "
            f"context={json.dumps(context, sort_keys=True)} | "
            f"actions={action_summaries} | "
            f"outcome={outcome}"
        )

    def _cosine_similarity(self, v1: Optional[List[float]], v2: Optional[List[float]]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
