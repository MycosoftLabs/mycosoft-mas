"""Psathyrella comms bridge: radio <-> acoustic translation + store/forward queue."""

from __future__ import annotations

import asyncio
import base64
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional
from uuid import uuid4


@dataclass
class BridgeFrame:
    """Normalized frame used across RF and acoustic links."""

    frame_id: str
    device_id: str
    direction: str
    payload: Dict[str, Any]
    received_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PsathyrellaCommsBridge:
    """
    Bridge for Side A hydrophone/transducer + Side B RF stack.

    Recommendation:
    - Side A: hydrophone capture and front-end signal conditioning.
    - Side B: RF transport orchestration (BLE/4G/WiFi/LoRa) and transducer TX/RX routing.
    """

    def __init__(self) -> None:
        self._radio_mode_by_device: Dict[str, str] = {}
        self._bridge_enabled_by_device: Dict[str, bool] = {}
        self._store_forward: Dict[str, Deque[BridgeFrame]] = {}
        self._acoustic_stream_queues: Dict[str, asyncio.Queue[Dict[str, Any]]] = {}

    def get_state(self, device_id: str) -> Dict[str, Any]:
        queue = self._store_forward.get(device_id)
        return {
            "device_id": device_id,
            "radio_mode": self._radio_mode_by_device.get(device_id, "auto"),
            "bridge_enabled": self._bridge_enabled_by_device.get(device_id, True),
            "store_forward_depth": len(queue) if queue else 0,
            "recommendation": self.recommended_side_assignment(),
        }

    def update_mode(self, device_id: str, radio_mode: str, bridge_enabled: Optional[bool] = None) -> Dict[str, Any]:
        self._radio_mode_by_device[device_id] = radio_mode
        if bridge_enabled is not None:
            self._bridge_enabled_by_device[device_id] = bridge_enabled
        return self.get_state(device_id)

    def translate_radio_to_acoustic(self, device_id: str, frame: Dict[str, Any]) -> Dict[str, Any]:
        encoded = base64.b64encode(json.dumps(frame, separators=(",", ":")).encode("utf-8")).decode("ascii")
        return {
            "protocol": "fsk",
            "carrier_hz": frame.get("carrier_hz", 32000),
            "symbol_rate_bps": frame.get("symbol_rate_bps", 1200),
            "payload_b64": encoded,
            "device_id": device_id,
        }

    def translate_acoustic_to_radio(self, acoustic_payload: Dict[str, Any]) -> Dict[str, Any]:
        raw = acoustic_payload.get("payload_b64")
        if not raw:
            return {"status": "pending", "detail": "missing_payload_b64"}
        decoded = base64.b64decode(raw.encode("ascii"))
        parsed = json.loads(decoded.decode("utf-8"))
        return {"status": "ok", "radio_frame": parsed}

    def enqueue_for_backhaul(self, device_id: str, direction: str, payload: Dict[str, Any]) -> BridgeFrame:
        queue = self._store_forward.setdefault(device_id, deque(maxlen=1024))
        frame = BridgeFrame(
            frame_id=str(uuid4()),
            device_id=device_id,
            direction=direction,
            payload=payload,
        )
        queue.append(frame)
        return frame

    def flush_store_forward(self, device_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        queue = self._store_forward.setdefault(device_id, deque(maxlen=1024))
        drained: List[Dict[str, Any]] = []
        count = 0
        while queue and count < limit:
            item = queue.popleft()
            drained.append(
                {
                    "frame_id": item.frame_id,
                    "device_id": item.device_id,
                    "direction": item.direction,
                    "payload": item.payload,
                    "received_at": item.received_at,
                }
            )
            count += 1
        return drained

    async def publish_acoustic_event(self, device_id: str, event: Dict[str, Any]) -> None:
        queue = self._acoustic_stream_queues.get(device_id)
        if queue is None:
            return
        await queue.put(event)

    def register_acoustic_stream(self, device_id: str) -> asyncio.Queue[Dict[str, Any]]:
        queue = self._acoustic_stream_queues.get(device_id)
        if queue is None:
            queue = asyncio.Queue(maxsize=256)
            self._acoustic_stream_queues[device_id] = queue
        return queue

    def unregister_acoustic_stream(self, device_id: str, queue: asyncio.Queue[Dict[str, Any]]) -> None:
        current = self._acoustic_stream_queues.get(device_id)
        if current is queue:
            self._acoustic_stream_queues.pop(device_id, None)

    @staticmethod
    def recommended_side_assignment() -> Dict[str, Any]:
        return {
            "side_a": {
                "recommended_components": ["hydrophone_preamp", "hydrophone_adc", "local_noise_gate"],
                "rationale": "Keep hydrophone capture close to analog front-end and reduce cable noise.",
            },
            "side_b": {
                "recommended_components": ["radio_stack", "transducer_txrx_router", "store_forward_queue"],
                "rationale": "Side B already hosts bridge transport and should arbitrate air-water backhaul.",
            },
            "notes": "AOTX/OPTX from Jan 2026 docs are baseline TX paths; underwater transducer RX remains hardware-dependent.",
        }


_bridge_instance: Optional[PsathyrellaCommsBridge] = None


def get_psathyrella_comms_bridge() -> PsathyrellaCommsBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = PsathyrellaCommsBridge()
    return _bridge_instance
