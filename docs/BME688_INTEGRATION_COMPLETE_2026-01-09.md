# BME688 Sensor Integration - Complete Documentation

**Date**: January 9, 2026  
**Author**: Claude AI + Human Review  
**Status**: ✅ COMPLETE AND TESTED

---

## Executive Summary

This document details the complete integration of dual BME688 environmental sensors with the MycoBrain Device Manager. The implementation includes firmware sensor support, Python service enhancements, Next.js API routes, and React UI components with anti-flicker optimizations.

---

## Hardware Configuration

### BME688 Sensors
| Sensor | I2C Address | Label | Description |
|--------|-------------|-------|-------------|
| BME688 #1 | 0x77 (119) | AMB | Ambient environment sensor |
| BME688 #2 | 0x76 (118) | ENV | Enclosure environment sensor |

### Pin Configuration
- **I2C SDA**: GPIO5
- **I2C SCL**: GPIO4
- **I2C Speed**: 100kHz (default)

### Address Modification
Each BME688 has a solder bridge to change its I2C address:
- Default address: 0x77
- Alternate address: 0x76 (bridge pads on breakout board)

---

## Firmware Implementation

### File: `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino`

### Dependencies
```cpp
#include <Adafruit_BME680.h>
#include <Adafruit_Sensor.h>
```

### Sensor Initialization
```cpp
Adafruit_BME680 bme1;  // Sensor at 0x77 (AMB)
Adafruit_BME680 bme2;  // Sensor at 0x76 (ENV)

static bool bme1_present = false;
static bool bme2_present = false;
static int bme688_count = 0;

void initBME688() {
  bme688_count = 0;
  
  // Initialize BME688 at 0x77 (AMB)
  if (bme1.begin(0x77, &Wire)) {
    bme1.setTemperatureOversampling(BME680_OS_8X);
    bme1.setHumidityOversampling(BME680_OS_2X);
    bme1.setPressureOversampling(BME680_OS_4X);
    bme1.setIIRFilterSize(BME680_FILTER_SIZE_3);
    bme1.setGasHeater(320, 150);  // 320°C for 150ms
    bme1_present = true;
    bme688_count++;
    Serial.println("[BME688] Initialized at 0x77 (AMB)");
  }
  
  // Initialize BME688 at 0x76 (ENV)
  if (bme2.begin(0x76, &Wire)) {
    bme2.setTemperatureOversampling(BME680_OS_8X);
    bme2.setHumidityOversampling(BME680_OS_2X);
    bme2.setPressureOversampling(BME680_OS_4X);
    bme2.setIIRFilterSize(BME680_FILTER_SIZE_3);
    bme2.setGasHeater(320, 150);
    bme2_present = true;
    bme688_count++;
    Serial.println("[BME688] Initialized at 0x76 (ENV)");
  }
}
```

### Sensor Reading
```cpp
void readBME688() {
  gSensor.valid = false;
  
  if (bme1_present && bme1.performReading()) {
    gSensor.bme1_temp = bme1.temperature;
    gSensor.bme1_humidity = bme1.humidity;
    gSensor.bme1_pressure = bme1.pressure / 100.0;
    gSensor.bme1_gas = bme1.gas_resistance;
    gSensor.valid = true;
  }
  
  if (bme2_present && bme2.performReading()) {
    gSensor.bme2_temp = bme2.temperature;
    gSensor.bme2_humidity = bme2.humidity;
    gSensor.bme2_pressure = bme2.pressure / 100.0;
    gSensor.bme2_gas = bme2.gas_resistance;
    gSensor.valid = true;
  }
}
```

### CLI Commands
| Command | Description | Output Format |
|---------|-------------|---------------|
| `scan` | Scan I2C bus and initialize sensors | JSON with i2c addresses |
| `sensors` | Read all sensor data | JSON with bme1/bme2 objects |
| `status` | Full device status including sensors | JSON telemetry |

### Sensors Command Output
```json
{
  "ok": true,
  "bme688_count": 2,
  "bme1": {
    "address": "0x77",
    "label": "AMB",
    "temp_c": 23.45,
    "humidity_pct": 47.8,
    "pressure_hpa": 1004.5,
    "gas_ohm": 85000
  },
  "bme2": {
    "address": "0x76",
    "label": "ENV",
    "temp_c": 24.12,
    "humidity_pct": 49.2,
    "pressure_hpa": 1004.2,
    "gas_ohm": 92000
  }
}
```

