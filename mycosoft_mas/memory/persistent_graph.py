"""
Persistent Knowledge Graph - February 4, 2026

PostgreSQL-backed knowledge graph for system relationships,
semantic connections, and rapid graph traversal.

Features:
- Node and edge storage in PostgreSQL
- In-memory cache for fast access
- Graph traversal algorithms
- Auto-indexing from registry
"""

import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger("PersistentGraph")


# ============================================================================
# Models
# ============================================================================

class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""
    SYSTEM = "system"
    AGENT = "agent"
    API = "api"
    SERVICE = "service"
    DEVICE = "device"
    DATABASE = "database"
    CONCEPT = "concept"
    FILE = "file"
    WORKFLOW = "workflow"
    USER = "user"
    MEMORY = "memory"


class EdgeType(str, Enum):
    """Types of relationships between nodes."""
    DEPENDS_ON = "depends_on"
    CALLS = "calls"
    CONTAINS = "contains"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    CONNECTS_TO = "connects_to"
    RELATED_TO = "related_to"
    MANAGES = "manages"
    HOSTS = "hosts"
    IMPLEMENTS = "implements"


class Node(BaseModel):
    """A node in the knowledge graph."""
    id: Optional[UUID] = None
    node_type: NodeType
    name: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Edge(BaseModel):
    """An edge connecting two nodes."""
    id: Optional[UUID] = None
    source_id: UUID
    target_id: UUID
    edge_type: EdgeType
    properties: Dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0
    created_at: Optional[datetime] = None


class GraphPath(BaseModel):
    """A path through the graph."""
    nodes: List[Node]
    edges: List[Edge]
    total_weight: float


# ============================================================================
# Persistent Knowledge Graph
# ============================================================================

