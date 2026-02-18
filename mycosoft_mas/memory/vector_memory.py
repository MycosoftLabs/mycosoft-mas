"""
Vector Memory - February 6, 2026

Semantic search with pgvector.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import asyncpg
except ImportError:
    asyncpg = None

from .embeddings import BaseEmbedder, get_embedder


class VectorMemory:
    """Vector-based semantic memory using pgvector."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        embedder: Optional[BaseEmbedder] = None,
    ):
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL",
            os.getenv("MINDEX_DATABASE_URL", "postgresql://mindex:mindex@localhost:5432/mindex")
        )
        self.embedder = embedder or get_embedder(os.getenv("EMBEDDER_PROVIDER", "openai"))
        self.pool: Optional[asyncpg.Pool] = None
        self._embedding_cache: Dict[str, List[float]] = {}
    
    async def initialize(self) -> None:
        """Initialize connection pool."""
        if asyncpg is None:
            raise ImportError("asyncpg required")
        
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=2,
            max_size=10
        )
    
    async def close(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
    
    def _cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def get_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """Get embedding for text, using cache if available."""
        cache_key = self._cache_key(text)
        
        if use_cache and cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        embedding = await self.embedder.embed_text(text)
        
        if use_cache:
            self._embedding_cache[cache_key] = embedding
            # Limit cache size
            if len(self._embedding_cache) > 1000:
                oldest_keys = list(self._embedding_cache.keys())[:100]
                for key in oldest_keys:
                    del self._embedding_cache[key]
        
        return embedding
    
    async def embed_and_store(
        self,
        node_id: str,
        text: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Embed text and store in node."""
        embedding = await self.get_embedding(text)
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE mindex.knowledge_nodes
                SET embedding = $1
                WHERE id = $2
                """,
                embedding,
                node_id,
            )
    
    async def semantic_search(
        self,
        query: str,
        node_type: Optional[str] = None,
        top_k: int = 10,
        min_similarity: float = 0.5,
        filters: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Search nodes by semantic similarity to query."""
        query_embedding = await self.get_embedding(query)
        
        conditions = ["NOT is_deleted", "embedding IS NOT NULL"]
        params = [query_embedding, min_similarity, top_k]
        param_idx = 4
        
        if node_type:
            conditions.append(f"node_type = ${param_idx}")
            params.append(node_type)
            param_idx += 1
        
        if filters:
            conditions.append(f"properties @> ${param_idx}")
            params.append(json.dumps(filters))
            param_idx += 1
        
        query_sql = f"""
            SELECT 
                id, node_type, name, description, properties,
                (1 - (embedding <=> $1)) as similarity
            FROM mindex.knowledge_nodes
            WHERE {' AND '.join(conditions)}
            AND (1 - (embedding <=> $1)) >= $2
            ORDER BY embedding <=> $1
            LIMIT $3
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query_sql, *params)
            
            return [
                {
                    "id": str(row["id"]),
                    "node_type": row["node_type"],
                    "name": row["name"],
                    "description": row["description"],
                    "properties": row["properties"],
                    "similarity": float(row["similarity"]),
                }
                for row in rows
            ]
    
    async def find_similar_nodes(
        self,
        node_id: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find nodes similar to a given node."""
        async with self.pool.acquire() as conn:
            # Get the node's embedding
            row = await conn.fetchrow(
                "SELECT embedding FROM mindex.knowledge_nodes WHERE id = $1",
                node_id
            )
            
            if not row or not row["embedding"]:
                return []
            
            # Find similar nodes
            rows = await conn.fetch(
                """
                SELECT 
                    id, node_type, name, description,
                    (1 - (embedding <=> $1)) as similarity
                FROM mindex.knowledge_nodes
                WHERE id != $2
                AND NOT is_deleted
                AND embedding IS NOT NULL
                ORDER BY embedding <=> $1
                LIMIT $3
                """,
                row["embedding"],
                node_id,
                top_k,
            )
            
            return [
                {
                    "id": str(r["id"]),
                    "node_type": r["node_type"],
                    "name": r["name"],
                    "description": r["description"],
                    "similarity": float(r["similarity"]),
                }
                for r in rows
            ]
    
    async def batch_embed_nodes(
        self,
        node_ids: List[str],
        text_field: str = "description",
    ) -> int:
        """Batch embed multiple nodes."""
        count = 0
        
        async with self.pool.acquire() as conn:
            for node_id in node_ids:
                row = await conn.fetchrow(
                    f"SELECT {text_field} FROM mindex.knowledge_nodes WHERE id = $1",
                    node_id
                )
                
                if row and row[text_field]:
                    await self.embed_and_store(node_id, row[text_field])
                    count += 1
        
        return count


# Global instance
_vector_memory: Optional[VectorMemory] = None


async def get_vector_memory() -> VectorMemory:
    """Get global vector memory instance."""
    global _vector_memory
    if _vector_memory is None:
        _vector_memory = VectorMemory()
        await _vector_memory.initialize()
    return _vector_memory