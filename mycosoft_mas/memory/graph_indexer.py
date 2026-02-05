"""
Graph Indexer - February 4, 2026

Automatically builds the knowledge graph from registry data,
creating nodes for systems, agents, APIs, services, and devices,
and edges representing their relationships.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

from mycosoft_mas.memory.persistent_graph import (
    get_knowledge_graph, PersistentKnowledgeGraph,
    Node, Edge, NodeType, EdgeType
)
from mycosoft_mas.registry.system_registry import get_registry, SystemRegistry

logger = logging.getLogger("GraphIndexer")


class GraphIndexer:
    """
    Builds knowledge graph from registry data.
    """
    
    def __init__(self):
        self._registry = get_registry()
        self._graph = get_knowledge_graph()
    
    async def build_graph(self) -> Dict[str, Any]:
        """Build complete knowledge graph from registry."""
        results = {
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "nodes_created": 0,
            "edges_created": 0,
            "errors": []
        }
        
        try:
            # Initialize services
            await self._registry.initialize()
            await self._graph.initialize()
            
            # Index systems
            systems = await self._index_systems()
            results["nodes_created"] += systems["nodes"]
            results["edges_created"] += systems["edges"]
            
            # Index agents
            agents = await self._index_agents()
            results["nodes_created"] += agents["nodes"]
            results["edges_created"] += agents["edges"]
            
            # Index APIs
            apis = await self._index_apis()
            results["nodes_created"] += apis["nodes"]
            results["edges_created"] += apis["edges"]
            
            # Index devices
            devices = await self._index_devices()
            results["nodes_created"] += devices["nodes"]
            results["edges_created"] += devices["edges"]
            
            # Create cross-system relationships
            relationships = await self._create_relationships()
            results["edges_created"] += relationships["edges"]
            
            logger.info(f"Graph built: {results['nodes_created']} nodes, {results['edges_created']} edges")
            
        except Exception as e:
            logger.error(f"Graph build failed: {e}")
            results["errors"].append(str(e))
        
        return results
    
    async def _index_systems(self) -> Dict[str, int]:
        """Index all systems as nodes."""
        systems = await self._registry.list_systems()
        nodes = 0
        edges = 0
        
        for system in systems:
            node = Node(
                node_type=NodeType.SYSTEM,
                name=system.name,
                properties={
                    "type": system.type.value,
                    "url": system.url,
                    "status": system.status,
                    "description": system.description
                }
            )
            await self._graph.add_node(node)
            nodes += 1
        
        return {"nodes": nodes, "edges": edges}
    
    async def _index_agents(self) -> Dict[str, int]:
        """Index all agents as nodes."""
        agents = await self._registry.list_agents()
        nodes = 0
        edges = 0
        
        for agent in agents:
            node = Node(
                node_type=NodeType.AGENT,
                name=agent.name,
                properties={
                    "type": agent.type,
                    "status": agent.status,
                    "version": agent.version,
                    "capabilities": agent.capabilities
                }
            )
            agent_node = await self._graph.add_node(node)
            nodes += 1
            
            # Link to MAS system
            mas_node = await self._graph.find_node_by_name("MAS", NodeType.SYSTEM)
            if mas_node:
                edge = Edge(
                    source_id=mas_node.id,
                    target_id=agent_node.id,
                    edge_type=EdgeType.CONTAINS
                )
                await self._graph.add_edge(edge)
                edges += 1
        
        return {"nodes": nodes, "edges": edges}
    
    async def _index_apis(self) -> Dict[str, int]:
        """Index all APIs as nodes and link to systems."""
        apis = await self._registry.list_apis()
        nodes = 0
        edges = 0
        
        for api in apis:
            node = Node(
                node_type=NodeType.API,
                name=f"{api.method} {api.path}",
                properties={
                    "method": api.method,
                    "path": api.path,
                    "description": api.description,
                    "tags": api.tags,
                    "auth_required": api.auth_required
                }
            )
            api_node = await self._graph.add_node(node)
            nodes += 1
            
            # Link to system
            if api.system_id:
                # Find system node
                systems = await self._registry.list_systems()
                for system in systems:
                    if system.id == api.system_id:
                        system_node = await self._graph.find_node_by_name(system.name, NodeType.SYSTEM)
                        if system_node:
                            edge = Edge(
                                source_id=system_node.id,
                                target_id=api_node.id,
                                edge_type=EdgeType.CONTAINS
                            )
                            await self._graph.add_edge(edge)
                            edges += 1
                        break
        
        return {"nodes": nodes, "edges": edges}
    
    async def _index_devices(self) -> Dict[str, int]:
        """Index all devices as nodes."""
        devices = await self._registry.list_devices()
        nodes = 0
        edges = 0
        
        for device in devices:
            node = Node(
                node_type=NodeType.DEVICE,
                name=device.name,
                properties={
                    "device_id": device.device_id,
                    "type": device.type.value,
                    "firmware": device.firmware_version,
                    "hardware": device.hardware_version,
                    "status": device.status
                }
            )
            device_node = await self._graph.add_node(node)
            nodes += 1
            
            # Link to MycoBrain system
            mycobrain = await self._graph.find_node_by_name("MycoBrain", NodeType.SYSTEM)
            if mycobrain:
                edge = Edge(
                    source_id=mycobrain.id,
                    target_id=device_node.id,
                    edge_type=EdgeType.MANAGES
                )
                await self._graph.add_edge(edge)
                edges += 1
        
        return {"nodes": nodes, "edges": edges}
    
    async def _create_relationships(self) -> Dict[str, int]:
        """Create cross-system relationship edges."""
        edges = 0
        
        # System relationships
        system_relationships = [
            ("MAS", "MINDEX", EdgeType.DEPENDS_ON, "memory and indexing"),
            ("MAS", "NatureOS", EdgeType.CALLS, "device control"),
            ("Website", "MAS", EdgeType.CALLS, "agent operations"),
            ("Website", "MINDEX", EdgeType.CALLS, "memory queries"),
            ("NatureOS", "MycoBrain", EdgeType.MANAGES, "device management"),
            ("MAS", "NLM", EdgeType.CALLS, "model inference"),
            ("MINDEX", "NLM", EdgeType.CALLS, "embedding generation"),
        ]
        
        for source, target, edge_type, description in system_relationships:
            source_node = await self._graph.find_node_by_name(source, NodeType.SYSTEM)
            target_node = await self._graph.find_node_by_name(target, NodeType.SYSTEM)
            
            if source_node and target_node:
                edge = Edge(
                    source_id=source_node.id,
                    target_id=target_node.id,
                    edge_type=edge_type,
                    properties={"description": description}
                )
                await self._graph.add_edge(edge)
                edges += 1
        
        # Create database nodes and relationships
        databases = [
            ("PostgreSQL", "MINDEX", "ledger, registry, graph storage"),
            ("Redis", "MAS", "memory cache, session storage"),
            ("Qdrant", "MINDEX", "vector embeddings"),
        ]
        
        for db_name, system_name, purpose in databases:
            db_node = Node(
                node_type=NodeType.DATABASE,
                name=db_name,
                properties={"purpose": purpose}
            )
            db_node = await self._graph.add_node(db_node)
            
            system_node = await self._graph.find_node_by_name(system_name, NodeType.SYSTEM)
            if system_node:
                edge = Edge(
                    source_id=system_node.id,
                    target_id=db_node.id,
                    edge_type=EdgeType.CONNECTS_TO,
                    properties={"purpose": purpose}
                )
                await self._graph.add_edge(edge)
                edges += 1
        
        return {"edges": edges}


# Singleton
_indexer = None


def get_graph_indexer() -> GraphIndexer:
    """Get singleton indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = GraphIndexer()
    return _indexer


async def build_knowledge_graph() -> Dict[str, Any]:
    """Convenience function to build the full knowledge graph."""
    indexer = get_graph_indexer()
    return await indexer.build_graph()
