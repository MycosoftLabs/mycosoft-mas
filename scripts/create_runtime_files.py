#!/usr/bin/env python3
"""
Create MAS v2 Runtime Files

This script creates all the necessary runtime files for the MAS v2 Agent Runtime Engine.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def create_dockerfile_agent():
    """Create the base agent Dockerfile"""
    content = '''# =============================================================================
# Dockerfile.agent - Base Agent Container Image for MAS v2
# =============================================================================
# This is the standardized container image for all MAS agents.
# Each agent runs in an isolated Docker container with:
# - Resource limits (CPU, Memory)
# - Health check endpoint
# - Task queue consumer (Redis)
# - Logging to MINDEX
# - Agent-to-Agent messaging capability
# =============================================================================

FROM python:3.11-slim

LABEL maintainer="Mycosoft"
LABEL version="2.0.0"
LABEL description="MAS Agent Container Runtime"

# Build arguments for agent configuration
ARG AGENT_ID=default-agent
ARG AGENT_TYPE=generic
ARG AGENT_CATEGORY=core

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    wget \\
    libpq5 \\
    redis-tools \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -s /bin/bash agent && \\
    mkdir -p /app/data /app/logs /app/snapshots && \\
    chown -R agent:agent /app

# Copy requirements first for better caching
COPY requirements-agent.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy runtime modules
COPY mycosoft_mas/runtime /app/runtime
COPY mycosoft_mas/agents /app/agents
COPY mycosoft_mas/core /app/core
COPY config/agent_config.json /app/config/agent_config.json

# Set ownership
RUN chown -R agent:agent /app

# Switch to non-root user
USER agent

# Environment variables
ENV PYTHONPATH=/app \\
    PYTHONUNBUFFERED=1 \\
    AGENT_ID=${AGENT_ID} \\
    AGENT_TYPE=${AGENT_TYPE} \\
    AGENT_CATEGORY=${AGENT_CATEGORY} \\
    AGENT_STATUS=initializing \\
    REDIS_URL=redis://redis:6379/0 \\
    MINDEX_URL=http://mindex:8000 \\
    ORCHESTRATOR_URL=http://orchestrator:8001 \\
    LOG_LEVEL=INFO \\
    HEALTH_CHECK_INTERVAL=30 \\
    HEARTBEAT_INTERVAL=10 \\
    TASK_TIMEOUT=300 \\
    MAX_CONCURRENT_TASKS=5

# Expose health check port
EXPOSE 8080

# Health check - agent must respond to /health
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Default command - runs the agent runtime
ENTRYPOINT ["python", "-m", "runtime.agent_runtime"]

# Default CMD passes the agent ID
CMD ["--agent-id", "${AGENT_ID}"]
'''
    docker_dir = BASE_DIR / "docker"
    docker_dir.mkdir(exist_ok=True)
    (docker_dir / "Dockerfile.agent").write_text(content)
    print("Created docker/Dockerfile.agent")


def create_runtime_init():
    """Create runtime __init__.py"""
    content = '''"""
MAS v2 Agent Runtime Engine

This module provides the containerized agent runtime system for the
Mycosoft Multi-Agent System. Each agent runs in an isolated Docker
container with resource limits, health monitoring, and communication
capabilities.

Key Components:
- AgentRuntime: Core agent execution engine
- AgentPool: Pool manager for running agent containers
- SnapshotManager: Agent state persistence and recovery
- MessageBroker: Agent-to-Agent communication via Redis
"""

from .models import (
    AgentState,
    AgentStatus,
    AgentConfig,
    AgentMessage,
    MessageType,
    TaskPriority,
    AgentTask,
    AgentSnapshot,
    AgentMetrics,
    AgentCategory,
)
from .agent_runtime import AgentRuntime
from .agent_pool import AgentPool
from .snapshot_manager import SnapshotManager
from .message_broker import MessageBroker

__all__ = [
    # Models
    "AgentState",
    "AgentStatus",
    "AgentConfig",
    "AgentMessage",
    "MessageType",
    "TaskPriority",
    "AgentTask",
    "AgentSnapshot",
    "AgentMetrics",
    "AgentCategory",
    # Runtime components
    "AgentRuntime",
    "AgentPool",
    "SnapshotManager",
    "MessageBroker",
]

__version__ = "2.0.0"
'''
    runtime_dir = BASE_DIR / "mycosoft_mas" / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    (runtime_dir / "__init__.py").write_text(content)
    print("Created mycosoft_mas/runtime/__init__.py")


def create_models():
    """Create runtime models.py"""
    content = '''"""
