from enum import Enum

class AgentStatus(Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown" 