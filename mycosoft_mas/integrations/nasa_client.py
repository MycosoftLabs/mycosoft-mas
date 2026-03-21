"""
NASA Full Data Client.

Earth Observing System, Landsat/MODIS imagery, FIRMS (fire), asteroid tracking,
Mars/Moon data, exoplanet archive, APOD. Complements SpaceWeatherClient for
DONKI/NEO; this client focuses on Earth data, imagery, and exoplanets.

Environment Variables:
    NASA_API_KEY: NASA API key (optional, DEMO_KEY works for limited testing)
    FIRMS_MAP_KEY: FIRMS map key for fire data (request at firms.modaps.eosdis.nasa.gov)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

NASA_BASE = "https://api.nasa.gov"
EONET_BASE = "https://eonet.gsfc.nasa.gov/api/v3.0"
FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api"
EXOPLANET_BASE = "https://exoplanetarchive.ipac.caltech.edu/cgi-bin/nstedAPI/nph-nstedAPI"


class NasaClient:
    """Client for NASA Earth data, imagery, FIRMS, exoplanets, APOD."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key") or os.environ.get("NASA_API_KEY", "DEMO_KEY")
        self.firms_key = self.config.get("firms_key") or os.environ.get("FIRMS_MAP_KEY", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # APOD
    async def get_apod(
        self,
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        count: Optional[int] = None,
        thumbs: bool = False,
    ) -> Dict[str, Any]:
        """Astronomy Picture of the Day."""
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"api_key": self.api_key}
            if date:
                params["date"] = date
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            if count:
                params["count"] = count
            if thumbs:
                params["thumbs"] = "True"
            r = await client.get(f"{NASA_BASE}/planetary/apod", params=params)
            r.raise_for_status()
            data = r.json()
            return {"status": "ok", "data": data if isinstance(data, list) else [data]}
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": str(e), "data": []}
        except Exception as e:
            logger.exception("APOD error: %s", e)
            return {"status": "error", "message": str(e), "data": []}

    # NEO (Near Earth Objects) - api.nasa.gov
    async def get_neo_feed(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Near Earth Object feed."""
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"api_key": self.api_key}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            r = await client.get(f"{NASA_BASE}/neo/rest/v1/feed", params=params)
            r.raise_for_status()
            return {"status": "ok", "data": r.json()}
        except Exception as e:
            logger.warning("NEO feed error: %s", e)
            return {"status": "error", "message": str(e), "data": {}}

    async def get_neo_lookup(self, asteroid_id: str) -> Dict[str, Any]:
        """Look up a specific NEO by ID."""
        try:
            client = await self._get_client()
            r = await client.get(
                f"{NASA_BASE}/neo/rest/v1/neo/{asteroid_id}",
                params={"api_key": self.api_key},
            )
            r.raise_for_status()
            return {"status": "ok", "data": r.json()}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    # EONET - Natural events (wildfires, etc.)
    async def get_eonet_events(
        self,
        sources: Optional[List[str]] = None,
        status: str = "open",
        limit: int = 50,
        days: Optional[int] = None,
        bbox: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Earth Observatory Natural Event Tracker - wildfires, storms, etc."""
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": limit}
            if sources:
                params["sources"] = ",".join(sources)
            if status:
                params["status"] = status
            if days:
                params["days"] = days
            if bbox:
                params["bbox"] = bbox
            r = await client.get(f"{EONET_BASE}/events", params=params)
            r.raise_for_status()
            return {"status": "ok", "data": r.json()}
        except Exception as e:
            logger.warning("EONET error: %s", e)
            return {"status": "error", "message": str(e), "data": {}}

    # FIRMS - Active fire data
    async def get_firms_fires(
        self,
        area: str = "world",
        source: str = "VIIRS_SNPP_NRT",
        day_range: int = 1,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        FIRMS active fire/hotspot data. Requires FIRMS_MAP_KEY.
        area: 'world' or 'west,south,east,north' (e.g. '-130,-60,-60,60')
        source: VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT, MODIS_NRT, etc.
        day_range: 1-5
        date: YYYY-MM-DD (optional; defaults to most recent)
        """
        if not self.firms_key:
            return {
                "status": "not_configured",
                "message": "FIRMS_MAP_KEY required; request at firms.modaps.eosdis.nasa.gov/api/map_key",
                "data": [],
            }
        try:
            client = await self._get_client()
            path = f"/area/csv/{self.firms_key}/{source}/{area}/{day_range}"
            if date:
                path += f"/{date}"
            r = await client.get(f"{FIRMS_BASE}{path}")
            r.raise_for_status()
            lines = r.text.strip().split("\n")
            if not lines:
                return {"status": "ok", "data": [], "raw_lines": 0}
            header = lines[0].split(",")
            rows = [dict(zip(header, ln.split(","))) for ln in lines[1:] if ln]
            return {"status": "ok", "data": rows, "raw_lines": len(lines)}
        except Exception as e:
            logger.warning("FIRMS error: %s", e)
            return {"status": "error", "message": str(e), "data": []}

    # Exoplanet Archive
    async def get_exoplanets(
        self,
        table: str = "ps",
        select: Optional[str] = None,
        format_type: str = "json",
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        NASA Exoplanet Archive. table: ps (Planet Systems), pscomppars, etc.
        select: comma-separated columns
        """
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"table": table, "format": format_type}
            if select:
                params["select"] = select
            r = await client.get(EXOPLANET_BASE, params=params)
            r.raise_for_status()
            data = r.json() if "json" in format_type else r.text
            if limit and isinstance(data, list):
                data = data[:limit]
            return {"status": "ok", "data": data}
        except Exception as e:
            logger.warning("Exoplanet Archive error: %s", e)
            return {"status": "error", "message": str(e), "data": []}

    # Earth imagery - NASA Earth API (if available)
    async def get_earth_imagery(
        self,
        lat: float,
        lon: float,
        date: Optional[str] = None,
        dim: float = 0.15,
        cloud_score: bool = True,
    ) -> Dict[str, Any]:
        """Earth imagery for a lat/lon from NASA Earth API (Landsat)."""
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {
                "api_key": self.api_key,
                "lat": lat,
                "lon": lon,
                "dim": dim,
                "cloud_score": "True" if cloud_score else "False",
            }
            if date:
                params["date"] = date
            r = await client.get(f"{NASA_BASE}/planetary/earth/imagery", params=params)
            r.raise_for_status()
            # Returns image URL
            return {"status": "ok", "url": r.url, "data": {"lat": lat, "lon": lon}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    async def health_check(self) -> Dict[str, Any]:
        """Verify NASA API connectivity."""
        try:
            client = await self._get_client()
            r = await client.get(
                f"{NASA_BASE}/planetary/apod",
                params={"api_key": self.api_key, "count": 1},
            )
            ok = r.status_code == 200
            return {
                "status": "healthy" if ok else "degraded",
                "nasa_api": ok,
                "firms_configured": bool(self.firms_key),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
