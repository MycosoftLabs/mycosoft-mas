from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import for type-checking only; avoid heavy imports at runtime.
    from .agent_manager import AgentManager  # noqa: F401
    from .task_manager import TaskManager  # noqa: F401

__all__ = ["AgentManager", "TaskManager"]
