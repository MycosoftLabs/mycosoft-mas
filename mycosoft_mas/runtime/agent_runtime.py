"""
MAS v2 Agent Runtime

The core agent execution engine that runs inside each agent container.
Handles task processing, health checks, and communication with the orchestrator.
"""

import asyncio
import os
import signal
import sys
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

import aiohttp
from aiohttp import web

from .models import (
    AgentStatus,
    AgentState,
    AgentConfig,
    AgentTask,
    AgentMessage,
    MessageType,
    AgentMetrics,
)
from .message_broker import MessageBroker


logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("AgentRuntime")


class AgentRuntime:
    """
    Core agent execution engine.
    
    Each agent runs an instance of this class which:
    - Listens for tasks from the orchestrator via Redis
    - Executes tasks using the agent's specific logic
    - Reports health and metrics
    - Handles graceful shutdown and snapshots
    """
    
    def __init__(self, agent_id: str, config: Optional[AgentConfig] = None):
        self.agent_id = agent_id
        self.config = config or self._load_config()
        
        # State
        self.status = AgentStatus.SPAWNING
        self.started_at: Optional[datetime] = None
        self.current_task: Optional[AgentTask] = None
        self.tasks_completed = 0
        self.tasks_failed = 0
        
        # Communication
        self.message_broker: Optional[MessageBroker] = None
        self.orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://orchestrator:8001")
        self.mindex_url = os.environ.get("MINDEX_URL", "http://mindex:8000")
        
        # HTTP server for health checks
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        
        # Shutdown flag
        self._shutdown = False
        self._task_queue: asyncio.Queue = asyncio.Queue()
        
        logger.info(f"AgentRuntime initialized for agent: {agent_id}")
    
    def _load_config(self) -> AgentConfig:
        """Load agent configuration from environment or file"""
        return AgentConfig(
            agent_id=self.agent_id,
            agent_type=os.environ.get("AGENT_TYPE", "generic"),
            category=os.environ.get("AGENT_CATEGORY", "core"),
            display_name=os.environ.get("AGENT_DISPLAY_NAME", self.agent_id),
            description=os.environ.get("AGENT_DESCRIPTION", ""),
            cpu_limit=float(os.environ.get("CPU_LIMIT", "1.0")),
            memory_limit=int(os.environ.get("MEMORY_LIMIT", "512")),
            max_concurrent_tasks=int(os.environ.get("MAX_CONCURRENT_TASKS", "5")),
            task_timeout=int(os.environ.get("TASK_TIMEOUT", "300")),
            health_check_interval=int(os.environ.get("HEALTH_CHECK_INTERVAL", "30")),
            heartbeat_interval=int(os.environ.get("HEARTBEAT_INTERVAL", "10")),
        )
    
    async def start(self):
        """Start the agent runtime"""
        logger.info(f"Starting agent runtime: {self.agent_id}")
        
        self.started_at = datetime.utcnow()
        
        # Connect to message broker
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.message_broker = MessageBroker(redis_url)
        await self.message_broker.connect()
        
        # Subscribe to agent-specific channel
        await self.message_broker.subscribe(
            f"agent:{self.agent_id}",
            self._handle_message
        )
        
        # Start health check server
        await self._start_health_server()
        
        # Register with orchestrator
        await self._register_with_orchestrator()
        
        # Set status to active
        self.status = AgentStatus.ACTIVE
        
        # Start background tasks
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._task_processor())
        
        logger.info(f"Agent {self.agent_id} is now ACTIVE")
    
    async def stop(self):
        """Stop the agent runtime gracefully"""
        logger.info(f"Stopping agent runtime: {self.agent_id}")
        
        self._shutdown = True
        self.status = AgentStatus.SHUTDOWN
        
        # Deregister from orchestrator
        await self._deregister_from_orchestrator()
        
        # Close message broker
        if self.message_broker:
            await self.message_broker.close()
        
        # Stop health server
        if self.runner:
            await self.runner.cleanup()
        
        logger.info(f"Agent {self.agent_id} has stopped")
    
    async def _start_health_server(self):
        """Start HTTP server for health checks"""
        self.app = web.Application()
        self.app.router.add_get("/health", self._health_handler)
        self.app.router.add_get("/metrics", self._metrics_handler)
        self.app.router.add_get("/status", self._status_handler)
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        port = int(os.environ.get("AGENT_PORT", "8080"))
        site = web.TCPSite(self.runner, "0.0.0.0", port)
        await site.start()
        
        logger.info(f"Health server started on port {port}")
    
    async def _health_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        is_healthy = self.status in [AgentStatus.ACTIVE, AgentStatus.BUSY, AgentStatus.IDLE]
        return web.json_response({
            "status": "ok" if is_healthy else "unhealthy",
            "agent_id": self.agent_id,
            "agent_status": self.status.value,
            "uptime_seconds": (datetime.utcnow() - self.started_at).total_seconds() if self.started_at else 0,
        }, status=200 if is_healthy else 503)
    
    async def _metrics_handler(self, request: web.Request) -> web.Response:
        """Metrics endpoint"""
        metrics = AgentMetrics(
            agent_id=self.agent_id,
            tasks_completed=self.tasks_completed,
            tasks_failed=self.tasks_failed,
            uptime_seconds=int((datetime.utcnow() - self.started_at).total_seconds()) if self.started_at else 0,
        )
        return web.json_response(metrics.to_dict())
    
    async def _status_handler(self, request: web.Request) -> web.Response:
        """Detailed status endpoint"""
        state = AgentState(
            agent_id=self.agent_id,
            status=self.status,
            started_at=self.started_at,
            last_heartbeat=datetime.utcnow(),
            current_task_id=self.current_task.id if self.current_task else None,
            tasks_completed=self.tasks_completed,
            tasks_failed=self.tasks_failed,
        )
        return web.json_response(state.to_dict())
    
    async def _register_with_orchestrator(self):
        """Register this agent with the orchestrator"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.orchestrator_url}/agents/register",
                    json={
                        "agent_id": self.agent_id,
                        "config": self.config.to_dict(),
                        "status": self.status.value,
                    }
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"Registered with orchestrator")
                    else:
                        logger.warning(f"Failed to register with orchestrator: {resp.status}")
        except Exception as e:
            logger.error(f"Error registering with orchestrator: {e}")
    
    async def _deregister_from_orchestrator(self):
        """Deregister this agent from the orchestrator"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.orchestrator_url}/agents/{self.agent_id}/deregister"
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"Deregistered from orchestrator")
        except Exception as e:
            logger.error(f"Error deregistering from orchestrator: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to orchestrator"""
        interval = self.config.heartbeat_interval
        
        while not self._shutdown:
            try:
                await self._send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            
            await asyncio.sleep(interval)
    
    async def _send_heartbeat(self):
        """Send a single heartbeat"""
        if self.message_broker:
            heartbeat = AgentMessage(
                from_agent=self.agent_id,
                to_agent="orchestrator",
                message_type=MessageType.HEARTBEAT,
                payload={
                    "status": self.status.value,
                    "tasks_completed": self.tasks_completed,
                    "tasks_failed": self.tasks_failed,
                    "current_task": self.current_task.id if self.current_task else None,
                }
            )
            await self.message_broker.publish("orchestrator:heartbeats", heartbeat.to_json())
    
    async def _handle_message(self, message_data: str):
        """Handle incoming messages from message broker"""
        try:
            message = AgentMessage.from_json(message_data)
            
            if message.message_type == MessageType.COMMAND:
                await self._handle_command(message)
            elif message.message_type == MessageType.REQUEST:
                # Convert request to task and queue it
                task = AgentTask(
                    agent_id=self.agent_id,
                    task_type=message.payload.get("task_type", "unknown"),
                    payload=message.payload,
                    priority=message.priority,
                    requester_agent=message.from_agent,
                )
                await self._task_queue.put(task)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_command(self, message: AgentMessage):
        """Handle command messages"""
        command = message.payload.get("command")
        
        if command == "pause":
            self.status = AgentStatus.PAUSED
            logger.info("Agent paused")
        elif command == "resume":
            self.status = AgentStatus.ACTIVE
            logger.info("Agent resumed")
        elif command == "stop":
            await self.stop()
        elif command == "snapshot":
            await self._create_snapshot(message.payload.get("reason", "manual"))
    
    async def _task_processor(self):
        """Process tasks from the queue"""
        while not self._shutdown:
            try:
                # Get next task with timeout
                try:
                    task = await asyncio.wait_for(
                        self._task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the task
                self.status = AgentStatus.BUSY
                self.current_task = task
                task.started_at = datetime.utcnow()
                task.status = "running"
                
                try:
                    result = await self._execute_task(task)
                    task.result = result
                    task.status = "completed"
                    task.completed_at = datetime.utcnow()
                    self.tasks_completed += 1
                    
                    # Send response if requested
                    if task.requester_agent:
                        await self._send_task_response(task)
                        
                except Exception as e:
                    task.error = str(e)
                    task.status = "failed"
                    task.completed_at = datetime.utcnow()
                    self.tasks_failed += 1
                    logger.error(f"Task {task.id} failed: {e}")
                
                finally:
                    self.current_task = None
                    self.status = AgentStatus.ACTIVE
                    
                    # Log to MINDEX
                    await self._log_task_to_mindex(task)
                
            except Exception as e:
                logger.error(f"Task processor error: {e}")
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute a task - override in subclasses for specific behavior"""
        # Default implementation - echo the payload
        logger.info(f"Executing task {task.id}: {task.task_type}")
        await asyncio.sleep(0.1)  # Simulate work
        return {"status": "completed", "task_type": task.task_type}
    
    async def _send_task_response(self, task: AgentTask):
        """Send task completion response"""
        if self.message_broker and task.requester_agent:
            response = AgentMessage(
                from_agent=self.agent_id,
                to_agent=task.requester_agent,
                message_type=MessageType.RESPONSE,
                payload={
                    "task_id": task.id,
                    "status": task.status,
                    "result": task.result,
                    "error": task.error,
                }
            )
            await self.message_broker.publish(
                f"agent:{task.requester_agent}",
                response.to_json()
            )
    
    async def _log_task_to_mindex(self, task: AgentTask):
        """Log task execution to MINDEX database"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.mindex_url}/api/agent_logs",
                    json={
                        "agent_id": self.agent_id,
                        "action_type": task.task_type,
                        "input_summary": str(task.payload)[:500],
                        "output_summary": str(task.result)[:500] if task.result else None,
                        "success": task.status == "completed",
                        "duration_ms": int((task.completed_at - task.started_at).total_seconds() * 1000) if task.started_at and task.completed_at else 0,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to log to MINDEX: {e}")
    
    async def _create_snapshot(self, reason: str):
        """Create a snapshot of current agent state"""
        from .snapshot_manager import SnapshotManager
        
        snapshot_manager = SnapshotManager(self.agent_id)
        state = AgentState(
            agent_id=self.agent_id,
            status=self.status,
            started_at=self.started_at,
            tasks_completed=self.tasks_completed,
            tasks_failed=self.tasks_failed,
        )
        await snapshot_manager.create_snapshot(state, self.config, reason)
        logger.info(f"Snapshot created: {reason}")


async def main():
    """Main entry point for agent runtime"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MAS Agent Runtime")
    parser.add_argument("--agent-id", default=os.environ.get("AGENT_ID", "agent-" + str(uuid4())[:8]))
    args = parser.parse_args()
    
    runtime = AgentRuntime(args.agent_id)
    
    # Handle signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(runtime.stop()))
    
    await runtime.start()
    
    # Keep running until shutdown
    while not runtime._shutdown:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
