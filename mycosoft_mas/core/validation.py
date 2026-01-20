"""Input validation utilities for MAS API."""

import re
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class SafeStringValidator:
    """Validator for preventing injection attacks in string inputs."""
    
    # Patterns that might indicate injection attempts
    DANGEROUS_PATTERNS = [
        r"<script\b",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers
        r"(\$\{|\$\()",  # Template injection
        r"{{.*}}",  # Template injection
        r";\s*(DROP|DELETE|UPDATE|INSERT|TRUNCATE|ALTER)\s",  # SQL keywords after semicolon
        r"'\s*OR\s+'?1'?\s*=\s*'?1",  # Classic SQL injection
        r"--\s*$",  # SQL comment
    ]
    
    @classmethod
    def is_safe(cls, value: str) -> bool:
        """Check if a string is safe from common injection patterns."""
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False
        return True
    
    @classmethod
    def sanitize(cls, value: str) -> str:
        """Basic sanitization - escape HTML entities."""
        return (
            value
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )


class ValidatedAgentInput(BaseModel):
    """Validated input model for agent operations."""
    
    agent_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    task: Optional[str] = Field(None, max_length=10000)
    parameters: Optional[dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator("task")
    @classmethod
    def validate_task(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not SafeStringValidator.is_safe(v):
            raise ValueError("Task contains potentially dangerous content")
        return v


class ValidatedQueryInput(BaseModel):
    """Validated input model for search/query operations."""
    
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not SafeStringValidator.is_safe(v):
            raise ValueError("Query contains potentially dangerous content")
        return v.strip()


class ValidatedDocumentInput(BaseModel):
    """Validated input model for document operations."""
    
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., max_length=100000)
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator("title", "content")
    @classmethod
    def validate_strings(cls, v: str) -> str:
        if not SafeStringValidator.is_safe(v):
            raise ValueError("Input contains potentially dangerous content")
        return v


class ValidatedWebhookPayload(BaseModel):
    """Validated input for webhook endpoints."""
    
    event_type: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    timestamp: Optional[str] = Field(None, max_length=50)
    data: Optional[dict[str, Any]] = Field(default_factory=dict)
    
    @model_validator(mode="after")
    def validate_data_size(self) -> "ValidatedWebhookPayload":
        """Ensure data dict isn't too large."""
        import json
        data_size = len(json.dumps(self.data or {}))
        if data_size > 50000:
            raise ValueError(f"Webhook data too large: {data_size} bytes (max 50000)")
        return self