class PersistentKnowledgeGraph:
    """
    PostgreSQL-backed knowledge graph with in-memory caching.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://mycosoft:mycosoft@postgres:5432/mycosoft"
        )
        self._pool = None
        self._initialized = False
        
        # In-memory cache
        self._node_cache: Dict[UUID, Node] = {}
        self._edge_cache: Dict[UUID, Edge] = {}
        self._adjacency: Dict[UUID, List[UUID]] = {}
    
    async def initialize(self) -> None:
        """Initialize database connection and cache."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=2,
                max_size=10
            )
            
            # Load cache
            await self._load_cache()
            
            self._initialized = True
            logger.info("Knowledge graph initialized")
        except Exception as e:
            logger.error(f"Failed to initialize graph: {e}")
            raise
    
    async def _load_cache(self) -> None:
        """Load nodes and edges into memory cache."""
        async with self._pool.acquire() as conn:
            # Load nodes
            node_rows = await conn.fetch("""
                SELECT id, node_type, name, properties, created_at, updated_at
                FROM graph.nodes
            """)
            
            import json
            for row in node_rows:
                node = Node(
                    id=row["id"],
                    node_type=NodeType(row["node_type"]),
                    name=row["name"],
                    properties=json.loads(row["properties"]) if row["properties"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                self._node_cache[node.id] = node
            
            # Load edges
            edge_rows = await conn.fetch("""
                SELECT id, source_id, target_id, edge_type, properties, weight, created_at
                FROM graph.edges
            """)
            
            for row in edge_rows:
                edge = Edge(
                    id=row["id"],
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    edge_type=EdgeType(row["edge_type"]),
                    properties=json.loads(row["properties"]) if row["properties"] else {},
                    weight=row["weight"],
                    created_at=row["created_at"]
                )
                self._edge_cache[edge.id] = edge
                
                # Build adjacency list
                if edge.source_id not in self._adjacency:
                    self._adjacency[edge.source_id] = []
                self._adjacency[edge.source_id].append(edge.target_id)
        
        logger.info(f"Loaded {len(self._node_cache)} nodes and {len(self._edge_cache)} edges into cache")
    
    async def add_node(self, node: Node) -> Node:
        """Add or update a node in the graph."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            row = await conn.fetchrow("""
                INSERT INTO graph.nodes (node_type, name, properties)
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT (name, node_type) DO UPDATE SET
                    properties = EXCLUDED.properties,
                    updated_at = NOW()
                RETURNING id, created_at, updated_at
            """, node.node_type.value, node.name, json.dumps(node.properties))
            
            node.id = row["id"]
            node.created_at = row["created_at"]
            node.updated_at = row["updated_at"]
        
        # Update cache
        self._node_cache[node.id] = node
        
        return node
    
    async def add_edge(self, edge: Edge) -> Edge:
        """Add or update an edge in the graph."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            row = await conn.fetchrow("""
                INSERT INTO graph.edges (source_id, target_id, edge_type, properties, weight)
                VALUES ($1, $2, $3, $4::jsonb, $5)
                ON CONFLICT (source_id, target_id, edge_type) DO UPDATE SET
                    properties = EXCLUDED.properties,
                    weight = EXCLUDED.weight
                RETURNING id, created_at
            """, edge.source_id, edge.target_id, edge.edge_type.value,
                json.dumps(edge.properties), edge.weight)
            
            edge.id = row["id"]
            edge.created_at = row["created_at"]
        
        # Update cache
        self._edge_cache[edge.id] = edge
        if edge.source_id not in self._adjacency:
            self._adjacency[edge.source_id] = []
        if edge.target_id not in self._adjacency[edge.source_id]:
            self._adjacency[edge.source_id].append(edge.target_id)
        
        return edge
    
    async def get_node(self, node_id: UUID) -> Optional[Node]:
        """Get a node by ID."""
        if node_id in self._node_cache:
            return self._node_cache[node_id]
        
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            row = await conn.fetchrow("""
                SELECT id, node_type, name, properties, created_at, updated_at
                FROM graph.nodes WHERE id = $1
            """, node_id)
            
            if row:
                node = Node(
                    id=row["id"],
                    node_type=NodeType(row["node_type"]),
                    name=row["name"],
                    properties=json.loads(row["properties"]) if row["properties"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                self._node_cache[node_id] = node
                return node
        
        return None
    
    async def find_node_by_name(self, name: str, node_type: Optional[NodeType] = None) -> Optional[Node]:
        """Find a node by name."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            if node_type:
                row = await conn.fetchrow("""
                    SELECT id, node_type, name, properties, created_at, updated_at
                    FROM graph.nodes WHERE name = $1 AND node_type = $2
                """, name, node_type.value)
            else:
                row = await conn.fetchrow("""
                    SELECT id, node_type, name, properties, created_at, updated_at
                    FROM graph.nodes WHERE name = $1
                """, name)
            
            if row:
                return Node(
                    id=row["id"],
                    node_type=NodeType(row["node_type"]),
                    name=row["name"],
                    properties=json.loads(row["properties"]) if row["properties"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
        
        return None
    
    async def get_neighbors(
        self,
        node_id: UUID,
        edge_type: Optional[EdgeType] = None,
        direction: str = "outgoing"
    ) -> List[Node]:
        """Get neighboring nodes."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            
            if direction == "outgoing":
                if edge_type:
                    rows = await conn.fetch("""
                        SELECT n.id, n.node_type, n.name, n.properties, n.created_at, n.updated_at
                        FROM graph.nodes n
                        JOIN graph.edges e ON e.target_id = n.id
                        WHERE e.source_id = $1 AND e.edge_type = $2
                    """, node_id, edge_type.value)
                else:
                    rows = await conn.fetch("""
                        SELECT n.id, n.node_type, n.name, n.properties, n.created_at, n.updated_at
                        FROM graph.nodes n
                        JOIN graph.edges e ON e.target_id = n.id
                        WHERE e.source_id = $1
                    """, node_id)
            else:  # incoming
                if edge_type:
                    rows = await conn.fetch("""
                        SELECT n.id, n.node_type, n.name, n.properties, n.created_at, n.updated_at
                        FROM graph.nodes n
                        JOIN graph.edges e ON e.source_id = n.id
                        WHERE e.target_id = $1 AND e.edge_type = $2
                    """, node_id, edge_type.value)
                else:
                    rows = await conn.fetch("""
                        SELECT n.id, n.node_type, n.name, n.properties, n.created_at, n.updated_at
                        FROM graph.nodes n
                        JOIN graph.edges e ON e.source_id = n.id
                        WHERE e.target_id = $1
                    """, node_id)
            
            return [
                Node(
                    id=row["id"],
                    node_type=NodeType(row["node_type"]),
                    name=row["name"],
                    properties=json.loads(row["properties"]) if row["properties"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in rows
            ]
    
    async def find_path(
        self,
        source_id: UUID,
        target_id: UUID,
        max_depth: int = 5
    ) -> Optional[GraphPath]:
        """Find shortest path between two nodes using BFS."""
        await self.initialize()
        
        if source_id == target_id:
            source_node = await self.get_node(source_id)
            return GraphPath(nodes=[source_node], edges=[], total_weight=0) if source_node else None
        
        # BFS
        visited = {source_id}
        queue = [(source_id, [], [])]  # (node_id, path_nodes, path_edges)
        
        while queue and len(queue[0][1]) < max_depth:
            current_id, path_nodes, path_edges = queue.pop(0)
            current_node = await self.get_node(current_id)
            
            if not current_node:
                continue
            
            path_nodes = path_nodes + [current_node]
            
            # Get outgoing edges
            async with self._pool.acquire() as conn:
                import json
                edge_rows = await conn.fetch("""
                    SELECT id, source_id, target_id, edge_type, properties, weight
                    FROM graph.edges WHERE source_id = $1
                """, current_id)
            
            for row in edge_rows:
                neighbor_id = row["target_id"]
                
                if neighbor_id in visited:
                    continue
                
                edge = Edge(
                    id=row["id"],
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    edge_type=EdgeType(row["edge_type"]),
                    properties=json.loads(row["properties"]) if row["properties"] else {},
                    weight=row["weight"]
                )
                
                new_edges = path_edges + [edge]
                
                if neighbor_id == target_id:
                    target_node = await self.get_node(target_id)
                    return GraphPath(
                        nodes=path_nodes + [target_node],
                        edges=new_edges,
                        total_weight=sum(e.weight for e in new_edges)
                    )
                
                visited.add(neighbor_id)
                queue.append((neighbor_id, path_nodes, new_edges))
        
        return None
    
    async def get_subgraph(
        self,
        center_id: UUID,
        depth: int = 2
    ) -> Dict[str, Any]:
        """Get a subgraph centered on a node."""
        await self.initialize()
        
        nodes = {}
        edges = []
        visited = set()
        
        async def explore(node_id: UUID, current_depth: int):
            if current_depth > depth or node_id in visited:
                return
            
            visited.add(node_id)
            node = await self.get_node(node_id)
            if node:
                nodes[str(node_id)] = node.dict()
            
            # Get edges
            async with self._pool.acquire() as conn:
                import json
                edge_rows = await conn.fetch("""
                    SELECT id, source_id, target_id, edge_type, properties, weight
                    FROM graph.edges WHERE source_id = $1 OR target_id = $1
                """, node_id)
            
            for row in edge_rows:
                edge = {
                    "id": str(row["id"]),
                    "source_id": str(row["source_id"]),
                    "target_id": str(row["target_id"]),
                    "edge_type": row["edge_type"],
                    "weight": row["weight"]
                }
                if edge not in edges:
                    edges.append(edge)
                
                neighbor_id = row["target_id"] if row["source_id"] == node_id else row["source_id"]
                await explore(neighbor_id, current_depth + 1)
        
        await explore(center_id, 0)
        
        return {
            "center": str(center_id),
            "depth": depth,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    
    async def list_nodes(
        self,
        node_type: Optional[NodeType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Node]:
        """List nodes with optional type filter."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            if node_type:
                rows = await conn.fetch("""
                    SELECT id, node_type, name, properties, created_at, updated_at
                    FROM graph.nodes WHERE node_type = $1
                    ORDER BY name LIMIT $2 OFFSET $3
                """, node_type.value, limit, offset)
            else:
                rows = await conn.fetch("""
                    SELECT id, node_type, name, properties, created_at, updated_at
                    FROM graph.nodes ORDER BY name LIMIT $1 OFFSET $2
                """, limit, offset)
            
            return [
                Node(
                    id=row["id"],
                    node_type=NodeType(row["node_type"]),
                    name=row["name"],
                    properties=json.loads(row["properties"]) if row["properties"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in rows
            ]
    
    async def list_edges(
        self,
        edge_type: Optional[EdgeType] = None,
        limit: int = 100
    ) -> List[Edge]:
        """List edges with optional type filter."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            import json
            if edge_type:
                rows = await conn.fetch("""
                    SELECT id, source_id, target_id, edge_type, properties, weight, created_at
                    FROM graph.edges WHERE edge_type = $1
                    LIMIT $2
                """, edge_type.value, limit)
            else:
                rows = await conn.fetch("""
                    SELECT id, source_id, target_id, edge_type, properties, weight, created_at
                    FROM graph.edges LIMIT $1
                """, limit)
            
            return [
                Edge(
                    id=row["id"],
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    edge_type=EdgeType(row["edge_type"]),
                    properties=json.loads(row["properties"]) if row["properties"] else {},
                    weight=row["weight"],
                    created_at=row["created_at"]
                )
                for row in rows
            ]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        await self.initialize()
        
        async with self._pool.acquire() as conn:
            node_count = await conn.fetchval("SELECT COUNT(*) FROM graph.nodes")
            edge_count = await conn.fetchval("SELECT COUNT(*) FROM graph.edges")
            
            type_counts = await conn.fetch("""
                SELECT node_type, COUNT(*) as count
                FROM graph.nodes GROUP BY node_type
            """)
            
            edge_type_counts = await conn.fetch("""
                SELECT edge_type, COUNT(*) as count
                FROM graph.edges GROUP BY edge_type
            """)
        
        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "cache_nodes": len(self._node_cache),
            "cache_edges": len(self._edge_cache),
            "by_node_type": {r["node_type"]: r["count"] for r in type_counts},
            "by_edge_type": {r["edge_type"]: r["count"] for r in edge_type_counts}
        }


# Singleton
_graph: Optional[PersistentKnowledgeGraph] = None


def get_knowledge_graph() -> PersistentKnowledgeGraph:
    """Get singleton graph instance."""
    global _graph
    if _graph is None:
        _graph = PersistentKnowledgeGraph()
    return _graph


# ============================================================================
# Enhanced Features - Multi-hop Reasoning and Registry Auto-population
# Added: February 5, 2026
# ============================================================================

class MultiHopReasoner:
    """
    Multi-hop reasoning engine for the knowledge graph.
    
    Enables complex queries that traverse multiple relationships
    to find implicit connections and derive new knowledge.
    """
    
    def __init__(self, graph: PersistentKnowledgeGraph):
        self._graph = graph
    
    async def query(
        self,
        start_node: str,
        relationship_path: List[str],
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Execute a multi-hop query.
        
        Example:
            query("MAS", ["contains", "depends_on", "hosts"])
            Finds: MAS -> (contains) -> agents -> (depends_on) -> services -> (hosts) -> ?
        """
        results = []
        
        # Find starting node
        start = await self._graph.find_node_by_name(start_node)
        if not start:
            return []
        
        # Initialize with start nodes
        current_nodes = [start]
        path_so_far = [(start, None)]
        
        # Traverse each relationship in path
        for rel in relationship_path:
            next_nodes = []
            edge_type = EdgeType(rel) if rel in EdgeType.__members__.values() else None
            
            for node in current_nodes:
                neighbors = await self._graph.get_neighbors(
                    node.id,
                    edge_type=edge_type,
                    direction="outgoing"
                )
                for neighbor in neighbors:
                    next_nodes.append(neighbor)
                    
                    # Build result
                    if rel == relationship_path[-1]:
                        result_path = path_so_far + [(neighbor, rel)]
                        results.append({
                            "path": [
                                {"node": n.name, "type": n.node_type.value, "via": via}
                                for n, via in result_path
                            ],
                            "final_node": {
                                "id": str(neighbor.id),
                                "name": neighbor.name,
                                "type": neighbor.node_type.value,
                                "properties": neighbor.properties
                            }
                        })
            
            current_nodes = next_nodes[:100]  # Limit fan-out
        
        return results[:max_results]
    
    async def find_all_paths(
        self,
        source_name: str,
        target_name: str,
        max_depth: int = 4
    ) -> List[Dict[str, Any]]:
        """Find all paths between two named nodes."""
        source = await self._graph.find_node_by_name(source_name)
        target = await self._graph.find_node_by_name(target_name)
        
        if not source or not target:
            return []
        
        paths = []
        
        async def dfs(current_id: UUID, path: List[Tuple[Node, Edge]], visited: Set[UUID]):
            if len(path) > max_depth:
                return
            
            if current_id == target.id:
                paths.append({
                    "length": len(path),
                    "path": [
                        {
                            "node": n.name,
                            "type": n.node_type.value,
                            "edge": e.edge_type.value if e else None
                        }
                        for n, e in path
                    ] + [{"node": target.name, "type": target.node_type.value, "edge": None}]
                })
                return
            
            neighbors = await self._graph.get_neighbors(current_id, direction="outgoing")
            
            for neighbor in neighbors:
                if neighbor.id not in visited:
                    # Get the edge
                    edge = None
                    async with self._graph._pool.acquire() as conn:
                        import json
                        row = await conn.fetchrow("""
                            SELECT id, source_id, target_id, edge_type, weight
                            FROM graph.edges
                            WHERE source_id = $1 AND target_id = $2
                            LIMIT 1
                        """, current_id, neighbor.id)
                        if row:
                            edge = Edge(
                                id=row["id"],
                                source_id=row["source_id"],
                                target_id=row["target_id"],
                                edge_type=EdgeType(row["edge_type"]),
                                weight=row["weight"]
                            )
                    
                    current_node = await self._graph.get_node(current_id)
                    visited.add(neighbor.id)
                    await dfs(neighbor.id, path + [(current_node, edge)], visited)
                    visited.remove(neighbor.id)
        
        await dfs(source.id, [], {source.id})
        
        return sorted(paths, key=lambda p: p["length"])
    
    async def infer_relationship(
        self,
        node_a: str,
        node_b: str
    ) -> Dict[str, Any]:
        """Infer possible relationship between two nodes."""
        a = await self._graph.find_node_by_name(node_a)
        b = await self._graph.find_node_by_name(node_b)
        
        if not a or not b:
            return {"error": "One or both nodes not found"}
        
        # Check direct relationship
        direct_paths = await self.find_all_paths(node_a, node_b, max_depth=1)
        if direct_paths:
            return {
                "relationship": "direct",
                "paths": direct_paths,
                "confidence": 1.0
            }
        
        # Check indirect relationship
        indirect_paths = await self.find_all_paths(node_a, node_b, max_depth=3)
        if indirect_paths:
            return {
                "relationship": "indirect",
                "paths": indirect_paths,
                "confidence": 0.8 / (indirect_paths[0]["length"] if indirect_paths else 1)
            }
        
        # Check common neighbors
        a_neighbors = await self._graph.get_neighbors(a.id, direction="outgoing")
        b_neighbors = await self._graph.get_neighbors(b.id, direction="outgoing")
        
        a_neighbor_ids = {n.id for n in a_neighbors}
        b_neighbor_ids = {n.id for n in b_neighbors}
        
        common = a_neighbor_ids & b_neighbor_ids
        if common:
            common_nodes = [await self._graph.get_node(nid) for nid in list(common)[:5]]
            return {
                "relationship": "common_neighbors",
                "common_nodes": [n.name for n in common_nodes if n],
                "confidence": 0.5
            }
        
        return {
            "relationship": "none",
            "confidence": 0.0
        }


class RegistryAutoPopulator:
    """
    Auto-populates the knowledge graph from system registries.
    
    Syncs from:
    - System registry (systems, services)
    - Agent registry (96+ agents)
    - Device registry (MycoBrain devices)
    - API registry
    """
    
    def __init__(self, graph: PersistentKnowledgeGraph, database_url: Optional[str] = None):
        self._graph = graph
        self._database_url = database_url or os.getenv(
            "MINDEX_DATABASE_URL",
            "postgresql://mycosoft:REDACTED_VM_SSH_PASSWORD@192.168.0.189:5432/mindex"
        )
        self._pool = None
    
    async def initialize(self) -> None:
        """Initialize database connection."""
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=3
            )
        except Exception as e:
            logger.warning(f"Failed to connect to MINDEX: {e}")
    
    async def sync_all(self) -> Dict[str, int]:
        """Sync all registries to the knowledge graph."""
        await self.initialize()
        
        counts = {
            "systems": await self._sync_systems(),
            "agents": await self._sync_agents(),
            "devices": await self._sync_devices(),
            "apis": await self._sync_apis()
        }
        
        # Create inter-registry relationships
        await self._create_relationships()
        
        return counts
    
    async def _sync_systems(self) -> int:
        """Sync systems from registry.systems."""
        if not self._pool:
            return 0
        
        count = 0
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM registry.systems")
                
                for row in rows:
                    node = Node(
                        node_type=NodeType.SYSTEM,
                        name=row["name"],
                        properties={
                            "type": row.get("type", "unknown"),
                            "url": row.get("url"),
                            "status": row.get("status", "unknown"),
                            "description": row.get("description", "")
                        }
                    )
                    await self._graph.add_node(node)
                    count += 1
        except Exception as e:
            logger.error(f"Failed to sync systems: {e}")
        
        logger.info(f"Synced {count} systems to knowledge graph")
        return count
    
    async def _sync_agents(self) -> int:
        """Sync agents from registry.agents."""
        if not self._pool:
            return 0
        
        count = 0
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM registry.agents")
                
                for row in rows:
                    node = Node(
                        node_type=NodeType.AGENT,
                        name=row["name"],
                        properties={
                            "type": row.get("type", "unknown"),
                            "status": row.get("status", "offline"),
                            "description": row.get("description", "")
                        }
                    )
                    await self._graph.add_node(node)
                    count += 1
        except Exception as e:
            logger.error(f"Failed to sync agents: {e}")
        
        logger.info(f"Synced {count} agents to knowledge graph")
        return count
    
    async def _sync_devices(self) -> int:
        """Sync devices from registry.devices."""
        if not self._pool:
            return 0
        
        count = 0
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM registry.devices")
                
                for row in rows:
                    node = Node(
                        node_type=NodeType.DEVICE,
                        name=row["name"],
                        properties={
                            "device_type": row.get("device_type", "unknown"),
                            "device_id": row.get("device_id", ""),
                            "status": row.get("status", "offline"),
                            "location": row.get("location", ""),
                            "firmware_version": row.get("firmware_version", "")
                        }
                    )
                    await self._graph.add_node(node)
                    count += 1
        except Exception as e:
            logger.error(f"Failed to sync devices: {e}")
        
        logger.info(f"Synced {count} devices to knowledge graph")
        return count
    
    async def _sync_apis(self) -> int:
        """Sync APIs from registry.apis."""
        if not self._pool:
            return 0
        
        count = 0
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM registry.apis")
                
                for row in rows:
                    node = Node(
                        node_type=NodeType.API,
                        name=row["name"],
                        properties={
                            "version": row.get("version", "1.0"),
                            "base_url": row.get("base_url", ""),
                            "status": row.get("status", "active")
                        }
                    )
                    await self._graph.add_node(node)
                    count += 1
        except Exception as e:
            logger.error(f"Failed to sync APIs: {e}")
        
        logger.info(f"Synced {count} APIs to knowledge graph")
        return count
    
    async def _create_relationships(self) -> int:
        """Create relationships between registered entities."""
        count = 0
        
        # MAS contains all agents
        mas_node = await self._graph.find_node_by_name("MAS", NodeType.SYSTEM)
        if mas_node:
            agents = await self._graph.list_nodes(NodeType.AGENT, limit=200)
            for agent in agents:
                edge = Edge(
                    source_id=mas_node.id,
                    target_id=agent.id,
                    edge_type=EdgeType.CONTAINS
                )
                await self._graph.add_edge(edge)
                count += 1
        
        # NatureOS manages devices
        natureos = await self._graph.find_node_by_name("NatureOS", NodeType.SYSTEM)
        if not natureos:
            natureos = await self._graph.find_node_by_name("MINDEX", NodeType.SYSTEM)
        
        if natureos:
            devices = await self._graph.list_nodes(NodeType.DEVICE, limit=100)
            for device in devices:
                edge = Edge(
                    source_id=natureos.id,
                    target_id=device.id,
                    edge_type=EdgeType.MANAGES
                )
                await self._graph.add_edge(edge)
                count += 1
        
        # PersonaPlex connects to voice agents
        personaplex = await self._graph.find_node_by_name("PersonaPlex", NodeType.SYSTEM)
        if personaplex:
            voice_agents = ["speech_agent", "tts_agent", "stt_agent", "voice_bridge_agent"]
            for agent_name in voice_agents:
                agent = await self._graph.find_node_by_name(agent_name, NodeType.AGENT)
                if agent:
                    edge = Edge(
                        source_id=personaplex.id,
                        target_id=agent.id,
                        edge_type=EdgeType.CONNECTS_TO
                    )
                    await self._graph.add_edge(edge)
                    count += 1
        
        # n8n hosts workflow agents
        n8n = await self._graph.find_node_by_name("n8n", NodeType.SYSTEM)
        if n8n:
            workflow_agents = ["n8n_workflow_agent", "trigger_agent", "scheduler_agent"]
            for agent_name in workflow_agents:
                agent = await self._graph.find_node_by_name(agent_name, NodeType.AGENT)
                if agent:
                    edge = Edge(
                        source_id=n8n.id,
                        target_id=agent.id,
                        edge_type=EdgeType.HOSTS
                    )
                    await self._graph.add_edge(edge)
                    count += 1
        
        logger.info(f"Created {count} relationships in knowledge graph")
        return count


# Extend PersistentKnowledgeGraph with new methods
async def enhance_graph_with_reasoning(graph: PersistentKnowledgeGraph) -> MultiHopReasoner:
    """Create a multi-hop reasoner for the graph."""
    await graph.initialize()
    return MultiHopReasoner(graph)


async def auto_populate_from_registry(graph: PersistentKnowledgeGraph) -> Dict[str, int]:
    """Auto-populate graph from registries."""
    populator = RegistryAutoPopulator(graph)
    return await populator.sync_all()


# Add to PersistentKnowledgeGraph class
PersistentKnowledgeGraph.get_reasoner = lambda self: MultiHopReasoner(self)
PersistentKnowledgeGraph.auto_populate = lambda self: RegistryAutoPopulator(self).sync_all()
