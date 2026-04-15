"""
Web Mercator weather tiles from Open-Meteo scalar grids (Apr 13, 2026).

Colormaps match CREP `weather-heatmap-layer.tsx` / `grid-raster.ts` piecewise-linear stops.
No synthetic data — values come from `fetch_scalar_grid_async` (real forecast API).
"""

from __future__ import annotations

import hashlib
import math
import struct
import zlib
from typing import Any, Dict, List, Optional, Tuple

# Color stops aligned with WeatherHeatmapLayer COLOR_SCALES (temperature / precipitation / humidity)
COLOR_STOPS: Dict[str, List[Tuple[float, Tuple[int, int, int, float]]]] = {
    "t2m": [
        (-40, (26, 0, 51, 1.0)),
        (-30, (49, 54, 149, 1.0)),
        (-20, (69, 117, 180, 1.0)),
        (-10, (116, 173, 209, 1.0)),
        (0, (171, 217, 233, 1.0)),
        (10, (224, 243, 248, 1.0)),
        (15, (255, 255, 191, 1.0)),
        (20, (254, 224, 144, 1.0)),
        (25, (253, 174, 97, 1.0)),
        (30, (244, 109, 67, 1.0)),
        (35, (215, 48, 39, 1.0)),
        (40, (165, 0, 38, 1.0)),
        (50, (103, 0, 31, 1.0)),
    ],
    "tp": [
        (0.0, (255, 255, 255, 0.0)),
        (0.1, (198, 230, 242, 1.0)),
        (1.0, (158, 202, 225, 1.0)),
        (2.5, (107, 174, 214, 1.0)),
        (5.0, (66, 146, 198, 1.0)),
        (10.0, (33, 113, 181, 1.0)),
        (15.0, (8, 81, 156, 1.0)),
        (25.0, (8, 48, 107, 1.0)),
        (50.0, (4, 31, 74, 1.0)),
    ],
    "tcwv": [
        (0, (255, 245, 235, 1.0)),
        (20, (254, 230, 206, 1.0)),
        (40, (253, 208, 162, 1.0)),
        (60, (253, 174, 107, 1.0)),
        (80, (253, 141, 60, 1.0)),
        (90, (230, 85, 13, 1.0)),
        (100, (166, 54, 3, 1.0)),
    ],
}

# API variable names accepted in URL path
VARIABLE_ALIASES = {
    "t2m": "t2m",
    "temperature": "t2m",
    "temp": "t2m",
    "tp": "tp",
    "precipitation": "tp",
    "precip": "tp",
    "tcwv": "tcwv",
    "humidity": "tcwv",
}


def normalize_variable(raw: str) -> str:
    key = raw.strip().lower()
    if key not in VARIABLE_ALIASES:
        raise ValueError(f"Unsupported tile variable: {raw}")
    return VARIABLE_ALIASES[key]


