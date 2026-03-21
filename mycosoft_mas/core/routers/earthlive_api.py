"""
EarthLIVE API Router - February 17, 2026

FastAPI router for EarthLIVE packetized environmental data:
- Weather (OpenMeteo)
- Seismic (USGS)
- Satellite (Celestrak)

Endpoints:
- GET  /api/earthlive/packet   - Unified EarthLIVE packet
- GET  /api/earthlive/weather  - Weather only
- GET  /api/earthlive/seismic  - Seismic only
- GET  /api/earthlive/satellite - Satellite only
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/earthlive", tags=["earthlive"])


@router.get("/packet")
async def get_earthlive_packet(
    latitude: float = Query(47.6062, description="Latitude"),
    longitude: float = Query(-122.3321, description="Longitude"),
    seismic_feed: str = Query("all_day", description="Seismic feed type"),
    satellite_group: str = Query("starlink", description="Satellite group"),
) -> Dict[str, Any]:
    """
    Assemble and return unified EarthLIVE packet from weather, seismic, satellite collectors.
    """
    try:
        from mycosoft_mas.earthlive.packet_assembler import assemble_from_collectors

        packet = await assemble_from_collectors(
            latitude=latitude,
            longitude=longitude,
            seismic_feed=seismic_feed,
            satellite_group=satellite_group,
        )
        return packet.to_dict()
    except Exception as e:
        logger.error(f"EarthLIVE packet assembly failed: {e}")
        return {
            "packet_id": None,
            "timestamp": None,
            "weather": {},
            "seismic": {},
            "satellite": {},
            "metadata": {"error": str(e)},
        }


@router.get("/weather")
async def get_weather(
    latitude: float = Query(47.6062, description="Latitude"),
    longitude: float = Query(-122.3321, description="Longitude"),
) -> Dict[str, Any]:
    """Get weather data only from OpenMeteo."""
    try:
        from mycosoft_mas.earthlive.collectors.weather import WeatherCollector

        wc = WeatherCollector(latitude=latitude, longitude=longitude)
        return await wc.collect()
    except Exception as e:
        logger.error(f"Weather collect failed: {e}")
        return {"error": str(e)}


@router.get("/seismic")
async def get_seismic(
    feed: str = Query("all_day", description="Seismic feed (all_day, significant)"),
) -> Dict[str, Any]:
    """Get seismic data only from USGS."""
    try:
        from mycosoft_mas.earthlive.collectors.seismic import SeismicCollector

        sc = SeismicCollector(feed=feed)
        return await sc.collect()
    except Exception as e:
        logger.error(f"Seismic collect failed: {e}")
        return {"error": str(e)}


@router.get("/satellite")
async def get_satellite(
    group: str = Query("starlink", description="Satellite group (starlink, iss, etc.)"),
) -> Dict[str, Any]:
    """Get satellite pass data only from Celestrak."""
    try:
        from mycosoft_mas.earthlive.collectors.satellite import SatelliteCollector

        satc = SatelliteCollector(group=group)
        return await satc.collect()
    except Exception as e:
        logger.error(f"Satellite collect failed: {e}")
        return {"error": str(e)}
