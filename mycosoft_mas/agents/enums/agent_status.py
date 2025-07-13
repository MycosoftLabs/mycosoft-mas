from enum import Enum

class AgentStatus(Enum):
    """Agent status enum used by agents."""
    # Agent has completed initialization and is ready
    INITIALIZED = "initialized"
    # Agent is in the process of initializing
    INITIALIZING = "initializing"
    # Agent is actively running
    ACTIVE = "active"
    # Agent is paused temporarily
    PAUSED = "paused"
    # Agent encountered an error
    ERROR = "error"
    # Agent has been stopped
    STOPPED = "stopped"
    # Agent has been shut down and will not restart
    SHUTDOWN = "shutdown"