"""
Knowledge Graph API - February 6, 2026

REST endpoints for knowledge graph and memory operations.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["knowledge-graph"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class CreateNodeRequest(BaseModel):
    node_type: str
    name: str
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None
    importance: float = 0.5


class CreateEdgeRequest(BaseModel):
    source_id: str
    target_id: str
    edge_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0
    is_bidirectional: bool = False


class SemanticSearchRequest(BaseModel):
    query: str
    node_type: Optional[str] = None
    limit: int = 10
    min_similarity: float = 0.5


class StoreFactRequest(BaseModel):
    fact: str
    entity_id: Optional[str] = None
    importance: float = 0.5


class UserContextUpdate(BaseModel):
    display_name: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    preferred_layers: Optional[List[str]] = None
    default_zoom_level: Optional[int] = None


# ============================================
# NODE ENDPOINTS
# ============================================

@router.get("/node/{node_id}")
async def get_node(node_id: str):
    """Get a node by ID."""
    try:
        from mycosoft_mas.memory.mindex_graph import get_graph
        
        graph = await get_graph()
        node = await graph.get_node(node_id)
        
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        return {
            "id": node.id,
            "node_type": node.node_type.value,
            "name": node.name,
            "description": node.description,
            "properties": node.properties,
            "source": node.source,
            "confidence": node.confidence,
            "importance": node.importance,
            "created_at": node.created_at.isoformat() if node.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get node error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_nodes(
    query: Optional[str] = None,
    node_type: Optional[str] = None,
    name: Optional[str] = None,
    limit: int = Query(50, le=100),
):
    """Search nodes by criteria."""
    try:
        from mycosoft_mas.memory.mindex_graph import get_graph
        from mycosoft_mas.memory.graph_schema import NodeType
        
        graph = await get_graph()
        
        nt = NodeType(node_type) if node_type else None
        nodes = await graph.find_nodes(
            node_type=nt,
            name_contains=name or query,
            limit=limit,
        )
        
        return {
            "count": len(nodes),
            "nodes": [
                {
                    "id": n.id,
                    "node_type": n.node_type.value,
                    "name": n.name,
                    "description": n.description,
                    "importance": n.importance,
                }
                for n in nodes
            ]
        }
    except Exception as e:
        logger.error(f"Search nodes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traverse")
async def traverse_graph(
    from_id: str = Query(..., alias="from"),
    depth: int = 2,
    edge_type: Optional[str] = None,
):
    """Traverse graph from a node."""
    try:
        from mycosoft_mas.memory.mindex_graph import get_graph
        from mycosoft_mas.memory.graph_schema import EdgeType
        
        graph = await get_graph()
        
        et = EdgeType(edge_type) if edge_type else None
        result = await graph.get_neighbors(from_id, edge_type=et, max_depth=depth)
        
        return {
            "start_node": {
                "id": result.start_node.id,
                "name": result.start_node.name,
                "type": result.start_node.node_type.value,
            },
            "neighbors": result.neighbors,
            "depth": result.depth,
        }
    except Exception as e:
        logger.error(f"Traverse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/node")
async def create_node(request: CreateNodeRequest):
    """Create a new node."""
    try:
        from mycosoft_mas.memory.mindex_graph import get_graph
        from mycosoft_mas.memory.graph_schema import NodeType
        
        graph = await get_graph()
        
        node = await graph.create_node(
            node_type=NodeType(request.node_type),
            name=request.name,
            description=request.description,
            properties=request.properties,
            source=request.source,
            importance=request.importance,
        )
        
        return {"id": node.id, "name": node.name}
    except Exception as e:
        logger.error(f"Create node error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edge")
async def create_edge(request: CreateEdgeRequest):
    """Create an edge between nodes."""
    try:
        from mycosoft_mas.memory.mindex_graph import get_graph
        from mycosoft_mas.memory.graph_schema import EdgeType
        
        graph = await get_graph()
        
        edge = await graph.create_edge(
            source_id=request.source_id,
            target_id=request.target_id,
            edge_type=EdgeType(request.edge_type),
            properties=request.properties,
            weight=request.weight,
            is_bidirectional=request.is_bidirectional,
        )
        
        return {"id": edge.id, "edge_type": edge.edge_type.value}
    except Exception as e:
        logger.error(f"Create edge error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SEMANTIC MEMORY ENDPOINTS
# ============================================

@router.post("/memory/search")
async def semantic_search(request: SemanticSearchRequest):
    """Search nodes by semantic similarity."""
    try:
        from mycosoft_mas.memory.vector_memory import get_vector_memory
        
        vector_mem = await get_vector_memory()
        
        results = await vector_mem.semantic_search(
            query=request.query,
            node_type=request.node_type,
            top_k=request.limit,
            min_similarity=request.min_similarity,
        )
        
        return {
            "query": request.query,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/store")
async def store_fact(request: StoreFactRequest):
    """Store a fact in memory."""
    try:
        from mycosoft_mas.memory.mindex_graph import get_graph
        from mycosoft_mas.memory.vector_memory import get_vector_memory
        from mycosoft_mas.memory.graph_schema import NodeType, EdgeType
        
        graph = await get_graph()
        vector_mem = await get_vector_memory()
        
        # Create fact node
        node = await graph.create_node(
            node_type=NodeType.FACT,
            name=request.fact[:100],
            description=request.fact,
            importance=request.importance,
        )
        
        # Store embedding
        await vector_mem.embed_and_store(node.id, request.fact)
        
        # Link to entity if provided
        if request.entity_id:
            await graph.create_edge(
                source_id=request.entity_id,
                target_id=node.id,
                edge_type=EdgeType.RELATED_TO,
            )
        
        return {"id": node.id, "stored": True}
    except Exception as e:
        logger.error(f"Store fact error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# USER CONTEXT ENDPOINTS
# ============================================

@router.get("/context/user/{user_id}")
async def get_user_context(user_id: str):
    """Get user context."""
    try:
        from mycosoft_mas.memory.user_context import get_context_manager
        
        manager = await get_context_manager()
        context = await manager.get_context(user_id)
        
        if not context:
            # Create new context
            context = await manager.create_context(user_id)
        
        return {
            "user_id": context.user_id,
            "display_name": context.display_name,
            "language": context.language,
            "timezone": context.timezone,
            "preferred_layers": context.preferred_layers,
            "recent_entities": context.recent_entities[:10],
            "recent_queries": context.recent_queries[:10],
            "saved_views": context.saved_views[:10],
        }
    except Exception as e:
        logger.error(f"Get user context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/context/user/{user_id}")
async def update_user_context(user_id: str, update: UserContextUpdate):
    """Update user context."""
    try:
        from mycosoft_mas.memory.user_context import get_context_manager
        
        manager = await get_context_manager()
        context = await manager.get_context(user_id)
        
        if not context:
            context = await manager.create_context(user_id)
        
        if update.display_name is not None:
            context.display_name = update.display_name
        if update.language is not None:
            context.language = update.language
        if update.timezone is not None:
            context.timezone = update.timezone
        if update.preferred_layers is not None:
            context.preferred_layers = update.preferred_layers
        if update.default_zoom_level is not None:
            context.default_zoom_level = update.default_zoom_level
        
        await manager.update_context(context)
        
        return {"success": True, "user_id": user_id}
    except Exception as e:
        logger.error(f"Update user context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SESSION CONTEXT ENDPOINTS
# ============================================

@router.get("/context/session/{session_id}")
async def get_session_context(session_id: str):
    """Get session context."""
    try:
        from mycosoft_mas.memory.session_memory import get_session_manager
        
        manager = await get_session_manager()
        session = await manager.get_session(session_id)
        
        if not session:
            session = await manager.create_session(session_id)
        
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "current_entities": session.current_entities,
            "current_region": session.current_region,
            "current_layers": session.current_layers,
            "working_memory": session.working_memory[:10],
            "is_active": session.is_active,
        }
    except Exception as e:
        logger.error(f"Get session context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context/session/{session_id}/message")
async def add_session_message(
    session_id: str,
    role: str = Query(...),
    content: str = Query(...),
):
    """Add message to session history."""
    try:
        from mycosoft_mas.memory.session_memory import get_session_manager
        
        manager = await get_session_manager()
        await manager.add_message(session_id, role, content)
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Add message error: {e}")
        raise HTTPException(status_code=500, detail=str(e))