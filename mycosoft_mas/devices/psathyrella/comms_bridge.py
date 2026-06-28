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

VALID_BEARERS = frozenset({"ble", "cellular", "wifi", "lora", "iridium", "starlink", "acoustic"})
RF_BEARERS = frozenset({"ble", "cellular", "wifi", "lora"})


@dataclass
class BridgeFrame:
    """Normalized frame used across RF and acoustic links."""

    frame_id: str
    device_id: str
    direction: str
    payload: Dict[str, Any]
    bearer: str = "lora"
    priority: int = 3
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
        self._preferred_bearer_by_device: Dict[str, str] = {}
        self._bridge_enabled_by_device: Dict[str, bool] = {}
        self._store_forward: Dict[str, Deque[BridgeFrame]] = {}
        self._mo_queues: Dict[str, Deque[BridgeFrame]] = {}
        self._mt_queues: Dict[str, Deque[BridgeFrame]] = {}
        self._satellite_state: Dict[str, Dict[str, Any]] = {}
        self._acoustic_stream_queues: Dict[str, asyncio.Queue[Dict[str, Any]]] = {}

    def set_bearer(self, device_id: str, bearer: str) -> Dict[str, Any]:
        """Set explicit bearer override for routing (comms.set_bearer)."""
        normalized = (bearer or "").strip().lower()
        if normalized not in VALID_BEARERS - {"acoustic"}:
            raise ValueError(f"bad_bearer:{bearer}")
        self._preferred_bearer_by_device[device_id] = normalized
        if normalized in {"iridium", "starlink"}:
            sat = self._satellite_state.setdefault(device_id, _empty_satellite())
            sat["bearer"] = normalized
        return self.get_state(device_id)

    def select_bearer(self, device_id: str, frame: Optional[Dict[str, Any]] = None) -> str:
        """Minimal bearer router — explicit override or auto preference."""
        preferred = self._preferred_bearer_by_device.get(device_id)
        if preferred:
            return preferred
        mode = self._radio_mode_by_device.get(device_id, "auto")
        if mode != "auto" and mode in VALID_BEARERS:
            return mode
        return "lora"

    def get_state(self, device_id: str) -> Dict[str, Any]:
        queue = self._store_forward.get(device_id)
        mo = self._mo_queues.get(device_id)
        mt = self._mt_queues.get(device_id)
        sat = self._satellite_state.get(device_id) or _empty_satellite()
        return {
            "device_id": device_id,
            "radio_mode": self._radio_mode_by_device.get(device_id, "auto"),
            "preferred_bearer": self._preferred_bearer_by_device.get(device_id),
            "bridge_enabled": self._bridge_enabled_by_device.get(device_id, True),
            "store_forward_depth": len(queue) if queue else 0,
            "mo_queued": len(mo) if mo else 0,
            "mt_queued": len(mt) if mt else 0,
            "satellite": sat,
            "recommendation": self.recommended_side_assignment(),
        }

    def get_satellite_state(self, device_id: str) -> Dict[str, Any]:
        return dict(self._satellite_state.get(device_id) or _empty_satellite())

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

    def enqueue_for_backhaul(
        self,
        device_id: str,
        direction: str,
        payload: Dict[str, Any],
        *,
        bearer: str = "lora",
        priority: int = 3,
        queue_kind: str = "legacy",
    ) -> BridgeFrame:
        if queue_kind == "mt":
            queue = self._mt_queues.setdefault(device_id, deque(maxlen=1024))
        elif queue_kind == "mo":
            queue = self._mo_queues.setdefault(device_id, deque(maxlen=1024))
        else:
            queue = self._store_forward.setdefault(device_id, deque(maxlen=1024))
        frame = BridgeFrame(
            frame_id=str(uuid4()),
            device_id=device_id,
            direction=direction,
            payload=payload,
            bearer=bearer,
            priority=priority,
        )
        queue.append(frame)
        return frame

    def flush_store_forward(self, device_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        queue = self._store_forward.setdefault(device_id, deque(maxlen=1024))
        drained: List[Dict[str, Any]] = []
        count = 0
        while queue and count < limit:
            item = queue.popleft()
            drained.append(self._frame_to_dict(item))
            count += 1
        return drained

    def enqueue_mt_command(
        self,
        device_id: str,
        payload: Dict[str, Any],
        *,
        bearer: str = "iridium",
        priority: int = 0,
    ) -> BridgeFrame:
        """Ground→buoy mobile-terminated queue (commands, mission uploads)."""
        return self.enqueue_for_backhaul(
            device_id,
            "ground_to_buoy",
            payload,
            bearer=bearer,
            priority=priority,
            queue_kind="mt",
        )

    def enqueue_mo_frame(
        self,
        device_id: str,
        direction: str,
        payload: Dict[str, Any],
        *,
        bearer: str = "lora",
        priority: int = 3,
    ) -> BridgeFrame:
        """Buoy→ground mobile-originated queue (telemetry, contacts, acks)."""
        return self.enqueue_for_backhaul(
            device_id,
            direction,
            payload,
            bearer=bearer,
            priority=priority,
            queue_kind="mo",
        )

    def flush_mt_queue(self, device_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Drain ground→buoy MT queue on reconnect / satellite pass."""
        queue = self._mt_queues.setdefault(device_id, deque(maxlen=1024))
        drained: List[Dict[str, Any]] = []
        count = 0
        while queue and count < limit:
            item = queue.popleft()
            drained.append(self._frame_to_dict(item))
            count += 1
        return drained

    def flush_mo_queue(self, device_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Drain buoy→ground MO queue during backhaul."""
        queue = self._mo_queues.setdefault(device_id, deque(maxlen=1024))
        drained: List[Dict[str, Any]] = []
        count = 0
        while queue and count < limit:
            item = queue.popleft()
            drained.append(self._frame_to_dict(item))
            count += 1
        return drained

    @staticmethod
    def pack_sbd_frame(payload: Dict[str, Any], *, max_bytes: int = 340) -> Dict[str, Any]:
        """
        Iridium SBD budget guard — compact JSON; returns oversize status when exceeded.
        Full binary/CBOR codec is hardware-blocked until modem integration.
        """
        encoded = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        if len(encoded) <= max_bytes:
            return {"status": "ok", "bytes": len(encoded), "payload": payload, "codec": "json_compact"}
        return {
            "status": "pending",
            "reason": "SBD_OVERSIZE",
            "bytes": len(encoded),
            "max_bytes": max_bytes,
            "detail": "frame exceeds SBD budget; fragmentation not yet wired",
        }

    @staticmethod
    def _frame_to_dict(item: BridgeFrame) -> Dict[str, Any]:
        return {
            "frame_id": item.frame_id,
            "device_id": item.device_id,
            "direction": item.direction,
            "payload": item.payload,
            "bearer": item.bearer,
            "priority": item.priority,
            "received_at": item.received_at,
        }

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


def _empty_satellite() -> Dict[str, Any]:
    return {
        "bearer": None,
        "connected": False,
        "rssiDbm": None,
        "credits": None,
        "mtQueued": 0,
        "moQueued": 0,
        "lastContactMsAgo": None,
        "nextPassEtaS": None,
    }


_bridge_instance: Optional[PsathyrellaCommsBridge] = None


def get_psathyrella_comms_bridge() -> PsathyrellaCommsBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = PsathyrellaCommsBridge()
    return _bridge_instance
