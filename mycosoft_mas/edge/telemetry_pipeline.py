"""
Telemetry pipeline for on-device Jetson operator.

Polls Side A for telemetry, wraps in IoT envelope, and forwards to:
- MAS /api/iot/envelope/ingest
- NLM /api/translate (optional) -> NLM /api/telemetry/ingest-verified (optional)
- MINDEX /api/fci/telemetry or /api/telemetry/envelope (optional)

Maintains a circular buffer for /telemetry/latest and SSE streaming.
"""

from __future__ import annotations

import asyncio
import collections
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional
import uuid

import httpx

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TelemetryEntry:
    """Single telemetry reading with envelope metadata."""

    envelope_id: str
    device_id: str
    seq: int
    payload: Dict[str, Any]
    received_at: str
    envelope: Dict[str, Any]


class TelemetryPipeline:
    """
    Background telemetry pipeline: poll Side A, wrap in envelope, forward to MAS/NLM/MINDEX.
    """

    def __init__(
        self,
        *,
        side_a_request_fn,
        device_id: str,
        mas_api_url: str,
        nlm_api_url: Optional[str] = None,
        mindex_api_url: Optional[str] = None,
        role: str = "mushroom1",
        poll_interval_seconds: float = 5.0,
        buffer_size: int = 100,
    ) -> None:
        self._side_a_request = side_a_request_fn
        self.device_id = device_id
        self.mas_api_url = mas_api_url.rstrip("/")
        self.nlm_api_url = (nlm_api_url or "").rstrip("/") or None
        self.mindex_api_url = (mindex_api_url or "").rstrip("/") or None
        self.role = role
        self.poll_interval = poll_interval_seconds
        self._buffer: Deque[TelemetryEntry] = collections.deque(maxlen=buffer_size)
        self._seq = 0
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def _read_telemetry(self) -> Optional[Dict[str, Any]]:
        """Poll Side A for telemetry via read_sensors command."""
        try:
            response = await self._side_a_request("read_sensors", {})
            if isinstance(response, dict):
                payload = response.get("payload")
                if isinstance(payload, dict) and payload:
                    return payload
                if response:
                    return response
            return None
        except Exception as exc:
            logger.warning("telemetry_pipeline read_sensors failed: %s", exc)
            return None

    def _build_envelope(self, payload: Dict[str, Any], seq: int) -> Dict[str, Any]:
        """Build IoT envelope from telemetry payload."""
        msg_id = str(uuid.uuid4())
        envelope = {
            "hdr": {
                "deviceId": self.device_id,
                "msgId": msg_id,
            },
            "seq": seq,
            "payload": payload,
            "ts": _utc_now(),
            "role": self.role,
        }
        return envelope

    async def _forward_to_mas(self, envelope: Dict[str, Any]) -> bool:
        """POST envelope to MAS /api/iot/envelope/ingest."""
        url = f"{self.mas_api_url}/api/iot/envelope/ingest"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json={"envelope": envelope})
                if res.status_code >= 400:
                    logger.warning("MAS envelope ingest failed %s: %s", res.status_code, res.text)
                    return False
                return True
        except Exception as exc:
            logger.warning("MAS envelope ingest error: %s", exc)
            return False

    async def _forward_to_nlm(self, envelope: Dict[str, Any], raw_payload: Dict[str, Any]) -> bool:
        """Translate via NLM and ingest verified telemetry (optional)."""
        if not self.nlm_api_url:
            return True
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # NLM translate: raw -> NMF (Normalized Mycoformat)
                translate_url = f"{self.nlm_api_url}/api/translate"
                trans_res = await client.post(
                    translate_url,
                    json={"raw": raw_payload, "device_id": self.device_id, "role": self.role},
                )
                if trans_res.status_code >= 400:
                    logger.debug("NLM translate not available or failed: %s", trans_res.status_code)
                    return True  # non-fatal
                nmf = trans_res.json() if trans_res.text else {}
                # NLM telemetry ingest-verified
                ingest_url = f"{self.nlm_api_url}/api/telemetry/ingest-verified"
                ingest_res = await client.post(
                    ingest_url,
                    json={
                        "nmf": nmf,
                        "envelope_seq": envelope.get("seq"),
                        "device_id": self.device_id,
                    },
                )
                if ingest_res.status_code >= 400:
                    logger.debug("NLM telemetry ingest not available or failed: %s", ingest_res.status_code)
            return True
        except Exception as exc:
            logger.debug("NLM forward skipped: %s", exc)
            return True  # non-fatal

    async def _forward_to_mindex(self, envelope: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        """POST to MINDEX FCI telemetry (optional)."""
        if not self.mindex_api_url:
            return True
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try /api/fci/telemetry first, fallback to /api/telemetry/envelope
                for path in ["/api/fci/telemetry", "/api/telemetry/envelope"]:
                    url = f"{self.mindex_api_url}{path}"
                    res = await client.post(
                        url,
                        json={
                            "envelope_id": envelope.get("hdr", {}).get("msgId", ""),
                            "device_id": self.device_id,
                            "seq": envelope.get("seq"),
                            "payload": payload,
                        },
                    )
                    if res.status_code < 400:
                        return True
                    if res.status_code != 404:
                        logger.debug("MINDEX %s failed %s: %s", path, res.status_code, res.text[:200])
            return True
        except Exception as exc:
            logger.debug("MINDEX forward skipped: %s", exc)
            return True  # non-fatal

    async def _process_one(self) -> None:
        """Read one telemetry sample, build envelope, forward, buffer, notify."""
        raw = await self._read_telemetry()
        if not raw or not isinstance(raw, dict):
            return
        payload = raw.get("payload", raw) if "payload" in raw else raw
        if not isinstance(payload, dict):
            payload = {"raw": payload}

        async with self._lock:
            self._seq += 1
            seq = self._seq

        envelope = self._build_envelope(payload, seq)
        envelope_id = envelope["hdr"]["msgId"]

        await self._forward_to_mas(envelope)
        await self._forward_to_nlm(envelope, payload)
        await self._forward_to_mindex(envelope, payload)

        entry = TelemetryEntry(
            envelope_id=envelope_id,
            device_id=self.device_id,
            seq=seq,
            payload=payload,
            received_at=_utc_now(),
            envelope=envelope,
        )
        async with self._lock:
            self._buffer.append(entry)
            for q in self._subscribers:
                try:
                    q.put_nowait(entry)
                except asyncio.QueueFull:
                    pass

    async def _poll_loop(self) -> None:
        """Background loop: poll Side A periodically."""
        logger.info("TelemetryPipeline started (role=%s, device=%s)", self.role, self.device_id)
        while not self._stop.is_set():
            await self._process_one()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.poll_interval)
            except asyncio.TimeoutError:
                pass
        logger.info("TelemetryPipeline stopped")

    def start(self) -> None:
        """Start the background poll loop."""
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop the background poll loop."""
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def get_latest(self, n: int = 10) -> list[Dict[str, Any]]:
        """Return last n telemetry entries (for /telemetry/latest)."""
        async with self._lock:
            entries = list(self._buffer)[-n:]
        return [asdict(e) for e in reversed(entries)]

    async def stream(self) -> AsyncIterator[TelemetryEntry]:
        """SSE-compatible async generator of new telemetry entries."""
        q: asyncio.Queue[Optional[TelemetryEntry]] = asyncio.Queue(maxsize=50)
        async with self._lock:
            self._subscribers.append(q)
        try:
            while True:
                entry = await q.get()
                if entry is None:
                    break
                yield entry
        finally:
            async with self._lock:
                if q in self._subscribers:
                    self._subscribers.remove(q)
