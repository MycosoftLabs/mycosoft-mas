"""Read-only integrity status for the MAS CMMC posture monitor."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from mycosoft_mas.security.posture_integrity_monitor import (
    posture_integrity_monitor,
)

router = APIRouter(prefix="/api/security", tags=["security", "cmmc-posture"])


@router.get("/posture-integrity")
async def posture_integrity_health() -> dict[str, object]:
    """Report whether MAS has a verified CMMC practice snapshot."""
    health = await posture_integrity_monitor.health()
    if health["last_known_good"] is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "snapshot_unavailable",
            },
        )
    return health
