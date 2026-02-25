"""
EarthLIVE Satellite Collector - Celestrak TLE

Fetches satellite TLE (Two-Line Element) data from Celestrak.
https://celestrak.org/

Created: February 25, 2026
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CELESTRAK_BASE = "https://celestrak.org/NORAD/elements"
# Groups: starlink, stations, weather, noaa, goes, iridium, iridium-NEXT, etc.
DEFAULT_GROUP = "starlink"


async def fetch_celestrak_tle(group: str = DEFAULT_GROUP) -> List[str]:
    """
    Fetch TLE data from Celestrak. Returns list of lines (name, line1, line2 per sat).
    """
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not installed; EarthLIVE satellite collector unavailable")
        return []

    url = f"{CELESTRAK_BASE}/gp.php"
    params = {"GROUP": group, "FORMAT": "tle"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                url,
                params=params,
                headers={"User-Agent": "Mycosoft-EarthLIVE/1.0"},
            )
            resp.raise_for_status()
            text = resp.text
            lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
            return lines
    except Exception as e:
        logger.warning("Celestrak fetch failed: %s", e)
        return []


def parse_tle_lines(lines: List[str]) -> List[Dict[str, Any]]:
    """Parse TLE lines into list of {name, line1, line2, norad_id}."""
    result = []
    i = 0
    while i + 2 <= len(lines):
        name = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]
        norad_id = None
        if len(line2) >= 14:
            norad_id = line2[2:7].strip()
        result.append({
            "name": name,
            "line1": line1,
            "line2": line2,
            "norad_id": norad_id,
        })
        i += 3
    return result


class SatelliteCollector:
    """Collect satellite TLE data from Celestrak."""

    def __init__(self, group: str = DEFAULT_GROUP, max_satellites: int = 50):
        self.group = group
        self.max_satellites = max_satellites

    async def collect(self) -> Dict[str, Any]:
        """Collect satellite TLE data."""
        lines = await fetch_celestrak_tle(group=self.group)
        sats = parse_tle_lines(lines)[: self.max_satellites]
        return {
            "source": "celestrak",
            "group": self.group,
            "count": len(sats),
            "satellites": sats,
        }
