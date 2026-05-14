"""Internal service-token guard for website-to-MAS privileged routes."""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


async def require_internal_service_token(
    x_myca_service_token: str | None = Header(default=None, alias="X-MYCA-Service-Token"),
    x_mycosoft_service_token: str | None = Header(default=None, alias="X-MYCOSOFT-Service-Token"),
    x_internal_service_token: str | None = Header(default=None, alias="X-Internal-Service-Token"),
):
    expected = (
        os.getenv("MYCA_INTERNAL_SERVICE_TOKEN")
        or os.getenv("MAS_INTERNAL_SERVICE_TOKEN")
        or os.getenv("MYCA_MAS_SERVICE_TOKEN")
    )
    if not expected:
        return True

    for provided in (x_myca_service_token, x_internal_service_token, x_mycosoft_service_token):
        if provided and hmac.compare_digest(provided, expected):
            return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid internal service token",
    )
