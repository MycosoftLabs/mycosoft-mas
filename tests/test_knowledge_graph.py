"""
Test Knowledge Graph - February 4, 2026
Verifies node/edge persistence, path finding, and graph operations.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import uuid4
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class NodeType(str, Enum):
    SYSTEM = "system"
    AGENT = "agent"
    API = "api"
    SERVICE = "service"
    DATABASE = "database"
    DEVICE = "device"


class EdgeType(str, Enum):
    CONTAINS = "contains"
    USES = "uses"
    CALLS = "calls"
    STORES_IN = "stores_in"
    DEPLOYED_ON = "deployed_on"


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def ok(self, msg: str):
        self.passed += 1
        print(f"  [PASS] {msg}")
    
    def fail(self, msg: str, error: str = None):
        self.failed += 1
        self.errors.append(f"{msg}: {error}")
        print(f"  [FAIL] {msg}: {error}")


class MockKnowledgeGraph:
    """Mock implementation of knowledge graph for testing."""
    
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Dict] = []
    
    async def add_node(
        self,
        node_id: str,
        name: str,
        node_type: NodeType,
        properties: Dict = None
    ) -> Dict:
        node = {
            "id": node_id,
            "name": name,
            "type": node_type.value,
            "properties": properties or {},
            "created_at": datetime.now().isoformat()
        }
        self.nodes[node_id] = node
        return node
    
    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        properties: Dict = None
    ) -> Optional[Dict]:
        if source_id not in self.nodes or target_id not in self.nodes:
            return None
        
        edge = {
            "id": str(uuid4()),
            "source_id": source_id,
            "target_id": target_id,
            "type": edge_type.value,
            "properties": properties or {},
            "created_at": datetime.now().isoformat()
        }
        self.edges.append(edge)
        return edge
    
    async def get_node(self, node_id: str) -> Optional[Dict]:
        return self.nodes.get(node_id)
    
    async def find_by_name(self, name: str) -> Optional[Dict]:
        for node in self.nodes.values():
            if node["name"] == name:
                return node
        return None
    
    async def get_neighbors(self, node_id: str, direction: str = "both") -> List[str]:
        neighbors = set()
        for edge in self.edges:
            if direction in ("both", "outgoing") and edge["source_id"] == node_id:
                neighbors.add(edge["target_id"])
            if direction in ("both", "incoming") and edge["target_id"] == node_id:
                neighbors.add(edge["source_id"])
        return list(neighbors)
    
    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5
    ) -> Optional[List[str]]:
        """BFS path finding."""
        if start_id == end_id:
            return [start_id]
        
        visited = {start_id}
        queue = [[start_id]]
        
        while queue:
            path = queue.pop(0)
            if len(path) > max_depth:
                continue
            
            current = path[-1]
            neighbors = await self.get_neighbors(current, "outgoing")
            
            for neighbor in neighbors:
                if neighbor == end_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        
        return None
    
    async def get_subgraph(self, center_id: str, depth: int = 2) -> Dict:
        """Get subgraph around a node."""
        nodes_in_subgraph = set()
        to_visit = [(center_id, 0)]
        
        while to_visit:
            node_id, current_depth = to_visit.pop(0)
            if node_id in nodes_in_subgraph or current_depth > depth:
                continue
            
            nodes_in_subgraph.add(node_id)
            if current_depth < depth:
                neighbors = await self.get_neighbors(node_id)
                for n in neighbors:
                    to_visit.append((n, current_depth + 1))
        
        subgraph_edges = [
            e for e in self.edges
            if e["source_id"] in nodes_in_subgraph and e["target_id"] in nodes_in_subgraph
        ]
        
        return {
            "nodes": [self.nodes[n] for n in nodes_in_subgraph if n in self.nodes],
            "edges": subgraph_edges
        }
    
    async def get_stats(self) -> Dict:
        node_types = {}
        for node in self.nodes.values():
            t = node["type"]
            node_types[t] = node_types.get(t, 0) + 1
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": node_types
        }


async def test_node_operations():
    """Test node CRUD operations."""
    result = TestResult("Node Operations")
    print("\n=== Test: Node Operations ===")
    
    graph = MockKnowledgeGraph()
    
    # Test 1: Add node
    node = await graph.add_node("mas-1", "MAS", NodeType.SYSTEM, {"version": "2.0"})
    if node and node["name"] == "MAS":
        result.ok("Node created successfully")
    else:
        result.fail("Create node", "Failed to create node")
    
    # Test 2: Get node by ID
    retrieved = await graph.get_node("mas-1")
    if retrieved and retrieved["id"] == "mas-1":
        result.ok("Node retrieved by ID")
    else:
        result.fail("Get node", "Failed to retrieve node")
    
    # Test 3: Find by name
    found = await graph.find_by_name("MAS")
    if found and found["id"] == "mas-1":
        result.ok("Node found by name")
    else:
        result.fail("Find by name", "Failed to find node")
    
    # Test 4: Node properties
    if retrieved["properties"].get("version") == "2.0":
        result.ok("Node properties stored correctly")
    else:
        result.fail("Properties", "Properties not stored correctly")
    
    # Test 5: Multiple nodes
    await graph.add_node("agent-1", "MYCA", NodeType.AGENT)
    await graph.add_node("api-1", "Memory API", NodeType.API)
    stats = await graph.get_stats()
    if stats["total_nodes"] == 3:
        result.ok(f"Multiple nodes created: {stats['total_nodes']}")
    else:
        result.fail("Node count", f"Expected 3, got {stats['total_nodes']}")
    
    return result


async def test_edge_operations():
    """Test edge CRUD operations."""
    result = TestResult("Edge Operations")
    print("\n=== Test: Edge Operations ===")
    
    graph = MockKnowledgeGraph()
    
    # Create nodes first
    await graph.add_node("mas-1", "MAS", NodeType.SYSTEM)
    await graph.add_node("agent-1", "MYCA", NodeType.AGENT)
    await graph.add_node("api-1", "Memory API", NodeType.API)
    
    # Test 1: Add edge
    edge = await graph.add_edge("mas-1", "agent-1", EdgeType.CONTAINS)
    if edge and edge["type"] == "contains":
        result.ok("Edge created successfully")
    else:
        result.fail("Create edge", "Failed to create edge")
    
    # Test 2: Add edge with properties
    edge2 = await graph.add_edge("agent-1", "api-1", EdgeType.CALLS, {"frequency": "high"})
    if edge2 and edge2["properties"].get("frequency") == "high":
        result.ok("Edge with properties created")
    else:
        result.fail("Edge properties", "Failed to store edge properties")
    
    # Test 3: Edge to non-existent node fails
    edge3 = await graph.add_edge("mas-1", "nonexistent", EdgeType.USES)
    if edge3 is None:
        result.ok("Edge to non-existent node rejected")
    else:
        result.fail("Validation", "Should reject edge to non-existent node")
    
    # Test 4: Edge count
    stats = await graph.get_stats()
    if stats["total_edges"] == 2:
        result.ok(f"Edge count correct: {stats['total_edges']}")
    else:
        result.fail("Edge count", f"Expected 2, got {stats['total_edges']}")
    
    return result


async def test_path_finding():
    """Test path finding between nodes."""
    result = TestResult("Path Finding")
    print("\n=== Test: Path Finding ===")
    
    graph = MockKnowledgeGraph()
    
    # Create a graph: MAS -> MYCA -> Memory API -> Redis
    await graph.add_node("mas", "MAS", NodeType.SYSTEM)
    await graph.add_node("myca", "MYCA", NodeType.AGENT)
    await graph.add_node("memory-api", "Memory API", NodeType.API)
    await graph.add_node("redis", "Redis", NodeType.DATABASE)
    await graph.add_node("postgres", "PostgreSQL", NodeType.DATABASE)
    
    await graph.add_edge("mas", "myca", EdgeType.CONTAINS)
    await graph.add_edge("myca", "memory-api", EdgeType.CALLS)
    await graph.add_edge("memory-api", "redis", EdgeType.STORES_IN)
    await graph.add_edge("memory-api", "postgres", EdgeType.STORES_IN)
    
    # Test 1: Direct path
    path = await graph.find_path("myca", "memory-api")
    if path == ["myca", "memory-api"]:
        result.ok("Direct path found")
    else:
        result.fail("Direct path", f"Expected ['myca', 'memory-api'], got {path}")
    
    # Test 2: Multi-hop path
    path2 = await graph.find_path("mas", "redis")
    if path2 and len(path2) == 4:
        result.ok(f"Multi-hop path found: {' -> '.join(path2)}")
    else:
        result.fail("Multi-hop path", f"Expected 4 nodes, got {path2}")
    
    # Test 3: Same node path
    path3 = await graph.find_path("mas", "mas")
    if path3 == ["mas"]:
        result.ok("Same node path returns single node")
    else:
        result.fail("Same node", f"Expected ['mas'], got {path3}")
    
    # Test 4: No path
    path4 = await graph.find_path("redis", "mas")  # No reverse edges
    if path4 is None:
        result.ok("No path returns None (correct)")
    else:
        result.fail("No path", f"Expected None, got {path4}")
    
    return result


async def test_neighbor_queries():
    """Test neighbor queries."""
    result = TestResult("Neighbor Queries")
    print("\n=== Test: Neighbor Queries ===")
    
    graph = MockKnowledgeGraph()
    
    # Create graph
    await graph.add_node("center", "Center", NodeType.SYSTEM)
    await graph.add_node("out1", "Outgoing1", NodeType.AGENT)
    await graph.add_node("out2", "Outgoing2", NodeType.AGENT)
    await graph.add_node("in1", "Incoming1", NodeType.SERVICE)
    
    await graph.add_edge("center", "out1", EdgeType.CONTAINS)
    await graph.add_edge("center", "out2", EdgeType.CONTAINS)
    await graph.add_edge("in1", "center", EdgeType.CALLS)
    
    # Test 1: Outgoing neighbors
    outgoing = await graph.get_neighbors("center", "outgoing")
    if set(outgoing) == {"out1", "out2"}:
        result.ok(f"Outgoing neighbors: {outgoing}")
    else:
        result.fail("Outgoing", f"Expected ['out1', 'out2'], got {outgoing}")
    
    # Test 2: Incoming neighbors
    incoming = await graph.get_neighbors("center", "incoming")
    if incoming == ["in1"]:
        result.ok(f"Incoming neighbors: {incoming}")
    else:
        result.fail("Incoming", f"Expected ['in1'], got {incoming}")
    
    # Test 3: Both directions
    both = await graph.get_neighbors("center", "both")
    if set(both) == {"out1", "out2", "in1"}:
        result.ok(f"Both directions: {both}")
    else:
        result.fail("Both", f"Expected 3 neighbors, got {both}")
    
    return result


async def test_subgraph_extraction():
    """Test subgraph extraction around a node."""
    result = TestResult("Subgraph Extraction")
    print("\n=== Test: Subgraph Extraction ===")
    
    graph = MockKnowledgeGraph()
    
    # Create larger graph
    nodes = [
        ("center", "Center", NodeType.SYSTEM),
        ("level1-a", "Level1A", NodeType.AGENT),
        ("level1-b", "Level1B", NodeType.AGENT),
        ("level2-a", "Level2A", NodeType.API),
        ("level2-b", "Level2B", NodeType.API),
        ("level3", "Level3", NodeType.DATABASE),
    ]
    for n in nodes:
        await graph.add_node(*n)
    
    await graph.add_edge("center", "level1-a", EdgeType.CONTAINS)
    await graph.add_edge("center", "level1-b", EdgeType.CONTAINS)
    await graph.add_edge("level1-a", "level2-a", EdgeType.CALLS)
    await graph.add_edge("level1-b", "level2-b", EdgeType.CALLS)
    await graph.add_edge("level2-a", "level3", EdgeType.STORES_IN)
    
    # Test 1: Depth 1 subgraph
    sub1 = await graph.get_subgraph("center", depth=1)
    if len(sub1["nodes"]) == 3:  # center + 2 level1
        result.ok(f"Depth 1 subgraph: {len(sub1['nodes'])} nodes")
    else:
        result.fail("Depth 1", f"Expected 3 nodes, got {len(sub1['nodes'])}")
    
    # Test 2: Depth 2 subgraph
    sub2 = await graph.get_subgraph("center", depth=2)
    if len(sub2["nodes"]) == 5:  # center + 2 level1 + 2 level2
        result.ok(f"Depth 2 subgraph: {len(sub2['nodes'])} nodes")
    else:
        result.fail("Depth 2", f"Expected 5 nodes, got {len(sub2['nodes'])}")
    
    # Test 3: Subgraph edges
    if len(sub2["edges"]) == 4:  # edges within subgraph only
        result.ok(f"Subgraph edges: {len(sub2['edges'])}")
    else:
        result.fail("Edges", f"Expected 4 edges, got {len(sub2['edges'])}")
    
    return result


async def test_graph_statistics():
    """Test graph statistics."""
    result = TestResult("Graph Statistics")
    print("\n=== Test: Graph Statistics ===")
    
    graph = MockKnowledgeGraph()
    
    # Create diverse graph
    await graph.add_node("s1", "System1", NodeType.SYSTEM)
    await graph.add_node("s2", "System2", NodeType.SYSTEM)
    await graph.add_node("a1", "Agent1", NodeType.AGENT)
    await graph.add_node("a2", "Agent2", NodeType.AGENT)
    await graph.add_node("a3", "Agent3", NodeType.AGENT)
    await graph.add_node("api1", "API1", NodeType.API)
    await graph.add_node("db1", "DB1", NodeType.DATABASE)
    
    await graph.add_edge("s1", "a1", EdgeType.CONTAINS)
    await graph.add_edge("s1", "a2", EdgeType.CONTAINS)
    await graph.add_edge("s2", "a3", EdgeType.CONTAINS)
    await graph.add_edge("a1", "api1", EdgeType.CALLS)
    await graph.add_edge("api1", "db1", EdgeType.STORES_IN)
    
    stats = await graph.get_stats()
    
    # Test 1: Total nodes
    if stats["total_nodes"] == 7:
        result.ok(f"Total nodes: {stats['total_nodes']}")
    else:
        result.fail("Total nodes", f"Expected 7, got {stats['total_nodes']}")
    
    # Test 2: Total edges
    if stats["total_edges"] == 5:
        result.ok(f"Total edges: {stats['total_edges']}")
    else:
        result.fail("Total edges", f"Expected 5, got {stats['total_edges']}")
    
    # Test 3: Node type counts
    if stats["node_types"].get("system") == 2:
        result.ok("System node count: 2")
    else:
        result.fail("System count", f"Expected 2, got {stats['node_types'].get('system')}")
    
    if stats["node_types"].get("agent") == 3:
        result.ok("Agent node count: 3")
    else:
        result.fail("Agent count", f"Expected 3, got {stats['node_types'].get('agent')}")
    
    return result


async def run_all_tests():
    """Run all knowledge graph tests."""
    print("=" * 60)
    print("KNOWLEDGE GRAPH TEST SUITE")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    
    results.append(await test_node_operations())
    results.append(await test_edge_operations())
    results.append(await test_path_finding())
    results.append(await test_neighbor_queries())
    results.append(await test_subgraph_extraction())
    results.append(await test_graph_statistics())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    
    for r in results:
        status = "PASS" if r.failed == 0 else "FAIL"
        print(f"  [{status}] {r.name}: {r.passed} passed, {r.failed} failed")
    
    print("-" * 60)
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    
    return total_failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
