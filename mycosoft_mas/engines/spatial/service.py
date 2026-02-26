"""
SpatialService - Geospatial operations for Grounded Cognition.

Stores and queries spatial points via MINDEX API (PostGIS).
Created: February 17, 2026
"""

import logging
import os
from typing import Any, Dict, List, Optional

from mycosoft_mas.engines.spatial.index import index_latlng_to_h3

logger = logging.getLogger(__name__)

MINDEX_URL = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
MINDEX_API_PREFIX = "/api/mindex"
MINDEX_API_KEY = os.environ.get("MINDEX_API_KEY", "")


async def _mindex_request(
    method: str,
    path: str,
    json: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Call MINDEX API with optional API key."""
    try:
        import httpx
        url = f"{MINDEX_URL}{MINDEX_API_PREFIX}{path}"
        headers = {}
        if MINDEX_API_KEY:
            headers["X-API-Key"] = MINDEX_API_KEY
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.request(method, url, json=json, params=params, headers=headers)
            r.raise_for_status()
            return r.json() if r.content else None
    except Exception as e:
        logger.warning("MINDEX spatial request failed: %s", e)
        return None


class SpatialService:
    """Geospatial indexing and queries for grounded cognition."""

    async def index_point(self, lat: float, lon: float, resolution: int = 9) -> Optional[str]:
        """Index a point to H3. Returns H3 cell ID or None if h3 not installed."""
        return index_latlng_to_h3(lat, lon, resolution)

    async def store_point(
        self,
        session_id: Optional[str],
        lat: float,
        lon: float,
        ep_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Store a spatial point in MINDEX. Returns the stored point ID or None on failure.
        """
        h3_cell = await self.index_point(lat, lon)
        body = {
            "session_id": session_id,
            "lat": lat,
            "lon": lon,
            "h3_cell": h3_cell,
            "ep_id": ep_id,
            "metadata": metadata,
        }
        out = await _mindex_request("POST", "/grounding/spatial/points", json=body)
        if out and "id" in out:
            return str(out["id"])
        return None

    async def query_nearby(
        self,
        lat: float,
        lon: float,
        radius_km: float = 10.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Query spatial points within radius_km of (lat, lon) via PostGIS.
        Returns list of points with dist_km.
        """
        out = await _mindex_request(
            "GET",
            "/grounding/spatial/points/nearby",
            params={"lat": lat, "lon": lon, "radius_km": radius_km, "limit": limit},
        )
        if isinstance(out, list):
            return out
        return []

    async def get_h3_neighbors(self, h3_cell: str, k: int = 1) -> List[Dict[str, Any]]:
        """
        Get spatial points in H3 cell and its k-ring neighbors.
        Uses h3.grid_disk when available, otherwise exact match.
        """
        try:
            import h3
            cells = list(h3.grid_disk(h3_cell, k))
        except ImportError:
            cells = [h3_cell]
        if not cells:
            return []
        params = {"h3_cells": ",".join(cells[:20]), "limit": 50}
        out = await _mindex_request("GET", "/grounding/spatial/points/h3", params=params)
        if isinstance(out, list):
            return out
        return []
