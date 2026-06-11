"""
Shared internal-token auth for infra-sensitive MAS routers — June 11, 2026.

Closes the unauthenticated-infra-route class from the June 9, 2026 backend
security audit (docs/SECURITY_AUDIT_ALL_SYSTEMS_JUN09_2026.md). Mirrors the
website PR #186 hardening on the MAS side so the direct 188:8001 path is
gated, not just the website proxies.

Behavior:
- Token read from env `MAS_INTERNAL_TOKEN` (comma-separated values allowed).
- Callers send `X-MAS-Internal-Token: <token>` (or `Authorization: Bearer <token>`).
- Fail-closed in production: if `MAS_ENV`/`ENVIRONMENT` is production and no
  token is configured, requests are rejected (503) rather than silently open.
- Outside production, an unset token logs a loud warning once and allows the
  request, so local dev and tests keep working without extra setup.
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Optional

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)

_warned_open = False


def _configured_tokens() -> list[str]:
    raw = os.getenv("MAS_INTERNAL_TOKEN", "") or os.getenv("MAS_INTERNAL_TOKENS", "")
    return [t.strip() for t in raw.split(",") if t.strip()]


def _is_production() -> bool:
    env = (os.getenv("MAS_ENV") or os.getenv("ENVIRONMENT") or "").strip().lower()
    return env in ("production", "prod")


async def require_internal_token(
    x_mas_internal_token: Optional[str] = Header(default=None, alias="X-MAS-Internal-Token"),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """FastAPI dependency gating mutating infra endpoints.

    Usage: APIRouter(..., dependencies=[Depends(require_internal_token)])
    """
    global _warned_open

    tokens = _configured_tokens()
    if not tokens:
        if _is_production():
            raise HTTPException(
                status_code=503,
                detail="MAS_INTERNAL_TOKEN not configured; infra endpoints disabled",
            )
        if not _warned_open:
            logger.warning(
                "MAS_INTERNAL_TOKEN unset — infra endpoints UNAUTHENTICATED (non-production only)"
            )
            _warned_open = True
        return "no-auth-dev"

    presented = (x_mas_internal_token or "").strip()
    if not presented and authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()

    if presented and any(secrets.compare_digest(presented, t) for t in tokens):
        return presented

    raise HTTPException(status_code=401, detail="Invalid or missing X-MAS-Internal-Token")
