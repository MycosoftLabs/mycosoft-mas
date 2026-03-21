"""
Semantic Memory Layer for MYCA (Qdrant-backed).
Created: February 28, 2026
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("SemanticMemory")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except Exception:  # pragma: no cover
    QdrantClient = None
    qmodels = None


@dataclass
class Fact:
    """Semantic fact payload."""

    fact_id: str
    fact: str
    metadata: Dict[str, Any]
    confidence: float
    score: float = 0.0


class SemanticMemory:
    """Qdrant-backed semantic memory collection for long-term facts."""

    def __init__(
        self,
        *,
        collection_name: Optional[str] = None,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
    ):
        self._collection_name = collection_name or os.getenv(
            "QDRANT_SEMANTIC_COLLECTION", "semantic_facts"
        )
        self._host = qdrant_host or os.getenv("QDRANT_HOST", "192.168.0.189")
        self._port = qdrant_port or int(os.getenv("QDRANT_PORT", "6333"))
        self._api_key = os.getenv("QDRANT_API_KEY")
        self._client: Optional[QdrantClient] = None
        self._embedder = None

    async def initialize(self) -> None:
        """Initialize Qdrant client/embedder and create collection if missing."""
        if self._client is not None and self._embedder is not None:
            return
        if QdrantClient is None or qmodels is None:
            raise RuntimeError("qdrant-client dependency is required for SemanticMemory.")

        from mycosoft_mas.memory.embeddings import get_embedder

        self._embedder = get_embedder(os.getenv("EMBEDDER_PROVIDER", "openai"))
        self._client = QdrantClient(
            host=self._host, port=self._port, api_key=self._api_key, timeout=30.0
        )

        try:
            await asyncio.to_thread(self._client.get_collection, self._collection_name)
        except Exception:
            await asyncio.to_thread(
                self._client.create_collection,
                collection_name=self._collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self._embedder.dimension, distance=qmodels.Distance.COSINE
                ),
            )

    async def store_fact(self, fact: str, embedding: List[float], metadata: Dict[str, Any]) -> str:
        """Store a semantic fact and return its fact_id."""
        if not self._client:
            await self.initialize()

        fact_id = str(metadata.get("fact_id") or uuid4())
        confidence = float(metadata.get("confidence", 0.7))
        payload = {
            "fact": fact,
            "metadata": metadata,
            "confidence": max(0.0, min(1.0, confidence)),
        }

        await asyncio.to_thread(
            self._client.upsert,
            collection_name=self._collection_name,
            points=[
                qmodels.PointStruct(
                    id=fact_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
        return fact_id

    async def query(self, query_embedding: List[float], top_k: int = 10) -> List[Fact]:
        """Query semantic facts by embedding vector similarity."""
        if not self._client:
            await self.initialize()

        hits = await asyncio.to_thread(
            self._client.search,
            collection_name=self._collection_name,
            query_vector=query_embedding,
            limit=max(1, top_k),
            with_payload=True,
        )

        results: List[Fact] = []
        for hit in hits:
            payload = hit.payload or {}
            metadata = payload.get("metadata") or {}
            results.append(
                Fact(
                    fact_id=str(hit.id),
                    fact=str(payload.get("fact") or ""),
                    metadata=metadata,
                    confidence=float(payload.get("confidence", 0.0)),
                    score=float(hit.score or 0.0),
                )
            )
        return results

    async def update_confidence(self, fact_id: str, confidence_delta: float) -> bool:
        """Adjust confidence for a fact (clamped to [0, 1])."""
        if not self._client:
            await self.initialize()

        points = await asyncio.to_thread(
            self._client.retrieve,
            collection_name=self._collection_name,
            ids=[fact_id],
            with_payload=True,
            with_vectors=False,
        )
        if not points:
            return False

        payload = points[0].payload or {}
        current = float(payload.get("confidence", 0.0))
        updated = max(0.0, min(1.0, current + confidence_delta))
        payload["confidence"] = updated

        await asyncio.to_thread(
            self._client.set_payload,
            collection_name=self._collection_name,
            payload={"confidence": updated},
            points=[fact_id],
        )
        return True
