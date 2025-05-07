"""
Enums for Mycosoft MAS
"""

from enum import Enum, auto

class AgentStatus(Enum):
    """Agent status enum."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ERROR = "error"
    STOPPED = "stopped" 