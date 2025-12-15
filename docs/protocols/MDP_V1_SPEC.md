# MDP v1 Protocol Specification

## Overview

MDP v1 (Mycosoft Device Protocol version 1) is a binary protocol for communication with MycoBrain devices. It uses COBS (Consistent Overhead Byte Stuffing) framing and CRC16 for error detection.

## Frame Structure

### Binary Frame Format

```
[Header (13 bytes)] [Payload (variable)] [CRC16 (2 bytes)]
```

**Header:**
- Message Type (1 byte): 0x01=TELEMETRY, 0x02=COMMAND, 0x03=EVENT, 0x04=ACK
- Sequence (2 bytes): Big-endian sequence number (0-65535)
- Payload Length (2 bytes): Big-endian payload length
- Timestamp (8 bytes): Big-endian Unix timestamp (seconds)

**CRC16:**
- CRC16-CCITT checksum of header + payload

### COBS Encoding

After constructing the binary frame, it is COBS-encoded:
- No zero bytes in output
- Frame delimiter: 0x00
- Code bytes indicate distance to next zero

## Message Types

### TELEMETRY (0x01)

Telemetry data from Side-A (Sensor MCU).

**Payload (JSON):**
```json
{
  "ai1_voltage": 3.3,
  "ai2_voltage": 2.5,
  "ai3_voltage": 1.8,
  "ai4_voltage": 0.0,
  "temperature": 25.5,
  "humidity": 60.0,
  "pressure": 1013.25,
  "gas_resistance": 50000,
  "mosfet_states": [true, false, false, false],
  "i2c_addresses": [118, 104],
  "power_status": {},
  "firmware_version": "1.0.0",
  "uptime_seconds": 3600
}
```

### COMMAND (0x02)

Command to Side-A (via Side-B).

**Payload (JSON):**
```json
{
  "command_id": 1,
  "command_type": "set_mosfet",
  "parameters": {
    "mosfet_index": 0,
    "state": true
  }
}
```

**Command Types:**
- `set_mosfet`: Control MOSFET outputs
- `set_telemetry_interval`: Set telemetry transmission interval
- `i2c_scan`: Initiate I²C bus scan
- `reset`: Reset Side-A MCU
- `read_sensor`: Read specific sensor

### EVENT (0x03)

System events (errors, state changes).

**Payload (JSON):**
```json
{
  "event_type": "error",
  "severity": "warning",
  "message": "I²C timeout",
  "data": {}
}
```

### ACK (0x04)

Acknowledgment message.

**Payload (JSON):**
```json
{
  "success": true,
  "ack_sequence": 123
}
```

## Sequence Numbers

- Sequence numbers increment for each sent frame
- Wrap around at 65535
- Used for idempotency and duplicate detection
- ACK messages reference the sequence number of the acknowledged frame

## Timestamps

- Unix timestamp in seconds (big-endian 64-bit)
- Used for data provenance
- Device clock may drift; use sequence numbers for ordering

## CRC16 Calculation

CRC16-CCITT polynomial: 0x1021
Initial value: 0xFFFF

```python
def calculate_crc16(data: bytes) -> int:
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
```

## COBS Encoding Algorithm

1. Start with code byte placeholder (0x00)
2. For each byte in input:
   - If byte is 0x00: Write code byte, start new code byte
   - Else: Append byte, increment code
   - If code reaches 0xFF: Write code byte, start new code byte
3. Write final code byte
4. Append frame delimiter (0x00)

## Example

**Input frame (before COBS):**
```
01 00 01 00 0D 00 00 00 00 65 7C 8B 00 {"temp":25.5} A1 B2
```

**COBS-encoded:**
```
02 01 03 01 0D 04 00 00 00 65 7C 8B 00 {"temp":25.5} A1 B2 00
```

## Error Handling

- **CRC16 mismatch**: Discard frame, log error
- **Invalid COBS**: Discard frame, log error
- **Duplicate sequence**: Log warning, process or discard based on policy
- **Missing ACK**: Retry command (up to max_retries)

## Best Practices

1. Always use COBS encoding for transmission
2. Verify CRC16 before processing payload
3. Track sequence numbers for idempotency
4. Handle telemetry as best-effort (may be lost)
5. Commands require ACK; implement retry logic
6. Use timestamps for data provenance, sequence for ordering
