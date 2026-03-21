"""
Deterministic canonicalization and hashing for Experience Packets.

Ensures stable JSON serialization for provenance hashing.
Secrets and sensitive keys are redacted before canonicalization.

Created: February 17, 2026
"""

import hashlib
import json
from typing import Any, List

# Key patterns to redact from canonicalization (case-insensitive)
SECRET_PATTERNS: List[str] = [
    "token",
    "key",
    "password",
    "secret",
    "credential",
    "api_key",
    "apikey",
    "auth",
    "bearer",
]


def _is_secret_key(key: str) -> bool:
    """Check if a key should be redacted."""
    key_lower = key.lower()
    for pattern in SECRET_PATTERNS:
        if pattern in key_lower:
            return True
    return False


def _redact_obj(obj: Any) -> Any:
    """
    Recursively redact secret values from a structure.
    Replaces secret values with '[REDACTED]'.
    """
    if obj is None:
        return None
    if isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if _is_secret_key(str(k)):
                result[k] = "[REDACTED]"
            else:
                result[k] = _redact_obj(v)
        return result
    if isinstance(obj, (list, tuple)):
        return [_redact_obj(item) for item in obj]
    # For dataclasses and custom objects, convert to dict first
    if hasattr(obj, "__dict__"):
        return _redact_obj(obj.__dict__)
    return obj


def _to_json_serializable(obj: Any) -> Any:
    """Convert object to JSON-serializable form."""
    if obj is None:
        return None
    if isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _to_json_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "value"):  # Enum
        return obj.value
    if hasattr(obj, "__dict__"):
        return _to_json_serializable(
            {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        )
    return str(obj)


def canonical_json(obj: Any, redact_secrets: bool = True) -> bytes:
    """
    Produce deterministic JSON bytes with sorted keys.
    Optionally redact secret values before serialization.
    """
    if redact_secrets:
        obj = _redact_obj(obj)
    serializable = _to_json_serializable(obj)

    def _sort_keys(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _sort_keys(v) for k, v in sorted(obj.items())}
        if isinstance(obj, list):
            return [_sort_keys(item) for item in obj]
        return obj

    sorted_obj = _sort_keys(serializable)
    return json.dumps(sorted_obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def hash_sha256(canonical_bytes: bytes) -> str:
    """Compute SHA256 hash of canonical bytes. Returns hex digest."""
    return hashlib.sha256(canonical_bytes).hexdigest()
