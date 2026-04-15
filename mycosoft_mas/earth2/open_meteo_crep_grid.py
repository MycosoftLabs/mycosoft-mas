"""
CREP map grids from Open-Meteo (real public forecast — not synthetic filler).

Operational GFS/IFS-based forecasts via api.open-meteo.com. Earth-2 GPU models on the
Legion host remain the source for model load/status and future native raster export.
"""

from __future__ import annotations

import asyncio
import math
from typing import Any, Dict, List, Optional, Tuple

import httpx

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"

SCALAR_MAP = {
    "t2m": "temperature_2m",
    "tp": "precipitation",
    "tcwv": "relative_humidity_2m",
    "msl": "pressure_msl",
    "sp": "surface_pressure",
}

BATCH_CONCURRENCY = 8
MAX_POINTS = 100


def _map_scalar(variable: str) -> str:
    return SCALAR_MAP.get(variable.lower(), variable)


def _grid_dimensions(
    north: float,
    south: float,
    east: float,
    west: float,
    resolution: float,
) -> Tuple[int, int, float]:
    eff = max(float(resolution), 0.25)
    nlat = max(2, int((north - south) / eff) + 1)
    nlon = max(2, int((east - west) / eff) + 1)
    while nlat * nlon > MAX_POINTS:
        eff *= 1.15
        nlat = max(2, int((north - south) / eff) + 1)
        nlon = max(2, int((east - west) / eff) + 1)
    return nlat, nlon, eff


async def _hourly_scalar(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
    om_var: str,
    hours: int,
) -> Optional[float]:
    hidx = max(0, min(hours, 200))
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": om_var,
        "forecast_hours": str(max(hours + 1, 1)),
        "timezone": "UTC",
    }
    r = await client.get(OPEN_METEO_FORECAST, params=params, timeout=45.0)
    if r.status_code != 200:
        return None
    data = r.json()
    hourly = data.get("hourly") or {}
    series = hourly.get(om_var)
    if not isinstance(series, list) or not series:
        return None
    hidx = min(hidx, len(series) - 1)
    val = series[hidx]
    return float(val) if val is not None else None


async def fetch_scalar_grid_async(
    *,
    variable: str,
    hours: int,
    north: float,
    south: float,
    east: float,
    west: float,
    resolution: float,
    extra_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    om_var = _map_scalar(variable)
    nlat, nlon, eff_used = _grid_dimensions(north, south, east, west, resolution)

    points: List[Tuple[int, int, float, float]] = []
    for i in range(nlat):
        lat = south + (north - south) * i / max(1, nlat - 1)
        for j in range(nlon):
            lon = west + (east - west) * j / max(1, nlon - 1)
            points.append((i, j, lat, lon))

    grid: List[List[float]] = [[float("nan")] * nlon for _ in range(nlat)]

    async with httpx.AsyncClient() as client:
        for start in range(0, len(points), BATCH_CONCURRENCY):
            chunk = points[start : start + BATCH_CONCURRENCY]

            async def one(p: Tuple[int, int, float, float]) -> None:
                ii, jj, la, lo = p
                v = await _hourly_scalar(client, la, lo, om_var, hours)
                if v is not None:
                    grid[ii][jj] = v

            await asyncio.gather(*(one(p) for p in chunk))

    flat = [x for row in grid for x in row if not math.isnan(x)]
    if not flat:
        raise RuntimeError("Open-Meteo returned no scalar values for this viewport")
    out: Dict[str, Any] = {
        "grid": grid,
        "min": min(flat),
        "max": max(flat),
        "variable": variable,
        "resolution": eff_used,
        "bounds": {"north": north, "south": south, "east": east, "west": west},
        "source": "open_meteo_forecast",
        "visualization_source": "open_meteo",
        "forecast_hour_index": hours,
    }
    if extra_meta:
        out.update(extra_meta)
    return out


def _wind_uv_from_speed_dir_kmh(speed_kmh: float, dir_deg: float) -> Tuple[float, float]:
    speed_ms = float(speed_kmh) / 3.6
    rad = math.radians(float(dir_deg))
    u = -speed_ms * math.sin(rad)
    v = -speed_ms * math.cos(rad)
    return u, v


async def _hourly_wind(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
    hours: int,
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m",
        "forecast_hours": str(max(hours + 1, 1)),
        "timezone": "UTC",
    }
    r = await client.get(OPEN_METEO_FORECAST, params=params, timeout=45.0)
    if r.status_code != 200:
        return None, None, None, None
    data = r.json()
    hourly = data.get("hourly") or {}
    ws = hourly.get("wind_speed_10m") or []
    wd = hourly.get("wind_direction_10m") or []
    if not ws or not wd:
        return None, None, None, None
    hidx = min(max(0, hours), len(ws) - 1, len(wd) - 1)
    u, v = _wind_uv_from_speed_dir_kmh(ws[hidx], wd[hidx])
    spd = math.hypot(u, v)
    return u, v, spd, float(wd[hidx])


async def fetch_wind_grids_async(
    *,
    hours: int,
    north: float,
    south: float,
    east: float,
    west: float,
    resolution: float,
    extra_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    nlat, nlon, _eff = _grid_dimensions(north, south, east, west, resolution)

    u_grid: List[List[float]] = [[0.0] * nlon for _ in range(nlat)]
    v_grid: List[List[float]] = [[0.0] * nlon for _ in range(nlat)]
    speed_grid: List[List[float]] = [[0.0] * nlon for _ in range(nlat)]
    dir_grid: List[List[float]] = [[0.0] * nlon for _ in range(nlat)]

    points: List[Tuple[int, int, float, float]] = []
    for i in range(nlat):
        lat = south + (north - south) * i / max(1, nlat - 1)
        for j in range(nlon):
            lon = west + (east - west) * j / max(1, nlon - 1)
            points.append((i, j, lat, lon))

    async with httpx.AsyncClient() as client:

        async def fill(p: Tuple[int, int, float, float]) -> None:
            ii, jj, la, lo = p
            u, v, spd, d = await _hourly_wind(client, la, lo, hours)
            if u is not None and v is not None:
                u_grid[ii][jj] = u
                v_grid[ii][jj] = v
                speed_grid[ii][jj] = spd or 0.0
                dir_grid[ii][jj] = d or 0.0

        for start in range(0, len(points), BATCH_CONCURRENCY):
            await asyncio.gather(*(fill(p) for p in points[start : start + BATCH_CONCURRENCY]))

    out: Dict[str, Any] = {
        "u": u_grid,
        "v": v_grid,
        "speed": speed_grid,
        "direction": dir_grid,
        "source": "open_meteo_forecast",
        "visualization_source": "open_meteo",
        "forecast_hour_index": hours,
    }
    if extra_meta:
        out.update(extra_meta)
    return out
