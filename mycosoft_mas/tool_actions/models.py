from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class ToolAction(BaseModel):
    """Typed tool action payload used for audit logging."""

    action: str
    category: Literal["external_write", "data_read", "system_change", "other"] = "other"
    actor: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def redacted_inputs(self) -> Dict[str, Any]:
        """Redact obvious secrets in inputs."""
        redacted = {}
        for key, value in self.inputs.items():
            if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
                redacted[key] = "***"
            else:
                redacted[key] = value
        return redacted
