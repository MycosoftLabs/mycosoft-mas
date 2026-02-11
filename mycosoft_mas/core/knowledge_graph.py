from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import networkx as nx

try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    websockets = None


class KnowledgeGraph:
    """
    In-memory knowledge graph for agents + relationships.

    The pytest suite expects a synchronous API:
    - add_agent(agent_obj), remove_agent(agent_id)
    - add_relationship(source_id, target_id, relationship_type)
    - to_json() returns a dict (not a JSON string)
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.agent_metadata: Dict[str, Dict[str, Any]] = {}
        self.last_update = datetime.now().isoformat()
        self.websocket_clients: Set[Any] = set()

    @property
    def agent_count(self) -> int:
        return len(self.graph.nodes)

    @property
    def active_agents(self) -> int:
        # In this implementation, nodes are the active set.
        return len(self.graph.nodes)

    async def initialize(self) -> bool:
        self.graph = nx.DiGraph()
        self.agent_metadata = {}
        self.last_update = datetime.now().isoformat()
        self.websocket_clients = set()
        return True

    # --- Synchronous API used by tests ----------------------------------------
    def add_agent(self, agent: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an agent node.

        Supports both call styles:
        - add_agent(agent_obj)  (used by unit tests)
        - add_agent(agent_id: str, metadata: dict) (used by some services)
        """
        if isinstance(agent, str):
            agent_id = agent
            meta = metadata or {}
        else:
            agent_id = getattr(agent, "agent_id", None)
            if not agent_id:
                raise ValueError("agent.agent_id is required")
            meta = {
                "agent_id": agent_id,
                "capabilities": list(getattr(agent, "capabilities", []) or []),
            }

        self.graph.add_node(agent_id)
        self.agent_metadata[agent_id] = meta
        self.last_update = datetime.now().isoformat()

    def remove_agent(self, agent_id: str) -> None:
        if agent_id in self.graph:
            self.graph.remove_node(agent_id)
        self.agent_metadata.pop(agent_id, None)
        self.last_update = datetime.now().isoformat()

    def add_relationship(self, source: str, target: str, relationship_type: str) -> None:
        if source in self.graph and target in self.graph:
            self.graph.add_edge(source, target, type=relationship_type)
            self.last_update = datetime.now().isoformat()

    def remove_relationship(self, source: str, target: str) -> None:
        if self.graph.has_edge(source, target):
            self.graph.remove_edge(source, target)
            self.last_update = datetime.now().isoformat()

    def get_agent_relationships(self, agent_id: str) -> List[Dict[str, Any]]:
        relationships: List[Dict[str, Any]] = []
        if agent_id in self.graph:
            for neighbor in self.graph.neighbors(agent_id):
                edge_data = self.graph.get_edge_data(agent_id, neighbor) or {}
                relationships.append({"target": neighbor, "type": edge_data.get("type", "unknown")})
        return relationships

    def get_agent_metadata(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.agent_metadata.get(agent_id)

    def to_json(self) -> Dict[str, Any]:
        nodes = [{"id": node, "metadata": self.agent_metadata.get(node, {})} for node in self.graph.nodes]
        edges = [
            {"source": source, "target": target, "type": data.get("type", "unknown")}
            for source, target, data in self.graph.edges(data=True)
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "last_update": self.last_update,
                "agent_count": self.agent_count,
                "active_agents": self.active_agents,
            },
        }

    def from_json(self, data: Dict[str, Any]) -> None:
        self.graph.clear()
        self.agent_metadata.clear()

        for node in data.get("nodes", []):
            node_id = node.get("id")
            if not node_id:
                continue
            self.graph.add_node(node_id)
            self.agent_metadata[node_id] = node.get("metadata", {}) or {}

        for edge in data.get("edges", []):
            src = edge.get("source")
            tgt = edge.get("target")
            if not src or not tgt:
                continue
            self.graph.add_edge(src, tgt, type=edge.get("type", "unknown"))

        self.last_update = (data.get("metadata") or {}).get("last_update") or datetime.now().isoformat()

    # --- Optional websocket helpers -------------------------------------------
    async def _broadcast_update(self) -> None:
        if not websockets or not self.websocket_clients:
            return
        payload = json.dumps({"type": "knowledge_graph", "graph": self.to_json()})
        disconnected: Set[Any] = set()
        for client in self.websocket_clients:
            try:
                await client.send(payload)
            except Exception:
                disconnected.add(client)
        self.websocket_clients -= disconnected

    async def handle_websocket(self, websocket: Any) -> None:
        if not websockets:
            return
        self.websocket_clients.add(websocket)
        try:
            await self._broadcast_update()
            async for _ in websocket:
                await asyncio.sleep(0)
        finally:
            self.websocket_clients.discard(websocket)