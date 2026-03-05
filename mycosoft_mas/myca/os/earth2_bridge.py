"""
Earth2 Bridge — Weather and climate simulation context.

Fetches weather predictions and simulation data from Earth2 API.
Used when MYCA is asked about weather, climate, or simulation.

Earth2 API: typically 8220 (local GPU) or 188:8220 (MAS proxy).
MAS scientific_equipment_api uses EARTH2_API_URL default http://192.168.0.188:8220.

Date: 2026-03-02
"""

import os
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger("myca.os.earth2_bridge")


class Earth2Bridge:
    """Bridge to Earth2 weather/climate simulation API."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._earth2_url = os.getenv("EARTH2_API_URL", "http://192.168.0.188:8220")
        self._mas_url = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")

    async def initialize(self):
        self._session = aiohttp.ClientSession()
        logger.info("Earth2 Bridge initialized (url=%s)", self._earth2_url)

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_weather_context(self, region: Optional[str] = None) -> str:
        """
        Fetch weather/simulation context for a region.

        Args:
            region: Optional region name or coordinates. If None, returns latest global snapshot.

        Returns:
            Human-readable weather context for LLM, or empty string on failure.
        """
        if not self._session or self._session.closed:
            return ""

        try:
            # Try MAS Earth2 proxy if available (MAS may proxy to Earth2 service)
            path = "/api/earth2/predictions/latest"
            url = f"{self._mas_url.rstrip('/')}{path}"
            # Some configs have Earth2 directly; try Earth2 URL first
            earth2_path = os.getenv("EARTH2_PREDICTIONS_ENDPOINT", "/api/earth2/predictions/latest")
            direct_url = f"{self._earth2_url.rstrip('/')}{earth2_path}"

            for base_url in [direct_url, url]:
                try:
                    async with self._session.get(
                        base_url,
                        timeout=aiohttp.ClientTimeout(total=8),
                        params={"region": region} if region else None,
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return _format_earth2_summary(data, region)
                except Exception:
                    continue

            return "Earth2: Service not reachable. Weather predictions available when Earth2 API is running."
        except Exception as e:
            logger.debug("Earth2 context fetch failed: %s", e)
            return ""


def _format_earth2_summary(data: dict, region: Optional[str]) -> str:
    """Format Earth2 API response as a short summary."""
    if not data:
        return ""
    parts = ["Earth2 weather context:"]
    if isinstance(data, dict):
        if "predictions" in data:
            preds = data["predictions"]
            if isinstance(preds, list) and preds:
                parts.append(f"{len(preds)} prediction(s) available.")
            elif isinstance(preds, dict):
                parts.append(str(preds)[:200])
        elif "temperature" in data or "precipitation" in data:
            t = data.get("temperature")
            p = data.get("precipitation")
            if t is not None:
                parts.append(f"Temperature: {t}")
            if p is not None:
                parts.append(f"Precipitation: {p}")
        else:
            parts.append(str(data)[:300])
    else:
        parts.append(str(data)[:200])
    if region:
        parts.insert(1, f"Region: {region}")
    return " ".join(parts)
