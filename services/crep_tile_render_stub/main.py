"""
CREP GPU tile render stub — :8230 on 192.168.0.249 (Earth-2) and 192.168.0.241 (Voice).

**URL contract (website proxy GET):**
  {TILE_RENDER_EARTH2_URL}/tile/{layer}/{z}/{x}/{y}.png
  {TILE_RENDER_DENSITY_URL}/tile/{layer}/{z}/{x}/{y}.png

**Per-legion layers (unknown layer → 404):**
  249: earth2-temperature, earth2-precip, earth2-wind  →  CREP_TILE_STUB_PROFILE=earth2
  241: inat-density, signal-coverage                   →  CREP_TILE_STUB_PROFILE=density
  If profile unset, all five allowed (local dev only).

**Response:** image/png (proxy accepts image/*), Cache-Control; 5s timeout is client-side in Next.

Run (example 249):
  set CREP_TILE_STUB_PROFILE=earth2
  uvicorn services.crep_tile_render_stub.main:app --host 0.0.0.0 --port 8230
"""
from __future__ import annotations

import base64
import os

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse

_PROFILE = (os.environ.get("CREP_TILE_STUB_PROFILE", "") or "").strip().lower()

EARTH2_LAYERS = frozenset({"earth2-temperature", "earth2-precip", "earth2-wind"})
DENSITY_LAYERS = frozenset({"inat-density", "signal-coverage"})

if _PROFILE == "earth2":
    ALLOWED: frozenset[str] = EARTH2_LAYERS
elif _PROFILE == "density":
    ALLOWED = DENSITY_LAYERS
else:
    ALLOWED = EARTH2_LAYERS | DENSITY_LAYERS

# 1x1 transparent PNG
_PNG1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

app = FastAPI(title="crep-tile-stub", version="0.2.0")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "gpu": False,
            "service": "crep-tile-stub",
            "profile": _PROFILE or "all",
            "layers": sorted(ALLOWED),
        }
    )


@app.get("/tile/{layer}/{z}/{x}/{y}.png")
def tile(layer: str, z: int, x: int, y: int) -> Response:
    if layer not in ALLOWED:
        raise HTTPException(
            status_code=404,
            detail="unknown layer for this host — check CREP_TILE_STUB_PROFILE (earth2 vs density)",
        )
    return Response(
        content=_PNG1,
        media_type="image/png",
        headers={
            "X-CREP-Tile-Stub": "1",
            "X-CREP-Layer": layer,
            "Cache-Control": "public, max-age=60",
        },
    )