def tile_latlon_bounds(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Web Mercator tile → WGS84 bounds (north, south, east, west)."""
    n = 2.0**z
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    south_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    north = math.degrees(north_rad)
    south = math.degrees(south_rad)
    return north, south, east, west


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def color_for_scalar(value: float, stops: List[Tuple[float, Tuple[int, int, int, float]]]) -> Tuple[int, int, int, int]:
    if not stops:
        return 128, 128, 128, 0
    if value <= stops[0][0]:
        r, g, b, a = stops[0][1]
        return r, g, b, int(round(a * 255))
    for i in range(len(stops) - 1):
        v0, c0 = stops[i]
        v1, c1 = stops[i + 1]
        if v0 <= value <= v1:
            t = (value - v0) / (v1 - v0 + 1e-9)
            r0, g0, b0, a0 = c0
            r1, g1, b1, a1 = c1
            return (
                int(round(_lerp(r0, r1, t))),
                int(round(_lerp(g0, g1, t))),
                int(round(_lerp(b0, b1, t))),
                int(round(_lerp(a0, a1, t) * 255)),
            )
    r, g, b, a = stops[-1][1]
    return r, g, b, int(round(a * 255))


def _bilinear(grid: List[List[float]], fi: float, fj: float) -> float:
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    if rows < 1 or cols < 1:
        return float("nan")
    i0 = max(0, min(rows - 1, int(math.floor(fi))))
    j0 = max(0, min(cols - 1, int(math.floor(fj))))
    i1 = max(0, min(rows - 1, i0 + 1))
    j1 = max(0, min(cols - 1, j0 + 1))
    ti = fi - i0
    tj = fj - j0
    v00 = grid[i0][j0]
    v01 = grid[i0][j1]
    v10 = grid[i1][j0]
    v11 = grid[i1][j1]
    v0 = _lerp(v00, v01, tj)
    v1 = _lerp(v10, v11, tj)
    return _lerp(v0, v1, ti)


def _grid_resolution_for_tile(north: float, south: float, east: float, west: float) -> float:
    """Degrees between samples: target ~24×24 grid max (under open_meteo MAX_POINTS)."""
    lat_span = max(abs(north - south), 1e-6)
    lon_span = max(abs(east - west), 1e-6)
    # ~24 samples per axis → 576 points; open_meteo caps at 100 by increasing eff
    target = 24
    return max(0.05, min(2.0, max(lat_span, lon_span) / target))


def raster_grid_to_rgba(
    grid: List[List[float]],
    *,
    north: float,
    south: float,
    east: float,
    west: float,
    width: int,
    height: int,
    stops: List[Tuple[float, Tuple[int, int, int, float]]],
) -> bytes:
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    out = bytearray(width * height * 4)
    if rows < 2 or cols < 2:
        return bytes(out)

    for py in range(height):
        lat = north - (py / max(1, height - 1)) * (north - south)
        fi = ((lat - south) / (north - south)) * (rows - 1)
        for px in range(width):
            lon = west + (px / max(1, width - 1)) * (east - west)
            fj = ((lon - west) / (east - west)) * (cols - 1)
            v = _bilinear(grid, fi, fj)
            idx = (py * width + px) * 4
            if not math.isfinite(v):
                out[idx : idx + 4] = (0, 0, 0, 0)
                continue
            r, g, b, a = color_for_scalar(v, stops)
            out[idx] = r
            out[idx + 1] = g
            out[idx + 2] = b
            out[idx + 3] = a
    return bytes(out)


def encode_png_rgba(rgba: bytes, width: int, height: int) -> bytes:
    """Minimal PNG encoder (RGBA8), stdlib only."""
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)  # filter type None
        row_start = y * stride
        raw.extend(rgba[row_start : row_start + stride])

    compressor = zlib.compressobj(9)
    compressed = compressor.compress(bytes(raw)) + compressor.flush()

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    return png


async def render_weather_tile_png(
    *,
    variable: str,
    z: int,
    x: int,
    y: int,
    hours: int = 0,
    tile_size: int = 256,
    extra_meta: Optional[Dict[str, Any]] = None,
) -> Tuple[bytes, Dict[str, str]]:
    """
    Fetch forecast grid for tile bbox and return PNG bytes + response headers.
    """
    from mycosoft_mas.earth2.open_meteo_crep_grid import fetch_scalar_grid_async

    if z < 0 or z > 22:
        raise ValueError("zoom out of range")
    vmax = 2**z
    if x < 0 or x >= vmax or y < 0 or y >= vmax:
        raise ValueError("tile coordinates out of range")

    norm = normalize_variable(variable)
    stops = COLOR_STOPS.get(norm)
    if not stops:
        raise ValueError(f"No colormap for {norm}")

    north, south, east, west = tile_latlon_bounds(z, x, y)
    # Normalize east/west for dateline (single world copy)
    if east < west:
        east, west = west, east
    resolution = _grid_resolution_for_tile(north, south, east, west)

    payload = await fetch_scalar_grid_async(
        variable=norm,
        hours=max(0, min(hours, 240)),
        north=north,
        south=south,
        east=east,
        west=west,
        resolution=resolution,
        extra_meta=extra_meta,
    )
    grid = payload.get("grid")
    if not isinstance(grid, list) or not grid:
        raise RuntimeError("empty grid")

    rgba = raster_grid_to_rgba(
        grid,
        north=north,
        south=south,
        east=east,
        west=west,
        width=tile_size,
        height=tile_size,
        stops=stops,
    )
    png = encode_png_rgba(rgba, tile_size, tile_size)

    # Weak ETag from grid stats + coords
    h = hashlib.sha256()
    h.update(struct.pack("4diiii", north, south, east, west, z, x, y, hours))
    h.update(norm.encode())
    h.update(png[: min(512, len(png))])
    etag = f'"{h.hexdigest()[:16]}"'

    headers = {
        "Cache-Control": "public, max-age=120",
        "ETag": etag,
    }
    return png, headers

