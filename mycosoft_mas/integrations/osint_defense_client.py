"""
OSINT Defense Tracking Client

Open-source intelligence feeds for military / defense tracking:
- FlightRadar24-style military aviation (via ADS-B Exchange)
- MarineTraffic / AIS for naval vessel tracking
- Submarine cable monitoring (TeleGeography)
- Military base / installation public data
- Liveuamap-style conflict monitoring RSS

All data comes from publicly available OSINT feeds.
No classified or restricted sources.

Env vars:
    ADSBX_API_KEY          -- ADS-B Exchange rapid API key
    MARINETRAFFIC_API_KEY  -- MarineTraffic API key
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

ADSBX_BASE = "https://adsbexchange-com1.p.rapidapi.com/v2"
MARINETRAFFIC_BASE = "https://services.marinetraffic.com/api"
SUBMARINE_CABLE_URL = "https://raw.githubusercontent.com/telegeography/www.submarinecablemap.com/master/web/public/api/v3/cable/cable-geo.json"


class OsintDefenseClient:
    """OSINT defense / military tracking via public feeds."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.adsbx_key = self.config.get("adsbx_api_key") or os.getenv("ADSBX_API_KEY", "")
        self.marine_key = self.config.get("marinetraffic_api_key") or os.getenv(
            "MARINETRAFFIC_API_KEY", ""
        )
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "adsbx_key_set": bool(self.adsbx_key),
            "marinetraffic_key_set": bool(self.marine_key),
            "ts": datetime.utcnow().isoformat(),
        }

    # -- Military Aviation (ADS-B Exchange) -----------------------------------

    async def military_aircraft_nearby(
        self, lat: float, lon: float, radius_nm: int = 250
    ) -> Dict[str, Any]:
        """Find military aircraft near a point via ADS-B Exchange."""
        c = await self._http()
        headers = {
            "X-RapidAPI-Key": self.adsbx_key,
            "X-RapidAPI-Host": "adsbexchange-com1.p.rapidapi.com",
        }
        r = await c.get(
            f"{ADSBX_BASE}/lat/{lat}/lon/{lon}/dist/{radius_nm}/",
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()
        mil_types = {
            "MIL",
            "MLAT",
            "C17",
            "C130",
            "KC135",
            "B52",
            "F16",
            "F35",
            "F22",
            "E3",
            "P8",
            "V22",
        }
        aircraft = data.get("ac", []) or []
        military = [
            ac
            for ac in aircraft
            if (ac.get("mil", "") == "1")
            or (ac.get("t", "") in mil_types)
            or (ac.get("ownOp", "") or "")
            .upper()
            .startswith(("USAF", "USN", "ARMY", "RAF", "NATO"))
        ]
        return {"total": len(aircraft), "military": military, "military_count": len(military)}

    async def track_aircraft(self, hex_id: str) -> Dict[str, Any]:
        """Track a specific aircraft by ICAO hex."""
        c = await self._http()
        headers = {
            "X-RapidAPI-Key": self.adsbx_key,
            "X-RapidAPI-Host": "adsbexchange-com1.p.rapidapi.com",
        }
        r = await c.get(f"{ADSBX_BASE}/icao/{hex_id}/", headers=headers)
        r.raise_for_status()
        return r.json()

    # -- Naval Vessel Tracking (MarineTraffic) --------------------------------

    async def naval_vessels_in_area(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        ship_type: int = 35,  # 35 = military
    ) -> Dict[str, Any]:
        """Find naval / military vessels in a bounding box."""
        c = await self._http()
        r = await c.get(
            f"{MARINETRAFFIC_BASE}/exportvessels/v:8/{self.marine_key}"
            f"/MINLAT:{min_lat}/MAXLAT:{max_lat}/MINLON:{min_lon}/MAXLON:{max_lon}"
            f"/SHIPTYPE:{ship_type}/protocol:jsono",
        )
        r.raise_for_status()
        return r.json()

    async def vessel_details(self, mmsi: str) -> Dict[str, Any]:
        """Get vessel details by MMSI."""
        c = await self._http()
        r = await c.get(
            f"{MARINETRAFFIC_BASE}/exportvessel/v:5/{self.marine_key}/mmsi:{mmsi}/protocol:jsono"
        )
        r.raise_for_status()
        return r.json()

    # -- Submarine Cable Monitoring -------------------------------------------

    async def submarine_cables(self) -> Dict[str, Any]:
        """Get global submarine cable map data (TeleGeography GeoJSON)."""
        c = await self._http()
        r = await c.get(SUBMARINE_CABLE_URL)
        r.raise_for_status()
        return r.json()

    # -- Conflict / Incident Monitoring (RSS) ---------------------------------

    async def conflict_feed(self, region: str = "world") -> str:
        """Fetch conflict/incident RSS feed (Liveuamap-style, ACLED, etc.)."""
        feeds = {
            "world": "https://liveuamap.com/rss",
            "ukraine": "https://liveuamap.com/rss/ukraine",
            "middleeast": "https://middleeast.liveuamap.com/rss",
            "africa": "https://africa.liveuamap.com/rss",
            "asia": "https://asia.liveuamap.com/rss",
        }
        url = feeds.get(region, feeds["world"])
        c = await self._http()
        r = await c.get(url)
        r.raise_for_status()
        return r.text

    # -- Military Base Data (public) ------------------------------------------

    async def military_installations(self, country: str = "US") -> Dict[str, Any]:
        """Retrieve public military installation list from data.mil or DoD open data."""
        c = await self._http()
        r = await c.get(
            "https://data.militaryinstallations.dod.mil/installations.json",
        )
        if r.status_code == 200:
            return r.json()
        return {"note": "DoD installation endpoint unavailable", "country": country}

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
