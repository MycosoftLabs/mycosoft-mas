# MycoBrain Brownout Power Fix

## Problem Identified

The board is stuck in a **brownout reset loop**:
```
E BOD: Brownout detector was triggered
ESP-ROM:esp32s3-20210327
rst:0x3 (RTC_SW_SYS_RST)
```

This happens at the ROM bootloader level - **BEFORE any firmware runs**. The firmware brownout disable code cannot help here.

## Root Cause

The diode bridge modification may have affected power delivery. The ESP32-S3 requires stable 3.3V power, derived from USB 5V through a regulator.

## Immediate Fixes to Try

### 1. Use a Powered USB Hub
A powered hub provides stable 5V at higher current:
- Connect board to powered USB hub (not directly to PC)
- Make sure the hub has its own power adapter

### 2. Try Different USB Port
Some PC USB ports are weak (especially front panel ports):
- Use a rear motherboard USB 3.0 port (usually blue)
- Avoid USB hubs without their own power

### 3. Use a Phone Charger USB Port
Many phone chargers can provide 2A+ at 5V:
- Connect a USB-A to USB-C cable to a phone charger
- Then connect the USB-C to a USB-C cable to the board

### 4. Disconnect BME688 Sensors
The sensors draw additional current during I2C operations:
- Unplug the BME688 sensor boards
- Try booting with nothing connected to the sensor headers

### 5. Check the Diode Bridge
If Garrett bridged a protection diode:
- The bridge may have too much resistance
- The solder joint may be cold/cracked
- Consider reverting the modification

### 6. External 5V Power
Bypass USB power entirely:
- Apply regulated 5V to the board's 5V input (if available)
- Use a lab power supply for testing

## Hardware Check Points

1. **Measure USB voltage at the board** - Should be 4.5V+ at the USB-C connector
2. **Measure 3.3V rail** - Should be stable 3.3V (±5%)
3. **Check for shorts** - Especially around the modified diode area
4. **Inspect solder joints** - Cold joints cause intermittent power issues

## What Won't Fix This

- **Firmware brownout disable**: Only works AFTER the ROM bootloader completes. The ROM has its own BOD that triggers first.
- **Different firmware**: The crash happens before firmware loads
- **Arduino IDE settings**: Settings don't affect ROM bootloader behavior

## Success Criteria

The board is working when you see:
```
====================================================================
  MycoBrain Side-A (Dual Mode)
  Mycosoft ESP32AB
====================================================================
```

Instead of the continuous `E BOD: Brownout detector was triggered` messages.

## If Nothing Works

The hardware may need physical repair:
1. Revert the diode bridge modification
2. Replace the voltage regulator if damaged
3. Check for damaged traces around the power input

