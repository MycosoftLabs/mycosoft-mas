"""
Graph API Router - February 4, 2026

FastAPI router exposing knowledge graph endpoints for:
- Node management
- Edge creation
- Graph traversal
- Subgraph extraction
- Graph statistics
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from mycosoft_mas.memory.persistent_graph import (
    get_knowledge_graph, Node, Edge, NodeType, EdgeType
)
from mycosoft_mas.memory.graph_indexer import build_knowledge_graph

logger = logging.getLogger("GraphAPI")

router = APIRouter(prefix="/api/graph", tags=["graph"])


# ============================================================================
# Request/Response Models
# ============================================================================

class NodeCreate(BaseModel):
    """Request to create a node."""
    node_type: str
    name: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class EdgeCreate(BaseModel):
    """Request to create an edge."""
    source_id: str
    target_id: str
    edge_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0


class PathRequest(BaseModel):
    """Request to find a path."""
    source_id: str
    target_id: str
    max_depth: int = 5


# ============================================================================
# Node Endpoints
# ============================================================================

@router.get("/nodes")
async def list_nodes(
    node_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """List nodes with optional type filter."""
    graph = get_knowledge_graph()
    
    nt = NodeType(node_type) if node_type else None
    nodes = await graph.list_nodes(nt, limit, offset)
    
    return {
        "nodes": [n.dict() for n in nodes],
        "count": len(nodes)
    }


@router.get("/nodes/{node_id}")
async def get_node(node_id: str):
    """Get a node by ID."""
    graph = get_knowledge_graph()
    
    node = await graph.get_node(UUID(node_id))
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return node.dict()


@router.get("/nodes/by-name/{name}")
async def find_node_by_name(name: str, node_type: Optional[str] = None):
    """Find a node by name."""
    graph = get_knowledge_graph()
    
    nt = NodeType(node_type) if node_type else None
    node = await graph.find_node_by_name(name, nt)
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return node.dict()


@router.post("/nodes")
async def create_node(request: NodeCreate):
    """Create or update a node."""
    graph = get_knowledge_graph()
    
    node = Node(
        node_type=NodeType(request.node_type),
        name=request.name,
        properties=request.properties
    )
    
    result = await graph.add_node(node)
    return result.dict()


@router.get("/nodes/{node_id}/neighbors")
async def get_neighbors(
    node_id: str,
    edge_type: Optional[str] = None,
    direction: str = Query("outgoing", regex="^(outgoing|incoming)$")
):
    """Get neighboring nodes."""
    graph = get_knowledge_graph()
    
    et = EdgeType(edge_type) if edge_type else None
    neighbors = await graph.get_neighbors(UUID(node_id), et, direction)
    
    return {
        "neighbors": [n.dict() for n in neighbors],
        "count": len(neighbors)
    }


# ============================================================================
# Edge Endpoints
# ============================================================================

@router.get("/edges")
async def list_edges(
    edge_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """List edges with optional type filter."""
    graph = get_knowledge_graph()
    
    et = EdgeType(edge_type) if edge_type else None
    edges = await graph.list_edges(et, limit)
    
    return {
        "edges": [e.dict() for e in edges],
        "count": len(edges)
    }


@router.post("/edges")
async def create_edge(request: EdgeCreate):
    """Create or update an edge."""
    graph = get_knowledge_graph()
    
    edge = Edge(
        source_id=UUID(request.source_id),
        target_id=UUID(request.target_id),
        edge_type=EdgeType(request.edge_type),
        properties=request.properties,
        weight=request.weight
    )
    
    result = await graph.add_edge(edge)
    return result.dict()


# ============================================================================
# Graph Traversal
# ============================================================================

@router.post("/path")
async def find_path(request: PathRequest):
    """Find shortest path between two nodes."""
    graph = get_knowledge_graph()
    
    path = await graph.find_path(
        UUID(request.source_id),
        UUID(request.target_id),
        request.max_depth
    )
    
    if not path:
        return {"found": False, "message": "No path found"}
    
    return {
        "found": True,
        "path": path.dict()
    }


@router.get("/subgraph/{node_id}")
async def get_subgraph(
    node_id: str,
    depth: int = Query(2, ge=1, le=5)
):
    """Get a subgraph centered on a node."""
    graph = get_knowledge_graph()
    return await graph.get_subgraph(UUID(node_id), depth)


# ============================================================================
# Graph Operations
# ============================================================================

@router.post("/build")
async def trigger_graph_build(background_tasks: BackgroundTasks):
    """Trigger graph build from registry (background)."""
    background_tasks.add_task(build_knowledge_graph)
    return {
        "status": "building",
        "message": "Graph build started in background"
    }


@router.post("/build/sync")
async def sync_build_graph():
    """Synchronously build graph from registry."""
    result = await build_knowledge_graph()
    return result


@router.get("/stats")
async def get_graph_stats():
    """Get graph statistics."""
    graph = get_knowledge_graph()
    return await graph.get_stats()


@router.get("/health")
async def graph_health():
    """Graph service health check."""
    graph = get_knowledge_graph()
    
    try:
        await graph.initialize()
        stats = await graph.get_stats()
        
        return {
            "status": "healthy",
            "service": "knowledge-graph",
            "node_count": stats.get("node_count", 0),
            "edge_count": stats.get("edge_count", 0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "knowledge-graph",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