---

## Python Service Implementation

### File: `minimal_mycobrain.py`

### Key Endpoints

#### `/devices` - List Devices
Returns all connected devices with `connected` boolean flag:
```python
@app.get("/devices")
def list_devices():
    safe_devices = []
    for port, dev in devices.items():
        is_connected = False
        try:
            ser = dev.get("serial")
            if ser and ser.is_open:
                is_connected = True
        except:
            pass
        
        safe_devices.append({
            "device_id": dev.get("device_id"),
            "port": dev.get("port"),
            "status": dev.get("status"),
            "protocol": dev.get("protocol"),
            "connected": is_connected,
        })
    return {"devices": safe_devices, "count": len(devices)}
```

#### `/devices/{device_id}/cli` - Send CLI Commands
Sends text commands with 2-second wait for multi-line responses:
```python
@app.post("/devices/{device_id}/cli")
def send_cli_command(device_id: str, body: dict):
    cmd = body.get("command", "help")
    ser.reset_input_buffer()
    ser.write((cmd + "\n").encode())
    time.sleep(2.0)  # Wait for sensor reads
    lines = []
    while ser.in_waiting:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            lines.append(line)
    return {"command": cmd, "response": "\n".join(lines), "lines": lines, "status": "ok"}
```

---

## Next.js API Routes

### Sensors API: `/api/mycobrain/[port]/sensors/route.ts`

**Purpose**: Fetch sensor data from device and parse into structured format.

**Key Features**:
- Uses `/cli` endpoint for reliable command handling
- Parses JSON format from firmware
- Includes 1.5-second cache to prevent UI flicker
- Transforms field names for widget compatibility

**Field Mapping**:
| Firmware Field | API Field |
|----------------|-----------|
| `temp_c` | `temperature` |
| `humidity_pct` | `humidity` |
| `pressure_hpa` | `pressure` |
| `gas_ohm` | `gas_resistance` |

### Peripherals API: `/api/mycobrain/[port]/peripherals/route.ts`

**Purpose**: Scan I2C bus and return detected peripherals with widget metadata.

**Known Device Database**:
```typescript
const KNOWN_I2C_DEVICES: Record<number, { type: string; name: string; vendor: string }> = {
  0x76: { type: "bme688", name: "BME688", vendor: "Bosch" },
  0x77: { type: "bme688", name: "BME688", vendor: "Bosch" },
  0x3C: { type: "ssd1306", name: "SSD1306 OLED", vendor: "Generic" },
  0x29: { type: "vl53l0x", name: "VL53L0X LiDAR", vendor: "ST" },
  // ... more devices
}
```

**Widget Mapping**:
```typescript
const WIDGET_MAP: Record<string, WidgetConfig> = {
  bme688: {
    widget: "environmental_sensor",
    icon: "thermometer",
    controls: [],
    telemetryFields: ["temperature", "humidity", "pressure", "gas_resistance", "iaq"],
    charts: ["temperature", "humidity", "pressure"],
  },
  // ... more widget types
}
```

---

## React UI Components

### PeripheralGrid Component

**File**: `components/mycobrain/widgets/peripheral-widget.tsx`

**Anti-Flicker Features**:
1. **Sensor Data Caching**: Uses `lastSensorDataRef` to preserve data during refreshes
2. **Never Clear Peripherals**: Once detected, peripherals remain visible
3. **60-Second Scan Interval**: Reduced from 5 seconds to prevent serial overload

```typescript
// Cache last known sensor data to prevent blinking
const lastSensorDataRef = useRef<Record<string, Record<string, unknown>>>({})

useEffect(() => {
  if (sensorData && Object.keys(sensorData).length > 0) {
    lastSensorDataRef.current = { ...lastSensorDataRef.current, ...sensorData }
  }
}, [sensorData])

// Use merged sensor data (current + cached) to prevent blinking
const effectiveSensorData = { ...lastSensorDataRef.current, ...sensorData }
```

### EnvironmentalSensorWidget

**Displays**:
- Temperature (°C) - Orange theme
- Humidity (%) - Blue theme
- Pressure (hPa) - Purple theme
- Gas Resistance (kΩ) - Green theme

**Note**: IAQ (Indoor Air Quality) requires BSEC library from Bosch. Current implementation uses Adafruit BME680 library which only provides raw gas resistance.

### Sensor Banner (Device Manager Header)

