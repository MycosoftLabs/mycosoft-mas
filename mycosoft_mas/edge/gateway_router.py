"""
Gateway router runtime for 4GB Jetson + LilyGO communications node.

Responsibilities:
- Accept transport messages (LoRa/BLE/WiFi/SIM ingress)
- Store-and-forward queue
- Publish upstream to MAS / Mycorrhizae / MINDEX / Website ingest
- IoT envelope wrapping, NLM translate for ingested telemetry
- /devices endpoint, periodic gateway self-heartbeat
- Optional OpenClaw task execution on gateway profile
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import uuid

from fastapi import FastAPI, HTTPException
import httpx
from pydantic import BaseModel, Field

from .opclaw_client import OpenClawClient

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class BufferedMessage:
    message_id: str
    device_id: str
    transport: Literal["lora", "ble", "wifi", "sim"]
    payload: Dict[str, Any]
    received_at: str
    attempts: int = 0
    last_error: Optional[str] = None


class IngestMessageRequest(BaseModel):
    device_id: str
    transport: Literal["lora", "ble", "wifi", "sim"]
    payload: Dict[str, Any] = Field(default_factory=dict)


class GatewayConfig(BaseModel):
    gateway_id: str
    host: str
    port: int = 8003
    location: str = "on-site"


class OpenClawTaskRequest(BaseModel):
    task: Dict[str, Any]
    source: str = "gateway_api"


class GatewayRouter:
    def __init__(self) -> None:
        self.gateway_id = os.getenv("GATEWAY_ID", "gateway-jetson4")
        self.gateway_host = os.getenv("GATEWAY_HOST", "127.0.0.1")
        self.gateway_port = int(os.getenv("GATEWAY_PORT", "8003"))
        self.location = os.getenv("GATEWAY_LOCATION", "on-site")
        self.queue: List[BufferedMessage] = []
        self._queue_lock = asyncio.Lock()
        self._flusher_task: Optional[asyncio.Task[Any]] = None
        self._heartbeat_task: Optional[asyncio.Task[Any]] = None
        self.audit_path = Path(os.getenv("GATEWAY_AUDIT_LOG", "data/edge/gateway_audit.jsonl"))
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.upstream_mas = os.getenv("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")
        self.upstream_mycorrhizae = os.getenv("MYCORRHIZAE_API_URL", "").rstrip("/")
        self.upstream_mindex = os.getenv("MINDEX_API_URL", "").rstrip("/")
        self.upstream_ingest = os.getenv("TELEMETRY_INGEST_URL", "").rstrip("/")
        self.nlm_api_url = (os.getenv("NLM_API_URL", "").rstrip("/") or None)
        self.max_attempts = int(os.getenv("GATEWAY_MAX_ATTEMPTS", "8"))
        self.flush_interval_seconds = int(os.getenv("GATEWAY_FLUSH_INTERVAL_SECONDS", "5"))
        self.heartbeat_interval_seconds = int(os.getenv("GATEWAY_HEARTBEAT_INTERVAL_SECONDS", "30"))
        self.opclaw_url = os.getenv("GATEWAY_OPENCLAW_BASE_URL", "").strip()
        self.opclaw_api_key = os.getenv("GATEWAY_OPENCLAW_API_KEY", "").strip() or None
        self.opclaw = OpenClawClient(self.opclaw_url) if self.opclaw_url else None
        self._device_registry: Dict[str, Dict[str, Any]] = {}
        self._device_lock = asyncio.Lock()
        self._envelope_seq = 0

    async def start(self) -> None:
        if self._flusher_task and not self._flusher_task.done():
            return
        self._flusher_task = asyncio.create_task(self._flush_loop(), name="gateway-flusher")
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(), name="gateway-heartbeat")
        await self._audit("gateway_start", {"gateway_id": self.gateway_id})

    async def stop(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
        if self._flusher_task:
            self._flusher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._flusher_task
        await self._audit("gateway_stop", {"gateway_id": self.gateway_id})

    async def ingest_message(self, req: IngestMessageRequest) -> BufferedMessage:
        msg = BufferedMessage(
            message_id=str(uuid.uuid4()),
            device_id=req.device_id,
            transport=req.transport,
            payload=req.payload,
            received_at=_utc_now(),
        )
        async with self._queue_lock:
            self.queue.append(msg)
        async with self._device_lock:
            self._device_registry[req.device_id] = {
                "device_id": req.device_id,
                "transport": req.transport,
                "last_seen": msg.received_at,
            }
        await self._audit("ingest", {"message_id": msg.message_id, "device_id": msg.device_id, "transport": msg.transport})
        return msg

    def _build_envelope(self, device_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap payload in IoT envelope for MAS/NLM/MINDEX ingest."""
        self._envelope_seq += 1
        msg_id = str(uuid.uuid4())
        return {
            "hdr": {
                "deviceId": device_id,
                "msgId": msg_id,
                "seq": self._envelope_seq,
            },
            "payload": payload,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _translate_via_nlm(self, client: httpx.AsyncClient, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call NLM /api/translate for ingested telemetry. Returns NMF or None."""
        if not self.nlm_api_url:
            return None
        try:
            r = await client.post(
                f"{self.nlm_api_url}/api/translate",
                json=payload,
                timeout=10.0,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("NLM translate failed: %s", e)
            return None

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(self.flush_interval_seconds)
            await self.flush_once()

    async def _heartbeat_loop(self) -> None:
        """Periodic gateway self-heartbeat to MAS every 30s."""
        while True:
            await asyncio.sleep(self.heartbeat_interval_seconds)
            try:
                await self.register_gateway()
            except Exception as e:
                logger.warning("Gateway self-heartbeat failed: %s", e)

    async def flush_once(self) -> Dict[str, Any]:
        async with self._queue_lock:
            snapshot = list(self.queue)

        delivered = 0
        failed = 0
        for msg in snapshot:
            ok, err = await self._publish_upstream(msg)
            if ok:
                delivered += 1
                async with self._queue_lock:
                    self.queue = [m for m in self.queue if m.message_id != msg.message_id]
            else:
                failed += 1
                msg.attempts += 1
                msg.last_error = err
                await self._audit("publish_failed", {"message_id": msg.message_id, "error": err, "attempts": msg.attempts})
                if msg.attempts >= self.max_attempts:
                    async with self._queue_lock:
                        self.queue = [m for m in self.queue if m.message_id != msg.message_id]
                    await self._audit("dropped", {"message_id": msg.message_id, "error": err})
        return {"delivered": delivered, "failed": failed, "queued": len(self.queue)}

    async def _publish_upstream(self, msg: BufferedMessage) -> tuple[bool, Optional[str]]:
        raw_payload = {
            "deviceId": msg.device_id,
            "deviceType": "mycobrain",
            "readings": msg.payload.get("readings", []),
            "transport": msg.transport,
            "via_gateway_id": self.gateway_id,
            "received_at": msg.received_at,
            **{k: v for k, v in msg.payload.items() if k not in {"readings"}},
        }
        envelope = self._build_envelope(msg.device_id, raw_payload)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # MAS heartbeat path (canonical ID preserved)
                hb = {
                    "device_id": msg.device_id,
                    "device_name": msg.payload.get("device_name", "MycoBrain"),
                    "device_role": msg.payload.get("device_role", "standalone"),
                    "host": self.gateway_host,
                    "port": self.gateway_port,
                    "firmware_version": msg.payload.get("firmware_version", "unknown"),
                    "board_type": msg.payload.get("board_type", "jetson4-gateway"),
                    "sensors": msg.payload.get("sensors", []),
                    "capabilities": msg.payload.get("capabilities", []),
                    "connection_type": "lan",
                    "ingestion_source": "gateway",
                    "extra": {
                        "via_gateway_id": self.gateway_id,
                        "transport": msg.transport,
                    },
                }
                await client.post(f"{self.upstream_mas}/api/devices/heartbeat", json=hb)

                # NLM translate for ingested LoRa/BLE/WiFi/SIM telemetry
                nmf = await self._translate_via_nlm(client, envelope)
                data_for_ingest = nmf if nmf else envelope

                if self.upstream_ingest:
                    ingest_url = self.upstream_ingest
                    if "/api/iot/envelope/ingest" not in ingest_url and "/api/devices/ingest" not in ingest_url:
                        ingest_url = ingest_url + "/api/iot/envelope/ingest"
                    await client.post(ingest_url, json=data_for_ingest)

                if self.upstream_mindex:
                    await client.post(f"{self.upstream_mindex}/api/fci/telemetry", json=data_for_ingest)

                if self.upstream_mycorrhizae:
                    env_pub = {
                        "device_id": msg.device_id,
                        "device_type": "mycobrain",
                        "payload_type": "telemetry",
                        "payload": data_for_ingest,
                    }
                    await client.post(f"{self.upstream_mycorrhizae}/api/channels/publish", json=env_pub)

            await self._audit("published", {"message_id": msg.message_id, "device_id": msg.device_id})
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    async def register_gateway(self) -> Dict[str, Any]:
        heartbeat = {
            "device_id": f"gateway-{self.gateway_id}",
            "device_name": "Jetson4 Gateway",
            "device_role": "gateway",
            "host": self.gateway_host,
            "port": self.gateway_port,
            "firmware_version": "gateway-router-1.0.0",
            "board_type": "jetson4",
            "sensors": [],
            "capabilities": ["lora", "ble", "wifi", "sim", "store_and_forward"],
            "connection_type": "lan",
            "ingestion_source": "gateway",
            "extra": {"gateway_id": self.gateway_id, "location": self.location},
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{self.upstream_mas}/api/devices/heartbeat", json=heartbeat)
            response.raise_for_status()
            data = response.json()
        await self._audit("gateway_registered", {"gateway_id": self.gateway_id})
        return data

    async def run_opclaw_task(self, req: OpenClawTaskRequest) -> Dict[str, Any]:
        if not self.opclaw:
            raise HTTPException(status_code=400, detail="gateway_openclaw_not_configured")
        result = await self.opclaw.run_task(req.task, api_key=self.opclaw_api_key)
        await self._audit("openclaw_task", {"source": req.source, "task": req.task, "result": result})
        return result

    async def _audit(self, event_type: str, payload: Dict[str, Any]) -> None:
        line = json.dumps({"ts": _utc_now(), "event_type": event_type, "payload": payload}, separators=(",", ":")) + "\n"
        await asyncio.to_thread(self._append_line, line)

    def _append_line(self, line: str) -> None:
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(line)


router = GatewayRouter()
app = FastAPI(title="MycoBrain Gateway Router", version="1.0.0")


@app.on_event("startup")
async def startup() -> None:
    await router.start()


@app.get("/health")
async def health() -> Dict[str, Any]:
    openclaw_health = None
    if router.opclaw:
        try:
            openclaw_health = await router.opclaw.health()
        except Exception as exc:  # noqa: BLE001
            openclaw_health = {"status": "unreachable", "error": str(exc)}
    return {
        "status": "healthy",
        "service": "gateway-router",
        "gateway_id": router.gateway_id,
        "queued_messages": len(router.queue),
        "openclaw": openclaw_health,
    }


@app.post("/gateway/register")
async def gateway_register() -> Dict[str, Any]:
    result = await router.register_gateway()
    return {"result": result}


@app.post("/ingest")
async def ingest(req: IngestMessageRequest) -> Dict[str, Any]:
    msg = await router.ingest_message(req)
    return {"message_id": msg.message_id, "queued": len(router.queue)}


@app.post("/flush")
async def flush_now() -> Dict[str, Any]:
    return await router.flush_once()


@app.get("/queue")
async def queue_state() -> Dict[str, Any]:
    return {
        "gateway_id": router.gateway_id,
        "queued": [
            {
                "message_id": m.message_id,
                "device_id": m.device_id,
                "transport": m.transport,
                "received_at": m.received_at,
                "attempts": m.attempts,
                "last_error": m.last_error,
            }
            for m in router.queue
        ],
    }


@app.get("/devices")
async def list_devices() -> Dict[str, Any]:
    """List all ingested device IDs and their last-seen time."""
    async with router._device_lock:
        devices = [
            {"device_id": dev_id, "transport": info.get("transport"), "last_seen": info.get("last_seen")}
            for dev_id, info in router._device_registry.items()
        ]
    return {"gateway_id": router.gateway_id, "devices": devices}


@app.post("/openclaw/task")
async def openclaw_task(req: OpenClawTaskRequest) -> Dict[str, Any]:
    return await router.run_opclaw_task(req)
