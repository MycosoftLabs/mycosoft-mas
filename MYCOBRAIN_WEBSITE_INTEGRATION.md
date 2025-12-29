# MycoBrain Website Integration - Complete

## Overview

This document describes the complete integration of MycoBrain devices into the NatureOS dashboard website. The integration provides real-time telemetry, device management, and control capabilities for MycoBrain V1 devices connected via USB-C serial ports.

## Components Created

### 1. USB Device Scanner (`scripts/scan_usb_devices.py`)
- Scans all USB serial ports on Windows
- Identifies ESP32 devices (VID 0x303A)
- Provides recommendations for Side-A and Side-B identification
- Outputs JSON for programmatic use

### 2. Enhanced MycoBrain Service (`services/mycobrain/mycobrain_dual_service.py`)
- **Version**: 2.1.0
- **Features**:
  - MDP v1 protocol support (COBS framing + CRC16)
  - Background telemetry reading threads
  - Device registration with MAC addresses
  - I2C sensor detection
  - Real-time telemetry caching
  - Command sending with MDP or JSON fallback

**Key Endpoints**:
- `GET /health` - Service health check
- `GET /devices` - List connected devices
- `GET /ports` - Scan available serial ports
- `POST /devices/connect/{port}` - Connect to device (Side-A or Side-B)
- `POST /devices/{device_id}/disconnect` - Disconnect device
- `GET /devices/{device_id}/status` - Get device status
- `GET /devices/{device_id}/telemetry` - Get latest telemetry
- `POST /devices/{device_id}/command` - Send command to device

### 3. Next.js API Routes

#### `/app/api/mycobrain/devices/route.ts`
- Device management (list, connect, disconnect, scan ports)
- Proxies requests to MycoBrain service

#### `/app/api/mycobrain/telemetry/route.ts`
- Fetch real-time telemetry from devices
- 2-second cache revalidation

#### `/app/api/mycobrain/command/route.ts`
- Send commands to devices (LEDs, buzzer, MOSFETs, I2C scan)
- Supports MDP protocol

#### `/app/api/mycobrain/ports/route.ts`
- Scan for available serial ports
- Fallback to Python script if service unavailable

### 4. React Components

#### `components/mycobrain-device-manager.tsx`
Complete device management UI with:
- **Device List**: Shows all connected MycoBrain devices
- **Port Scanner**: Lists available COM ports for connection
- **Telemetry Display**: Real-time sensor data (temperature, humidity, pressure, gas resistance)
- **Device Controls**:
  - NeoPixel LED control (4 LEDs, individual or all off)
  - Buzzer control (beep/off)
  - MOSFET outputs (4 channels, on/off toggle)
  - I2C bus scanning

### 5. Updated NatureOS Devices Page
- Added "MycoBrain Devices" tab
- Integrated MycoBrainDeviceManager component
- Maintains existing network device and client views

## Device Registration & Identification

### MAC Address
- Devices are queried for MAC address on connection
- MAC address is stored with device metadata
- Used for device identification and future reconnection

### I2C Sensor Detection
- BME688 sensors are detected via I2C scan
- I2C addresses are displayed in device info
- Telemetry includes detected I2C addresses

### Side-A vs Side-B
- Side-A: Sensor MCU (handles sensors, I2C, analog inputs, MOSFETs)
- Side-B: Router MCU (handles UART routing, LoRa, acknowledgements)
- Devices can be manually assigned or auto-detected

## Telemetry Data Structure

```typescript
{
  device_id: string;
  side: "side-a" | "side-b";
  timestamp: string;
  telemetry: {
    temperature?: number;        // BME688
    humidity?: number;            // BME688
    pressure?: number;            // BME688
    gas_resistance?: number;      // BME688
    ai1_voltage?: number;         // Analog input 1
    ai2_voltage?: number;         // Analog input 2
    ai3_voltage?: number;         // Analog input 3
    ai4_voltage?: number;         // Analog input 4
    mosfet_states?: boolean[];     // MOSFET 0-3 states
    i2c_addresses?: number[];    // Detected I2C devices
    firmware_version?: string;
    uptime_seconds?: number;
  }
}
```

