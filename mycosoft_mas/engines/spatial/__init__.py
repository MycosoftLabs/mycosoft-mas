"""
Spatial Engine - H3 geospatial indexing.

Phase 2 stub. Full implementation will use PostGIS/TimescaleDB.
Created: February 17, 2026
"""

from mycosoft_mas.engines.spatial.index import index_latlng_to_h3
from mycosoft_mas.engines.spatial.service import SpatialService

__all__ = ["SpatialService", "index_latlng_to_h3"]
