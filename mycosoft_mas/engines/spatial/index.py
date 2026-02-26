"""
H3 indexing stub - Phase 2.

Adds H3 cell index when geo is available.
Requires: pip install h3 (optional).
Created: February 17, 2026
"""

from typing import Optional


def index_latlng_to_h3(lat: float, lon: float, resolution: int = 9) -> Optional[str]:
    """Convert lat/lon to H3 cell ID. Returns None if h3 not installed."""
    try:
        import h3
        return h3.latlng_to_cell(lat, lon, resolution)
    except ImportError:
        return None
