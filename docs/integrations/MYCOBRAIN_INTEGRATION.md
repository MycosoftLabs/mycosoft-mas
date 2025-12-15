# MycoBrain Integration Guide

## Overview

This guide describes how to integrate MycoBrain V1 devices with the Mycosoft Multi-Agent System (MAS), MINDEX, and NatureOS.

## Architecture

MycoBrain is a modular, dual-ESP32-S3 board with an integrated SX1262 LoRa module. The design splits functions into:

- **Side-A (Sensor MCU)**: Handles sensors, I²C scanning, analog inputs, and MOSFET control
- **Side-B (Router MCU)**: Handles UART↔LoRa routing, acknowledgements, and command channel

Telemetry, commands, and events are wrapped in **MDP v1 (Mycosoft Device Protocol)** using COBS framing and CRC16.

## Components

### 1. MDP v1 Protocol Library

Location: `mycosoft_mas/protocols/mdp_v1.py`

The MDP v1 library provides:
- COBS (Consistent Overhead Byte Stuffing) encoding/decoding
- CRC16 checksum calculation
- Frame encoding/decoding
- Message types: TELEMETRY, COMMAND, EVENT, ACK

**Usage:**
```python
from mycosoft_mas.protocols.mdp_v1 import MDPEncoder, MDPDecoder, MDPTelemetry, MDPCommand

# Encode telemetry
encoder = MDPEncoder()
telemetry = MDPTelemetry(
    ai1_voltage=3.3,
    temperature=25.5,
    humidity=60.0
)
frame_bytes = encoder.encode_telemetry(telemetry)

# Decode frame
decoder = MDPDecoder()
frame, parsed = decoder.decode(frame_bytes)
```

### 2. MycoBrain Device Agent

Location: `mycosoft_mas/agents/mycobrain/device_agent.py`

Manages connections to MycoBrain devices and handles:
- Device connections (UART or LoRa via Gateway)
- Command sending with retry logic
- Telemetry reception and processing
- Device state tracking

**Configuration:**
```yaml
device_id: "mycobrain-001"
serial_number: "MB001234"
connection_type: "uart"  # or "lora", "gateway"
uart_port: "/dev/ttyUSB0"
uart_baudrate: 115200
command_timeout: 5.0
max_retries: 3
```

**Usage:**
```python
from mycosoft_mas.agents.mycobrain import MycoBrainDeviceAgent

agent = MycoBrainDeviceAgent(
    agent_id="mycobrain-agent-001",
    name="MycoBrain Device Agent",
    config={
        "device_id": "mycobrain-001",
        "connection_type": "uart",
        "uart_port": "/dev/ttyUSB0"
    }
)

await agent.initialize()

# Send command
success = await agent.send_command(
    command_type="set_mosfet",
    parameters={"mosfet_index": 0, "state": True}
)

# Get device status
status = agent.get_status()
```

### 3. MycoBrain Ingestion Agent

Location: `mycosoft_mas/agents/mycobrain/ingestion_agent.py`

Handles telemetry ingestion from MycoBrain devices to MINDEX:
- Subscribes to telemetry from device agents
- Maps telemetry fields to MINDEX schema
- Ensures idempotent inserts using sequence numbers
- Batch processing for efficiency

**Configuration:**
```yaml
device_api_keys:
  mycobrain-001: "api_key_here"
device_locations:
  mycobrain-001:
    lat: 37.7749
    lon: -122.4194
batch_size: 10
batch_timeout: 5.0
```

**Usage:**
```python
from mycosoft_mas.agents.mycobrain import MycoBrainIngestionAgent

agent = MycoBrainIngestionAgent(
    agent_id="ingestion-agent",
    name="MycoBrain Ingestion Agent",
    config={
        "device_api_keys": {"mycobrain-001": "key123"},
        "batch_size": 10
    }
)

await agent.initialize()

# Ingest telemetry (typically called by device agent)
await agent.ingest_telemetry(
    device_id="mycobrain-001",
    telemetry=telemetry,
    sequence=123,
    timestamp=datetime.now()
)
```

## MINDEX Integration

### Device Schema

MycoBrain devices are registered in MINDEX with the following schema:

```sql
-- Device registration
INSERT INTO devices (
    device_id,
    device_type,
    serial_number,
    firmware_version,
    location
) VALUES (
    'mycobrain-001',
    'mycobrain',
    'MB001234',
    '1.0.0',
    ST_SetSRID(ST_MakePoint(-122.4194, 37.7749), 4326)
);
```

### Telemetry Schema

Telemetry data is stored with fields:
- `device_id`: Device identifier
- `timestamp`: ISO timestamp
- `sequence`: MDP sequence number (for idempotency)
- `analog_inputs`: AI1-AI4 voltages
- `environmental`: Temperature, humidity, pressure, gas resistance
- `mosfet_states`: MOSFET output states
- `i2c_sensors`: Detected I²C addresses
- `power`: Power status
- `device_metadata`: Firmware version, uptime

### API Methods

**Register Device:**
```python
from mycosoft_mas.integrations import UnifiedIntegrationManager

manager = UnifiedIntegrationManager()
await manager.initialize()

device = await manager.mindex.register_mycobrain_device(
    device_id="mycobrain-001",
    serial_number="MB001234",
    firmware_version="1.0.0",
    location={"lat": 37.7749, "lon": -122.4194}
)
```

