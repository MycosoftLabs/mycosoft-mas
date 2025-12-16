"""
Structured Logging Configuration

Provides JSON-formatted structured logging with:
- Correlation ID tracking per request
- Automatic secret redaction
- Prometheus metrics integration
- Log level configuration via environment

Usage:
    from mycosoft_mas.core.logging_config import setup_logging, get_logger
    
    # Setup at application start
    setup_logging()
    
    # Get a logger
    logger = get_logger(__name__)
    logger.info("Message", extra={"user_id": "123"})
"""

import json
import logging
import os
import re
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[UUID]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> UUID:
    """Get the current correlation ID or create a new one."""
    cid = correlation_id_var.get()
    if cid is None:
        cid = uuid4()
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: UUID) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(cid)


class SecretRedactor:
    """
    Redacts sensitive information from log messages.
    """
    
    # Patterns that indicate sensitive data
    SENSITIVE_PATTERNS = [
        r'password["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',
        r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',
        r'secret["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',
        r'token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',
        r'authorization["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)',
        r'bearer\s+([^\s]+)',
        r'sk-[a-zA-Z0-9]+',  # OpenAI API keys
        r'sk-ant-[a-zA-Z0-9]+',  # Anthropic API keys
    ]
    
    # Compiled patterns
    _compiled = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_PATTERNS]
    
    @classmethod
    def redact(cls, message: str) -> str:
        """Redact sensitive information from a message."""
        result = message
        for pattern in cls._compiled:
            result = pattern.sub(lambda m: "[REDACTED]", result)
        return result
    
    @classmethod
    def redact_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive information from a dictionary."""
        result = {}
        sensitive_keys = {
            "password", "secret", "token", "api_key", "apikey",
            "authorization", "auth", "key", "credential", "private"
        }
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key is sensitive
            if any(s in key_lower for s in sensitive_keys):
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = cls.redact_dict(value)
            elif isinstance(value, str):
                result[key] = cls.redact(value)
            else:
                result[key] = value
        
        return result


class JsonFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    
    Outputs logs in JSON format with:
    - timestamp
    - level
    - logger name
    - message
    - correlation_id
    - extra fields
    """
    
    def __init__(self, include_extra: bool = True, redact_secrets: bool = True):
        super().__init__()
        self.include_extra = include_extra
        self.redact_secrets = redact_secrets
        
        # Fields to exclude from extra
        self._exclude_fields = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module", "msecs",
            "message", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName",
            "taskName",
        }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add correlation ID
        cid = correlation_id_var.get()
        if cid:
            log_data["correlation_id"] = str(cid)
        
        # Add location info for errors
        if record.levelno >= logging.ERROR:
            log_data["location"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if self.include_extra:
            extra = {}
            for key, value in record.__dict__.items():
                if key not in self._exclude_fields:
                    try:
                        # Ensure JSON serializable
                        json.dumps(value)
                        extra[key] = value
                    except (TypeError, ValueError):
                        extra[key] = str(value)
            
            if extra:
                if self.redact_secrets:
                    extra = SecretRedactor.redact_dict(extra)
                log_data["extra"] = extra
        
        # Redact message if needed
        if self.redact_secrets:
            log_data["message"] = SecretRedactor.redact(log_data["message"])
        
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """
    Text formatter for human-readable logs (development mode).
    """
    
    def __init__(self, redact_secrets: bool = True):
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        super().__init__(fmt=fmt)
        self.redact_secrets = redact_secrets
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as text."""
        # Add correlation ID to message
        cid = correlation_id_var.get()
        if cid:
            record.msg = f"[{str(cid)[:8]}] {record.msg}"
        
        result = super().format(record)
        
        if self.redact_secrets:
            result = SecretRedactor.redact(result)
        
        return result


class CorrelationIdFilter(logging.Filter):
    """
    Filter that adds correlation_id to all log records.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        cid = correlation_id_var.get()
        record.correlation_id = str(cid) if cid else ""
        return True


def setup_logging(
    level: Optional[str] = None,
    format_type: Optional[str] = None,
    redact_secrets: bool = True,
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("json" or "text")
        redact_secrets: Whether to redact sensitive information
    """
    # Get settings from environment
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    log_format = format_type or os.getenv("LOG_FORMAT", "json")
    
    # Convert level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Set formatter based on format type
    if log_format.lower() == "json":
        formatter = JsonFormatter(redact_secrets=redact_secrets)
    else:
        formatter = TextFormatter(redact_secrets=redact_secrets)
    
    console_handler.setFormatter(formatter)
    
    # Add correlation ID filter
    console_handler.addFilter(CorrelationIdFilter())
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Log startup message
    root_logger.info(
        "Logging configured",
        extra={"level": log_level, "format": log_format},
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LoggingMiddleware:
    """
    FastAPI middleware for request logging with correlation IDs.
    
    Usage:
        from fastapi import FastAPI
        from mycosoft_mas.core.logging_config import LoggingMiddleware
        
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)
    """
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger("http")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Generate or extract correlation ID
        headers = dict(scope.get("headers", []))
        cid_header = headers.get(b"x-correlation-id", b"").decode()
        
        if cid_header:
            try:
                cid = UUID(cid_header)
            except ValueError:
                cid = uuid4()
        else:
            cid = uuid4()
        
        # Set correlation ID for this request
        set_correlation_id(cid)
        
        # Log request
        start_time = datetime.now()
        method = scope.get("method", "")
        path = scope.get("path", "")
        
        self.logger.info(
            f"Request started: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "client": scope.get("client", ["", 0])[0],
            },
        )
        
        # Track response status
        status_code = 500
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            self.logger.exception(f"Request failed: {method} {path}")
            raise
        finally:
            # Log response
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.logger.info(
                f"Request completed: {method} {path} -> {status_code}",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
