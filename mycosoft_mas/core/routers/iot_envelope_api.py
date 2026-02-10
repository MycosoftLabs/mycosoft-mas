"""
IoT Envelope Ingest API (Local-first) - FEB09 2026

Receives unified envelopes from gateways/transports, forwards them into the
Mycorrhizae Protocol, and returns an ACK contract suitable for device replay.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/iot", tags=["iot"])


class EnvelopeIngestRequest(BaseModel):
    envelope: Dict[str, Any] = Field(default_factory=dict)
    channel: Optional[str] = None


class ReplayAckRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=200)
    msg_id: str = Field(..., min_length=1, max_length=200)
    seq: int = Field(..., ge=0)
    accepted: bool = True
    reason: Optional[str] = None


def _get_mycorrhizae_config() -> tuple[str, str]:
    # Default to localhost for the common deployment: Mycorrhizae container on MAS VM 188.
    # Override with MYCORRHIZAE_API_URL when running elsewhere (e.g., Sandbox VM 187).
    api_url = os.getenv("MYCORRHIZAE_API_URL", "http://127.0.0.1:8002").rstrip("/")
    api_key = os.getenv("MYCORRHIZAE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MYCORRHIZAE_API_KEY not configured")
    return api_url, api_key


@router.post("/envelope/ingest")
async def ingest_envelope(request: EnvelopeIngestRequest):
    """
    Ingest a transport-agnostic envelope and forward to Mycorrhizae.

    This endpoint does not persist locally; it relies on Mycorrhizae's Redis
    broker + stream persistence + dedupe.
    """
    env = request.envelope or {}
    hdr = env.get("hdr") if isinstance(env, dict) else None
    if not isinstance(hdr, dict):
        raise HTTPException(status_code=400, detail="missing_hdr")

    device_id = hdr.get("deviceId")
    msg_id = hdr.get("msgId")
    seq = env.get("seq")
    if not device_id or not msg_id or not isinstance(seq, int):
        raise HTTPException(status_code=400, detail="missing_deviceId_msgId_seq")

    channel = request.channel or f"device.{device_id}.telemetry"

    api_url, api_key = _get_mycorrhizae_config()
    publish_url = f"{api_url}/api/channels/{channel}/publish"

    payload = {
        "payload": env,
        "message_type": "telemetry",
        "source_id": "mas",
        "device_serial": str(device_id),
        "priority": 5,
        "tags": ["envelope", "verified-by-mycorrhizae"],
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(publish_url, headers={"X-API-Key": api_key}, json=payload)
        if res.status_code >= 400:
            raise HTTPException(status_code=res.status_code, detail=res.text)

    return {
        "accepted": True,
        "deviceId": device_id,
        "msgId": msg_id,
        "seq": seq,
        "channel": channel,
        "forwardedAtUtc": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/replay/ack")
async def replay_ack(request: ReplayAckRequest):
    api_url, api_key = _get_mycorrhizae_config()
    ack_url = f"{api_url}/api/stream/replay/ack"
    body = {
        "device_id": request.device_id,
        "msg_id": request.msg_id,
        "seq": request.seq,
        "accepted": request.accepted,
        "reason": request.reason,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(ack_url, headers={"X-API-Key": api_key}, json=body)
        if res.status_code >= 400:
            raise HTTPException(status_code=res.status_code, detail=res.text)
        return res.json()
