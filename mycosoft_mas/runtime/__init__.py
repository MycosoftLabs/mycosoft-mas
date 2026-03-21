"""
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

from .agent_pool import AgentPool
from .agent_runtime import AgentRuntime
from .message_broker import MessageBroker
from .models import (
    AgentCategory,
    AgentConfig,
    AgentMessage,
    AgentMetrics,
    AgentSnapshot,
    AgentState,
    AgentStatus,
    AgentTask,
    MessageType,
    TaskPriority,
)
from .snapshot_manager import SnapshotManager

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
