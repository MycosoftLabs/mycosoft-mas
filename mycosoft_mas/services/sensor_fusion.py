"""
Sensor fusion: BME688, FCI, camera, audio → NaturePacket.

Fuses MycoBrain sensors (BME688, FCI) with Jetson camera/audio into
timestamped NaturePackets every 100ms for consciousness pipeline.

Created: February 17, 2026
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

NATURE_PACKET_INTERVAL_MS = 100
MYCOBRAIN_URL = os.getenv("MYCOBRAIN_SERVICE_URL", "http://localhost:8003")
JETSON_URL = os.getenv("JETSON_SERVER_URL", "http://192.168.0.100:8080")


@dataclass
class NaturePacket:
    """Unified timestamped sensor packet for consciousness."""

    timestamp: datetime
    bme688: Dict[str, Any] = field(default_factory=dict)
    fci: Dict[str, Any] = field(default_factory=dict)
    camera_frame_ref: Optional[str] = None  # URL or storage ref; frame not embedded
    camera_frame_bytes: Optional[bytes] = None
    audio_level_db: Optional[float] = None
    audio_transcript: Optional[str] = None
    proprioception: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "bme688": self.bme688,
            "fci": self.fci,
            "camera_frame_ref": self.camera_frame_ref,
            "has_frame": self.camera_frame_bytes is not None
            and len(self.camera_frame_bytes or b"") > 0,
            "audio_level_db": self.audio_level_db,
            "audio_transcript": self.audio_transcript,
            "proprioception": self.proprioception,
        }


async def _fetch_mycobrain_telemetry(device_id: str) -> Optional[Dict[str, Any]]:
    """Fetch telemetry from MycoBrain for one device."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{MYCOBRAIN_URL}/devices/{device_id}/telemetry")
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.debug("MycoBrain fetch failed for %s: %s", device_id, e)
        return None


def _extract_bme688(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Extract BME688 (temp, humidity, pressure, VOC) from MycoBrain telemetry."""
    out: Dict[str, Any] = {}
    for key in ("bme1", "bme2"):
        d = telemetry.get(key)
        if not isinstance(d, dict):
            continue
        out = {
            "temperature_c": d.get("temperature"),
            "humidity_percent": d.get("humidity"),
            "pressure_hpa": d.get("pressure"),
            "gas_resistance_ohms": d.get("gas_resistance"),
            "iaq_index": d.get("iaq"),
        }
        break
    return out


def _extract_fci(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Extract FCI (fungal electrical signals) from MycoBrain telemetry."""
    out: Dict[str, Any] = {}
    fci = telemetry.get("fci") or telemetry.get("fungal")
    if isinstance(fci, dict):
        out = dict(fci)
    elif isinstance(fci, list):
        out = {"signals": fci[-10:] if len(fci) > 10 else fci}
    return out


async def _fetch_camera_frame() -> Optional[bytes]:
    """Fetch single frame from Jetson camera."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{JETSON_URL}/camera/frame")
            r.raise_for_status()
            return r.content
    except Exception as e:
        logger.debug("Camera frame fetch failed: %s", e)
        return None


async def _fetch_mycobrain_devices() -> List[str]:
    """Get list of MycoBrain device IDs."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{MYCOBRAIN_URL}/devices")
            r.raise_for_status()
            data = r.json()
            devices = (
                data.get("devices", data)
                if isinstance(data, dict)
                else (data if isinstance(data, list) else [])
            )
            if not isinstance(devices, list):
                return []
            ids = []
            for d in devices:
                if isinstance(d, dict):
                    ids.append(d.get("device_id") or d.get("id") or str(d))
                else:
                    ids.append(str(d))
            return ids
    except Exception as e:
        logger.debug("MycoBrain devices fetch failed: %s", e)
        return []


class SensorFusionService:
    """Fuses sensors into NaturePackets at 100ms intervals."""

    def __init__(
        self,
        interval_ms: int = NATURE_PACKET_INTERVAL_MS,
        include_camera: bool = True,
        mycobrain_url: Optional[str] = None,
        jetson_url: Optional[str] = None,
        replay_day_key: Optional[str] = None,
    ) -> None:
        self.interval_ms = interval_ms
        self.include_camera = include_camera
        self._mycobrain_url = mycobrain_url or MYCOBRAIN_URL
        self._jetson_url = jetson_url or JETSON_URL
        self._replay_day_key = replay_day_key
        self._devices: List[str] = []
        self._last_bme: Dict[str, Any] = {}
        self._last_fci: Dict[str, Any] = {}
        self._running = False
        self._tick = 0

    async def _refresh_devices(self) -> None:
        """Refresh MycoBrain device list periodically."""
        global MYCOBRAIN_URL
        MYCOBRAIN_URL = self._mycobrain_url
        self._devices = await _fetch_mycobrain_devices()
        if not self._devices:
            self._devices = ["default"]

    async def _gather_sensor_data(self) -> NaturePacket:
        """Gather all sensor data into one NaturePacket."""
        ts = datetime.now(timezone.utc)
        bme: Dict[str, Any] = {}
        fci: Dict[str, Any] = {}
        frame_bytes: Optional[bytes] = None

        # MycoBrain (BME688 + FCI)
        if self._devices:
            telemetry = await _fetch_mycobrain_telemetry(self._devices[0])
            if telemetry:
                raw = telemetry.get("telemetry", telemetry)
                if isinstance(raw, dict):
                    bme = _extract_bme688(raw)
                    fci = _extract_fci(raw)
                    if bme:
                        self._last_bme = bme
                    if fci:
                        self._last_fci = fci
        if not bme:
            bme = dict(self._last_bme)
        if not fci:
            fci = dict(self._last_fci)

        # Camera (from Jetson)
        if self.include_camera:
            global JETSON_URL
            JETSON_URL = self._jetson_url
            frame_bytes = await _fetch_camera_frame()

        return NaturePacket(
            timestamp=ts,
            bme688=bme,
            fci=fci,
            camera_frame_bytes=frame_bytes,
        )

    async def stream(self) -> AsyncIterator[NaturePacket]:
        """Async generator of NaturePackets every interval_ms."""
        self._running = True
        await self._refresh_devices()
        interval_sec = self.interval_ms / 1000.0
        while self._running:
            try:
                packet = await self._gather_sensor_data()
                if self._replay_day_key:
                    from mycosoft_mas.services.nature_replay import NatureReplayStore

                    replay_store = NatureReplayStore()
                    await replay_store.append_packet(self._replay_day_key, packet)
                yield packet
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Sensor fusion error: %s", e)
                yield NaturePacket(timestamp=datetime.now(timezone.utc))
            await asyncio.sleep(interval_sec)
            self._tick += 1
            # Refresh device list every ~60 packets (~6 seconds at 100ms interval).
            if self._tick % 60 == 0:
                await self._refresh_devices()

    def stop(self) -> None:
        self._running = False


async def stream_nature_packets(
    interval_ms: int = NATURE_PACKET_INTERVAL_MS,
    include_camera: bool = True,
) -> AsyncIterator[NaturePacket]:
    """
    Convenience: stream NaturePackets. Use with SensorFusionService for control.
    """
    svc = SensorFusionService(interval_ms=interval_ms, include_camera=include_camera)
    async for pkt in svc.stream():
        yield pkt
