"""
Agent Event Schema - February 9, 2026

Pydantic models for Agent Event Bus messages.
Used by /ws/agent-bus WebSocket endpoint and Redis pub/sub bridge.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

EVENT_TYPES = Literal[
    "task",
    "result",
    "alert",
    "heartbeat",
    "tool_call",
    "status",
]


class AgentEvent(BaseModel):
    """Agent-to-agent event for the Event Bus."""

    type: EVENT_TYPES = Field(
        ...,
        description="Event type: task, result, alert, heartbeat, tool_call, status",
    )
    from_agent: str = Field(..., min_length=1, max_length=256, description="Source agent ID")
    to_agent: str | Literal["broadcast"] = Field(
        ...,
        description="Target agent ID or 'broadcast' for all",
    )
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp",
    )
    trace_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique trace ID for request correlation",
    )
    classification: str = Field(
        default="UNCLASS",
        description="Classification tag: UNCLASS, CUI, ITAR",
    )

    model_config = {"extra": "forbid"}
