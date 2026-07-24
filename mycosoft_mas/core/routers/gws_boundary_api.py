"""Read-only status API for Google Workspace CUI-boundary scan results."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from mycosoft_mas.soc.gws_boundary_scan import get_boundary_status

router = APIRouter(prefix="/api/security/gws-boundary", tags=["security", "gws-boundary"])


@router.get("/health")
async def gws_boundary_health() -> dict[str, Any]:
    status = await get_boundary_status()
    return {
        "ok": status["status"] not in {"error"},
        "configured": status["configured"],
        "status": status["status"],
    }


@router.get("/status")
async def gws_boundary_status() -> dict[str, Any]:
    """Return metadata-only scan state for the website BFF."""
    return await get_boundary_status()
