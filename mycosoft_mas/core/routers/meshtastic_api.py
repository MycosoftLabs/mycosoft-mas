"""
Meshtastic mesh REST + SSE (MAS) — proxies MINDEX internal reads and tails Redis stream ``mesh:packets``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from mycosoft_mas.integrations.mqtt_mycobrain_bridge import _mindex_hmac_token
from mycosoft_mas.integrations.mqtt_meshtastic_bridge import STREAM_KEY

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meshtastic", tags=["meshtastic"])

REDIS_URL = os.environ.get("REDIS_URL", "redis://192.168.0.189:6379/0")


def _mindex_meshtastic_base() -> str:
    """Resolve internal meshtastic base. ``MINDEX_API_URL`` may be origin-only or include ``/api/mindex`` (Fusarium style)."""
    u = (os.environ.get("MINDEX_API_URL") or "http://192.168.0.189:8000").rstrip("/")
    if u.endswith("/api/mindex"):
        return f"{u}/internal/meshtastic"
    return f"{u}/api/mindex/internal/meshtastic"


def _internal_token() -> str:
    secret = (os.environ.get("MINDEX_INTERNAL_SECRET") or "").strip()
    if secret:
        svc = (os.environ.get("MINDEX_INTERNAL_SERVICE_NAME") or "mas-orchestrator").strip()
        return _mindex_hmac_token(svc, secret)
    return (
        os.environ.get("MINDEX_INTERNAL_TOKEN")
        or os.environ.get("MINDEX_INTERNAL_TOKENS", "").split(",")[0]
        or ""
    ).strip()


def _mindex_headers() -> Dict[str, str]:
    t = _internal_token()
    if not t:
        return {}
    return {"X-Internal-Token": t, "Accept": "application/json"}


async def _mindex_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    token = _internal_token()
    if not token:
        raise HTTPException(status_code=503, detail="MINDEX internal token not configured")
    url = f"{_mindex_meshtastic_base()}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, headers=_mindex_headers(), params=params or {})
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text[:800])
        return r.json()


@router.get("/nodes")
async def mesh_nodes(
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    return await _mindex_get("/nodes", {"limit": limit, "offset": offset})


@router.get("/packets")
async def mesh_packets(
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    since: Optional[datetime] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    if since:
        params["since"] = since.isoformat()
    return await _mindex_get("/packets", params)


@router.get("/observers")
async def mesh_observers() -> Dict[str, Any]:
    return await _mindex_get("/observers")


@router.get("/routes")
async def mesh_routes(limit: int = Query(500, ge=1, le=5000)) -> Dict[str, Any]:
    return await _mindex_get("/routes", {"limit": limit})


@router.get("/stats")
async def mesh_stats() -> Dict[str, Any]:
    return await _mindex_get("/stats")


async def _mesh_packet_event_stream() -> AsyncIterator[dict]:
    try:
        import redis.asyncio as aioredis
    except ImportError as e:
        raise HTTPException(status_code=500, detail="redis asyncio not available") from e

    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        recent = await r.xrevrange(STREAM_KEY, count=80)
        for entry_id, fields in reversed(recent):
            data = fields.get("data") if fields else None
            if data:
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    payload = {"raw": data}
                yield {"event": "packet", "id": entry_id, "data": payload}
        while True:
            try:
                out = await r.xread({STREAM_KEY: "$"}, block=25000, count=25)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("xread error: %s", exc)
                await asyncio.sleep(2)
                continue
            if not out:
                continue
            for _stream, entries in out:
                for entry_id, fields in entries:
                    raw = fields.get("data") if fields else None
                    if raw:
                        try:
                            payload = json.loads(raw)
                        except json.JSONDecodeError:
                            payload = {"raw": raw}
                        yield {"event": "packet", "id": entry_id, "data": payload}
    finally:
        await r.aclose()


class LoRaIngestBody(BaseModel):
    """Raw mesh frame forwarded from MycoBrain gateway (Yagi path); body matches MINDEX ingest shape."""

    packet_uid: str
    from_node_id: Optional[str] = None
    to_node_id: Optional[str] = None
    gateway_node_id: Optional[str] = None
    channel: Optional[str] = None
    port_num: str = Field(default="UNKNOWN")
    payload: Dict[str, Any] = Field(default_factory=dict)
    payload_text: Optional[str] = None
    rx_rssi: Optional[float] = None
    rx_snr: Optional[float] = None
    hop_limit: Optional[int] = None
    hop_start: Optional[int] = None
    want_ack: Optional[bool] = None
    topic: Optional[str] = None
    raw_b64: Optional[str] = None


async def _mindex_post(path: str, body: Dict[str, Any]) -> Any:
    token = _internal_token()
    if not token:
        raise HTTPException(status_code=503, detail="MINDEX internal token not configured")
    url = f"{_mindex_meshtastic_base()}{path}"
    hdr = dict(_mindex_headers())
    hdr["Content-Type"] = "application/json"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers=hdr, json=body)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text[:800])
        return r.json()


@router.post("/ingest/lora")
async def ingest_lora_packet(body: LoRaIngestBody) -> Dict[str, Any]:
    """MycoBrain / Yagi gateway posts decoded mesh frames (not from public MQTT)."""
    payload = body.model_dump()
    payload["via_mqtt"] = False
    return await _mindex_post("/ingest/packet", payload)


@router.get("/stream")
async def mesh_stream() -> EventSourceResponse:
    async def gen():
        async for item in _mesh_packet_event_stream():
            yield {
                "event": item.get("event", "packet"),
                "id": item.get("id"),
                "data": json.dumps(item.get("data", {})),
            }

    return EventSourceResponse(gen(), ping=15)
