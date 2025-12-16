"""
Mycosoft Device Protocol (MDP) v1 Library

This module provides the MDP v1 protocol implementation for MycoBrain devices.
MDP v1 uses COBS (Consistent Overhead Byte Stuffing) framing and CRC16 for error detection.

Protocol Overview:
- Side-A (Sensor MCU): Handles sensors, I²C scanning, analog inputs, MOSFET control
- Side-B (Router MCU): Handles UART↔LoRa routing, acknowledgements, command channel
- Telemetry, commands, and events are wrapped in MDP v1 frames with COBS framing and CRC16

Message Types:
- TELEMETRY: Sensor data from Side-A
- COMMAND: Commands to Side-A (via Side-B)
- EVENT: System events (errors, state changes)
- ACK: Acknowledgment messages
"""

from .mdp_v1 import (
    MDPFrame,
    MDPMessageType,
    MDPCommand,
    MDPTelemetry,
    MDPEvent,
    MDPEncoder,
    MDPDecoder,
    encode_frame,
    decode_frame,
    calculate_crc16,
    cobs_encode,
    cobs_decode,
)

__all__ = [
    "MDPFrame",
    "MDPMessageType",
    "MDPCommand",
    "MDPTelemetry",
    "MDPEvent",
    "MDPEncoder",
    "MDPDecoder",
    "encode_frame",
    "decode_frame",
    "calculate_crc16",
    "cobs_encode",
    "cobs_decode",
]
