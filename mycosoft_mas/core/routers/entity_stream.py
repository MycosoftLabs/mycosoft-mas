"""
Unified Entity Stream Router - February 13, 2026

Streams viewport-scoped entity updates over WebSocket.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from mycosoft_mas.realtime.redis_pubsub import PubSubMessage, get_client

router = APIRouter(tags=["Entity Stream"])


def _parse_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _to_epoch_seconds(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        iso = value.replace("Z", "+00:00")
        return datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return None


def _passes_filter(payload: dict[str, Any], allowed_types: set[str], time_from: Optional[float]) -> bool:
    entity_type = payload.get("type")
    if allowed_types and entity_type not in allowed_types:
        return False

    if time_from is None:
        return True

    observed_at = (
        payload.get("time", {}).get("observed_at")
        if isinstance(payload.get("time"), dict)
        else payload.get("observed_at")
    )
    if not observed_at:
        return True

    try:
        observed_epoch = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00")).timestamp()
        return observed_epoch >= time_from
    except ValueError:
        return True


@router.websocket("/api/entities/stream")
async def entity_stream(
    websocket: WebSocket,
    cells: Optional[str] = Query(default=None, description="Comma-separated S2 cell IDs"),
    types: Optional[str] = Query(default=None, description="Comma-separated entity types"),
    time_from: Optional[str] = Query(default=None, description="ISO8601 lower time bound"),
):
    await websocket.accept()

    cell_ids = _parse_csv(cells)
    allowed_types = set(_parse_csv(types))
    time_from_epoch = _to_epoch_seconds(time_from)
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=512)
    client = await get_client()

    channels = [f"entities:{cell}" for cell in cell_ids] if cell_ids else ["entities:lifecycle", "crep:live"]

    async def on_message(message: PubSubMessage):
        payload = message.data if isinstance(message.data, dict) else {"data": message.data}
        if "entity" in payload and isinstance(payload["entity"], dict):
            payload = payload["entity"]
        if not _passes_filter(payload, allowed_types, time_from_epoch):
            return
        if queue.full():
            return
        await queue.put(payload)

    for channel in channels:
        await client.subscribe(channel, on_message)

    await websocket.send_json(
        {
            "type": "connected",
            "channels": channels,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }
    )

    try:
        while True:
            payload = await queue.get()
            # Send as binary JSON frame to support binary transport clients.
            await websocket.send_bytes(json.dumps(payload).encode("utf-8"))
    except WebSocketDisconnect:
        pass
    finally:
        for channel in channels:
            await client.unsubscribe(channel, on_message)
