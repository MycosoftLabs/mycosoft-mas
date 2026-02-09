"""
Memory Store Tool - February 6, 2026

LangGraph tools for storing and recalling facts.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MemoryStoreInput(BaseModel):
    """Input for memory store."""
    fact: str = Field(description="The fact or observation to store")
    entity_id: Optional[str] = Field(None, description="ID of related entity (if any)")
    entity_name: Optional[str] = Field(None, description="Name of related entity (if any)")
    entity_type: Optional[str] = Field(None, description="Type of related entity")
    importance: float = Field(0.5, description="Importance score 0.0-1.0")
    source: str = Field("llm_agent", description="Source of the fact")


class MemoryStoreTool:
    """
    Store facts in long-term memory.
    """
    
    name = "memory_store"
    description = """Store a fact or observation in long-term memory.
    Use this to remember important information that should persist across sessions.
    Can optionally link the fact to an existing entity."""
    args_schema: Type[BaseModel] = MemoryStoreInput
    
    async def _arun(
        self,
        fact: str,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        entity_type: Optional[str] = None,
        importance: float = 0.5,
        source: str = "llm_agent",
    ) -> str:
        """Store a fact in memory."""
        try:
            from mycosoft_mas.memory.mindex_graph import get_graph
            from mycosoft_mas.memory.vector_memory import get_vector_memory
            from mycosoft_mas.memory.graph_schema import NodeType, EdgeType
            
            graph = await get_graph()
            vector_mem = await get_vector_memory()
            
            # Create a fact node
            node = await graph.create_node(
                node_type=NodeType.FACT,
                name=fact[:100],  # Short name
                description=fact,
                properties={
                    "full_text": fact,
                    "stored_at": datetime.utcnow().isoformat(),
                    "related_entity_name": entity_name,
                },
                source=source,
                importance=importance,
            )
            
            # Generate and store embedding
            await vector_mem.embed_and_store(node.id, fact)
            
            # Link to entity if provided
            if entity_id:
                try:
                    await graph.create_edge(
                        source_id=entity_id,
                        target_id=node.id,
                        edge_type=EdgeType.RELATED_TO,
                        properties={"created_by": "llm_agent"},
                    )
                except Exception as e:
                    logger.warning(f"Could not link to entity: {e}")
            
            return json.dumps({
                "success": True,
                "node_id": node.id,
                "message": f"Stored fact: {fact[:50]}..."
            })
            
        except Exception as e:
            logger.error(f"Memory store error: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })


class MemoryRecallInput(BaseModel):
    """Input for memory recall."""
    query: str = Field(description="What to search for in memory")
    limit: int = Field(5, description="Maximum number of results")
    min_similarity: float = Field(0.5, description="Minimum similarity threshold")


class SemanticRecallTool:
    """
    Recall facts from long-term memory using semantic search.
    """
    
    name = "memory_recall"
    description = """Recall facts from long-term memory using semantic search.
    Use this to remember information stored in previous sessions.
    Returns facts that are semantically similar to the query."""
    args_schema: Type[BaseModel] = MemoryRecallInput
    
    async def _arun(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.5,
    ) -> str:
        """Recall facts from memory."""
        try:
            from mycosoft_mas.memory.vector_memory import get_vector_memory
            
            vector_mem = await get_vector_memory()
            
            results = await vector_mem.semantic_search(
                query=query,
                node_type="fact",
                top_k=limit,
                min_similarity=min_similarity,
            )
            
            if not results:
                return json.dumps({
                    "count": 0,
                    "message": "No matching facts found in memory."
                })
            
            facts = [
                {
                    "id": r["id"],
                    "fact": r["description"] or r["name"],
                    "similarity": round(r["similarity"], 3),
                }
                for r in results
            ]
            
            return json.dumps({
                "count": len(facts),
                "facts": facts
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Memory recall error: {e}")
            return json.dumps({
                "count": 0,
                "error": str(e)
            })


def create_memory_store_tool():
    """Create a memory store tool instance."""
    return MemoryStoreTool()


def create_memory_recall_tool():
    """Create a semantic recall tool instance."""
    return SemanticRecallTool()