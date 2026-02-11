from __future__ import annotations

import asyncio
import inspect
from typing import Dict, List, Optional, Any

from ..agents.base_agent import BaseAgent
from ..agents.enums.agent_status import AgentStatus

class Cluster:
    """A cluster represents a group of agents working together to achieve specific goals."""
    
    def __init__(self, cluster_id: str = "default_cluster", name: str = "Default Cluster"):
        """Initialize a new cluster.
        
        Args:
            cluster_id (str): Unique identifier for the cluster
            name (str): Human-readable name for the cluster
        """
        self.cluster_id = cluster_id
        self.name = name

        # Legacy tests expect a list-like `nodes` plus counters and string status.
        self.nodes: List[BaseAgent] = []
        self.node_count = 0
        self.active_nodes = 0
        self.status = "stopped"

        # Internal map for fast lookups; keep in sync with `nodes`.
        self.agents: Dict[str, BaseAgent] = {}
        self._agent_status = AgentStatus.IDLE
        
    # --- Legacy API used by tests -------------------------------------------------
    def add_node(self, agent: BaseAgent) -> None:
        if agent.agent_id in self.agents:
            return
        self.agents[agent.agent_id] = agent
        self.nodes.append(agent)
        self.node_count = len(self.nodes)
        self.active_nodes = self.node_count
        self.status = "running" if self.node_count > 0 else "stopped"
        
    def remove_node(self, agent_id: str) -> Optional[BaseAgent]:
        agent = self.agents.pop(agent_id, None)
        if agent:
            self.nodes = [n for n in self.nodes if n.agent_id != agent_id]
        self.node_count = len(self.nodes)
        self.active_nodes = self.node_count
        self.status = "running" if self.node_count > 0 else "stopped"
        return agent
        
    def get_node(self, agent_id: str) -> Optional[BaseAgent]:
        return self.agents.get(agent_id)
        
    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "node_count": self.node_count,
            "active_nodes": self.active_nodes,
        }
        
    def restart(self) -> None:
        self.status = "running" if self.node_count > 0 else "stopped"
        self.active_nodes = self.node_count if self.status == "running" else 0
        
    def stop(self) -> None:
        self.status = "stopped"
        self.active_nodes = 0

    def start(self) -> None:
        self.status = "running" if self.node_count > 0 else "stopped"
        self.active_nodes = self.node_count if self.status == "running" else 0

    def distribute_task(self, task: Dict[str, Any]) -> None:
        for node in list(self.nodes):
            fn = getattr(node, "process_task", None)
            if fn:
                result = fn(task)
                if inspect.isawaitable(result):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(result)
                    except RuntimeError:
                        # No running loop; best-effort synchronous fallback.
                        asyncio.run(result)

    def get_node_status(self, agent_id: str) -> Dict[str, Any]:
        node = self.get_node(agent_id)
        if not node:
            return {"status": "unknown"}
        fn = getattr(node, "get_status", None)
        return fn() if fn else {"status": "unknown"}

    def handle_node_failure(self, agent_id: str) -> None:
        self.remove_node(agent_id)

    # --- Newer / internal API ----------------------------------------------------
    def add_agent(self, agent: BaseAgent) -> None:
        self.add_node(agent)

    def remove_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self.remove_node(agent_id)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self.get_node(agent_id)

    def get_all_agents(self) -> List[BaseAgent]:
        return list(self.nodes)

    def update_status(self, status: AgentStatus) -> None:
        self._agent_status = status