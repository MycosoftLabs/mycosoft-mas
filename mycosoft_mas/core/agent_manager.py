"""
Agent Manager for Mycosoft MAS

This module implements the AgentManager class that manages all agents in the system.
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime
import psutil
import time

class AgentManager:
    """
    Manages all agents in the Mycosoft Multi-Agent System.
    
    This class:
    - Tracks agent status and health
    - Manages agent lifecycle (start, stop, restart)
    - Routes messages between agents
    - Monitors agent performance
    """
    
    def __init__(self):
        """Initialize the Agent Manager."""
        self.agents = {}
        self.agent_status = {}
        self.agent_metrics = {}
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialized AgentManager")
        
    async def initialize(self) -> bool:
        """
        Initialize the Agent Manager.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Initialize agent status tracking
            self.agent_status = {}
            self.agent_metrics = {}
            
            # Start background tasks
            asyncio.create_task(self._monitor_agents())
            
            self.logger.info("Agent Manager initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Agent Manager: {str(e)}")
            return False
            
    async def _monitor_agents(self):
        """Background task to monitor agent health and metrics."""
        while True:
            try:
                for agent_id in self.agents:
                    await self.update_agent_metrics(agent_id)
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                self.logger.error(f"Error in agent monitoring: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
        
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get the current status of all agents."""
        current_time = datetime.now().isoformat()
        return {
            agent_id: {
                "status": self.agent_status.get(agent_id, "unknown"),
                "last_heartbeat": self.agent_metrics.get(agent_id, {}).get("last_heartbeat", current_time),
                "metrics": self.agent_metrics.get(agent_id, {})
            }
            for agent_id in self.agents
        }
        
    async def get_agent_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all agents."""
        current_time = datetime.now().isoformat()
        return {
            agent_id: {
                "cpu_usage": self.agent_metrics.get(agent_id, {}).get("cpu_usage", 0),
                "memory_usage": self.agent_metrics.get(agent_id, {}).get("memory_usage", 0),
                "messages_processed": self.agent_metrics.get(agent_id, {}).get("messages_processed", 0),
                "last_updated": current_time
            }
            for agent_id in self.agents
        }
        
    async def register_agent(self, agent_id: str, agent: Any) -> None:
        """Register a new agent with the manager."""
        if agent_id in self.agents:
            raise ValueError(f"Agent {agent_id} already registered")
            
        self.agents[agent_id] = agent
        self.agent_status[agent_id] = "registered"
        self.agent_metrics[agent_id] = {
            "cpu_usage": 0,
            "memory_usage": 0,
            "messages_processed": 0,
            "last_heartbeat": datetime.now().isoformat()
        }
        self.logger.info(f"Registered agent: {agent_id}")
        
    async def start_agent(self, agent_id: str) -> None:
        """Start a registered agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
            
        agent = self.agents[agent_id]
        if hasattr(agent, 'start'):
            await agent.start()
            self.agent_status[agent_id] = "running"
            self.logger.info(f"Started agent: {agent_id}")
        else:
            raise ValueError(f"Agent {agent_id} does not have a start method")
            
    async def stop_agent(self, agent_id: str) -> None:
        """Stop a running agent."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
            
        agent = self.agents[agent_id]
        if hasattr(agent, 'stop'):
            await agent.stop()
            self.agent_status[agent_id] = "stopped"
            self.logger.info(f"Stopped agent: {agent_id}")
        else:
            raise ValueError(f"Agent {agent_id} does not have a stop method")
            
    async def update_agent_metrics(self, agent_id: str) -> None:
        """Update metrics for a specific agent."""
        if agent_id not in self.agents:
            return
            
        agent = self.agents[agent_id]
        process = psutil.Process()
        
        self.agent_metrics[agent_id].update({
            "cpu_usage": process.cpu_percent(),
            "memory_usage": process.memory_percent(),
            "last_heartbeat": datetime.now().isoformat()
        })
        
    async def get_active_agents(self) -> List[str]:
        """Get list of currently active agents."""
        return [
            agent_id for agent_id, status in self.agent_status.items()
            if status == "running"
        ] 