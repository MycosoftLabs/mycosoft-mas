"""
MINDEX Bridge — Connection to all databases on VM 189.

MINDEX (189) is the sole data layer for the entire Mycosoft system:
- PostgreSQL (5432) — persistent memory, knowledge graph, agent state
- Redis (6379) — session memory, pub/sub, A2A messaging, caching
- Qdrant (6333) — vector embeddings, semantic search
- MINDEX API (8000) — species database, taxonomy, compounds

This bridge provides MYCA OS with memory, knowledge, and state persistence.

Date: 2026-03-04
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import aiohttp

logger = logging.getLogger("myca.os.mindex_bridge")


class MINDEXBridge:
    """Bridge to MINDEX databases on VM 189."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._mindex_api = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
        self._redis_url = os.getenv("MINDEX_REDIS_URL", "redis://192.168.0.189:6379")
        self._pg_host = os.getenv("MINDEX_PG_HOST", "192.168.0.189")
        self._pg_port = int(os.getenv("MINDEX_PG_PORT", "5432"))
        self._qdrant_url = os.getenv("QDRANT_URL", "http://192.168.0.189:6333")

        self._redis = None
        self._pg_pool = None

    async def initialize(self):
        self._session = aiohttp.ClientSession()

        # Try MINDEX API
        health = await self.health_check()
        if health.get("healthy"):
            logger.info(f"MINDEX Bridge connected to {self._mindex_api}")
        else:
            logger.warning(f"MINDEX API not reachable at {self._mindex_api}")

        # Try Redis
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self._redis = None

        # Try PostgreSQL
        try:
            import asyncpg

            self._pg_pool = await asyncpg.create_pool(
                host=self._pg_host,
                port=self._pg_port,
                user=os.getenv("MINDEX_PG_USER", "mycosoft"),
                password=os.getenv("MINDEX_PG_PASSWORD", ""),
                database=os.getenv("MINDEX_PG_DB", "mycosoft_mas"),
                min_size=1,
                max_size=5,
            )
            logger.info("PostgreSQL connected")
        except Exception as e:
            logger.warning(f"PostgreSQL not available: {e}")
            self._pg_pool = None

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()
        if self._redis:
            await self._redis.close()
        if self._pg_pool:
            await self._pg_pool.close()

    async def health_check(self) -> dict:
        """Check MINDEX services health.

        Primary gate: MINDEX API must be reachable (http://189:8000).
        Redis, Postgres, Qdrant are optional — they live inside VM 189's
        Docker network and may not be reachable from MYCA (e.g. on VM 191).
        If the API is up, MINDEX is considered healthy for MYCA's purposes.
        """
        checks = {}

        # MINDEX API — primary interface, must be reachable from MYCA VM
        if self._session and not self._session.closed:
            try:
                async with self._session.get(
                    f"{self._mindex_api.rstrip('/')}/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    checks["api"] = resp.status == 200
            except Exception:
                checks["api"] = False
        else:
            checks["api"] = False

        # Redis — optional; often not exposed cross-VM
        if self._redis:
            try:
                await self._redis.ping()
                checks["redis"] = True
            except Exception:
                checks["redis"] = False
        else:
            checks["redis"] = False

        # PostgreSQL — optional; often not exposed cross-VM
        if self._pg_pool:
            try:
                async with self._pg_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                checks["postgres"] = True
            except Exception:
                checks["postgres"] = False
        else:
            checks["postgres"] = False

        # Qdrant — optional; often not exposed cross-VM
        if self._session and not self._session.closed:
            try:
                async with self._session.get(
                    f"{self._qdrant_url.rstrip('/')}/healthz",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    checks["qdrant"] = resp.status == 200
            except Exception:
                checks["qdrant"] = False
        else:
            checks["qdrant"] = False

        # Healthy if MINDEX API is reachable (primary interface for MYCA)
        checks["healthy"] = checks.get("api", False)
        return checks

    # ── Memory Operations ────────────────────────────────────────

    async def remember(self, key: str, value: str, ttl: int = None, layer: str = "working"):
        """Store a memory in the appropriate layer."""
        if self._redis and layer in ("ephemeral", "session", "working"):
            ttl_map = {"ephemeral": 1800, "session": 86400, "working": 604800}
            effective_ttl = ttl or ttl_map.get(layer, 604800)
            await self._redis.setex(f"myca:memory:{layer}:{key}", effective_ttl, value)
        elif self._pg_pool and layer in ("semantic", "episodic", "system"):
            async with self._pg_pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO agent_memory (agent_id, memory_key, memory_value, memory_layer, created_at)
                       VALUES ($1, $2, $3, $4, $5)
                       ON CONFLICT (agent_id, memory_key, memory_layer)
                       DO UPDATE SET memory_value = EXCLUDED.memory_value""",
                    "myca_os",
                    key,
                    value,
                    layer,
                    datetime.now(timezone.utc),
                )

    async def recall(self, key: str, layer: str = None) -> Optional[str]:
        """Recall a memory by key, searching layers if not specified."""
        if layer:
            return await self._recall_from_layer(key, layer)

        # Search all layers, most recent first
        for l in ["ephemeral", "session", "working", "semantic", "episodic", "system"]:
            result = await self._recall_from_layer(key, l)
            if result:
                return result
        return None

    async def _recall_from_layer(self, key: str, layer: str) -> Optional[str]:
        if layer in ("ephemeral", "session", "working") and self._redis:
            return await self._redis.get(f"myca:memory:{layer}:{key}")
        elif layer in ("semantic", "episodic", "system") and self._pg_pool:
            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT memory_value FROM agent_memory WHERE agent_id = $1 AND memory_key = $2 AND memory_layer = $3",
                    "myca_os",
                    key,
                    layer,
                )
                return row["memory_value"] if row else None
        return None

    async def learn_fact(self, fact: str, category: str = "general", confidence: float = 1.0):
        """Store a learned fact in semantic memory."""
        await self.remember(
            f"fact:{category}:{hash(fact) % 100000}",
            json.dumps(
                {
                    "fact": fact,
                    "category": category,
                    "confidence": confidence,
                    "learned_at": datetime.now(timezone.utc).isoformat(),
                }
            ),
            layer="semantic",
        )

    # ── Experience Packets (Grounded Cognition) ────────────────────

    async def store_experience_packet(
        self,
        task: dict,
        result: dict,
        session_id: str = "e2e-demo",
        user_id: Optional[str] = None,
    ) -> Optional[str]:
        """Store a deployment experience packet to MINDEX for grounded cognition.

        Used by e2e demo: Discord -> deploy -> confirm -> EP logged.
        Soft-fail: returns None on error, EP id on success.
        """
        import uuid

        if not self._session or self._session.closed:
            return None
        ep_id = str(uuid.uuid4())
        user_id = user_id or task.get("source", "morgan")
        body = {
            "id": ep_id,
            "session_id": session_id,
            "user_id": user_id,
            "ground_truth": {
                "task_type": task.get("type", "deployment"),
                "target": task.get("target", "website"),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "status": result.get("status", "completed"),
            },
            "observation": {
                "modality": "log",
                "raw_payload": json.dumps(
                    {
                        "task": {k: v for k, v in task.items() if k not in ("raw",)},
                        "result": result,
                    }
                ),
            },
            "self_state": {},
            "world_state": {},
            "uncertainty": {},
            "provenance": {"source": "myca_os", "demo": "e2e-deploy"},
        }
        headers = {}
        api_key = os.getenv("MINDEX_API_KEY") or os.getenv("API_KEYS", "").split(",")[0].strip()
        if api_key:
            headers["X-API-Key"] = api_key
        try:
            async with self._session.post(
                f"{self._mindex_api.rstrip('/')}/api/mindex/grounding/experience-packets",
                json=body,
                headers=headers or None,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    logger.info(f"EP stored: {data.get('id', ep_id)}")
                    return data.get("id", ep_id)
                logger.warning(f"EP store failed: {resp.status} {await resp.text()}")
        except Exception as e:
            logger.warning(f"EP store failed: {e}")
        return None

    # ── Event Logging ────────────────────────────────────────────

    async def store_event(self, event: dict):
        """Store an event in the event ledger."""
        if self._pg_pool:
            try:
                async with self._pg_pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO myca_events (event_type, event_data, created_at)
                           VALUES ($1, $2, $3)""",
                        event.get("action", "unknown"),
                        json.dumps(event),
                        datetime.now(timezone.utc),
                    )
            except Exception as e:
                logger.warning(f"Event store failed: {e}")

        # Also publish to Redis for real-time subscribers
        if self._redis:
            try:
                await self._redis.publish("myca:events", json.dumps(event))
            except Exception:
                pass

    # ── Knowledge Query ──────────────────────────────────────────

    async def search_knowledge(self, query: str, limit: int = 10) -> list:
        """Search the MINDEX knowledge base via unified-search or /api/search."""
        if not self._session or self._session.closed:
            return []
        try:
            # Try MINDEX unified-search first (taxa, compounds, genetics, etc.)
            async with self._session.get(
                f"{self._mindex_api.rstrip('/')}/api/mindex/unified-search",
                params={"q": query, "limit": limit},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", {})
                    if isinstance(results, dict):
                        flat = []
                        for k, v in results.items():
                            if isinstance(v, list):
                                flat.extend(v[:3])
                        return flat[:limit] if flat else []
                    return results.get("results", []) if isinstance(results, dict) else []
        except Exception:
            pass
        try:
            async with self._session.get(
                f"{self._mindex_api.rstrip('/')}/api/search",
                params={"q": query, "limit": limit},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    return (await resp.json()).get("results", [])
        except Exception:
            pass
        return []

    async def query_knowledge_graph(self, query: str, limit: int = 5) -> list:
        """Query MINDEX for taxonomy, species, compounds when the question is domain-specific."""
        return await self.search_knowledge(query, limit=limit)

    async def recall_semantic(self, query: str, limit: int = 5) -> list:
        """Vector/semantic search for relevant past context. Uses search_knowledge as proxy."""
        return await self.search_knowledge(query, limit=limit)

    async def vector_search(
        self, query: str, collection: str = "knowledge", limit: int = 5
    ) -> list:
        """Semantic vector search via Qdrant."""
        # This would use an embedding model — simplified for now
        try:
            async with self._session.post(
                f"{self._qdrant_url}/collections/{collection}/points/search",
                json={
                    "vector": [0.0] * 384,  # Placeholder — needs real embedding
                    "limit": limit,
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    return (await resp.json()).get("result", [])
        except Exception:
            pass
        return []

    # ── Pub/Sub ──────────────────────────────────────────────────

    async def publish(self, channel: str, message: dict):
        """Publish a message to Redis pub/sub."""
        if self._redis:
            await self._redis.publish(f"myca:{channel}", json.dumps(message))

    async def subscribe(self, channel: str):
        """Subscribe to a Redis pub/sub channel. Returns async iterator."""
        if self._redis:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(f"myca:{channel}")
            return pubsub
        return None