MAS v2 Agent Runtime Models

Data models for agent state, configuration, messaging, and metrics.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from uuid import uuid4
import json


class AgentStatus(str, Enum):
    """Agent lifecycle states"""
    SPAWNING = "spawning"       # Container initializing
    ACTIVE = "active"           # Ready and processing
    BUSY = "busy"               # Processing a task
    IDLE = "idle"               # Waiting for work
    PAUSED = "paused"           # Temporarily suspended
    ERROR = "error"             # Failed state
    SHUTDOWN = "shutdown"       # Graceful stop in progress
    DEAD = "dead"               # Unresponsive
    ARCHIVED = "archived"       # Preserved state (not running)


class MessageType(str, Enum):
    """Agent-to-Agent message types"""
    REQUEST = "request"         # Task/action request
    RESPONSE = "response"       # Response to request
    EVENT = "event"             # Notification event
    COMMAND = "command"         # Direct command
    HEARTBEAT = "heartbeat"     # Liveness signal
    BROADCAST = "broadcast"     # Message to all agents
    ACK = "ack"                 # Acknowledgment


class TaskPriority(int, Enum):
    """Task priority levels"""
    CRITICAL = 10   # Immediate execution
    HIGH = 8        # Next in queue
    NORMAL = 5      # Standard priority
    LOW = 3         # When resources available
    BACKGROUND = 1  # Lowest priority


class AgentCategory(str, Enum):
    """Agent category classification"""
    CORE = "core"
    CORPORATE = "corporate"
    FINANCIAL = "financial"
    MYCOLOGY = "mycology"
    DATA = "data"
    INFRASTRUCTURE = "infrastructure"
    DEVICE = "device"
    INTEGRATION = "integration"
    SECURITY = "security"
    SIMULATION = "simulation"
    COMMUNICATION = "communication"
    DAO = "dao"
    NLM = "nlm"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """Agent configuration parameters"""
    agent_id: str
    agent_type: str
    category: AgentCategory
    display_name: str
    description: str = ""
    version: str = "1.0.0"
    
    # Resource limits
    cpu_limit: float = 1.0      # CPU cores
    memory_limit: int = 512     # MB
    max_concurrent_tasks: int = 5
    task_timeout: int = 300     # seconds
    
    # Health check settings
    health_check_interval: int = 30  # seconds
    heartbeat_interval: int = 10     # seconds
    max_retries: int = 3
    
    # Communication
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # Execution
    auto_start: bool = True
    auto_restart: bool = True
    
    # Custom settings
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "category": self.category.value if isinstance(self.category, AgentCategory) else self.category,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "cpu_limit": self.cpu_limit,
            "memory_limit": self.memory_limit,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "task_timeout": self.task_timeout,
            "health_check_interval": self.health_check_interval,
            "heartbeat_interval": self.heartbeat_interval,
            "max_retries": self.max_retries,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "auto_start": self.auto_start,
            "auto_restart": self.auto_restart,
            "settings": self.settings,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        category = data.get("category", "custom")
        if isinstance(category, str):
            try:
                category = AgentCategory(category)
            except ValueError:
                category = AgentCategory.CUSTOM
        return cls(
            agent_id=data["agent_id"],
            agent_type=data["agent_type"],
            category=category,
            display_name=data.get("display_name", data["agent_id"]),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            cpu_limit=data.get("cpu_limit", 1.0),
            memory_limit=data.get("memory_limit", 512),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 5),
            task_timeout=data.get("task_timeout", 300),
            health_check_interval=data.get("health_check_interval", 30),
            heartbeat_interval=data.get("heartbeat_interval", 10),
            max_retries=data.get("max_retries", 3),
            capabilities=data.get("capabilities", []),
            dependencies=data.get("dependencies", []),
            auto_start=data.get("auto_start", True),
            auto_restart=data.get("auto_restart", True),
            settings=data.get("settings", {}),
        )


@dataclass
class AgentState:
    """Current state of an agent"""
    agent_id: str
    status: AgentStatus
    container_id: Optional[str] = None
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    current_task_id: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    error_message: Optional[str] = None
    cpu_usage: float = 0.0
    memory_usage: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "container_id": self.container_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "current_task_id": self.current_task_id,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "error_message": self.error_message,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
        }


