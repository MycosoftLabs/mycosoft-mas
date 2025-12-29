# CRITICAL FINDING - BME688 Power Draw

## The Problem
The bridged board is crashing **even with minimal firmware that doesn't initialize sensors**.

This means: **The BME688 sensors are drawing power even when not initialized!**

## Root Cause
BME688 sensors are **physically connected** to the board's power supply. Even if we don't initialize them in code, they still:
- Draw current from the 3.3V power rail
- Cause voltage drop
- Trigger brownout detector

## Solution: Remove BME688s Temporarily

### Test 1: Board Without Sensors
1. **Unplug both BME688 sensors** from the board
2. Upload minimal test firmware
3. Board should run stable without sensors
4. This confirms the sensors are the power problem

### Test 2: Board With One Sensor
1. Plug in **only ONE BME688 sensor**
2. Upload firmware
3. If it works, the board can handle one sensor
4. If it crashes, even one sensor is too much

### Test 3: External Power
1. If board has external power input, use it
2. Provide **5V @ 1A minimum** external supply
3. Keep USB for data only
4. Then plug in sensors - should work

## Why This Happens
- **USB power is limited** (500mA typical)
- **ESP32-S3 draws ~80-200mA**
- **Each BME688 draws ~10-20mA**
- **Two BME688s = 20-40mA additional**
- **Total = 100-240mA** (should be OK, but...)
- **Voltage drop under load** causes brownout

## The Bridge Modification
Garrett's bridge was to bypass a diode that was limiting power. But:
- Even with bridge, USB power may not be enough
- Bridge might have come loose
- Bridge might need to be re-soldered

## Immediate Action
**UNPLUG THE BME688 SENSORS** and test if board runs stable.

If board runs without sensors → **Sensors are the problem**
If board still crashes → **Hardware issue (bridge, power regulator, etc.)**

