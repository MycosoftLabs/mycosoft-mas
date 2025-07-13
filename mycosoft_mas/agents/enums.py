"""
Enums for Mycosoft MAS
"""

from enum import Enum, auto

class AgentStatus(Enum):
    """Agent status enum."""
    # Agent has completed initialization and is ready for use
    INITIALIZED = "initialized"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ERROR = "error"
    STOPPED = "stopped"