**Ingest Telemetry:**
```python
telemetry_data = {
    "device_id": "mycobrain-001",
    "device_type": "mycobrain",
    "timestamp": "2024-01-01T12:00:00Z",
    "sequence": 123,
    "analog_inputs": {
        "ai1_voltage": 3.3,
        "ai2_voltage": 2.5,
        "ai3_voltage": 1.8,
        "ai4_voltage": 0.0
    },
    "environmental": {
        "temperature": 25.5,
        "humidity": 60.0,
        "pressure": 1013.25,
        "gas_resistance": 50000
    },
    "mosfet_states": {
        "mosfet_0": True,
        "mosfet_1": False,
        "mosfet_2": False,
        "mosfet_3": False
    }
}

result = await manager.mindex.ingest_mycobrain_telemetry(
    device_id="mycobrain-001",
    telemetry_data=telemetry_data,
    api_key="device_api_key"
)
```

## NatureOS Integration

### Device Registration

Register MycoBrain devices with NatureOS for dashboard visualization:

```python
device = await manager.natureos.register_mycobrain_device(
    device_id="mycobrain-001",
    serial_number="MB001234",
    name="Lab Sensor 1",
    firmware_version="1.0.0",
    location={"lat": 37.7749, "lon": -122.4194},
    metadata={
        "i2c_addresses": [0x76, 0x68],
        "analog_labels": ["AI1", "AI2", "AI3", "AI4"]
    }
)
```

### Sending Commands

Send commands to MycoBrain devices via NatureOS:

```python
result = await manager.natureos.send_mycobrain_command(
    device_id="mycobrain-001",
    command_type="set_mosfet",
    parameters={"mosfet_index": 0, "state": True}
)
```

### Retrieving Telemetry

Get telemetry data from NatureOS:

```python
telemetry = await manager.natureos.get_mycobrain_telemetry(
    device_id="mycobrain-001",
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now(),
    limit=100
)
```

## Mycorrhizae Protocol Integration

The Mycorrhizae Protocol Agent can be extended to use MycoBrain devices:

```python
from mycosoft_mas.agents.clusters.protocol_management.mycobrain_protocol_extension import (
    MycoBrainProtocolExtension
)

# Initialize extension
extension = MycoBrainProtocolExtension(protocol_agent)

# Subscribe device to protocol
await extension.subscribe_device_to_protocol(
    device_id="mycobrain-001",
    protocol_id="protocol-123"
)

# Create protocol step with MycoBrain interaction
step = await extension.create_mycobrain_protocol_step(
    step_name="Maintain Temperature",
    description="Keep temperature at 25°C using MycoBrain",
    device_id="mycobrain-001",
    temperature=25.0,
    humidity=60.0,
    mosfet_actions={0: True},  # Turn on MOSFET 0
    telemetry_interval=10,  # 10 seconds
    duration=60  # 60 minutes
)
```

## Device Setup Checklist

1. **Power the device**
   - Ensure proper power supply (5V via USB-C or external power)
   - Check power LED indicators

2. **Flash firmware**
   - Use PlatformIO to flash Side-A and Side-B firmware
   - Verify firmware versions match

3. **Connect to MAS**
   - Configure UART port or LoRa Gateway
   - Register device in MINDEX and NatureOS
   - Configure API keys for authentication

4. **Test connection**
   - Send test command (e.g., I²C scan)
   - Verify telemetry reception
   - Check MINDEX ingestion

5. **Configure telemetry interval**
   - Set appropriate telemetry interval (default: 10 seconds)
   - Monitor data flow

## Troubleshooting

### Device Not Responding

- Check UART connection and baudrate (115200)
- Verify firmware is flashed correctly
- Check power supply stability
- Review device logs

### Telemetry Not Appearing in MINDEX

- Verify API key is configured correctly
- Check sequence numbers for duplicates
- Review ingestion agent logs
- Verify MINDEX API endpoint is accessible

### Commands Not Executing

- Check device connection status
- Verify command format matches MDP v1 spec
- Review ACK messages
- Check retry logic and timeouts

### COBS/CRC Errors

- Ensure COBS framing is used (never send raw bytes)
- Verify CRC16 calculation matches firmware
- Check for data corruption in transmission
- Review frame boundaries

## Best Practices

1. **Always use COBS framing**: Never send raw MDP frames without COBS encoding
2. **Handle telemetry as best-effort**: Telemetry may be lost; use sequence numbers for idempotency
3. **Commands are reliable**: Commands use ACK + retry logic; wait for acknowledgment
4. **Monitor device health**: Track last telemetry time and connection status
5. **Use batch ingestion**: Batch telemetry records for efficient MINDEX ingestion
6. **Store telemetry locally**: Keep local copies of telemetry for debugging

## References

- [MycoBrain Hardware Documentation](https://github.com/MycosoftLabs/MycoBrain)
- [MDP v1 Protocol Specification](../protocols/MDP_V1_SPEC.md)
- [MINDEX API Documentation](../integrations/MINDEX_API.md)
- [NatureOS API Documentation](../integrations/NATUREOS_API.md)
