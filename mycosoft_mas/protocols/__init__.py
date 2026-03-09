"""
Mycosoft Device Protocol Stack

Layer 3: Mycorrhizae  — Cloud/topic/schema contract (MQTT topics, Redis pub/sub)
Layer 2: MMP          — Normalized semantic envelope (mmp.py)
Layer 1: MDP          — Framed transport with COBS + CRC16 (mdp_v1.py)
Layer 0: Physical     — UART, USB-CDC, LoRa, Wi-Fi, BLE

Protocol Overview:
- Side-A (Sensor MCU): Handles sensors, I²C scanning, analog inputs, MOSFET control
- Side-B (Router MCU): Handles UART↔LoRa routing, acknowledgements, command channel
- Jetson (Optional Cortex): Camera, NLM, local LLM, IK, NaturePacket assembly
- MDP frames carry raw bytes; MMP envelopes carry semantic meaning
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

from .mmp import (
    MMPEnvelope,
    MMPKind,
    MMPProducer,
    MeasurementClass,
    CapabilityManifestEntry,
    CapabilityManifest,
    MMP_SCHEMA_VERSION,
    mdp_telemetry_to_mmp,
    fci_signal_to_mmp,
    nature_packet_to_mmp,
    validate_actuation_intent,
    create_command_envelope,
    ALLOWED_ACTUATION_INTENTS,
)

__all__ = [
    # MDP v1
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
    # MMP
    "MMPEnvelope",
    "MMPKind",
    "MMPProducer",
    "MeasurementClass",
    "CapabilityManifestEntry",
    "CapabilityManifest",
    "MMP_SCHEMA_VERSION",
    "mdp_telemetry_to_mmp",
    "fci_signal_to_mmp",
    "nature_packet_to_mmp",
    "validate_actuation_intent",
    "create_command_envelope",
    "ALLOWED_ACTUATION_INTENTS",
]