@dataclass
class AgentMessage:
    """Agent-to-Agent message"""
    id: str = field(default_factory=lambda: str(uuid4()))
    from_agent: str = ""
    to_agent: str = ""                  # "broadcast" for all agents
    message_type: MessageType = MessageType.EVENT
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    requires_ack: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None  # For request/response matching
    ttl: int = 300                        # Time-to-live in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "priority": self.priority.value,
            "requires_ack": self.requires_ack,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "ttl": self.ttl,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(
            id=data.get("id", str(uuid4())),
            from_agent=data.get("from_agent", ""),
            to_agent=data.get("to_agent", ""),
            message_type=MessageType(data.get("message_type", "event")),
            payload=data.get("payload", {}),
            priority=TaskPriority(data.get("priority", 5)),
            requires_ack=data.get("requires_ack", False),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            correlation_id=data.get("correlation_id"),
            ttl=data.get("ttl", 300),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "AgentMessage":
        return cls.from_dict(json.loads(json_str))


@dataclass
class AgentTask:
    """Task to be executed by an agent"""
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    task_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed, cancelled
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timeout: int = 300
    retries: int = 0
    max_retries: int = 3
    requester_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "timeout": self.timeout,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "requester_agent": self.requester_agent,
        }


@dataclass
class AgentSnapshot:
    """Snapshot of agent state for persistence/recovery"""
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    snapshot_time: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    pending_tasks: List[Dict[str, Any]] = field(default_factory=list)
    memory_state: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "snapshot_time": self.snapshot_time.isoformat(),
            "reason": self.reason,
            "state": self.state,
            "config": self.config,
            "pending_tasks": self.pending_tasks,
            "memory_state": self.memory_state,
        }


@dataclass
class AgentMetrics:
    """Performance metrics for an agent"""
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Resource usage
    cpu_percent: float = 0.0
    memory_mb: int = 0
    network_in_bytes: int = 0
    network_out_bytes: int = 0
    
    # Task metrics
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_task_duration_ms: float = 0.0
    
    # Communication metrics
    messages_sent: int = 0
    messages_received: int = 0
    avg_response_time_ms: float = 0.0
    
    # Health
    uptime_seconds: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "network_in_bytes": self.network_in_bytes,
            "network_out_bytes": self.network_out_bytes,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "avg_task_duration_ms": self.avg_task_duration_ms,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "avg_response_time_ms": self.avg_response_time_ms,
            "uptime_seconds": self.uptime_seconds,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }
'''
    runtime_dir = BASE_DIR / "mycosoft_mas" / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    (runtime_dir / "models.py").write_text(content)
    print("Created mycosoft_mas/runtime/models.py")


def create_agent_runtime():
    """Create agent_runtime.py - core execution engine"""
    content = '''"""
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
'''
    runtime_dir = BASE_DIR / "mycosoft_mas" / "runtime"
    (runtime_dir / "agent_runtime.py").write_text(content)
    print("Created mycosoft_mas/runtime/agent_runtime.py")


def create_agent_pool():
    """Create agent_pool.py - pool manager for agent containers"""
    content = '''"""
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
'''
    runtime_dir = BASE_DIR / "mycosoft_mas" / "runtime"
    (runtime_dir / "agent_pool.py").write_text(content)
    print("Created mycosoft_mas/runtime/agent_pool.py")


def create_snapshot_manager():
    """Create snapshot_manager.py"""
    content = '''"""
MAS v2 Snapshot Manager

Manages agent state snapshots for persistence and recovery.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiofiles

from .models import (
    AgentConfig,
    AgentState,
    AgentSnapshot,
)


logger = logging.getLogger("SnapshotManager")


class SnapshotManager:
    """
    Manages agent state snapshots.
    
    Provides methods for:
    - Creating snapshots of agent state
    - Restoring agents from snapshots
    - Listing available snapshots
    - Cleaning up old snapshots
    """
    
    def __init__(self, agent_id: str, snapshot_dir: Optional[str] = None):
        self.agent_id = agent_id
        self.snapshot_dir = Path(snapshot_dir or os.environ.get("SNAPSHOT_DIR", "/app/snapshots"))
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_snapshot(
        self,
        state: AgentState,
        config: AgentConfig,
        reason: str = "manual",
        memory_state: Optional[Dict[str, Any]] = None,
        pending_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentSnapshot:
        """
        Create a snapshot of agent state.
        
        Args:
            state: Current agent state
            config: Agent configuration
            reason: Reason for snapshot
            memory_state: Optional memory/context state
            pending_tasks: Optional list of pending tasks
            
        Returns:
            Created snapshot
        """
        snapshot = AgentSnapshot(
            agent_id=self.agent_id,
            reason=reason,
            state=state.to_dict(),
            config=config.to_dict(),
            memory_state=memory_state or {},
            pending_tasks=pending_tasks or [],
        )
        
        # Save to file
        filename = f"{self.agent_id}_{snapshot.snapshot_time.strftime('%Y%m%d_%H%M%S')}_{snapshot.id[:8]}.json"
        filepath = self.snapshot_dir / filename
        
        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(snapshot.to_dict(), indent=2))
        
        logger.info(f"Snapshot created: {filename}")
        
        return snapshot
    
    async def list_snapshots(self, limit: int = 10) -> List[AgentSnapshot]:
        """List available snapshots for this agent"""
        snapshots = []
        
        pattern = f"{self.agent_id}_*.json"
        files = sorted(self.snapshot_dir.glob(pattern), reverse=True)
        
        for filepath in files[:limit]:
            try:
                async with aiofiles.open(filepath, "r") as f:
                    content = await f.read()
                    data = json.loads(content)
                    data["snapshot_time"] = datetime.fromisoformat(data["snapshot_time"])
                    snapshots.append(AgentSnapshot(**data))
            except Exception as e:
                logger.warning(f"Error reading snapshot {filepath}: {e}")
        
        return snapshots
    
    async def get_latest_snapshot(self) -> Optional[AgentSnapshot]:
        """Get the most recent snapshot"""
        snapshots = await self.list_snapshots(limit=1)
        return snapshots[0] if snapshots else None
    
    async def get_snapshot_by_id(self, snapshot_id: str) -> Optional[AgentSnapshot]:
        """Get a specific snapshot by ID"""
        pattern = f"{self.agent_id}_*_{snapshot_id[:8]}.json"
        files = list(self.snapshot_dir.glob(pattern))
        
        if not files:
            return None
        
        async with aiofiles.open(files[0], "r") as f:
            content = await f.read()
            data = json.loads(content)
            data["snapshot_time"] = datetime.fromisoformat(data["snapshot_time"])
            return AgentSnapshot(**data)
    
    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a specific snapshot"""
        pattern = f"{self.agent_id}_*_{snapshot_id[:8]}.json"
        files = list(self.snapshot_dir.glob(pattern))
        
        if not files:
            return False
        
        files[0].unlink()
        logger.info(f"Deleted snapshot: {files[0].name}")
        return True
    
    async def cleanup_old_snapshots(self, keep_count: int = 10, max_age_days: int = 7):
        """Clean up old snapshots"""
        pattern = f"{self.agent_id}_*.json"
        files = sorted(self.snapshot_dir.glob(pattern), reverse=True)
        
        now = datetime.utcnow()
        deleted = 0
        
        for i, filepath in enumerate(files):
            # Keep recent snapshots
            if i < keep_count:
                continue
            
            # Check age
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            age_days = (now - mtime).days
            
            if age_days > max_age_days:
                filepath.unlink()
                deleted += 1
        
        if deleted:
            logger.info(f"Cleaned up {deleted} old snapshots")
        
        return deleted
'''
    runtime_dir = BASE_DIR / "mycosoft_mas" / "runtime"
    (runtime_dir / "snapshot_manager.py").write_text(content)
    print("Created mycosoft_mas/runtime/snapshot_manager.py")


def create_message_broker():
    """Create message_broker.py"""
    content = '''"""
MAS v2 Message Broker

Handles Agent-to-Agent communication via Redis Pub/Sub and Streams.
"""

import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as redis
from redis.asyncio.client import PubSub


logger = logging.getLogger("MessageBroker")


