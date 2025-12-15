"""
MDP v1 Protocol Implementation

Mycosoft Device Protocol version 1 implementation with COBS framing and CRC16.

Protocol Specification:
- Frame format: [COBS-encoded payload with CRC16]
- Message types: TELEMETRY, COMMAND, EVENT, ACK
- Sequence numbers for idempotency
- Timestamps for data provenance
"""

import struct
import logging
from enum import IntEnum
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class MDPMessageType(IntEnum):
    """MDP v1 message types."""
    TELEMETRY = 0x01
    COMMAND = 0x02
    EVENT = 0x03
    ACK = 0x04


@dataclass
class MDPFrame:
    """MDP v1 frame structure."""
    message_type: MDPMessageType
    sequence: int
    timestamp: int  # Unix timestamp in seconds
    payload: bytes
    crc16: int = 0
    
    def to_bytes(self) -> bytes:
        """Convert frame to bytes (before COBS encoding)."""
        header = struct.pack(
            "!BHHQ",
            self.message_type.value,
            self.sequence,
            len(self.payload),
            self.timestamp
        )
        frame = header + self.payload
        self.crc16 = calculate_crc16(frame)
        return frame + struct.pack("!H", self.crc16)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "MDPFrame":
        """Create frame from bytes (after COBS decoding)."""
        if len(data) < 15:  # Minimum frame size
            raise ValueError(f"Frame too short: {len(data)} bytes")
        
        # Verify CRC16
        frame_data = data[:-2]
        crc16_received = struct.unpack("!H", data[-2:])[0]
        crc16_calculated = calculate_crc16(frame_data)
        
        if crc16_received != crc16_calculated:
            raise ValueError(f"CRC16 mismatch: received {crc16_received:04x}, calculated {crc16_calculated:04x}")
        
        # Parse header
        message_type_val, sequence, payload_len, timestamp = struct.unpack("!BHHQ", frame_data[:13])
        
        if len(frame_data) < 13 + payload_len:
            raise ValueError(f"Payload length mismatch: expected {payload_len}, got {len(frame_data) - 13}")
        
        payload = frame_data[13:13 + payload_len]
        
        return cls(
            message_type=MDPMessageType(message_type_val),
            sequence=sequence,
            timestamp=timestamp,
            payload=payload,
            crc16=crc16_received
        )


@dataclass
class MDPTelemetry:
    """Telemetry message from Side-A."""
    # Analog inputs (AI1-AI4)
    ai1_voltage: float = 0.0
    ai2_voltage: float = 0.0
    ai3_voltage: float = 0.0
    ai4_voltage: float = 0.0
    
    # BME688 sensor readings
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    gas_resistance: Optional[float] = None
    
    # MOSFET states (0-3)
    mosfet_states: List[bool] = None
    
    # I²C sensor addresses detected
    i2c_addresses: List[int] = None
    
    # Power status
    power_status: Dict[str, Any] = None
    
    # Metadata
    firmware_version: Optional[str] = None
    uptime_seconds: Optional[int] = None
    
    def __post_init__(self):
        if self.mosfet_states is None:
            self.mosfet_states = [False] * 4
        if self.i2c_addresses is None:
            self.i2c_addresses = []
        if self.power_status is None:
            self.power_status = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MDPTelemetry":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class MDPCommand:
    """Command message to Side-A."""
    command_id: int
    command_type: str  # "set_mosfet", "set_telemetry_interval", "i2c_scan", "reset", etc.
    parameters: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MDPCommand":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class MDPEvent:
    """Event message from device."""
    event_type: str  # "error", "state_change", "sensor_detected", etc.
    severity: str  # "info", "warning", "error", "critical"
    message: str
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MDPEvent":
        """Create from dictionary."""
        return cls(**data)


class MDPEncoder:
    """Encoder for MDP v1 messages."""
    
    def __init__(self):
        self.sequence_counter = 0
    
    def encode_telemetry(self, telemetry: MDPTelemetry) -> bytes:
        """Encode telemetry message."""
        import json
        payload = json.dumps(telemetry.to_dict()).encode('utf-8')
        frame = MDPFrame(
            message_type=MDPMessageType.TELEMETRY,
            sequence=self.sequence_counter,
            timestamp=int(datetime.now().timestamp()),
            payload=payload
        )
        self.sequence_counter = (self.sequence_counter + 1) % 65536
        frame_bytes = frame.to_bytes()
        return cobs_encode(frame_bytes)
    
    def encode_command(self, command: MDPCommand) -> bytes:
        """Encode command message."""
        import json
        payload = json.dumps(command.to_dict()).encode('utf-8')
        frame = MDPFrame(
            message_type=MDPMessageType.COMMAND,
            sequence=self.sequence_counter,
            timestamp=int(datetime.now().timestamp()),
            payload=payload
        )
        self.sequence_counter = (self.sequence_counter + 1) % 65536
        frame_bytes = frame.to_bytes()
        return cobs_encode(frame_bytes)
    
    def encode_event(self, event: MDPEvent) -> bytes:
        """Encode event message."""
        import json
        payload = json.dumps(event.to_dict()).encode('utf-8')
        frame = MDPFrame(
            message_type=MDPMessageType.EVENT,
            sequence=self.sequence_counter,
            timestamp=int(datetime.now().timestamp()),
            payload=payload
        )
        self.sequence_counter = (self.sequence_counter + 1) % 65536
        frame_bytes = frame.to_bytes()
        return cobs_encode(frame_bytes)
    
    def encode_ack(self, sequence: int, success: bool = True) -> bytes:
        """Encode acknowledgment message."""
        import json
        payload = json.dumps({"success": success, "ack_sequence": sequence}).encode('utf-8')
        frame = MDPFrame(
            message_type=MDPMessageType.ACK,
            sequence=self.sequence_counter,
            timestamp=int(datetime.now().timestamp()),
            payload=payload
        )
        self.sequence_counter = (self.sequence_counter + 1) % 65536
        frame_bytes = frame.to_bytes()
        return cobs_encode(frame_bytes)


