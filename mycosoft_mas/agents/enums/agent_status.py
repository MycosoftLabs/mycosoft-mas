from enum import Enum

class AgentStatus(Enum):
    """Agent lifecycle status enumeration."""
    INITIALIZED = "initialized"  # Agent created but not yet started
    INITIALIZING = "initializing"  # Agent is starting up
    RUNNING = "running"  # Legacy/test alias for "active"
    ACTIVE = "active"  # Agent is running and processing
    PAUSED = "paused"  # Agent is temporarily suspended
    IDLE = "idle"  # Agent is running but has no tasks
    BUSY = "busy"  # Agent is actively processing a task
    ERROR = "error"  # Agent encountered an error
    RECOVERING = "recovering"  # Agent is recovering from an error
    SHUTDOWN = "shutdown"  # Agent has been stopped
    TERMINATED = "terminated"  # Agent has been forcefully stopped 