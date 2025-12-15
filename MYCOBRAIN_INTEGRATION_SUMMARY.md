# MycoBrain Integration Summary

## Overview

This document summarizes the MycoBrain V1 integration with the Mycosoft Multi-Agent System (MAS), MINDEX, and NatureOS. All required components have been implemented and documented.

## Components Created

### 1. MDP v1 Protocol Library
**Location:** `mycosoft_mas/protocols/mdp_v1.py`

- COBS (Consistent Overhead Byte Stuffing) encoding/decoding
- CRC16-CCITT checksum calculation
- Frame encoding/decoding
- Message types: TELEMETRY, COMMAND, EVENT, ACK
- Sequence number tracking for idempotency

**Key Classes:**
- `MDPFrame`: Frame structure with header, payload, CRC16
- `MDPTelemetry`: Telemetry data structure
- `MDPCommand`: Command structure
- `MDPEvent`: Event structure
- `MDPEncoder`: Encoder for outgoing messages
- `MDPDecoder`: Decoder for incoming messages

### 2. MycoBrain Device Agent
**Location:** `mycosoft_mas/agents/mycobrain/device_agent.py`

- Manages device connections (UART, LoRa, Gateway)
- Sends commands with retry logic and ACK handling
- Receives and processes telemetry
- Tracks device state and health
- Handles connection monitoring and reconnection

**Key Features:**
- Async command queue processing
- Sequence number tracking for duplicate detection
- Telemetry caching and event emission
- Connection health monitoring

### 3. MycoBrain Ingestion Agent
**Location:** `mycosoft_mas/agents/mycobrain/ingestion_agent.py`

- Subscribes to telemetry from device agents
- Maps telemetry fields to MINDEX schema
- Ensures idempotent inserts using sequence numbers
- Batch processing for efficiency
- API key authentication per device

**Key Features:**
- Batch buffering and processing
- Duplicate sequence detection
- MINDEX schema mapping
- Error handling and retry logic

### 4. MycoBrain Protocol Extension
**Location:** `mycosoft_mas/agents/clusters/protocol_management/mycobrain_protocol_extension.py`

- Extends Mycorrhizae Protocol Agent for MycoBrain devices
- Device subscription to protocols
- Telemetry-based protocol step monitoring
- Command sending during protocol execution
- Environmental condition checking

**Key Features:**
- Device-to-protocol subscriptions
- Telemetry cache for protocol steps
- Protocol step creation with device interaction
- Temperature/humidity condition monitoring

### 5. MINDEX Client Extensions
**Location:** `mycosoft_mas/integrations/mindex_client.py`

**New Methods:**
- `ingest_mycobrain_telemetry()`: Ingest telemetry with idempotency
- `register_mycobrain_device()`: Register device in MINDEX
- `get_mycobrain_devices()`: List registered devices
- `get_mycobrain_telemetry()`: Query telemetry data

### 6. NatureOS Client Extensions
**Location:** `mycosoft_mas/integrations/natureos_client.py`

**New Methods:**
- `register_mycobrain_device()`: Register device with NatureOS
- `send_mycobrain_command()`: Send commands via NatureOS
- `get_mycobrain_devices()`: List devices
- `get_mycobrain_telemetry()`: Get telemetry data

### 7. Device Coordinator Agent Update
**Location:** `mycosoft_mas/agents/clusters/device_management/device_coordinator_agent.py`

- Added `MYCOBRAIN` device type to `DeviceType` enum

## Documentation Created

### 1. Integration Guide
**Location:** `docs/integrations/MYCOBRAIN_INTEGRATION.md`

Comprehensive guide covering:
- Architecture overview
- Component usage examples
- MINDEX integration
- NatureOS integration
- Mycorrhizae Protocol integration
- Device setup checklist
- Troubleshooting guide
- Best practices

### 2. Protocol Specification
**Location:** `docs/protocols/MDP_V1_SPEC.md`

Complete protocol specification:
- Frame structure
- Message types
- COBS encoding algorithm
- CRC16 calculation
- Sequence numbers
- Error handling
- Code examples

### 3. Notion Knowledge Base Structure
**Location:** `docs/notion/MYCOBRAIN_KNOWLEDGE_BASE.md`

Template structure for Notion knowledge base:
- Database schema
- Page templates
- Properties and relations
- Views and filters
- Maintenance guidelines

