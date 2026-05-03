"""
Petri Dish v2 — proxy to Rust `petri_engine_service` on Sandbox (PETRI_ENGINE_V2_URL).

Legacy petri routes remain under `/api/simulation/petri` (petri_sim_api).
"""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter(prefix="/api/simulation/petri/v2", tags=["simulation", "petri-v2"])


def _base_url() -> str:
    url = (os.environ.get("PETRI_ENGINE_V2_URL") or "").strip().rstrip("/")
    if not url:
        raise HTTPException(
            status_code=503,
            detail="PETRI_ENGINE_V2_URL is not configured (e.g. http://192.168.0.187:8050)",
        )
    return url


async def _forward(method: str, path: str, *, json_body: Any = None) -> Response:
    base = _base_url()
    url = f"{base}{path}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.request(method, url, json=json_body)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"petri_engine unreachable: {e}") from e
    return Response(content=r.content, status_code=r.status_code, media_type=r.headers.get("content-type", "application/json"))


@router.get("/health")
async def health_v2():
    """MAS health + engine reachability (does not 503 when engine URL unset)."""
    url = (os.environ.get("PETRI_ENGINE_V2_URL") or "").strip().rstrip("/")
    if not url:
        return {
            "status": "degraded",
            "mas": "ok",
            "petri_v2": "PETRI_ENGINE_V2_URL not configured",
        }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{url}/health")
        return Response(
            content=r.content,
            status_code=r.status_code,
            media_type=r.headers.get("content-type", "application/json"),
        )
    except httpx.RequestError as e:
        return {
            "status": "degraded",
            "mas": "ok",
            "petri_v2": "engine_unreachable",
            "error": str(e),
        }


@router.get("/state")
async def get_state():
    return await _forward("GET", "/state")


@router.post("/step")
async def step(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {"n": 1}
    return await _forward("POST", "/step", json_body=payload or {"n": 1})


@router.post("/reset")
async def reset(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return await _forward("POST", "/reset", json_body=payload)


@router.post("/pause")
async def pause(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {"paused": True}
    if not isinstance(body, dict):
        body = {"paused": True}
    return await _forward("POST", "/pause", json_body=body)


@router.post("/seed")
async def seed(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return await _forward("POST", "/seed", json_body=payload)


@router.get("/config")
async def get_config():
    return await _forward("GET", "/config")


@router.api_route("/engine/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def engine_catchall(full_path: str, request: Request):
    """Passthrough for future engine subpaths (recordings, ai, etc.)."""
    path = f"/{full_path}"
    if path.startswith("//"):
        path = path[1:]
    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
        except Exception:
            body = None
    return await _forward(request.method, path, json_body=body)
