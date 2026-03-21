"""
MINDEX Earth Client — talks to the MINDEX VM's new earth-scale endpoints.

MINDEX (192.168.0.189:8000) now has:
  - /earth — unified search across 35 domains with CREP-compatible results
  - /earth/nearby — radius search around any lat/lng
  - /earth/domains — list all 35 searchable domains
  - /earth/map/bbox — bounding box spatial queries for CREP map layers
  - /earth/stats — entity counts across all domains
  - /earth/crep/sync — push domain data into crep.unified_entities
  - /earth/map/layers — available CREP map layers
  - /earth/earthquakes/recent — recent earthquakes
  - /earth/satellites/active — active satellites
  - /earth/solar/recent — recent solar events

This client is the primary data source for MAS Earth Search, providing instant
local-database access to pre-ingested data from all 9 ETL connectors.

Created: March 15, 2026
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class MINDEXEarthClient:
    """Client for MINDEX earth-scale search endpoints on VM 189."""

    def __init__(self):
        self.base_url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
        self.api_key = os.getenv("MINDEX_API_KEY", "")
        self.timeout = 15

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}{path}", params=params, headers=self._headers()
                )
                if resp.status_code == 200:
                    return resp.json()
                logger.warning("MINDEX earth GET %s returned %d", path, resp.status_code)
        except Exception as e:
            logger.warning("MINDEX earth GET %s error: %s", path, e)
        return None

    async def _post(self, path: str, json_body: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}{path}", json=json_body, headers=self._headers()
                )
                if resp.status_code in (200, 201):
                    return resp.json()
                logger.warning("MINDEX earth POST %s returned %d", path, resp.status_code)
        except Exception as e:
            logger.warning("MINDEX earth POST %s error: %s", path, e)
        return None

    # ── Unified Earth Search ─────────────────────────────────────────────────

    async def earth_search(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        domain_groups: Optional[List[str]] = None,
        limit: int = 20,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_km: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Call MINDEX /earth endpoint — unified search across all 35 domains.
        Returns CREP-compatible universal_results with lat/lng for map pins.
        """
        params: Dict[str, Any] = {"q": query, "limit": limit}
        if domains:
            params["domains"] = ",".join(domains)
        if domain_groups:
            params["domain_groups"] = ",".join(domain_groups)
        if lat is not None and lng is not None:
            params["lat"] = lat
            params["lng"] = lng
        if radius_km is not None:
            params["radius_km"] = radius_km

        data = await self._get("/earth", params=params)
        return data or {"results": [], "universal_results": [], "total": 0}

    async def earth_nearby(
        self,
        lat: float,
        lng: float,
        radius_km: float = 50,
        domains: Optional[List[str]] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Call MINDEX /earth/nearby — radius search around a point."""
        params: Dict[str, Any] = {
            "lat": lat,
            "lng": lng,
            "radius_km": radius_km,
            "limit": limit,
        }
        if domains:
            params["domains"] = ",".join(domains)

        data = await self._get("/earth/nearby", params=params)
        return data or {"results": [], "total": 0}

    async def earth_domains(self) -> Dict[str, Any]:
        """Call MINDEX /earth/domains — list all searchable domains."""
        data = await self._get("/earth/domains")
        return data or {"domains": [], "groups": {}}

    # ── Map / CREP ───────────────────────────────────────────────────────────

    async def map_bbox(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        layers: Optional[List[str]] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """Call MINDEX /earth/map/bbox — spatial query for CREP map layers."""
        params: Dict[str, Any] = {
            "north": north,
            "south": south,
            "east": east,
            "west": west,
            "limit": limit,
        }
        if layers:
            params["layers"] = ",".join(layers)

        data = await self._get("/earth/map/bbox", params=params)
        return data or {"layers": {}, "total": 0}

    async def map_layers(self) -> List[str]:
        """Get available CREP map layers from MINDEX."""
        data = await self._get("/earth/map/layers")
        if data and isinstance(data, dict):
            return data.get("layers", [])
        if isinstance(data, list):
            return data
        return []

    async def crep_sync(self, domains: Optional[List[str]] = None) -> Dict[str, Any]:
        """Trigger CREP sync — push domain data into crep.unified_entities."""
        body = {}
        if domains:
            body["domains"] = domains
        data = await self._post("/earth/crep/sync", json_body=body)
        return data or {"status": "error"}

    # ── Stats ────────────────────────────────────────────────────────────────

    async def stats(self) -> Dict[str, Any]:
        """Get entity counts across all domains."""
        data = await self._get("/earth/stats")
        return data or {}

    # ── Domain-specific shortcuts ────────────────────────────────────────────

    async def recent_earthquakes(self, limit: int = 20) -> List[Dict[str, Any]]:
        data = await self._get("/earth/earthquakes/recent", params={"limit": limit})
        return data if isinstance(data, list) else (data or {}).get("results", [])

    async def active_satellites(self, limit: int = 50) -> List[Dict[str, Any]]:
        data = await self._get("/earth/satellites/active", params={"limit": limit})
        return data if isinstance(data, list) else (data or {}).get("results", [])

    async def recent_solar_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        data = await self._get("/earth/solar/recent", params={"limit": limit})
        return data if isinstance(data, list) else (data or {}).get("results", [])

    async def health(self) -> Dict[str, Any]:
        """Check MINDEX earth endpoints health."""
        data = await self._get("/earth/stats")
        if data:
            return {"status": "healthy", "stats": data}
        return {"status": "unreachable"}


# Singleton
_client: Optional[MINDEXEarthClient] = None


def get_mindex_earth_client() -> MINDEXEarthClient:
    global _client
    if _client is None:
        _client = MINDEXEarthClient()
    return _client
