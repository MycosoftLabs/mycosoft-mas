"""Bench registry heartbeat for psathyrella-1 — prevents MAS device TTL expiry during Jetson bench."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from mycosoft_mas.core.routers import device_registry_api
from mycosoft_mas.devices.psathyrella.constants import (
    PSATHYRELLA_CANONICAL_DEVICE_ID,
    PSATHYRELLA_MUSHROOM1_AGENT_URL,
    PSATHYRELLA_PROPULSION_AGENT_URL,
    PSATHYRELLA_REGISTRY_KEEPALIVE,
)
from mycosoft_mas.devices.psathyrella.jetson_forward import propulsion_agent_reachable

logger = logging.getLogger(__name__)

_keepalive_task: Optional[asyncio.Task] = None


def _jetson_host() -> str:
    url = PSATHYRELLA_MUSHROOM1_AGENT_URL or PSATHYRELLA_PROPULSION_AGENT_URL
    host = url.split("://", 1)[-1].split(":", 1)[0].strip()
    return host or (os.getenv("JETSON_IP") or "192.168.0.123").strip()


async def _heartbeat_once() -> bool:
    propulsion_up = await propulsion_agent_reachable({})
    mushroom_url = PSATHYRELLA_MUSHROOM1_AGENT_URL.rstrip("/")
    sensors_up = False
    if mushroom_url:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{mushroom_url}/health")
                sensors_up = response.status_code == 200
        except Exception:  # noqa: BLE001
            sensors_up = False
    if not propulsion_up and not sensors_up:
        return False

    host = _jetson_host()
    heartbeat = device_registry_api.DeviceHeartbeat(
        device_id=PSATHYRELLA_CANONICAL_DEVICE_ID,
        device_name="Psathyrella Mushroom 1",
        device_role="psathyrella",
        device_display_name="Psathyrella Buoy",
        host=host,
        port=8787,
        firmware_version="jetson-bench",
        board_type="jetson",
        sensors=["bme688", "propulsion"],
        capabilities=["nav", "telemetry", "propulsion"],
        location="bench",
        connection_type="lan",
        ingestion_source="wifi",
        extra={
            "agent_url": PSATHYRELLA_MUSHROOM1_AGENT_URL,
            "propulsion_agent_url": PSATHYRELLA_PROPULSION_AGENT_URL,
            "bench_keepalive": True,
        },
    )
    device_registry_api._upsert_device_heartbeat(heartbeat)  # noqa: SLF001
    return True


async def psathyrella_registry_keepalive_loop() -> None:
    interval_s = float(os.getenv("PSATHYRELLA_REGISTRY_HEARTBEAT_S", "45"))
    logger.info(
        "Psathyrella registry keepalive every %.0fs (device=%s)",
        interval_s,
        PSATHYRELLA_CANONICAL_DEVICE_ID,
    )
    while True:
        try:
            if await _heartbeat_once():
                logger.debug("Psathyrella registry heartbeat refreshed")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Psathyrella registry keepalive failed: %s", exc)
        await asyncio.sleep(interval_s)


def start_psathyrella_registry_keepalive() -> None:
    global _keepalive_task
    if not PSATHYRELLA_REGISTRY_KEEPALIVE:
        logger.info("Psathyrella registry keepalive disabled (PSATHYRELLA_REGISTRY_KEEPALIVE=0)")
        return
    if _keepalive_task is not None and not _keepalive_task.done():
        return
    _keepalive_task = asyncio.create_task(psathyrella_registry_keepalive_loop())
