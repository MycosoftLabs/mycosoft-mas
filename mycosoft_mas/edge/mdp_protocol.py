"""
MDP v1 protocol helpers for on-device Jetson and gateway services.

Implements:
- Header packing/unpacking
- CRC16-CCITT-FALSE
- COBS encode/decode
- Frame build/parse with JSON payloads
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import struct
from typing import Any, Dict

MDP_MAGIC = 0xA15A
MDP_VERSION = 1
MDP_HEADER_STRUCT = struct.Struct("<HBBIIBBBB")


class MdpMsgType:
    TELEMETRY = 0x01
    COMMAND = 0x02
    ACK = 0x03
    EVENT = 0x05
    HELLO = 0x06


class MdpEndpoint:
    SIDE_A = 0xA1
    SIDE_B = 0xB1
    GATEWAY = 0xC0
    BCAST = 0xFF


class MdpFlags:
    ACK_REQUESTED = 0x01
    IS_ACK = 0x02
    IS_NACK = 0x04


@dataclass(slots=True)
class MdpHeader:
    magic: int
    version: int
    msg_type: int
    seq: int
    ack: int
    flags: int
    src: int
    dst: int
    rsv: int = 0


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def cobs_encode(data: bytes) -> bytes:
    out = bytearray()
    code_index = 0
    out.append(0)  # placeholder for first code
    code = 1
    for byte in data:
        if byte == 0:
            out[code_index] = code
            code_index = len(out)
            out.append(0)
            code = 1
        else:
            out.append(byte)
            code += 1
            if code == 0xFF:
                out[code_index] = code
                code_index = len(out)
                out.append(0)
                code = 1
    out[code_index] = code
    return bytes(out)


def cobs_decode(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        code = data[i]
        if code == 0:
            raise ValueError("invalid cobs code 0")
        i += 1
        end = i + code - 1
        if end > n:
            raise ValueError("invalid cobs length")
        out.extend(data[i:end])
        i = end
        if code != 0xFF and i < n:
            out.append(0)
    return bytes(out)


def build_frame(
    *,
    msg_type: int,
    seq: int,
    ack: int,
    flags: int,
    src: int,
    dst: int,
    payload: Dict[str, Any],
) -> bytes:
    header = MDP_HEADER_STRUCT.pack(
        MDP_MAGIC,
        MDP_VERSION,
        msg_type,
        seq,
        ack,
        flags,
        src,
        dst,
        0,
    )
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    frame_no_crc = header + payload_bytes
    crc = crc16_ccitt_false(frame_no_crc)
    raw = frame_no_crc + struct.pack("<H", crc)
    return cobs_encode(raw) + b"\x00"


def parse_frame(frame: bytes) -> tuple[MdpHeader, Dict[str, Any]]:
    if not frame:
        raise ValueError("empty frame")
    encoded = frame[:-1] if frame.endswith(b"\x00") else frame
    raw = cobs_decode(encoded)
    if len(raw) < MDP_HEADER_STRUCT.size + 2:
        raise ValueError("frame too short")

    body = raw[:-2]
    got_crc = struct.unpack("<H", raw[-2:])[0]
    expected_crc = crc16_ccitt_false(body)
    if got_crc != expected_crc:
        raise ValueError("crc mismatch")

    fields = MDP_HEADER_STRUCT.unpack(body[: MDP_HEADER_STRUCT.size])
    header = MdpHeader(*fields)
    if header.magic != MDP_MAGIC or header.version != MDP_VERSION:
        raise ValueError("invalid mdp header")

    payload_bytes = body[MDP_HEADER_STRUCT.size :]
    payload = json.loads(payload_bytes.decode("utf-8") or "{}")
    return header, payload