## Command Types

### LED Control
```json
{
  "command": "set_neopixel",
  "parameters": {
    "led_index": 0,
    "r": 255,
    "g": 0,
    "b": 255
  }
}
```

### Buzzer Control
```json
{
  "command": "set_buzzer",
  "parameters": {
    "frequency": 1000,
    "duration": 200
  }
}
```

### MOSFET Control
```json
{
  "command": "set_mosfet",
  "parameters": {
    "mosfet_index": 0,
    "state": true
  }
}
```

### I2C Scan
```json
{
  "command": "i2c_scan",
  "parameters": {}
}
```

## Setup Instructions

### 1. Start MycoBrain Service
```bash
cd services/mycobrain
python mycobrain_dual_service.py
```

Or set environment variable:
```bash
export MYCOBRAIN_SERVICE_PORT=8003
```

### 2. Connect Devices
1. Plug in both USB-C cables (Side-A and Side-B)
2. Open NatureOS dashboard → Devices → MycoBrain Devices tab
3. Click "Scan Ports" to see available COM ports
4. Click "Connect Side-A" or "Connect Side-B" for each port

### 3. View Telemetry
- Telemetry updates automatically every 2 seconds
- Select a device to see detailed telemetry and controls

### 4. Control Devices
- Use the control panel to:
  - Change NeoPixel LED colors
  - Trigger buzzer
  - Toggle MOSFET outputs
  - Scan I2C bus

## Troubleshooting

### COM Port Not Detected
- Run `python scripts/scan_usb_devices.py` to see all ports
- Check Device Manager for COM port assignments
- Ensure USB drivers are installed (CH340/CP2102 for ESP32)

### Connection Fails
- Check if port is already in use (close other serial monitors)
- Verify baud rate (default: 115200)
- Try different USB ports/cables

### No Telemetry
- Verify device firmware is sending MDP telemetry frames
- Check serial connection is stable
- Review service logs for errors

### I2C Sensors Not Detected
- Ensure BME688 sensors are properly connected
- Run I2C scan command from dashboard
- Check I2C address (BME688 typically 0x76 or 0x77)

## Future Enhancements

1. **Gateway Integration**: Support for LoRa gateway connections
2. **Multi-Device Management**: Handle multiple MycoBrain devices simultaneously
3. **Data Logging**: Store telemetry history in database
4. **Alerts & Notifications**: Set thresholds for sensor values
5. **Protocol Execution**: Integrate with Mycorrhizae Protocol for automated workflows
6. **N8n Workflows**: Connect device events to N8n automation

## Docker/N8n Integration

The MycoBrain service can be integrated with Docker and N8n workflows:

1. **Docker**: Add service to `docker-compose.yml`:
```yaml
mycobrain-service:
  build: ./services/mycobrain
  ports:
    - "8003:8003"
  volumes:
    - /dev:/dev  # For serial port access
  devices:
    - /dev/ttyUSB0:/dev/ttyUSB0
    - /dev/ttyUSB1:/dev/ttyUSB1
```

2. **N8n**: Create workflows that:
   - Monitor telemetry values
   - Trigger actions based on thresholds
   - Send commands to devices
   - Log data to databases

## Environment Variables

- `MYCOBRAIN_SERVICE_URL`: URL of MycoBrain service (default: http://localhost:8003)
- `MYCOBRAIN_SERVICE_PORT`: Port for service (default: 8003)

## API Documentation

Full API documentation available at:
- Service: `http://localhost:8003/docs` (FastAPI Swagger UI)
- Website API: `/api/mycobrain/*` routes

## Notes

- MDP protocol is preferred but JSON fallback is available
- Telemetry is cached for 2 seconds to reduce API calls
- Background threads handle continuous data reading
- Device connections persist until explicitly disconnected
- MAC addresses are used for device identification and registration

