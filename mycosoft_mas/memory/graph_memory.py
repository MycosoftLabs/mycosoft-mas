"""Knowledge graph memory. Created: February 3, 2026"""
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

class GraphNode:
    def __init__(self, node_id: UUID, node_type: str, properties: Dict[str, Any]):
        self.node_id = node_id
        self.node_type = node_type
        self.properties = properties

class GraphEdge:
    def __init__(self, source: UUID, target: UUID, relationship: str, properties: Dict[str, Any] = None):
        self.source = source
        self.target = target
        self.relationship = relationship
        self.properties = properties or {}

class GraphMemory:
    """Knowledge graph for structured memory."""
    
    def __init__(self):
        self._nodes: Dict[UUID, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._adjacency: Dict[UUID, Set[UUID]] = {}
    
    def add_node(self, node_type: str, properties: Dict[str, Any]) -> UUID:
        node_id = uuid4()
        self._nodes[node_id] = GraphNode(node_id, node_type, properties)
        self._adjacency[node_id] = set()
        return node_id
    
    def add_edge(self, source: UUID, target: UUID, relationship: str, properties: Dict[str, Any] = None) -> bool:
        if source not in self._nodes or target not in self._nodes:
            return False
        self._edges.append(GraphEdge(source, target, relationship, properties))
        self._adjacency[source].add(target)
        return True
    
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
