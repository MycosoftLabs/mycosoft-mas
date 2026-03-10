"""
Serial bridge for MDP v1 framed communication.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Any, Dict, Optional

from .mdp_protocol import (
    MdpEndpoint,
    MdpFlags,
    MdpMsgType,
    build_frame,
    parse_frame,
)

try:
    import serial  # type: ignore
except Exception:  # pragma: no cover
    serial = None


@dataclass(slots=True)
class MdpResponse:
    header: Dict[str, Any]
    payload: Dict[str, Any]


class MdpSerialBridge:
    def __init__(
        self,
        *,
        port: str,
        baudrate: int,
        src_endpoint: int,
        default_dst: int,
        timeout_seconds: float = 2.0,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.src_endpoint = src_endpoint
        self.default_dst = default_dst
        self.timeout_seconds = timeout_seconds
        self._seq = 1
        self._lock = threading.Lock()
        self._serial: Optional["serial.Serial"] = None

    def connect(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is required for MDP serial bridge")
        if self._serial and self._serial.is_open:
            return
        self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout_seconds)
        self._serial.reset_input_buffer()

    def close(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    def _read_until_delimiter(self) -> bytes:
        assert self._serial is not None
        buf = bytearray()
        while True:
            b = self._serial.read(1)
            if not b:
                break
            buf.extend(b)
            if b == b"\x00":
                break
        return bytes(buf)

    def request(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        dst: Optional[int] = None,
        ack_requested: bool = True,
    ) -> MdpResponse:
        if not self._serial or not self._serial.is_open:
            self.connect()
        assert self._serial is not None

        with self._lock:
            seq = self._seq
            self._seq += 1
            payload = {"cmd": command, "params": params or {}}
            flags = MdpFlags.ACK_REQUESTED if ack_requested else 0
            frame = build_frame(
                msg_type=MdpMsgType.COMMAND,
                seq=seq,
                ack=0,
                flags=flags,
                src=self.src_endpoint,
                dst=dst if dst is not None else self.default_dst,
                payload=payload,
            )
            self._serial.write(frame)
            self._serial.flush()

            while True:
                incoming = self._read_until_delimiter()
                if not incoming:
                    raise TimeoutError(f"No MDP response on {self.port} for seq={seq}")
                header, body = parse_frame(incoming)
                if header.ack == seq or header.seq == seq:
                    return MdpResponse(
                        header={
                            "seq": header.seq,
                            "ack": header.ack,
                            "msg_type": header.msg_type,
                            "flags": header.flags,
                            "src": header.src,
                            "dst": header.dst,
                        },
                        payload=body,
                    )


def build_side_a_bridge(port: str, baudrate: int = 115200) -> MdpSerialBridge:
    return MdpSerialBridge(
        port=port,
        baudrate=baudrate,
        src_endpoint=MdpEndpoint.GATEWAY,
        default_dst=MdpEndpoint.SIDE_A,
    )


def build_side_b_bridge(port: str, baudrate: int = 115200) -> MdpSerialBridge:
    return MdpSerialBridge(
        port=port,
        baudrate=baudrate,
        src_endpoint=MdpEndpoint.GATEWAY,
        default_dst=MdpEndpoint.SIDE_B,
    )
