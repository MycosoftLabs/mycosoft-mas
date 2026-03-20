"""
MINDEX Internal Authentication Utility

Generates X-Internal-Token headers for service-to-service communication
between MAS (VM 188) and MINDEX (VM 189) using a shared secret.

The token is an HMAC-SHA256 signature over a timestamp, providing:
- Authentication: only services with the shared secret can generate valid tokens
- Replay protection: tokens expire after 5 minutes

Environment Variables:
    MINDEX_INTERNAL_SECRET: Shared secret between MAS and MINDEX for internal API auth

Created: 2026-03-19
"""

import hashlib
import hmac
import os
import time
from typing import Dict


# Shared secret for internal service-to-service auth
MINDEX_INTERNAL_SECRET = os.getenv("MINDEX_INTERNAL_SECRET", "")

# Token validity window (seconds)
TOKEN_TTL = 300  # 5 minutes


def generate_internal_token() -> str:
    """
    Generate an HMAC-SHA256 token for internal MINDEX API calls.

    Format: ``{timestamp}:{hmac_hex}``

    The MINDEX server validates by:
    1. Splitting on ':'
    2. Checking timestamp is within TOKEN_TTL
    3. Recomputing HMAC and comparing

    Returns empty string if MINDEX_INTERNAL_SECRET is not configured,
    allowing graceful degradation in dev environments.
    """
    secret = MINDEX_INTERNAL_SECRET
    if not secret:
        return ""

    timestamp = str(int(time.time()))
    signature = hmac.new(
        secret.encode("utf-8"),
        timestamp.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{timestamp}:{signature}"


def get_internal_headers() -> Dict[str, str]:
    """
    Return headers dict with X-Internal-Token for MINDEX internal API calls.

    If MINDEX_INTERNAL_SECRET is not set, returns an empty dict so existing
    API-key-based auth can still work as a fallback.
    """
    token = generate_internal_token()
    if token:
        return {"X-Internal-Token": token}
    return {}
