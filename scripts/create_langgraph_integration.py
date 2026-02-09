"""Helper script to create langgraph_integration.py"""
import os

content = '''"""
LangGraph Integration for MYCA Voice System
Created: February 4, 2026

Complex multi-agent orchestration using LangGraph patterns.
"""

import logging
from typing import Dict, List, Optional, Any, Callable, TypedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Types of nodes in the graph."""
    AGENT = "agent"
    TOOL = "tool"
    ROUTER = "router"
    CONDITIONAL = "conditional"
    END = "end"


class GraphState(TypedDict, total=False):
    """State passed through the graph."""
    messages: List[Dict[str, str]]
    current_agent: str
    task: str
    result: Any
    error: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class GraphNode:
    """A node in the agent graph."""
    node_id: str
    name: str
    node_type: NodeType
    handler: Optional[Callable] = None
    next_nodes: List[str] = field(default_factory=list)
    condition: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """An edge connecting nodes."""
    from_node: str
    to_node: str
    condition: Optional[str] = None


class AgentGraph:
    """
    LangGraph-style agent graph for complex orchestration.
    
    Features:
    - Multi-agent workflows
    - Conditional routing
    - State management
    - Parallel execution
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.entry_point: Optional[str] = None
        self.state: GraphState = {}
        
        logger.info(f"AgentGraph '{name}' initialized")
    
    def add_node(
        self,
        node_id: str,
        name: str,
        node_type: NodeType = NodeType.AGENT,
        handler: Optional[Callable] = None,
    ) -> "AgentGraph":
        """Add a node to the graph."""
        node = GraphNode(
            node_id=node_id,
            name=name,
            node_type=node_type,
            handler=handler,
        )
        self.nodes[node_id] = node
        logger.debug(f"Added node: {node_id}")
        return self
    
    def add_edge(self, from_node: str, to_node: str, condition: Optional[str] = None) -> "AgentGraph":
        """Add an edge between nodes."""
        edge = GraphEdge(from_node=from_node, to_node=to_node, condition=condition)
        self.edges.append(edge)
        
        if from_node in self.nodes:
            self.nodes[from_node].next_nodes.append(to_node)
        
        logger.debug(f"Added edge: {from_node} -> {to_node}")
        return self
    
    def add_conditional_edges(
        self,
        from_node: str,
        condition_fn: Callable[[GraphState], str],
        destinations: Dict[str, str],
    ) -> "AgentGraph":
        """Add conditional edges based on state."""
        if from_node in self.nodes:
            self.nodes[from_node].condition = condition_fn
            self.nodes[from_node].metadata["destinations"] = destinations
            
            for dest in destinations.values():
                self.edges.append(GraphEdge(from_node=from_node, to_node=dest, condition="conditional"))
        
        return self
    
    def set_entry_point(self, node_id: str) -> "AgentGraph":
        """Set the entry point of the graph."""
        self.entry_point = node_id
        return self
    
    async def run(self, initial_state: Optional[GraphState] = None) -> GraphState:
        """Execute the graph."""
        self.state = initial_state or {}
        self.state.setdefault("messages", [])
        self.state.setdefault("metadata", {})
        
        if not self.entry_point:
            raise ValueError("No entry point set")
        
        current_node = self.entry_point
        visited = set()
        max_iterations = 100
        iterations = 0
        
        logger.info(f"Starting graph execution from: {current_node}")
        
        while current_node and iterations < max_iterations:
            iterations += 1
            
            if current_node == "END" or current_node not in self.nodes:
                break
            
            node = self.nodes[current_node]
            
            # Execute node handler
            if node.handler:
                try:
                    result = await node.handler(self.state)
                    if isinstance(result, dict):
                        self.state.update(result)
                except Exception as e:
                    self.state["error"] = str(e)
                    logger.error(f"Node {current_node} failed: {e}")
                    break
            
            # Determine next node
            if node.condition:
                # Conditional routing
                destinations = node.metadata.get("destinations", {})
                route = node.condition(self.state)
                current_node = destinations.get(route, "END")
            elif node.next_nodes:
                current_node = node.next_nodes[0]
            else:
                current_node = None
            
            visited.add(node.node_id)
        
        logger.info(f"Graph execution completed after {iterations} iterations")
        return self.state
    
    def compile(self) -> Dict[str, Any]:
        """Compile the graph to a serializable format."""
        return {
            "name": self.name,
            "nodes": [
                {
                    "id": n.node_id,
                    "name": n.name,
                    "type": n.node_type.value,
                    "next": n.next_nodes,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {"from": e.from_node, "to": e.to_node, "condition": e.condition}
                for e in self.edges
            ],
            "entry_point": self.entry_point,
        }


class VoiceAgentGraph(AgentGraph):
    """Pre-configured graph for voice agent workflows."""
    
    def __init__(self):
        super().__init__("voice_agent_graph")
        self._setup_default_nodes()
    
    def _setup_default_nodes(self):
        """Set up default voice workflow nodes."""
        # Entry: Voice input processing
        self.add_node("input", "Voice Input", NodeType.AGENT)
        
        # Intent classification
        self.add_node("classify", "Intent Classifier", NodeType.ROUTER)
        
        # Agent nodes for different intents
        self.add_node("coding", "Coding Agent", NodeType.AGENT)
        self.add_node("learning", "Learning Agent", NodeType.AGENT)
        self.add_node("corporate", "Corporate Agent", NodeType.AGENT)
        self.add_node("infrastructure", "Infrastructure Agent", NodeType.AGENT)
        self.add_node("security", "Security Agent", NodeType.AGENT)
        self.add_node("general", "General Agent", NodeType.AGENT)
        
        # Response generation
        self.add_node("respond", "Response Generator", NodeType.AGENT)
        
        # Set up edges
        self.add_edge("input", "classify")
        
        # Conditional edges from classifier
        self.add_conditional_edges(
            "classify",
            self._route_by_intent,
            {
                "coding": "coding",
                "learning": "learning",
                "corporate": "corporate",
                "infrastructure": "infrastructure",
                "security": "security",
                "general": "general",
            }
        )
        
        # All agents connect to response
        for agent in ["coding", "learning", "corporate", "infrastructure", "security", "general"]:
            self.add_edge(agent, "respond")
        
        self.add_edge("respond", "END")
        self.set_entry_point("input")
    
    @staticmethod
    def _route_by_intent(state: GraphState) -> str:
        """Route based on classified intent."""
        intent = state.get("metadata", {}).get("intent_category", "general")
        valid_intents = ["coding", "learning", "corporate", "infrastructure", "security"]
        return intent if intent in valid_intents else "general"


class MultiAgentOrchestrator:
    """
    Orchestrator for complex multi-agent workflows.
    
    Uses LangGraph patterns for:
    - Supervisor-worker patterns
    - Hierarchical agent teams
    - Parallel execution
    """
    
    def __init__(self):
        self.graphs: Dict[str, AgentGraph] = {}
        self.active_executions: Dict[str, GraphState] = {}
        
        # Create default graphs
        self.graphs["voice"] = VoiceAgentGraph()
        
        logger.info("MultiAgentOrchestrator initialized")
    
    def create_graph(self, name: str) -> AgentGraph:
        """Create a new agent graph."""
        graph = AgentGraph(name)
        self.graphs[name] = graph
        return graph
    
    def get_graph(self, name: str) -> Optional[AgentGraph]:
        """Get an existing graph."""
        return self.graphs.get(name)
    
    async def execute(self, graph_name: str, initial_state: Optional[GraphState] = None) -> GraphState:
        """Execute a graph."""
        graph = self.graphs.get(graph_name)
        if not graph:
            return {"error": f"Graph not found: {graph_name}"}
        
        import hashlib
        exec_id = hashlib.md5(f"{graph_name}{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        
        result = await graph.run(initial_state)
        self.active_executions[exec_id] = result
        
        return result
    
    async def execute_voice_workflow(
        self,
        transcript: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> GraphState:
        """Execute the voice agent workflow."""
        initial_state: GraphState = {
            "messages": [{"role": "user", "content": transcript}],
            "current_agent": "input",
            "task": transcript,
            "metadata": {
                "user_id": user_id,
                "context": context or {},
            },
        }
        
        return await self.execute("voice", initial_state)
    
    def list_graphs(self) -> List[Dict[str, Any]]:
        """List all available graphs."""
        return [graph.compile() for graph in self.graphs.values()]


# Singleton
_orchestrator_instance: Optional[MultiAgentOrchestrator] = None


def get_multi_agent_orchestrator() -> MultiAgentOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = MultiAgentOrchestrator()
    return _orchestrator_instance


__all__ = [
    "AgentGraph",
    "GraphNode",
    "GraphEdge",
    "GraphState",
    "NodeType",
    "VoiceAgentGraph",
    "MultiAgentOrchestrator",
    "get_multi_agent_orchestrator",
]
'''

os.makedirs('mycosoft_mas/orchestration', exist_ok=True)
with open('mycosoft_mas/orchestration/langgraph_integration.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Created langgraph_integration.py')
