# MycoBoard Development Roadmap

> **Future Plans and Development Priorities**

This document outlines planned features, improvements, and development priorities for the MycoBoard hardware and software ecosystem.

## Current Status (December 2024)

### ✅ Completed

| Feature | Status | Notes |
|---------|--------|-------|
| ESP32-S3 firmware with BME688 | ✅ Complete | Dual sensor support |
| Serial CLI over USB-CDC | ✅ Complete | 115200 baud |
| NeoPixel LED control | ✅ Complete | GPIO 15, FastLED |
| Piezo buzzer sounds | ✅ Complete | GPIO 46, PWM |
| MycoBrain service (Python) | ✅ Complete | Port 8003 |
| Website Device Manager | ✅ Complete | /natureos/devices |
| Docker containerization | ✅ Complete | Always-on stack |
| USB passthrough (Windows/WSL2) | ✅ Complete | usbipd-win |
| Diagnostics API | ✅ Complete | Board ID, I2C scan |
| MINDEX telemetry logging | ✅ Complete | For MYCA learning |

### ⚠️ Partially Complete

| Feature | Status | Notes |
|---------|--------|-------|
| LoRa radio integration | ⚠️ Firmware only | Not exposed via API |
| Communication tab UI | ⚠️ UI only | Backend not connected |
| Analytics charts | ⚠️ Placeholder | No historical data |

## Q1 2025 Priorities

### 1. LoRa Communication (High Priority)

**Goal:** Enable Side-A ↔ Side-B communication over LoRa radio.

**Tasks:**
- [ ] Add LoRa initialization to firmware
- [ ] Implement `lora send <message>` CLI command
- [ ] Implement `lora status` CLI command
- [ ] Add `/devices/{id}/lora` API endpoints
- [ ] Connect Communication tab to real LoRa data
- [ ] Test range and reliability

**Technical Details:**
```
Frequency: 915 MHz (US)
Spreading Factor: SF7 (fast) to SF12 (long range)
Bandwidth: 125 kHz
TX Power: 14-20 dBm
Chip: SX1262
```

**Firmware Commands (Planned):**
```
lora init              # Initialize LoRa radio
lora status            # Get LoRa status
lora send <msg>        # Send message to peer
lora power <dBm>       # Set TX power
lora sf <7-12>         # Set spreading factor
lora listen            # Enable receive mode
```

### 2. Analytics & Historical Data

**Goal:** Store and visualize sensor data over time.

**Tasks:**
- [ ] Add sensor history storage to MINDEX
- [ ] Create `/telemetry/history` API endpoint
- [ ] Add time-series charts to Analytics tab
- [ ] Implement configurable retention period
- [ ] Add data export (CSV, JSON)

**Data Points to Store:**
- Temperature (AMB, ENV)
- Humidity (AMB, ENV)
- Pressure (AMB, ENV)
- IAQ (AMB, ENV)
- CO2 equivalent
- VOC levels

### 3. ESP-NOW Mesh Networking

**Goal:** Local mesh networking without WiFi infrastructure.

**Tasks:**
- [ ] Implement ESP-NOW peer discovery
- [ ] Add mesh routing protocol
- [ ] Create mesh visualization in UI
- [ ] Support up to 20 nodes

## Q2 2025 Priorities

### 4. WiFi & Bluetooth Integration

**Goal:** Add wireless connectivity options.

**WiFi Tasks:**
- [ ] Add WiFi credentials storage
- [ ] Implement MQTT client
- [ ] Add cloud connectivity option
- [ ] Support OTA firmware updates

**Bluetooth Tasks:**
- [ ] Enable BLE server mode
- [ ] Create mobile app for configuration
- [ ] Implement BLE sensor streaming

### 5. Additional Sensors

**Goal:** Support more I2C sensors.

**Planned Sensors:**
| Sensor | Address | Purpose |
|--------|---------|---------|
| SCD40 | 0x62 | CO2 sensor |
| VEML7700 | 0x10 | Light level |
| VL53L0X | 0x29 | Distance/presence |
| MPU6050 | 0x68 | Accelerometer |

**Tasks:**
- [ ] Add sensor auto-detection
- [ ] Create modular sensor driver framework
- [ ] Update diagnostics for new sensors
- [ ] Add sensor configuration UI

### 6. MycoBoard v2 Hardware

**Goal:** Improved hardware design.

**Planned Changes:**
- External antenna connector for LoRa
- Screw terminals for external sensors
- Battery connector (LiPo)
- Solar charging support
- Weatherproof enclosure option

## Q3-Q4 2025 Priorities

### 7. Multi-Board Orchestration

**Goal:** Manage fleet of MycoBoards.

**Tasks:**
- [ ] Board discovery and registration
- [ ] Centralized configuration management
- [ ] Group command broadcasting
- [ ] Alert and notification system

### 8. AI Integration (MYCA)

**Goal:** AI-powered environmental monitoring.

**Tasks:**
- [ ] Train models on sensor patterns
- [ ] Implement anomaly detection
- [ ] Add predictive alerts
- [ ] Voice control via MYCA

### 9. Mobile Application

**Goal:** Native iOS/Android app.

**Tasks:**
- [ ] React Native app development
- [ ] Push notifications
- [ ] Offline mode with BLE
- [ ] Widget support

## Technical Debt

### Code Improvements Needed

1. **MycoBrain Service**
   - [ ] Add connection retry logic
   - [ ] Implement proper error boundaries
   - [ ] Add request rate limiting
   - [ ] Improve logging (structured JSON)

2. **Website**
   - [ ] Extract device hooks to separate package
   - [ ] Add unit tests for API routes
   - [ ] Implement proper loading states
   - [ ] Add error recovery UI

3. **Firmware**
   - [ ] Add watchdog timer
   - [ ] Implement config persistence (NVS)
   - [ ] Add OTA update support
   - [ ] Improve power management

### Documentation Needed

- [ ] API reference (OpenAPI/Swagger)
- [ ] Firmware development guide
- [ ] Hardware assembly guide
- [ ] Deployment checklist

## Success Metrics

### Current Baseline

| Metric | Current | Target |
|--------|---------|--------|
| Sensor update latency | ~2s | <500ms |
| Service uptime | 99% | 99.9% |
| LoRa range | N/A | 1km |
| Connected devices | 1 | 10+ |
| Historical data | None | 30 days |

### Q1 2025 Goals

- [ ] LoRa communication working between 2 boards
- [ ] Analytics showing 7-day history
- [ ] Service uptime >99.5%
- [ ] Zero UI errors in console

## Contributing

### How to Contribute

1. Check this roadmap for planned work
2. Create an issue for new features
3. Submit PRs against `develop` branch
4. Follow code style guidelines

### Team Assignments

| Area | Owner |
|------|-------|
| Hardware | Alberto |
| Firmware | Garrett |
| MycoBrain Service | Chris |
| Website/UI | Morgan |
| MINDEX/AI | Team |

## Related Documents

- [MycoBoard Technical Reference](./MYCOBOARD_TECHNICAL_REFERENCE.md)
- [System Integration Guide](./SYSTEM_INTEGRATION_GUIDE.md)
- [MycoBrain Service README](../services/mycobrain/README.md)

---

*Last Updated: December 2024*
*Document Owner: Engineering Team*
