"""
Typed Action Definitions

Provides Pydantic models for strongly-typed action inputs and outputs.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


T = TypeVar("T")


class ActionStatus(str, Enum):
    """Status of an action execution."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionInput(BaseModel):
    """Base class for typed action inputs."""
    
    class Config:
        extra = "allow"  # Allow additional fields
        
    def redact_sensitive(self) -> dict[str, Any]:
        """
        Return a copy with sensitive fields redacted.
        Override in subclasses to specify sensitive fields.
        """
        return self.model_dump()


class ActionOutput(BaseModel):
    """Base class for typed action outputs."""
    
    class Config:
        extra = "allow"
        
    def redact_sensitive(self) -> dict[str, Any]:
        """Return a copy with sensitive fields redacted."""
        return self.model_dump()


class ActionError(BaseModel):
    """Structured action error."""
    error_type: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    stack_trace: Optional[str] = None
    retryable: bool = False
    
    @classmethod
    def from_exception(cls, exc: Exception, retryable: bool = False) -> "ActionError":
        """Create ActionError from an exception."""
        import traceback
        return cls(
            error_type=type(exc).__name__,
            message=str(exc),
            stack_trace=traceback.format_exc(),
            retryable=retryable,
        )


class ActionResult(BaseModel, Generic[T]):
    """
    Result of an action execution.
    
    Generic over the output type for type-safe results.
    """
    success: bool
    action_id: UUID = Field(default_factory=uuid4)
    action_name: str
    status: ActionStatus = ActionStatus.COMPLETED
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Result
    output: Optional[T] = None
    error: Optional[ActionError] = None
    
    # Metadata
    correlation_id: Optional[UUID] = None
    agent_id: Optional[str] = None
    
    @classmethod
    def ok(
        cls,
        action_name: str,
        output: T,
        correlation_id: Optional[UUID] = None,
        agent_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
    ) -> "ActionResult[T]":
        """Create a successful result."""
        now = datetime.now()
        start = started_at or now
        return cls(
            success=True,
            action_name=action_name,
            status=ActionStatus.COMPLETED,
            started_at=start,
            completed_at=now,
            duration_ms=int((now - start).total_seconds() * 1000),
            output=output,
            correlation_id=correlation_id,
            agent_id=agent_id,
        )
    
    @classmethod
    def fail(
        cls,
        action_name: str,
        error: ActionError | Exception,
        correlation_id: Optional[UUID] = None,
        agent_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
    ) -> "ActionResult[T]":
        """Create a failed result."""
        now = datetime.now()
        start = started_at or now
        
        if isinstance(error, Exception):
            error = ActionError.from_exception(error)
        
        return cls(
            success=False,
            action_name=action_name,
            status=ActionStatus.FAILED,
            started_at=start,
            completed_at=now,
            duration_ms=int((now - start).total_seconds() * 1000),
            error=error,
            correlation_id=correlation_id,
            agent_id=agent_id,
        )


# =============================================================================
# COMMON ACTION INPUT TYPES
# =============================================================================

class FileReadInput(ActionInput):
    """Input for file read operations."""
    path: str
    encoding: str = "utf-8"
    
    def redact_sensitive(self) -> dict[str, Any]:
        return {"path": self.path, "encoding": self.encoding}


class FileWriteInput(ActionInput):
    """Input for file write operations."""
    path: str
    content: str
    encoding: str = "utf-8"
    create_dirs: bool = True
    
    # Sensitive fields to redact
    _sensitive_fields = {"content"}
    
    def redact_sensitive(self) -> dict[str, Any]:
        data = self.model_dump()
        data["content"] = f"[REDACTED: {len(self.content)} chars]"
        return data


class HttpRequestInput(ActionInput):
    """Input for HTTP request operations."""
    url: str
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    timeout: int = 30
    
    def redact_sensitive(self) -> dict[str, Any]:
        data = self.model_dump()
        # Redact auth headers
        if "headers" in data:
            for key in list(data["headers"].keys()):
                if "auth" in key.lower() or "token" in key.lower() or "key" in key.lower():
                    data["headers"][key] = "[REDACTED]"
        return data


class DatabaseQueryInput(ActionInput):
    """Input for database query operations."""
    query: str
    params: dict[str, Any] = Field(default_factory=dict)
    
    def redact_sensitive(self) -> dict[str, Any]:
        # Redact query params that might contain sensitive data
        data = self.model_dump()
        for key in list(data.get("params", {}).keys()):
            if "password" in key.lower() or "secret" in key.lower() or "token" in key.lower():
                data["params"][key] = "[REDACTED]"
        return data


class LLMCallInput(ActionInput):
    """Input for LLM API calls."""
    prompt: str
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    
    def redact_sensitive(self) -> dict[str, Any]:
        data = self.model_dump()
        # Truncate long prompts in logs
        if len(self.prompt) > 500:
            data["prompt"] = self.prompt[:500] + f"... [truncated: {len(self.prompt)} total chars]"
        if self.system_prompt and len(self.system_prompt) > 200:
            data["system_prompt"] = self.system_prompt[:200] + "... [truncated]"
        return data


class EmailSendInput(ActionInput):
    """Input for email send operations."""
    to: list[str]
    subject: str
    body: str
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    
    def redact_sensitive(self) -> dict[str, Any]:
        data = self.model_dump()
        # Redact email body
        data["body"] = f"[REDACTED: {len(self.body)} chars]"
        # Redact BCC recipients
        data["bcc"] = [f"[REDACTED: {len(self.bcc)} recipients]"] if self.bcc else []
        return data


class ExternalAPIInput(ActionInput):
    """Input for external API calls."""
    service: str
    endpoint: str
    method: str = "GET"
    params: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[dict[str, Any]] = None
    
    def redact_sensitive(self) -> dict[str, Any]:
        data = self.model_dump()
        # Redact auth headers
        for key in list(data.get("headers", {}).keys()):
            if "auth" in key.lower() or "token" in key.lower() or "key" in key.lower():
                data["headers"][key] = "[REDACTED]"
        # Redact sensitive params
        for key in list(data.get("params", {}).keys()):
            if "password" in key.lower() or "secret" in key.lower() or "key" in key.lower():
                data["params"][key] = "[REDACTED]"
        return data
