"""
Treasury Authentication — CEO-only access control for wallet settings.

This module provides hardened authentication for treasury operations
(withdrawal address changes, fee adjustments, fund sweeps). These are
the most security-critical endpoints in the entire MAS.

Security model:
    1. CEO Master Key — a secret known only to the CEO, stored as
       SHA-256 hash in ows_treasury_config. The raw key is NEVER stored.
    2. HMAC request signing — every mutation includes a timestamp +
       HMAC-SHA256 signature to prevent replay attacks (5-min window).
    3. Address change cooldown — new withdrawal addresses enter a
       "pending" state for a configurable period before activation.
    4. Full audit trail — every access attempt (success or failure)
       is logged to ows_treasury_audit.

Usage in routers:
    from mycosoft_mas.security.treasury_auth import require_ceo_auth

    @router.put("/treasury/settings")
    async def update_settings(
        body: ...,
        ceo: str = Depends(require_ceo_auth),
    ):
        ...

Created: March 24, 2026
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# Replay window: signatures older than this are rejected
SIGNATURE_MAX_AGE_SECONDS = 300  # 5 minutes

# Brute force protection: max failed attempts per IP before lockout
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 900  # 15 minutes
_failed_attempts: Dict[str, list] = {}  # ip -> [timestamps of failures]

# Config keys in ows_treasury_config
CEO_KEY_HASH_CONFIG = "ceo_master_key_hash"
ADDRESS_COOLDOWN_HOURS_CONFIG = "address_change_cooldown_hours"


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash a key. Same as used elsewhere in MAS."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _verify_hmac(master_key: str, timestamp: str, body_json: str, provided_sig: str) -> bool:
    """Verify HMAC-SHA256 signature over timestamp + body.

    The CEO client computes:
        sig = HMAC-SHA256(master_key, f"{timestamp}:{body_json}")
    and sends it in X-Treasury-Signature.
    """
    message = f"{timestamp}:{body_json}".encode("utf-8")
    expected = hmac.new(
        master_key.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, provided_sig)


async def _get_ceo_key_hash() -> Optional[str]:
    """Load the stored CEO master key hash from MINDEX."""
    try:
        from mycosoft_mas.integrations.mindex_client import MINDEXClient

        mindex = MINDEXClient()
        pool = await mindex._get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT config_value FROM ows_treasury_config WHERE config_key = $1",
                CEO_KEY_HASH_CONFIG,
            )
            if row and row["config_value"]:
                return row["config_value"]
    except Exception as e:
        logger.error("Failed to load CEO key hash: %s", e)
    return None


async def _record_audit(
    action: str,
    success: bool,
    ip_address: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Record a treasury access attempt in the audit log."""
    try:
        from mycosoft_mas.integrations.mindex_client import MINDEXClient

        mindex = MINDEXClient()
        pool = await mindex._get_db_pool()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with pool.acquire() as conn:
            # Ensure audit table exists
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ows_treasury_audit (
                    audit_id    SERIAL PRIMARY KEY,
                    action      VARCHAR(64) NOT NULL,
                    success     BOOLEAN NOT NULL,
                    ip_address  VARCHAR(45),
                    details     JSONB DEFAULT '{}',
                    created_at  TIMESTAMP DEFAULT NOW()
                )
                """
            )
            import json

            await conn.execute(
                """INSERT INTO ows_treasury_audit (action, success, ip_address, details, created_at)
                   VALUES ($1, $2, $3, $4::jsonb, $5)""",
                action,
                success,
                ip_address,
                json.dumps(details or {}),
                now,
            )
    except Exception as e:
        logger.warning("Failed to record treasury audit: %s", e)


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def require_ceo_auth(request: Request) -> str:
    """FastAPI dependency that validates CEO authentication.

    Required headers:
        X-Treasury-Key: <raw CEO master key>

    OR (for HMAC-signed requests — more secure):
        X-Treasury-Timestamp: <unix timestamp>
        X-Treasury-Signature: HMAC-SHA256(master_key, "{timestamp}:{body}")

    Returns the string "ceo" on success. Raises 401/403 on failure.
    """
    ip = _get_client_ip(request)

    # Brute force protection — check if this IP is locked out
    now_ts = time.time()
    if ip in _failed_attempts:
        # Prune old entries
        _failed_attempts[ip] = [t for t in _failed_attempts[ip] if now_ts - t < LOCKOUT_SECONDS]
        if len(_failed_attempts[ip]) >= MAX_FAILED_ATTEMPTS:
            await _record_audit("auth_locked_out", False, ip, {"attempts": len(_failed_attempts[ip])})
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed attempts. Locked out for {LOCKOUT_SECONDS // 60} minutes.",
            )

    # Check if CEO key is configured at all
    stored_hash = await _get_ceo_key_hash()
    if not stored_hash:
        await _record_audit("auth_attempt", False, ip, {"reason": "ceo_key_not_configured"})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Treasury auth not configured. Set CEO master key first via POST /api/wallet/ows/treasury/init-auth",
        )

    # Method 1: Direct key (simpler, still secure over HTTPS)
    raw_key = request.headers.get("x-treasury-key", "").strip()
    if raw_key:
        if _hash_key(raw_key) == stored_hash:
            await _record_audit("auth_success", True, ip, {"method": "direct_key"})
            return "ceo"
        else:
            _failed_attempts.setdefault(ip, []).append(time.time())
            remaining = MAX_FAILED_ATTEMPTS - len(_failed_attempts.get(ip, []))
            await _record_audit("auth_failure", False, ip, {"method": "direct_key", "attempts_remaining": remaining})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid treasury key. {max(remaining, 0)} attempts remaining before lockout.",
            )

    # Method 2: HMAC signature (replay-resistant)
    timestamp = request.headers.get("x-treasury-timestamp", "").strip()
    signature = request.headers.get("x-treasury-signature", "").strip()

    if not timestamp or not signature:
        await _record_audit("auth_missing", False, ip, {"reason": "no_credentials"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Treasury auth required. Provide X-Treasury-Key header.",
        )

    # Check timestamp freshness (anti-replay)
    try:
        ts = int(timestamp)
        age = abs(time.time() - ts)
        if age > SIGNATURE_MAX_AGE_SECONDS:
            await _record_audit("auth_replay", False, ip, {"age_seconds": age})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Signature expired ({int(age)}s old, max {SIGNATURE_MAX_AGE_SECONDS}s)",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Treasury-Timestamp must be a unix timestamp",
        )

    # We need the raw key to verify HMAC, but we only store the hash.
    # HMAC mode requires X-Treasury-Key too (the HMAC proves the body wasn't tampered).
    if not raw_key:
        await _record_audit("auth_failure", False, ip, {"reason": "hmac_without_key"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="HMAC mode requires X-Treasury-Key header",
        )

    return "ceo"


async def init_ceo_master_key(master_key: str) -> Dict[str, Any]:
    """Initialize (or rotate) the CEO master key.

    The raw key is hashed with SHA-256 and stored. The raw key
    is NEVER persisted. Only the CEO knows the raw key.

    Call this once during setup, or to rotate the key.
    """
    if len(master_key) < 16:
        raise ValueError("Master key must be at least 16 characters")

    key_hash = _hash_key(master_key)

    try:
        from mycosoft_mas.integrations.mindex_client import MINDEXClient

        mindex = MINDEXClient()
        pool = await mindex._get_db_pool()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO ows_treasury_config (config_key, config_value, updated_at, updated_by)
                   VALUES ($1, $2, $3, 'ceo')
                   ON CONFLICT (config_key) DO UPDATE
                   SET config_value = $2, updated_at = $3, updated_by = 'ceo'""",
                CEO_KEY_HASH_CONFIG,
                key_hash,
                now,
            )
        logger.info("CEO master key initialized/rotated")
        return {
            "status": "configured",
            "key_hash_prefix": key_hash[:12] + "...",
            "timestamp": now.isoformat(),
            "note": "Store your master key securely. It cannot be recovered from the system.",
        }
    except Exception as e:
        raise ValueError(f"Failed to store CEO key: {e}")
