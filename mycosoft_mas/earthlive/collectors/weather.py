"""
EarthLIVE Weather Collector - OpenMeteo API

Fetches real weather data from Open-Meteo (no API key required).
https://open-meteo.com/

Created: February 25, 2026
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

OPENMETEO_BASE = "https://api.open-meteo.com/v1"


async def fetch_openmeteo_forecast(
    latitude: float = 47.6062,
    longitude: float = -122.3321,
) -> Dict[str, Any]:
    """
    Fetch current weather and forecast from Open-Meteo.
    Uses Seattle area by default.
    """
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not installed; EarthLIVE weather collector unavailable")
        return {}

    url = f"{OPENMETEO_BASE}/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,surface_pressure,cloud_cover,precipitation,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation",
        "timezone": "auto",
        "forecast_days": 2,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("OpenMeteo fetch failed: %s", e)
        return {}


class WeatherCollector:
    """Collect weather data from Open-Meteo."""

    def __init__(self, latitude: float = 47.6062, longitude: float = -122.3321):
        self.latitude = latitude
        self.longitude = longitude

    async def collect(self) -> Dict[str, Any]:
        """Collect current weather and forecast."""
        data = await fetch_openmeteo_forecast(
            latitude=self.latitude,
            longitude=self.longitude,
        )
        if not data:
            return {"source": "openmeteo", "error": "no_data"}

        current = data.get("current", {})
        return {
            "source": "openmeteo",
            "latitude": self.latitude,
            "longitude": self.longitude,
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "pressure_hpa": current.get("surface_pressure"),
            "cloud_cover_pct": current.get("cloud_cover"),
            "precipitation_mm": current.get("precipitation"),
            "weather_code": current.get("weather_code"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "hourly": data.get("hourly", {}),
            "raw": data,
        }
