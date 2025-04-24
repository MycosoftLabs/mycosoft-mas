from typing import Dict, List, Optional
from ..agents.base_agent import BaseAgent
from ..agents.enums.agent_status import AgentStatus

class Cluster:
    """A cluster represents a group of agents working together to achieve specific goals."""
    
    def __init__(self, cluster_id: str, name: str):
        """Initialize a new cluster.
        
        Args:
            cluster_id (str): Unique identifier for the cluster
            name (str): Human-readable name for the cluster
        """
        self.cluster_id = cluster_id
        self.name = name
        self.agents: Dict[str, BaseAgent] = {}
        self.status = AgentStatus.IDLE
        
    def add_agent(self, agent: BaseAgent) -> None:
        """Add an agent to the cluster.
        
        Args:
            agent (BaseAgent): The agent to add to the cluster
        """
        self.agents[agent.agent_id] = agent
        
    def remove_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Remove an agent from the cluster.
        
        Args:
            agent_id (str): ID of the agent to remove
            
        Returns:
            Optional[BaseAgent]: The removed agent if found, None otherwise
        """
        return self.agents.pop(agent_id, None)
        
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID.
        
        Args:
            agent_id (str): ID of the agent to retrieve
            
        Returns:
            Optional[BaseAgent]: The agent if found, None otherwise
        """
        return self.agents.get(agent_id)
        
    def get_all_agents(self) -> List[BaseAgent]:
        """Get all agents in the cluster.
        
        Returns:
            List[BaseAgent]: List of all agents in the cluster
        """
        return list(self.agents.values())
        
    def get_status(self) -> AgentStatus:
        """Get the current status of the cluster.
        
        Returns:
            AgentStatus: Current status of the cluster
        """
        return self.status
        
    def update_status(self, status: AgentStatus) -> None:
        """Update the status of the cluster.
        
        Args:
            status (AgentStatus): New status for the cluster
        """
        self.status = status 