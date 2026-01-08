# Dual-Mode Firmware Status

**Date**: January 6, 2026

## Current Configuration

### Hardware Setup
- **Both Boards**: USB connected to Side-B, Power connected to Side-A
- **Board 1 (COM4)**: Has 2x BME688 sensors
- **Board 2 (COM6)**: Second board

### Firmware Flashed
- **Side-B Firmware** flashed to both COM4 and COM6
- Side-B is a router that communicates with Side-A via UART
- Uses MDP v1 protocol (COBS framing + CRC16)

## Issue

The Side-B firmware is a **router** that expects to communicate with Side-A firmware via UART. Since:
- USB is on Side-B (where we flashed firmware)
- Power is on Side-A (needs its own firmware)

**We need BOTH firmwares:**
1. **Side-A firmware** on the Side-A MCU (power side) - handles sensors, NeoPixel, buzzer
2. **Side-B firmware** on the Side-B MCU (USB side) - routes commands/telemetry

## What "Dual Mode" Means

The user mentioned "dual mode firmware" that worked before. This likely means:
- A firmware that supports **both plaintext CLI commands** (like `coin`, `led rgb`, `bump`) AND
- JSON/MDP protocol for device manager integration

## Next Steps

1. **Find the working dual-mode firmware** that had:
   - Plaintext CLI: `coin`, `bump`, `1up`, `morgio`, `led rgb <r> <g> <b>`
   - NeoPixel control on GPIO15
   - Buzzer control on GPIO16
   - BME688 sensor support
   - Machine mode (NDJSON output)

2. **Flash to Side-A** (power side) - this is where sensors/NeoPixel/buzzer are

3. **Keep Side-B firmware** on Side-B (USB side) - this routes to Side-A

4. **Test via Device Manager** at http://localhost:3000

## Services Status

- ✅ MycoBrain Service: Running on port 8003 (2 devices connected: COM4, COM6)
- ⚠️ Website: Needs to be started persistently

## Arduino IDE Settings (from memory)

- USB CDC on boot: Enabled
- USB DFU on boot: Enabled  
- USB Mode: Hardware CDC and JTAG
- PSRAM: OPI PSRAM
- CPU Frequency: 240 MHz
- Flash Mode: QIO @ 80 MHz
- Flash Size: 16 MB
- Partition Scheme: 16MB flash, 3MB app / 9.9MB FATFS
- Upload Speed: 921600
- Baud Rate: 115200

## Hardware Pins

- NeoPixel: GPIO15
- Buzzer: GPIO16
- I2C SDA: GPIO5
- I2C SCL: GPIO4
