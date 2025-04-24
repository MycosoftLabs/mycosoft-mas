from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import networkx as nx
import json
import asyncio
import websockets

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.agent_metadata = {}
        self.system_state = {
            "last_update": None,
            "agent_count": 0,
            "active_agents": set(),
            "system_status": "initializing"
        }
        self.websocket_clients: Set[websockets.WebSocketServerProtocol] = set()

    async def initialize(self) -> bool:
        """
        Initialize the Knowledge Graph.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Initialize the graph
            self.graph = nx.DiGraph()
            self.agent_metadata = {}
            self.system_state = {
                "last_update": datetime.now().isoformat(),
                "agent_count": 0,
                "active_agents": set(),
                "system_status": "active"
            }
            self.websocket_clients = set()
            
            return True
        except Exception as e:
            print(f"Failed to initialize Knowledge Graph: {str(e)}")
            return False

    async def add_agent(self, agent_id: str, metadata: Dict[str, Any]) -> None:
        """Add an agent to the knowledge graph."""
        self.graph.add_node(agent_id)
        self.agent_metadata[agent_id] = metadata
        self.system_state["agent_count"] = len(self.graph.nodes)
        self.system_state["active_agents"].add(agent_id)
        self._update_system_state()
        await self._broadcast_update()

    async def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the knowledge graph."""
        if agent_id in self.graph:
            self.graph.remove_node(agent_id)
            del self.agent_metadata[agent_id]
            self.system_state["agent_count"] = len(self.graph.nodes)
            self.system_state["active_agents"].discard(agent_id)
            self._update_system_state()
            await self._broadcast_update()

    async def add_relationship(self, source: str, target: str, relationship_type: str) -> None:
        """Add a relationship between two agents."""
        if source in self.graph and target in self.graph:
            self.graph.add_edge(source, target, type=relationship_type)
            await self._broadcast_update()

    async def remove_relationship(self, source: str, target: str) -> None:
        """Remove a relationship between two agents."""
        if source in self.graph and target in self.graph:
            if self.graph.has_edge(source, target):
                self.graph.remove_edge(source, target)
                await self._broadcast_update()

    def get_agent_metadata(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific agent."""
        return self.agent_metadata.get(agent_id)

    def get_agent_relationships(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a specific agent."""
        relationships = []
        if agent_id in self.graph:
            for neighbor in self.graph.neighbors(agent_id):
                edge_data = self.graph.get_edge_data(agent_id, neighbor)
                relationships.append({
                    "target": neighbor,
                    "type": edge_data.get("type", "unknown")
                })
        return relationships

    def get_system_state(self) -> Dict[str, Any]:
        """Get the current system state."""
        return self.system_state

    def _update_system_state(self) -> None:
        """Update the system state with current information."""
        self.system_state["last_update"] = datetime.now().isoformat()
        if len(self.system_state["active_agents"]) == 0:
            self.system_state["system_status"] = "inactive"
        else:
            self.system_state["system_status"] = "active"

    async def _broadcast_update(self) -> None:
        """Broadcast the current state of the knowledge graph to all connected clients."""
        if not self.websocket_clients:
            return

        message = {
            "type": "knowledge_graph",
            "graph": {
                "nodes": [
                    {
                        "id": node,
                        "metadata": self.agent_metadata[node]
                    }
                    for node in self.graph.nodes
                ],
                "edges": [
                    {
                        "source": source,
                        "target": target,
                        "type": data.get("type", "unknown")
                    }
                    for source, target, data in self.graph.edges(data=True)
                ],
                "system_state": self.system_state
            }
        }

        disconnected = set()
        for client in self.websocket_clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.add(client)

        self.websocket_clients -= disconnected

    async def handle_websocket(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Handle a new WebSocket connection."""
        self.websocket_clients.add(websocket)
        try:
            # Send initial state
            await self._broadcast_update()
            # Keep connection alive
            async for message in websocket:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.websocket_clients.remove(websocket)

    def to_json(self) -> str:
        """Convert the knowledge graph to JSON format."""
        data = {
            "nodes": [
                {
                    "id": node,
                    "metadata": self.agent_metadata[node]
                }
                for node in self.graph.nodes
            ],
            "edges": [
                {
                    "source": source,
                    "target": target,
                    "type": data.get("type", "unknown")
                }
                for source, target, data in self.graph.edges(data=True)
            ],
            "system_state": self.system_state
        }
        return json.dumps(data, indent=2)

    def from_json(self, json_data: str) -> None:
        """Load the knowledge graph from JSON format."""
        data = json.loads(json_data)
        self.graph.clear()
        self.agent_metadata.clear()
        
        for node in data["nodes"]:
            self.graph.add_node(node["id"])
            self.agent_metadata[node["id"]] = node["metadata"]
        
        for edge in data["edges"]:
            self.graph.add_edge(edge["source"], edge["target"], type=edge["type"])
        
        self.system_state = data["system_state"]

    async def get_graph_data(self) -> Dict[str, Any]:
        """Get the current state of the knowledge graph in a format suitable for the dashboard."""
        return {
            "nodes": [
                {
                    "id": node,
                    "label": node,
                    "title": json.dumps(self.agent_metadata.get(node, {}), indent=2),
                    "color": {
                        "background": "#97C2FC",
                        "border": "#2B7CE9",
                        "highlight": {
                            "background": "#D2E5FF",
                            "border": "#2B7CE9"
                        }
                    }
                }
                for node in self.graph.nodes
            ],
            "edges": [
                {
                    "from": source,
                    "to": target,
                    "label": data.get("type", "unknown"),
                    "arrows": "to",
                    "color": {
                        "color": "#848484",
                        "highlight": "#848484"
                    }
                }
                for source, target, data in self.graph.edges(data=True)
            ]
        } 