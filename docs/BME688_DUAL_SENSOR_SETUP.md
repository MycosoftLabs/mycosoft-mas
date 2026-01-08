# BME688 Dual Sensor Setup - Garret's Modification

## Overview

The MycoBrain ESP32-S3 supports **TWO** BME688 environmental sensors simultaneously on the same I2C bus. This requires a hardware modification to change the I2C address of one sensor.

---

## The Problem

### Default Behavior:
- **ALL** BME688 sensors come with I2C address `0x77` by default
- If you connect two BME688s to the same I2C bus without modification:
  - ❌ **I2C address conflict**
  - ❌ **Only one sensor responds**
  - ❌ **Board firmware cannot initialize both sensors**
  - ❌ **BSEC library fails or crashes**
  - ❌ **Bootloop may occur**

---

## The Solution: Garret's Solder Bridge Modification

### What Garret Did:

On **ONE** of the two BME688 breakout boards, he added a solder bridge to change its I2C address from `0x77` to `0x76`.

### How to Do It:

#### 1. Identify the Address Select Jumper

Most BME688 breakout boards have:
- Two solder pads labeled `ADDR`, `ADR`, `A0`, or similar
- Usually located near the BME688 chip
- Pads are typically 1-2mm apart

#### 2. Apply Solder Bridge

**For ONE sensor only** (the ENV sensor):
1. Clean the solder pads with isopropyl alcohol
2. Apply flux to both pads
3. Use a soldering iron to bridge the two pads with solder
4. Create a small solder blob that connects both pads
5. Verify continuity with multimeter (optional)

#### 3. Label the Modified Sensor

- Mark the modified sensor as **"ENV - 0x76"**
- Mark the unmodified sensor as **"AMB - 0x77"**

---

## Verification

### Test with I2C Scanner:

After connecting both sensors, run the `scan` command in the firmware:

```
Expected output:
I2C scan:
  0x76 (BME688)
  0x77 (BME688)
count: 2
```

### If You See Only ONE Address:

1. Check solder bridge is properly connected
2. Verify both sensors have power (3.3V and GND)
3. Check I2C connections (SDA to GPIO5, SCL to GPIO4)
4. Try scanning with a standalone I2C scanner sketch

---

## Sensor Configuration in Firmware

```cpp
// Two fixed sensor slots by I2C address
static SensorSlot S_AMB = { "AMB", 0x77 };  // Unmodified sensor
static SensorSlot S_ENV = { "ENV", 0x76 };  // Garret's modified sensor
```

### BSEC2 Library Requirements:

Each BME688 sensor requires:
- **Separate BSEC2 instance** (`Bsec2` object)
- **Separate memory buffer** (`uint8_t mem[BSEC_INSTANCE_SIZE]`)
- **Separate initialization** (`bsec.begin()`)
- **Separate callbacks** (`checkSensorResult_AMB()`, `checkSensorResult_ENV()`)

### Why Separate Instances?

The BSEC2 library maintains complex state:
- Sensor calibration data
- Historical readings for algorithm
- Air quality calculation state
- Gas sensor baseline

**Sharing BSEC state between sensors causes:**
- ❌ Incorrect IAQ calculations
- ❌ Wrong CO2 equivalent values
- ❌ VOC index errors
- ❌ Possible crashes

---

## I2C Bus Limitations

### Maximum Devices:

Theoretical: 112 devices (0x08 to 0x77, excluding reserved addresses)
Practical: ~10-20 devices depending on:
- Bus capacitance
- Wire length
- Pull-up resistor values
- Device drive strength

### Our Configuration:

| Address | Device | Notes |
|---------|--------|-------|
| 0x76 | BME688 ENV | Garret's modification required |
| 0x77 | BME688 AMB | Default address |
| 0x3C | OLED (optional) | SSD1306 display |
| 0x68 | IMU (optional) | MPU6050 or similar |
| 0x48 | ADC (optional) | ADS1115 |
| 0x40 | PWM (optional) | PCA9685 |

---

## Troubleshooting

### Only One Sensor Detected

**Symptoms:**
- `scan` shows only 0x77
- ENV sensor doesn't respond

**Solutions:**
1. Verify solder bridge with multimeter (continuity test)
2. Reflow solder joint if needed
3. Check sensor isn't damaged
4. Try swapping which sensor is modified

### Both Sensors at 0x77

**Symptoms:**
- `scan` shows only one 0x77
- Firmware says "2 sensors" but only one works

**Solutions:**
1. Solder bridge not connected
2. Wrong pads bridged
3. Check BME688 datasheet for your specific breakout board

### Bootloop with Both Sensors

**Symptoms:**
- Board reboots continuously
- Serial output shows repeated init attempts

**Solutions:**
1. Flash bare board firmware first (no BSEC)
2. Test I2C scanning works
3. Then upgrade to BSEC firmware
4. Check brownout settings (`WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0)`)

### Sensors Work Individually But Not Together

**Symptoms:**
- Works with just AMB (0x77)
- Works with just ENV (0x76)
- Fails with both connected

**Causes:**
- Insufficient power supply (BME688 uses significant current)
- I2C bus capacitance too high
- Missing or wrong pull-up resistors

**Solutions:**
1. Use powered USB hub
2. Check 3.3V supply current capability (need ~100mA per sensor)
3. Verify I2C pull-ups (typically 4.7kΩ)
4. Keep wires short (<15cm)

---

## Technical Details

### BME688 I2C Address Selection:

The BME688 has a hardware pin (SDO) that determines I2C address:
- **SDO Low (GND)**: Address = 0x76
- **SDO High (VDDIO)**: Address = 0x77

On breakout boards:
- Default: SDO pulled high → 0x77
- Solder bridge: Connects SDO to GND → 0x76

### Garret's Design Choice:

| Sensor | Address | SDO State | Purpose |
|--------|---------|-----------|---------|
| AMB | 0x77 | High (default) | Ambient air quality |
| ENV | 0x76 | Low (modified) | Environmental monitoring |

---

## Future Expansion

### Adding More Sensors:

The firmware's peripheral library can detect:
- BME680/BME688 (0x76, 0x77)
- MPU6050/BME280 (0x68)
- OLED SSD1306 (0x3C)
- ADS1115 ADC (0x48)
- PCA9685 PWM (0x40)

### To Add New Peripheral:

1. Update `knownPeripherals[]` array in firmware
2. Add address and name
3. Firmware will auto-detect on `scan`

```cpp
static Peripheral knownPeripherals[] = {
  {0x76, "BME688", false},
  {0x77, "BME688", false},
  {0x68, "MPU6050", false},
  {0x3C, "OLED", false},
  // Add your new peripheral here:
  {0xYOUR_ADDR, "YOUR_SENSOR", false},
};
```

---

## References

- BME688 Datasheet: Section 5.3 (I2C Interface)
- BSEC2 Library: https://github.com/boschsensortec/Bosch-BSEC2-Library
- I2C Specification: NXP UM10204
- Adafruit BME688 Guide: https://learn.adafruit.com/adafruit-bme688

---

**Important**: Always test with ONE sensor first before adding the second!
