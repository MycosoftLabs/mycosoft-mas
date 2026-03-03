"""Knowledge graph memory. Created: February 3, 2026"""
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

class GraphNode:
    def __init__(self, node_id: UUID, node_type: str, properties: Dict[str, Any]):
        self.node_id = node_id
        self.node_type = node_type
        self.properties = properties

class GraphEdge:
    def __init__(self, source: UUID, target: UUID, relationship: str, properties: Optional[Dict[str, Any]] = None):
        self.source = source
        self.target = target
        self.relationship = relationship
        self.properties = properties or {}

class GraphMemory:
    """Knowledge graph for structured memory."""
    
    def __init__(self, database_url: Optional[str] = None):
        self._nodes: Dict[UUID, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._adjacency: Dict[UUID, Set[UUID]] = {}
        self._database_url = database_url or os.getenv("MINDEX_DATABASE_URL")
        self._pool = None
        self._persistence_enabled = False
    
    async def initialize_persistence(self) -> None:
        """Enable PostgreSQL-backed edge persistence (`mindex.knowledge_edges`)."""
        if self._persistence_enabled or not self._database_url:
            return
        try:
            import asyncpg
        except Exception:
            return
        self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=3)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mindex.knowledge_edges (
                    id UUID PRIMARY KEY,
                    source_id UUID NOT NULL,
                    target_id UUID NOT NULL,
                    relationship TEXT NOT NULL,
                    properties_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_knowledge_edges_source
                ON mindex.knowledge_edges (source_id);
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_knowledge_edges_target
                ON mindex.knowledge_edges (target_id);
                """
            )
        self._persistence_enabled = True
    
    def add_node(self, node_type: str, properties: Dict[str, Any]) -> UUID:
        # Validate node_type against STATIC constraint index
        try:
            from mycosoft_mas.llm.constrained.validator import get_static_validator
            validator = get_static_validator()
            if validator.is_initialized and not validator.is_valid_graph_node_type(node_type):
                import logging
                logging.getLogger(__name__).warning(
                    f"Unknown graph node_type '{node_type}' — not in STATIC index"
                )
        except ImportError:
            pass
        node_id = uuid4()
        self._nodes[node_id] = GraphNode(node_id, node_type, properties)
        self._adjacency[node_id] = set()
        return node_id

    def add_edge(self, source: UUID, target: UUID, relationship: str, properties: Optional[Dict[str, Any]] = None) -> bool:
        if source not in self._nodes or target not in self._nodes:
            return False
        # Validate relationship type against STATIC constraint index
        try:
            from mycosoft_mas.llm.constrained.validator import get_static_validator
            validator = get_static_validator()
            if validator.is_initialized and not validator.is_valid_graph_edge_type(relationship):
                import logging
                logging.getLogger(__name__).warning(
                    f"Unknown graph edge type '{relationship}' — not in STATIC index"
                )
        except ImportError:
            pass
        edge = GraphEdge(source, target, relationship, properties)
        self._edges.append(edge)
        self._adjacency[source].add(target)
        if self._persistence_enabled:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.persist_edge(edge))
            except RuntimeError:
                pass
        return True

    async def persist_edge(self, edge: GraphEdge) -> bool:
        """Persist one edge into PostgreSQL if persistence is enabled."""
        if not self._persistence_enabled or not self._pool:
            return False
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.knowledge_edges (
                    id, source_id, target_id, relationship, properties_json, created_at
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                ON CONFLICT (id) DO NOTHING;
                """,
                uuid4(),
                edge.source,
                edge.target,
                edge.relationship,
                json.dumps(edge.properties),
                datetime.now(timezone.utc),
            )
        return True

    async def load_edges_from_persistence(self, limit: int = 5000) -> int:
        """Hydrate in-memory edges from PostgreSQL knowledge_edges table."""
        if not self._persistence_enabled or not self._pool:
            return 0
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT source_id, target_id, relationship, properties_json
                FROM mindex.knowledge_edges
                ORDER BY created_at DESC
                LIMIT $1;
                """,
                max(1, limit),
            )
        loaded = 0
        for row in rows:
            source = row["source_id"]
            target = row["target_id"]
            if source not in self._nodes or target not in self._nodes:
                continue
            properties = row["properties_json"]
            if isinstance(properties, str):
                properties = json.loads(properties)
            self._edges.append(GraphEdge(source, target, row["relationship"], properties or {}))
            self._adjacency[source].add(target)
            loaded += 1
        return loaded
    
    def get_node(self, node_id: UUID) -> Optional[GraphNode]:
        return self._nodes.get(node_id)
    
    def get_neighbors(self, node_id: UUID) -> List[UUID]:
        return list(self._adjacency.get(node_id, set()))
    
    def find_path(self, start: UUID, end: UUID) -> List[UUID]:
        if start not in self._nodes or end not in self._nodes:
            return []
        visited = set()
        queue = [[start]]
        while queue:
            path = queue.pop(0)
            node = path[-1]
            if node == end:
                return path
            if node not in visited:
                visited.add(node)
                for neighbor in self._adjacency.get(node, []):
                    queue.append(path + [neighbor])
        return []
    
    def query(self, node_type: Optional[str] = None, relationship: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        if node_type:
            for node in self._nodes.values():
                if node.node_type == node_type:
                    results.append({"node_id": str(node.node_id), "type": node.node_type, "properties": node.properties})
        if relationship:
            for edge in self._edges:
                if edge.relationship == relationship:
                    results.append({"source": str(edge.source), "target": str(edge.target), "relationship": edge.relationship})
        return results
