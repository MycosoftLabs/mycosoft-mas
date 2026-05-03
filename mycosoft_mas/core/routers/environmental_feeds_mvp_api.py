"""
Environmental feeds MVP — real OpenAQ measurements; honest unavailability for radiation / virus overlays.

May 03, 2026. No fabricated PM2.5 or dose readings.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from mycosoft_mas.integrations.environmental_client import EnvironmentalClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/natureos/feeds", tags=["natureos-environmental-feeds"])


@router.get("/openaq/measurements")
async def openaq_measurements(
    limit: int = Query(25, ge=1, le=200),
    country: Optional[str] = Query(None, description="ISO country code, e.g. US"),
) -> Dict[str, Any]:
    """Proxy to OpenAQ v2 measurements — public API; optional OPENAQ_API_KEY for higher limits."""
    try:
        client = EnvironmentalClient()
        data = await client.get_air_quality_measurements(country=country, limit=limit)
        return {
            "source": "openaq",
            "available": True,
            "provenance": "https://api.openaq.org/v2/measurements",
            "data": data,
        }
    except Exception as exc:
        logger.warning("OpenAQ feed failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"openaq_unavailable: {exc!s}") from exc


@router.get("/radiation/status")
async def radiation_status(
    lat: float = Query(37.7749, description="Probe latitude"),
    lon: float = Query(-122.4194, description="Probe longitude"),
    distance: int = Query(25000, ge=1000, le=200000),
) -> JSONResponse:
    """
    Safecast measurements.json — may work without API key for coarse public reads.
    If the upstream rejects the request, return structured unavailability (never fake uSv/h).
    """
    try:
        client = EnvironmentalClient()
        readings = await client.get_radiation_measurements(lat=lat, lon=lon, distance=distance)
        payload: Dict[str, Any] = {
            "source": "safecast",
            "available": True,
            "provenance": "https://api.safecast.org/measurements.json",
            "count": len(readings) if isinstance(readings, list) else 0,
            "data": readings,
        }
        return JSONResponse(status_code=200, content=payload)
    except Exception as exc:
        logger.info("Radiation feed unavailable: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "source": "safecast",
                "available": False,
                "provenance": "https://api.safecast.org/measurements.json",
                "message": "Radiation feed unavailable from this runtime (network, rate limit, or Safecast response).",
                "detail": str(exc),
                "hint": "Set SAFECAST_API_KEY if your deployment requires authenticated access.",
            },
        )


@router.get("/virus-aerosol/status")
async def virus_aerosol_status() -> JSONResponse:
    """Explicit deferral — no surrogate viral load metrics are synthesized."""

    return JSONResponse(
        status_code=503,
        content={
            "feed": "virus_aerosol",
            "available": False,
            "message": "No virus/aerosol ingest connector is configured in this MVP — deferred to MINDEX/CREP ingest design.",
            "provenance": None,
        },
    )
