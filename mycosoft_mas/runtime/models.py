"""
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
