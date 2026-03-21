"""
Enums for Mycosoft MAS
"""

from enum import Enum


class AgentStatus(Enum):
    """Agent status enum."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    ACTIVE = "active"
    ERROR = "error"
    STOPPED = "stopped"
