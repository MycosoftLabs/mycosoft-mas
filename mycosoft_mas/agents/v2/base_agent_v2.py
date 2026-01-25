"""
MAS v2 Base Agent

Base class for all MAS v2 agents with standardized capabilities.
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiohttp

from mycosoft_mas.runtime import (
    AgentConfig,
    AgentState,
    AgentStatus,
    AgentTask,
    AgentMessage,
    MessageType,
    MessageBroker,
    AgentMetrics,
)


logger = logging.getLogger(__name__)


class BaseAgentV2(ABC):
    """
    Base class for MAS v2 agents.
    
    All agents should inherit from this class and implement:
    - execute_task: Main task execution logic
    - get_capabilities: List of agent capabilities
    """
    
    def __init__(self, agent_id: str, config: Optional[AgentConfig] = None):
        self.agent_id = agent_id
        self.config = config or self._default_config()
        
        # State
        self.status = AgentStatus.SPAWNING
        self.started_at: Optional[datetime] = None
        self.current_task: Optional[AgentTask] = None
        self.tasks_completed = 0
        self.tasks_failed = 0
        
        # Communication
        self.message_broker: Optional[MessageBroker] = None
        self.orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://orchestrator:8001")
        
        # Internal state
        self._shutdown = False
        self._task_handlers: Dict[str, callable] = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def _default_config(self) -> AgentConfig:
        """Get default configuration"""
        return AgentConfig(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            category=self.category,
            display_name=self.display_name,
            description=self.description,
        )
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Agent type identifier"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        """Agent category"""
        pass
    
    @property
    def display_name(self) -> str:
        """Display name for the agent"""
        return self.agent_id
    
    @property
    def description(self) -> str:
        """Agent description"""
        return f"{self.agent_type} agent"
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get list of agent capabilities"""
        pass
    
    def _register_default_handlers(self):
        """Register default task handlers"""
        self._task_handlers["health_check"] = self._handle_health_check
        self._task_handlers["get_status"] = self._handle_get_status
        self._task_handlers["get_capabilities"] = self._handle_get_capabilities
    
    def register_handler(self, task_type: str, handler: callable):
        """Register a task handler"""
        self._task_handlers[task_type] = handler
    
    async def start(self):
        """Start the agent"""
        logger.info(f"Starting agent: {self.agent_id}")
        
        self.started_at = datetime.utcnow()
        
        # Connect to message broker
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.message_broker = MessageBroker(redis_url)
        await self.message_broker.connect()
        
        # Subscribe to agent channel
        await self.message_broker.subscribe(
            f"agent:{self.agent_id}",
            self._handle_message
        )
        
        # Agent-specific initialization
        await self.on_start()
        
        self.status = AgentStatus.ACTIVE
        logger.info(f"Agent {self.agent_id} is now ACTIVE")
    
    async def stop(self):
        """Stop the agent"""
        logger.info(f"Stopping agent: {self.agent_id}")
        
        self._shutdown = True
        self.status = AgentStatus.SHUTDOWN
        
        # Agent-specific cleanup
        await self.on_stop()
        
        if self.message_broker:
            await self.message_broker.close()
        
        logger.info(f"Agent {self.agent_id} stopped")
    
    async def on_start(self):
        """Called when agent starts - override for custom initialization"""
        pass
    
    async def on_stop(self):
        """Called when agent stops - override for custom cleanup"""
        pass
    
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a task.
        
        Override this method in subclasses for custom task handling.
        Default implementation uses registered handlers.
        """
        handler = self._task_handlers.get(task.task_type)
        
        if handler:
            return await handler(task)
        else:
            return await self._handle_unknown_task(task)
    
    async def _handle_message(self, message_data: str):
        """Handle incoming messages"""
        try:
            message = AgentMessage.from_json(message_data)
            
            if message.message_type == MessageType.REQUEST:
                task = AgentTask(
                    agent_id=self.agent_id,
                    task_type=message.payload.get("task_type", "unknown"),
                    payload=message.payload,
                    priority=message.priority,
                    requester_agent=message.from_agent,
                )
                
                result = await self.execute_task(task)
                
                # Send response
                if message.from_agent:
                    response = AgentMessage(
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        message_type=MessageType.RESPONSE,
                        payload={"result": result},
                        correlation_id=message.id,
                    )
                    await self.message_broker.publish(
                        f"agent:{message.from_agent}",
                        response.to_json()
                    )
            
            elif message.message_type == MessageType.COMMAND:
                await self._handle_command(message)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_command(self, message: AgentMessage):
        """Handle command messages"""
        command = message.payload.get("command")
        
        if command == "pause":
            self.status = AgentStatus.PAUSED
        elif command == "resume":
            self.status = AgentStatus.ACTIVE
        elif command == "stop":
            await self.stop()
    
    async def _handle_health_check(self, task: AgentTask) -> Dict[str, Any]:
        """Handle health check task"""
        return {
            "status": "healthy",
            "agent_id": self.agent_id,
            "uptime_seconds": (datetime.utcnow() - self.started_at).total_seconds() if self.started_at else 0,
        }
    
    async def _handle_get_status(self, task: AgentTask) -> Dict[str, Any]:
        """Handle get status task"""
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
        }
    
    async def _handle_get_capabilities(self, task: AgentTask) -> Dict[str, Any]:
        """Handle get capabilities task"""
        return {
            "agent_id": self.agent_id,
            "capabilities": self.get_capabilities(),
        }
    
    async def _handle_unknown_task(self, task: AgentTask) -> Dict[str, Any]:
        """Handle unknown task type"""
        logger.warning(f"Unknown task type: {task.task_type}")
        return {
            "status": "error",
            "message": f"Unknown task type: {task.task_type}",
            "supported_tasks": list(self._task_handlers.keys()),
        }
    
    async def send_message(
        self,
        to_agent: str,
        message_type: MessageType,
        payload: Dict[str, Any],
    ) -> str:
        """Send a message to another agent"""
        if not self.message_broker:
            raise RuntimeError("Message broker not connected")
        
        message = AgentMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
        )
        
        channel = "mas:broadcast" if to_agent == "broadcast" else f"agent:{to_agent}"
        await self.message_broker.publish(channel, message.to_json())
        
        return message.id
    
    async def request_from_agent(
        self,
        agent_id: str,
        task_type: str,
        payload: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Optional[Dict[str, Any]]:
        """Request something from another agent and wait for response"""
        # This is a simplified implementation
        # A full implementation would use correlation IDs and response waiting
        message_id = await self.send_message(
            agent_id,
            MessageType.REQUEST,
            {"task_type": task_type, **payload},
        )
        
        # For now, return None - full implementation needs response tracking
        return None
    
    async def log_to_mindex(self, action: str, data: Dict[str, Any], success: bool = True):
        """Log an action to MINDEX"""
        try:
            mindex_url = os.environ.get("MINDEX_URL", "http://mindex:8000")
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{mindex_url}/api/agent_logs",
                    json={
                        "agent_id": self.agent_id,
                        "action_type": action,
                        "input_summary": str(data)[:500],
                        "success": success,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to log to MINDEX: {e}")
