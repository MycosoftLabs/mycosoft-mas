"""
Mindex Graph - February 6, 2026

PostgreSQL-based knowledge graph implementation.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import asyncpg
except ImportError:
    asyncpg = None
    logger.warning("asyncpg not installed, graph operations will fail")

from .graph_schema import (
    EdgeType,
    GraphSearchResult,
    GraphTraversalResult,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
    SemanticSearchResult,
)


class MindexGraph:
    """
    PostgreSQL-based knowledge graph with async operations.
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL",
            "postgresql://mycosoft:mycosoft@localhost:5432/mindex"
        )
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> None:
        """Initialize connection pool."""
        if asyncpg is None:
            raise ImportError("asyncpg is required for MindexGraph")
        
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=2,
            max_size=10
        )
        logger.info("MindexGraph initialized")
    
    async def close(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
    
    async def create_node(
        self,
        node_type: NodeType,
        name: str,
        description: Optional[str] = None,
        properties: Optional[Dict] = None,
        embedding: Optional[List[float]] = None,
        source: Optional[str] = None,
        confidence: float = 1.0,
        importance: float = 0.5,
    ) -> KnowledgeNode:
        """Create a new node in the graph."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO mindex.knowledge_nodes 
                (node_type, name, description, properties, embedding, source, confidence, importance)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                node_type.value,
                name,
                description,
                json.dumps(properties or {}),
                embedding,
                source,
                confidence,
                importance,
            )
            return KnowledgeNode.from_db_row(dict(row))
    
    async def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """Get a node by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM mindex.knowledge_nodes 
                WHERE id = $1 AND NOT is_deleted
                """,
                node_id,
            )
            if row:
                # Update last accessed
                await conn.execute(
                    "UPDATE mindex.knowledge_nodes SET last_accessed_at = NOW() WHERE id = $1",
                    node_id
                )
                return KnowledgeNode.from_db_row(dict(row))
            return None
    
    async def find_nodes(
        self,
        node_type: Optional[NodeType] = None,
        name_contains: Optional[str] = None,
        properties_filter: Optional[Dict] = None,
        limit: int = 50,
    ) -> List[KnowledgeNode]:
        """Find nodes matching criteria."""
        conditions = ["NOT is_deleted"]
        params = []
        param_idx = 1
        
        if node_type:
            conditions.append(f"node_type = ${param_idx}")
            params.append(node_type.value)
            param_idx += 1
        
        if name_contains:
            conditions.append(f"name ILIKE ${param_idx}")
            params.append(f"%{name_contains}%")
            param_idx += 1
        
        if properties_filter:
            conditions.append(f"properties @> ${param_idx}")
            params.append(json.dumps(properties_filter))
            param_idx += 1
        
        params.append(limit)
        
        query = f"""
            SELECT * FROM mindex.knowledge_nodes
            WHERE {' AND '.join(conditions)}
            ORDER BY importance DESC, created_at DESC
            LIMIT ${param_idx}
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [KnowledgeNode.from_db_row(dict(row)) for row in rows]
    
    async def update_node(
        self,
        node_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        properties: Optional[Dict] = None,
        embedding: Optional[List[float]] = None,
        importance: Optional[float] = None,
    ) -> Optional[KnowledgeNode]:
        """Update a node."""
        updates = []
        params = []
        param_idx = 1
        
        if name is not None:
            updates.append(f"name = ${param_idx}")
            params.append(name)
            param_idx += 1
        
        if description is not None:
            updates.append(f"description = ${param_idx}")
            params.append(description)
            param_idx += 1
        
        if properties is not None:
            updates.append(f"properties = ${param_idx}")
            params.append(json.dumps(properties))
            param_idx += 1
        
        if embedding is not None:
            updates.append(f"embedding = ${param_idx}")
            params.append(embedding)
            param_idx += 1
        
        if importance is not None:
            updates.append(f"importance = ${param_idx}")
            params.append(importance)
            param_idx += 1
        
        if not updates:
            return await self.get_node(node_id)
        
        params.append(node_id)
        
        query = f"""
            UPDATE mindex.knowledge_nodes
            SET {', '.join(updates)}
            WHERE id = ${param_idx} AND NOT is_deleted
            RETURNING *
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            if row:
                return KnowledgeNode.from_db_row(dict(row))
            return None
    
    async def delete_node(self, node_id: str, hard_delete: bool = False) -> bool:
        """Delete a node (soft delete by default)."""
        async with self.pool.acquire() as conn:
            if hard_delete:
                result = await conn.execute(
                    "DELETE FROM mindex.knowledge_nodes WHERE id = $1",
                    node_id
                )
            else:
                result = await conn.execute(
                    "UPDATE mindex.knowledge_nodes SET is_deleted = TRUE WHERE id = $1",
                    node_id
                )
            return "DELETE" in result or "UPDATE" in result
    
    async def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        properties: Optional[Dict] = None,
        weight: float = 1.0,
        is_bidirectional: bool = False,
    ) -> KnowledgeEdge:
        """Create an edge between nodes."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO mindex.knowledge_edges
                (source_id, target_id, edge_type, properties, weight, is_bidirectional)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (source_id, target_id, edge_type) 
                DO UPDATE SET weight = EXCLUDED.weight, properties = EXCLUDED.properties
                RETURNING *
                """,
                source_id,
                target_id,
                edge_type.value,
                json.dumps(properties or {}),
                weight,
                is_bidirectional,
            )
            return KnowledgeEdge.from_db_row(dict(row))
    
    async def get_edges(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        edge_type: Optional[EdgeType] = None,
    ) -> List[KnowledgeEdge]:
        """Get edges matching criteria."""
        conditions = []
        params = []
        param_idx = 1
        
        if source_id:
            conditions.append(f"source_id = ${param_idx}")
            params.append(source_id)
            param_idx += 1
        
        if target_id:
            conditions.append(f"target_id = ${param_idx}")
            params.append(target_id)
            param_idx += 1
        
        if edge_type:
            conditions.append(f"edge_type = ${param_idx}")
            params.append(edge_type.value)
            param_idx += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"SELECT * FROM mindex.knowledge_edges {where_clause}"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [KnowledgeEdge.from_db_row(dict(row)) for row in rows]
    
    async def get_neighbors(
        self,
        node_id: str,
        edge_type: Optional[EdgeType] = None,
        direction: str = "both",
        max_depth: int = 1,
    ) -> GraphTraversalResult:
        """Get neighboring nodes."""
        start_node = await self.get_node(node_id)
        if not start_node:
            raise ValueError(f"Node {node_id} not found")
        
        edge_type_param = edge_type.value if edge_type else None
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM mindex.get_neighbors($1, $2, $3)",
                node_id,
                edge_type_param,
                max_depth,
            )
            
            neighbors = [
                {
                    "node_id": str(row["node_id"]),
                    "node_type": row["node_type"],
                    "node_name": row["node_name"],
                    "edge_type": row["edge_type"],
                    "depth": row["depth"],
                }
                for row in rows
            ]
            
            return GraphTraversalResult(
                start_node=start_node,
                neighbors=neighbors,
                depth=max_depth,
            )
    
    async def semantic_search(
        self,
        embedding: List[float],
        node_type: Optional[NodeType] = None,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> List[SemanticSearchResult]:
        """Search nodes by semantic similarity."""
        node_type_param = node_type.value if node_type else None
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM mindex.semantic_search($1, $2, $3, $4)",
                embedding,
                node_type_param,
                limit,
                min_similarity,
            )
            
            results = []
            for row in rows:
                node = KnowledgeNode(
                    id=str(row["node_id"]),
                    node_type=NodeType(row["node_type"]),
                    name=row["name"],
                    description=row["description"],
                )
                results.append(SemanticSearchResult(
                    node=node,
                    similarity=row["similarity"],
                ))
            
            return results


# Global instance
_graph: Optional[MindexGraph] = None


async def get_graph() -> MindexGraph:
    """Get the global graph instance."""
    global _graph
    if _graph is None:
        _graph = MindexGraph()
        await _graph.initialize()
    return _graph