class MDPDecoder:
    """Decoder for MDP v1 messages."""
    
    def __init__(self):
        self.received_sequences: set = set()
    
    def decode(self, data: bytes) -> Tuple[MDPFrame, Dict[str, Any]]:
        """Decode COBS-encoded frame and parse payload."""
        # Decode COBS
        frame_bytes = cobs_decode(data)
        
        # Parse frame
        frame = MDPFrame.from_bytes(frame_bytes)
        
        # Check for duplicate sequence numbers
        if frame.sequence in self.received_sequences:
            logger.warning(f"Duplicate sequence number: {frame.sequence}")
        else:
            self.received_sequences.add(frame.sequence)
            # Keep only last 1000 sequences
            if len(self.received_sequences) > 1000:
                self.received_sequences = set(list(self.received_sequences)[-1000:])
        
        # Parse payload based on message type
        import json
        payload_dict = json.loads(frame.payload.decode('utf-8'))
        
        if frame.message_type == MDPMessageType.TELEMETRY:
            parsed = MDPTelemetry.from_dict(payload_dict)
        elif frame.message_type == MDPMessageType.COMMAND:
            parsed = MDPCommand.from_dict(payload_dict)
        elif frame.message_type == MDPMessageType.EVENT:
            parsed = MDPEvent.from_dict(payload_dict)
        else:
            parsed = payload_dict
        
        return frame, parsed


def calculate_crc16(data: bytes) -> int:
    """Calculate CRC16-CCITT checksum."""
    crc = 0xFFFF
    polynomial = 0x1021
    
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFFFF
    
    return crc


def cobs_encode(data: bytes) -> bytes:
    """
    Encode data using COBS (Consistent Overhead Byte Stuffing).
    
    COBS encoding ensures no zero bytes in the output, making it suitable
    for protocols that use null bytes as delimiters.
    """
    if not data:
        return bytes([0x01, 0x00])
    
    output = bytearray()
    output.append(0x00)  # Placeholder for first code byte
    code_index = 0
    code = 0x01
    
    for byte in data:
        if byte == 0x00:
            output[code_index] = code
            code_index = len(output)
            output.append(0x00)  # Placeholder
            code = 0x01
        else:
            output.append(byte)
            code += 1
            if code == 0xFF:
                output[code_index] = code
                code_index = len(output)
                output.append(0x00)  # Placeholder
                code = 0x01
    
    output[code_index] = code
    output.append(0x00)  # Frame delimiter
    
    return bytes(output)


def cobs_decode(data: bytes) -> bytes:
    """
    Decode COBS-encoded data.
    
    Raises ValueError if data is invalid.
    """
    if len(data) < 2:
        raise ValueError("COBS data too short")
    
    if data[-1] != 0x00:
        raise ValueError("COBS frame delimiter missing")
    
    output = bytearray()
    i = 0
    
    while i < len(data) - 1:  # Exclude trailing delimiter
        code = data[i]
        i += 1
        
        if code == 0x00:
            raise ValueError("Invalid COBS code byte: 0x00")
        
        # Copy the next (code - 1) bytes
        for _ in range(code - 1):
            if i >= len(data) - 1:
                raise ValueError("COBS data truncated")
            output.append(data[i])
            i += 1
        
        # If code is not 0xFF and we're not at the end, insert a zero
        if code < 0xFF and i < len(data) - 1:
            output.append(0x00)
    
    return bytes(output)


def encode_frame(message_type: MDPMessageType, payload: Dict[str, Any], sequence: int = 0) -> bytes:
    """Convenience function to encode a frame."""
    import json
    payload_bytes = json.dumps(payload).encode('utf-8')
    frame = MDPFrame(
        message_type=message_type,
        sequence=sequence,
        timestamp=int(datetime.now().timestamp()),
        payload=payload_bytes
    )
    frame_bytes = frame.to_bytes()
    return cobs_encode(frame_bytes)


def decode_frame(data: bytes) -> Tuple[MDPFrame, Dict[str, Any]]:
    """Convenience function to decode a frame."""
    decoder = MDPDecoder()
    return decoder.decode(data)
