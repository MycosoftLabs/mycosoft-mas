"""
Error Sanitization for MYCA LLM and API Responses

Strips API keys, tokens, credentials, and internal details from error messages
before they reach users or logs. Prevents exposure of sensitive data.

Created: February 17, 2026
"""

import re
from typing import Optional

# Patterns that indicate sensitive data (case-insensitive)
SENSITIVE_PATTERNS = [
    r"[aA][pP][iI][-_]?[kK]ey\s*[:=]\s*['\"]?[^\s'\"]+",
    r"[tT]oken\s*[:=]\s*['\"]?[^\s'\"]+",
    r"[pP]assword\s*[:=]\s*['\"]?[^\s'\"]+",
    r"[sS]ecret\s*[:=]\s*['\"]?[^\s'\"]+",
    r"[bB]earer\s+[a-zA-Z0-9_\-\.]+",
    r"sk-[a-zA-Z0-9\-]{20,}",
    r"sk-proj-[a-zA-Z0-9\-_]+",
    r"sk-ant-[a-zA-Z0-9\-_]+",
    r"AIza[a-zA-Z0-9_\-]{35}",
    r"xai-[a-zA-Z0-9\-_]+",
    r"gsk_[a-zA-Z0-9\-_]+",
]

# Compiled regex for API key-like strings (alphanumeric + underscores, 20+ chars)
KEY_LIKE = re.compile(r"\b[A-Za-z0-9_\-]{30,}\b")


def _redact_sensitive(text: str) -> str:
    """Replace sensitive patterns with [REDACTED]."""
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""
    result = text
    for pattern in SENSITIVE_PATTERNS:
        result = re.sub(pattern, "[REDACTED]", result, flags=re.IGNORECASE)
    # Redact long key-like strings
    result = KEY_LIKE.sub("[REDACTED]", result)
    return result


def sanitize_for_user(error: Exception) -> str:
    """
    Return a safe, user-facing error message.
    Never exposes API keys, internal paths, or stack traces.
    """
    if error is None:
        return "An unexpected error occurred. Please try again."
    msg = str(error)
    if not msg:
        return "Something went wrong. Please try again in a moment."
    # Always return generic message for users - never raw exception text
    redacted = _redact_sensitive(msg)
    if redacted != msg or any(
        s in msg.lower()
        for s in ("api", "key", "token", "credential", "connection", "timeout")
    ):
        return "I'm having a moment of difficulty with that request. Could you try again in a moment?"
    # For benign-looking errors, still avoid exposing internals
    return "I'm having a moment of difficulty with that request. Could you try again in a moment?"


def sanitize_for_log(error: Exception, max_len: int = 200) -> str:
    """
    Return a sanitized string safe for logging.
    Redacts keys/tokens but preserves error type and non-sensitive context.
    """
    if error is None:
        return "None"
    msg = str(error)
    if not msg:
        return f"{type(error).__name__}: (empty)"
    redacted = _redact_sensitive(msg)
    if len(redacted) > max_len:
        redacted = redacted[: max_len - 3] + "..."
    return f"{type(error).__name__}: {redacted}"


def sanitize_error_body(body: bytes, max_len: int = 100) -> str:
    """
    Sanitize an HTTP response body for logging.
    Redacts any keys/tokens that might appear in error responses.
    """
    if not body:
        return ""
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        return "[binary response]"
    redacted = _redact_sensitive(text)
    if len(redacted) > max_len:
        redacted = redacted[: max_len - 3] + "..."
    return redacted