## Dependencies Added

**requirements.txt:**
- `pyserial==3.5`: Serial port communication
- `pyserial-asyncio==0.6`: Async serial support

## Integration Flow

```
MycoBrain Device (Side-A/Side-B)
    ↓ (MDP v1 frames via UART/LoRa)
MycoBrain Device Agent
    ↓ (Telemetry events)
MycoBrain Ingestion Agent
    ↓ (MINDEX API)
MINDEX Database
    ↓ (Mycorrhizae Protocol)
NatureOS Dashboard
```

## Quick Start

### 1. Register Device

```python
from mycosoft_mas.integrations import UnifiedIntegrationManager

manager = UnifiedIntegrationManager()
await manager.initialize()

# Register in MINDEX
device = await manager.mindex.register_mycobrain_device(
    device_id="mycobrain-001",
    serial_number="MB001234",
    firmware_version="1.0.0",
    location={"lat": 37.7749, "lon": -122.4194}
)

# Register in NatureOS
device = await manager.natureos.register_mycobrain_device(
    device_id="mycobrain-001",
    serial_number="MB001234",
    name="Lab Sensor 1",
    firmware_version="1.0.0",
    location={"lat": 37.7749, "lon": -122.4194}
)
```

### 2. Initialize Device Agent

```python
from mycosoft_mas.agents.mycobrain import MycoBrainDeviceAgent

agent = MycoBrainDeviceAgent(
    agent_id="mycobrain-agent-001",
    name="MycoBrain Device Agent",
    config={
        "device_id": "mycobrain-001",
        "connection_type": "uart",
        "uart_port": "/dev/ttyUSB0",
        "uart_baudrate": 115200
    }
)

await agent.initialize()
```

### 3. Initialize Ingestion Agent

```python
from mycosoft_mas.agents.mycobrain import MycoBrainIngestionAgent

ingestion_agent = MycoBrainIngestionAgent(
    agent_id="ingestion-agent",
    name="MycoBrain Ingestion Agent",
    config={
        "device_api_keys": {
            "mycobrain-001": "your_api_key_here"
        },
        "device_locations": {
            "mycobrain-001": {"lat": 37.7749, "lon": -122.4194}
        },
        "batch_size": 10
    }
)

await ingestion_agent.initialize()
```

### 4. Send Commands

```python
# Via device agent
success = await agent.send_command(
    command_type="set_mosfet",
    parameters={"mosfet_index": 0, "state": True}
)

# Via NatureOS
result = await manager.natureos.send_mycobrain_command(
    device_id="mycobrain-001",
    command_type="set_mosfet",
    parameters={"mosfet_index": 0, "state": True}
)
```

## Next Steps

1. **Test Integration**
   - Connect a MycoBrain device
   - Verify telemetry ingestion
   - Test command sending
   - Check MINDEX and NatureOS dashboards

2. **Configure Production**
   - Set up API keys for devices
   - Configure device locations
   - Set up monitoring and alerts
   - Review telemetry intervals

3. **Populate Notion Knowledge Base**
   - Create database structure
   - Import hardware documentation
   - Add firmware changelogs
   - Document troubleshooting cases

4. **Website Updates**
   - Add MycoBrain product page
   - Create integration documentation
   - Update device listings
   - Add download links

## Key Design Decisions

1. **COBS Framing**: Always required for transmission to avoid null byte issues
2. **Sequence Numbers**: Used for idempotency in MINDEX ingestion
3. **Batch Processing**: Telemetry batched for efficient MINDEX writes
4. **ACK + Retry**: Commands use reliable delivery with retry logic
5. **Best-Effort Telemetry**: Telemetry may be lost; use sequence numbers for deduplication

## References

- Integration Guide: `docs/integrations/MYCOBRAIN_INTEGRATION.md`
- Protocol Spec: `docs/protocols/MDP_V1_SPEC.md`
- Notion Structure: `docs/notion/MYCOBRAIN_KNOWLEDGE_BASE.md`
- MINDEX Client: `mycosoft_mas/integrations/mindex_client.py`
- NatureOS Client: `mycosoft_mas/integrations/natureos_client.py`

## Support

For issues or questions:
1. Check troubleshooting section in integration guide
2. Review protocol specification
3. Check device agent logs
4. Review MINDEX/NatureOS API responses
