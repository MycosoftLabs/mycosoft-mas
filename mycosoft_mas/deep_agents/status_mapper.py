"""
Status mapping between MAS task states and agent protocol states.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

try:
    from mycosoft_mas.agents.enums.task_status import TaskStatus as CoreTaskStatus
except Exception:  # noqa: BLE001
    CoreTaskStatus = None

try:
    from agents.enums.task_status import TaskStatus as LegacyTaskStatus
except Exception:  # noqa: BLE001
    LegacyTaskStatus = None


class DeepAgentTaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


def _normalize_status_value(status: object) -> Optional[str]:
    if status is None:
        return None
    if isinstance(status, Enum):
        return str(status.value)
    return str(status)


def map_mas_status_to_deep(status: object) -> DeepAgentTaskState:
    normalized = (_normalize_status_value(status) or "").lower()
    if normalized in {"todo", "scheduled", "on_hold"}:
        return DeepAgentTaskState.PENDING
    if normalized in {"in_progress", "review"}:
        return DeepAgentTaskState.RUNNING
    if normalized == "completed":
        return DeepAgentTaskState.SUCCEEDED
    if normalized in {"cancelled"}:
        return DeepAgentTaskState.CANCELLED
    if normalized in {"blocked", "overdue"}:
        return DeepAgentTaskState.BLOCKED
    return DeepAgentTaskState.FAILED


def map_deep_to_agent_protocol_state(status: DeepAgentTaskState) -> str:
    mapping = {
        DeepAgentTaskState.PENDING: "TASK_STATE_PENDING",
        DeepAgentTaskState.RUNNING: "TASK_STATE_RUNNING",
        DeepAgentTaskState.SUCCEEDED: "TASK_STATE_COMPLETED",
        DeepAgentTaskState.FAILED: "TASK_STATE_FAILED",
        DeepAgentTaskState.CANCELLED: "TASK_STATE_CANCELED",
        DeepAgentTaskState.BLOCKED: "TASK_STATE_WAITING",
    }
    return mapping[status]


__all__ = [
    "CoreTaskStatus",
    "LegacyTaskStatus",
    "DeepAgentTaskState",
    "map_mas_status_to_deep",
    "map_deep_to_agent_protocol_state",
]
