"""
Graph Lookup Tool - February 6, 2026

LangGraph tool for knowledge graph queries.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GraphLookupInput(BaseModel):
    """Input for graph lookup."""
    entity_name: str = Field(description="Name of the entity to look up")
    entity_type: Optional[str] = Field(None, description="Type of entity (species, device, location, etc.)")
    relationship_type: Optional[str] = Field(None, description="Type of relationship to traverse")
    max_depth: int = Field(2, description="Maximum traversal depth")


class GraphLookupTool:
    """
    Look up entities in the knowledge graph.
    """
    
    name = "graph_lookup"
    description = """Look up an entity in the knowledge graph and find related entities.
    Use this to find information about species, devices, locations, events, and their relationships.
    Returns the entity details and connected entities up to the specified depth."""
    args_schema: Type[BaseModel] = GraphLookupInput
    
    async def _arun(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
        relationship_type: Optional[str] = None,
        max_depth: int = 2,
    ) -> str:
        """Execute graph lookup."""
        try:
            from mycosoft_mas.memory.mindex_graph import get_graph
            from mycosoft_mas.memory.graph_schema import NodeType, EdgeType
            
            graph = await get_graph()
            
            # Find the entity
            node_type = NodeType(entity_type) if entity_type else None
            nodes = await graph.find_nodes(
                node_type=node_type,
                name_contains=entity_name,
                limit=5
            )
            
            if not nodes:
                return f"No entity found matching '{entity_name}'"
            
            # Get the best match
            node = nodes[0]
            
            # Get neighbors
            edge_type = EdgeType(relationship_type) if relationship_type else None
            traversal = await graph.get_neighbors(
                node.id,
                edge_type=edge_type,
                max_depth=max_depth
            )
            
            # Format result
            result = {
                "entity": {
                    "id": node.id,
                    "type": node.node_type.value,
                    "name": node.name,
                    "description": node.description,
                    "properties": node.properties,
                },
                "related_entities": traversal.neighbors[:10]
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Graph lookup error: {e}")
            return f"Error looking up entity: {str(e)}"


def create_graph_lookup_tool():
    """Create a graph lookup tool instance."""
    return GraphLookupTool()