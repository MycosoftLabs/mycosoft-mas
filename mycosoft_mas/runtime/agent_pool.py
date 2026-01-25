"""
MAS v2 Agent Pool

Manages the pool of running agent containers. Provides methods for
spawning, stopping, and monitoring agent containers.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import docker
from docker.errors import DockerException, NotFound

from .models import (
    AgentConfig,
    AgentState,
    AgentStatus,
    AgentCategory,
)


logger = logging.getLogger("AgentPool")


class AgentPool:
    """
    Manages the pool of running agent containers.
    
    Provides methods for:
    - Spawning new agent containers
    - Stopping agent containers
    - Monitoring container health
    - Scaling agents up/down
    - Resource management
    """
    
    def __init__(self):
        self.docker_client: Optional[docker.DockerClient] = None
        self.agents: Dict[str, AgentState] = {}
        self.configs: Dict[str, AgentConfig] = {}
        self.network_name = os.environ.get("MAS_NETWORK", "mas-network")
        self._initialized = False
    
    async def initialize(self):
        """Initialize Docker client and network"""
        try:
            self.docker_client = docker.from_env()
            logger.info("Connected to Docker daemon")
            
            # Ensure network exists
            await self._ensure_network()
            
            # Discover existing agent containers
            await self._discover_agents()
            
            self._initialized = True
            
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise
    
    async def _ensure_network(self):
        """Ensure the MAS network exists"""
        try:
            self.docker_client.networks.get(self.network_name)
            logger.info(f"Network {self.network_name} exists")
        except NotFound:
            self.docker_client.networks.create(
                self.network_name,
                driver="bridge",
                labels={"created_by": "mas-pool"}
            )
            logger.info(f"Created network {self.network_name}")
    
    async def _discover_agents(self):
        """Discover existing agent containers"""
        containers = self.docker_client.containers.list(
            filters={"label": "mas.agent=true"}
        )
        
        for container in containers:
            agent_id = container.labels.get("mas.agent_id", container.name)
            status = AgentStatus.ACTIVE if container.status == "running" else AgentStatus.DEAD
            
            self.agents[agent_id] = AgentState(
                agent_id=agent_id,
                status=status,
                container_id=container.id,
                started_at=datetime.utcnow(),
            )
            logger.info(f"Discovered agent: {agent_id} ({status.value})")
    
    async def spawn_agent(
        self,
        config: AgentConfig,
        image: str = "mycosoft/mas-agent:latest",
    ) -> AgentState:
        """
        Spawn a new agent container.
        
        Args:
            config: Agent configuration
            image: Docker image to use
            
        Returns:
            AgentState for the new agent
        """
        if not self._initialized:
            await self.initialize()
        
        agent_id = config.agent_id
        
        # Check if agent already exists
        if agent_id in self.agents:
            existing = self.agents[agent_id]
            if existing.status in [AgentStatus.ACTIVE, AgentStatus.BUSY]:
                logger.warning(f"Agent {agent_id} already running")
                return existing
        
        logger.info(f"Spawning agent: {agent_id}")
        
        # Set initial state
        state = AgentState(
            agent_id=agent_id,
            status=AgentStatus.SPAWNING,
        )
        self.agents[agent_id] = state
        self.configs[agent_id] = config
        
        try:
            # Container configuration
            container_config = {
                "image": image,
                "name": f"mas-agent-{agent_id}",
                "detach": True,
                "network": self.network_name,
                "environment": {
                    "AGENT_ID": agent_id,
                    "AGENT_TYPE": config.agent_type,
                    "AGENT_CATEGORY": config.category.value if isinstance(config.category, AgentCategory) else config.category,
                    "AGENT_DISPLAY_NAME": config.display_name,
                    "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO"),
                    "REDIS_URL": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
                    "MINDEX_URL": os.environ.get("MINDEX_URL", "http://mindex:8000"),
                    "ORCHESTRATOR_URL": os.environ.get("ORCHESTRATOR_URL", "http://orchestrator:8001"),
                },
                "labels": {
                    "mas.agent": "true",
                    "mas.agent_id": agent_id,
                    "mas.agent_type": config.agent_type,
                    "mas.agent_category": config.category.value if isinstance(config.category, AgentCategory) else config.category,
                },
                "mem_limit": f"{config.memory_limit}m",
                "cpu_period": 100000,
                "cpu_quota": int(config.cpu_limit * 100000),
                "restart_policy": {"Name": "unless-stopped"} if config.auto_restart else {"Name": "no"},
            }
            
            # Create and start container
            container = self.docker_client.containers.run(**container_config)
            
            state.container_id = container.id
            state.status = AgentStatus.ACTIVE
            state.started_at = datetime.utcnow()
            
            logger.info(f"Agent {agent_id} spawned successfully (container: {container.short_id})")
            
            return state
            
        except DockerException as e:
            state.status = AgentStatus.ERROR
            state.error_message = str(e)
            logger.error(f"Failed to spawn agent {agent_id}: {e}")
            raise
    
    async def stop_agent(self, agent_id: str, force: bool = False) -> bool:
        """
        Stop an agent container.
        
        Args:
            agent_id: Agent to stop
            force: If True, kill immediately instead of graceful stop
            
        Returns:
            True if stopped successfully
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent {agent_id} not found in pool")
            return False
        
        state = self.agents[agent_id]
        
        if not state.container_id:
            logger.warning(f"Agent {agent_id} has no container")
            return False
        
        try:
            container = self.docker_client.containers.get(state.container_id)
            
            if force:
                container.kill()
            else:
                container.stop(timeout=30)
            
            state.status = AgentStatus.SHUTDOWN
            logger.info(f"Agent {agent_id} stopped")
            
            return True
            
        except NotFound:
            state.status = AgentStatus.DEAD
            logger.warning(f"Container for agent {agent_id} not found")
            return False
        except DockerException as e:
            logger.error(f"Error stopping agent {agent_id}: {e}")
            return False
    
    async def restart_agent(self, agent_id: str) -> AgentState:
        """Restart an agent container"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        await self.stop_agent(agent_id)
        await asyncio.sleep(1)
        
        config = self.configs.get(agent_id)
        if config:
            return await self.spawn_agent(config)
        else:
            raise ValueError(f"No config found for agent {agent_id}")
    
    async def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get current state of an agent"""
        return self.agents.get(agent_id)
    
    async def get_all_agents(self) -> List[AgentState]:
        """Get all agent states"""
        return list(self.agents.values())
    
    async def get_agents_by_status(self, status: AgentStatus) -> List[AgentState]:
        """Get agents with a specific status"""
        return [a for a in self.agents.values() if a.status == status]
    
    async def get_agents_by_category(self, category: AgentCategory) -> List[AgentState]:
        """Get agents in a specific category"""
        return [
            a for a in self.agents.values()
            if self.configs.get(a.agent_id) and 
            self.configs[a.agent_id].category == category
        ]
    
    async def update_agent_health(self):
        """Check and update health status of all agents"""
        for agent_id, state in list(self.agents.items()):
            if not state.container_id:
                continue
            
            try:
                container = self.docker_client.containers.get(state.container_id)
                
                if container.status == "running":
                    # Check if container is healthy
                    health = container.attrs.get("State", {}).get("Health", {})
                    if health.get("Status") == "unhealthy":
                        state.status = AgentStatus.ERROR
                        state.error_message = "Container unhealthy"
                    elif state.status == AgentStatus.ERROR:
                        state.status = AgentStatus.ACTIVE
                        state.error_message = None
                else:
                    state.status = AgentStatus.DEAD
                    
            except NotFound:
                state.status = AgentStatus.DEAD
                state.container_id = None
            except Exception as e:
                logger.error(f"Error checking agent {agent_id}: {e}")
    
    async def cleanup_dead_agents(self):
        """Remove dead agent containers"""
        for agent_id, state in list(self.agents.items()):
            if state.status == AgentStatus.DEAD and state.container_id:
                try:
                    container = self.docker_client.containers.get(state.container_id)
                    container.remove(force=True)
                    logger.info(f"Removed dead container for agent {agent_id}")
                except NotFound:
                    pass
                except Exception as e:
                    logger.error(f"Error removing container: {e}")
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics about the agent pool"""
        total = len(self.agents)
        by_status = {}
        for status in AgentStatus:
            count = len([a for a in self.agents.values() if a.status == status])
            if count > 0:
                by_status[status.value] = count
        
        return {
            "total_agents": total,
            "by_status": by_status,
            "network": self.network_name,
        }