class MessageBroker:
    """
    Handles Agent-to-Agent communication.
    
    Uses Redis for:
    - Pub/Sub for real-time events and broadcasts
    - Streams for persistent task queues
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[PubSub] = None
        self._subscriptions: Dict[str, Callable] = {}
        self._listener_task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            self.pubsub = self.redis.pubsub()
            logger.info("Connected to Redis message broker")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Disconnected from Redis message broker")
    
    async def publish(self, channel: str, message: str):
        """Publish a message to a channel"""
        if not self.redis:
            raise RuntimeError("Not connected to Redis")
        
        await self.redis.publish(channel, message)
        logger.debug(f"Published to {channel}: {message[:100]}...")
    
    async def subscribe(self, channel: str, callback: Callable[[str], Any]):
        """Subscribe to a channel with a callback"""
        if not self.pubsub:
            raise RuntimeError("Not connected to Redis")
        
        await self.pubsub.subscribe(channel)
        self._subscriptions[channel] = callback
        logger.info(f"Subscribed to channel: {channel}")
        
        # Start listener if not running
        if not self._listener_task or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._listen())
    
    async def unsubscribe(self, channel: str):
        """Unsubscribe from a channel"""
        if not self.pubsub:
            return
        
        await self.pubsub.unsubscribe(channel)
        self._subscriptions.pop(channel, None)
        logger.info(f"Unsubscribed from channel: {channel}")
    
    async def _listen(self):
        """Listen for messages on subscribed channels"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    
                    callback = self._subscriptions.get(channel)
                    if callback:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(data)
                            else:
                                callback(data)
                        except Exception as e:
                            logger.error(f"Error in callback for {channel}: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Listener error: {e}")
    
    # Stream operations for persistent task queues
    
    async def add_to_stream(self, stream: str, data: Dict[str, Any]) -> str:
        """Add a message to a stream"""
        if not self.redis:
            raise RuntimeError("Not connected to Redis")
        
        # Flatten dict for Redis
        flat_data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in data.items()}
        
        message_id = await self.redis.xadd(stream, flat_data)
        logger.debug(f"Added to stream {stream}: {message_id}")
        return message_id
    
    async def read_from_stream(
        self,
        stream: str,
        consumer_group: str,
        consumer_name: str,
        count: int = 1,
        block: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Read messages from a stream as a consumer"""
        if not self.redis:
            raise RuntimeError("Not connected to Redis")
        
        try:
            # Ensure consumer group exists
            try:
                await self.redis.xgroup_create(stream, consumer_group, id="0", mkstream=True)
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
            
            # Read messages
            messages = await self.redis.xreadgroup(
                consumer_group,
                consumer_name,
                {stream: ">"},
                count=count,
                block=block,
            )
            
            result = []
            for stream_name, stream_messages in messages:
                for message_id, data in stream_messages:
                    # Parse JSON values
                    parsed = {}
                    for k, v in data.items():
                        try:
                            parsed[k] = json.loads(v)
                        except json.JSONDecodeError:
                            parsed[k] = v
                    parsed["_id"] = message_id
                    result.append(parsed)
            
            return result
            
        except Exception as e:
            logger.error(f"Error reading from stream {stream}: {e}")
            return []
    
    async def ack_message(self, stream: str, consumer_group: str, message_id: str):
        """Acknowledge a message from a stream"""
        if not self.redis:
            raise RuntimeError("Not connected to Redis")
        
        await self.redis.xack(stream, consumer_group, message_id)
    
    async def get_stream_length(self, stream: str) -> int:
        """Get the length of a stream"""
        if not self.redis:
            return 0
        
        return await self.redis.xlen(stream)
    
    async def trim_stream(self, stream: str, maxlen: int):
        """Trim a stream to a maximum length"""
        if not self.redis:
            return
        
        await self.redis.xtrim(stream, maxlen=maxlen)
'''
    runtime_dir = BASE_DIR / "mycosoft_mas" / "runtime"
    (runtime_dir / "message_broker.py").write_text(content)
    print("Created mycosoft_mas/runtime/message_broker.py")


def create_requirements_agent():
    """Create requirements file for agent containers"""
    content = '''# MAS Agent Container Requirements
aiohttp>=3.9.0
aiofiles>=23.2.0
redis>=5.0.0
docker>=7.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
httpx>=0.25.0
structlog>=23.2.0
tenacity>=8.2.0
prometheus-client>=0.19.0
'''
    (BASE_DIR / "requirements-agent.txt").write_text(content)
    print("Created requirements-agent.txt")


def main():
    """Create all runtime files"""
    print("Creating MAS v2 Runtime Files...")
    print(f"Base directory: {BASE_DIR}")
    print()
    
    create_dockerfile_agent()
    create_runtime_init()
    create_models()
    create_agent_runtime()
    create_agent_pool()
    create_snapshot_manager()
    create_message_broker()
    create_requirements_agent()
    
    print()
    print("All runtime files created successfully!")


if __name__ == "__main__":
    main()
