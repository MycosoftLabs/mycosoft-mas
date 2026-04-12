from __future__ import annotations

from enum import IntEnum


class MDPv2MessageType(IntEnum):
    HEARTBEAT = 0x01
    SENSOR_TELEMETRY = 0x02
    COMMAND = 0x03
    ACK = 0x04

    ACOUSTIC_RAW = 0x20
    ACOUSTIC_FINGERPRINT = 0x21
    MAGNETIC_ANOMALY = 0x22
    OCEAN_ENVIRONMENT = 0x23
    TACTICAL_ASSESSMENT = 0x24
    ZEETA_BRIDGE = 0x25


MDP_V2_TYPE_NAME = {message_type.value: message_type.name for message_type in MDPv2MessageType}


def validate_message_type(value: int) -> bool:
    return value in MDP_V2_TYPE_NAME