**Anti-Flicker Implementation**:
```typescript
// Cache sensor count to prevent blinking during refreshes
const lastSensorCountRef = useRef<string | null>(null)

const sensorCount = (() => {
  let count: string | null = null
  
  if (device?.capabilities?.bme688_count) {
    count = `${device.capabilities.bme688_count}x BME688`
  }
  else if (device?.sensor_data?.bme688_1) {
    count = device.sensor_data?.bme688_2 ? "2x BME688" : "1x BME688"
  }
  // ... more checks
  
  if (count) lastSensorCountRef.current = count
  return count || lastSensorCountRef.current || "None"
})()
```

---

## useMycoBrain Hook Optimizations

**File**: `hooks/use-mycobrain.ts`

### Data Preservation
When fetching new device list, existing sensor data is preserved:
```typescript
setState((prev) => {
  const devices = (data.devices || []).map((d: any) => {
    const existing = prev.devices.find((e) => e.port === d.port)
    
    return {
      ...d,
      sensor_data: d.sensor_data || existing?.sensor_data || {},
      capabilities: d.capabilities || existing?.capabilities || {...},
      location: d.location || existing?.location || {...},
    }
  })
  // ...
})
```

### Refresh Intervals
| Component | Interval | Purpose |
|-----------|----------|---------|
| Device list | 15s | Check for new/disconnected devices |
| Sensor data | 15s | Update temperature/humidity readings |
| Peripheral scan | 60s | Detect new I2C devices |
| Overview widget | 30s | Dashboard summary refresh |

---

## Testing Results

### Terminal Verification
```powershell
# Sensors API
Invoke-RestMethod -Uri "http://localhost:3002/api/mycobrain/COM7/sensors"

# Response:
{
  "sensors": {
    "bme688_1": { "temperature": 23.2, "humidity": 47.4, "pressure": 1004.8, "gas_resistance": 71388 },
    "bme688_2": { "temperature": 23.5, "humidity": 48.5, "pressure": 1004.3, "gas_resistance": 110297 }
  }
}

# Peripherals API
Invoke-RestMethod -Uri "http://localhost:3002/api/mycobrain/COM7/peripherals"

# Response:
{
  "count": 2,
  "peripherals": [
    { "address": "0x76", "type": "bme688", "vendor": "Bosch", "product": "BME688" },
    { "address": "0x77", "type": "bme688", "vendor": "Bosch", "product": "BME688" }
  ]
}
```

### UI Verification
- ✅ Both BME688 sensors detected
- ✅ Temperature, Humidity, Pressure, Gas Resistance displayed
- ✅ No blinking during data refresh
- ✅ Sensor banner shows "2x BME688" consistently

---

## Troubleshooting

### Sensors Not Detected
1. Check I2C wiring (SDA → GPIO5, SCL → GPIO4)
2. Verify solder bridge configuration on sensor boards
3. Run `scan` command via terminal to see I2C addresses
4. Check power supply (BME688 requires 1.8-3.6V)

### Data Showing "--" in Widgets
1. Ensure MycoBrain service is running on port 8003
2. Check device is connected (green status indicator)
3. Wait 15 seconds for sensor polling cycle
4. Click "Rescan" button on Sensors tab

### Widget Blinking
If widgets still blink, increase intervals:
- Edit `peripheral-widget.tsx` line with `setInterval`
- Edit `mycobrain-device-manager.tsx` sensor polling interval

---

## Files Modified

### MAS Repository
- `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino`
- `minimal_mycobrain.py`
- `docs/BME688_INTEGRATION_COMPLETE_2026-01-09.md` (this file)

### Website Repository
- `app/api/mycobrain/[port]/sensors/route.ts`
- `app/api/mycobrain/[port]/peripherals/route.ts`
- `components/mycobrain/widgets/peripheral-widget.tsx`
- `components/mycobrain/mycobrain-device-manager.tsx`
- `components/mycobrain/mycobrain-overview-widget.tsx`
- `hooks/use-mycobrain.ts`

---

## Future Improvements

1. **BSEC Library Integration**: Add Bosch BSEC2 for IAQ, VOC, and CO2eq calculations
2. **Sensor Calibration**: Store calibration offsets per sensor
3. **Historical Data**: Store sensor readings in time-series database
4. **Alerts**: Configure thresholds for temperature/humidity alerts
5. **Multi-Device Support**: Aggregate sensor data from multiple MycoBrain devices
