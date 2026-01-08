# MycoBrain Optical & Acoustic Modem Test Results

**Date**: January 8, 2026, 1:00 PM PST  
**Firmware**: MycoBrain_DeviceManager v1.1.0  
**Board**: ESP32-S3 on COM7  
**Tester**: Claude AI + Human Observation

---

## Executive Summary

Both optical (OPTX) and acoustic (AOTX) modem transmitters have been **successfully implemented and tested**. All core functionality is working:

- ✅ Optical TX (On-Off Keying via LED on GPIO15)
- ✅ Acoustic TX (Frequency-Shift Keying via Buzzer on GPIO16)
- ✅ Simultaneous operation of both modems
- ✅ Variable payload lengths
- ✅ Status monitoring during transmission

---

## Test Results

### 1. Optical TX (OPTX) - LED Flashing

| Test | Payload | Bits | Result | bit_index Progression |
|------|---------|------|--------|----------------------|
| Basic | AB | 16 | ✅ PASS | 1 → 16 |
| Medium | HELLO | 40 | ✅ PASS | 13 → 25 → 37 → 40 |
| Binary | \xAA | 8 | ✅ PASS | LED alternating pulses |

**Mode**: OOK (On-Off Keying)  
**Rate**: ~10-12 bits/second  
**LED**: SK6805 NeoPixel on GPIO15

### 2. Acoustic TX (AOTX) - FSK Tones

| Test | Payload | Bits | Result | bit_index Progression |
|------|---------|------|--------|----------------------|
| Basic | AB | 16 | ✅ PASS | 7 → 16 |
| Short | SOS | 24 | ✅ PASS | 11 → 21 → 24 |
| Long | TEST123 | 56 | ✅ PASS | 14 → 26 → 38 → 50 → 56 |

**Mode**: FSK (Frequency-Shift Keying)  
**Frequencies**: f0=1000Hz (bit 0), f1=2000Hz (bit 1)  
**Symbol Duration**: ~100ms per bit  
**Buzzer**: Passive buzzer on GPIO16 (LEDC PWM)

### 3. Simultaneous Operation

| OPTX Payload | AOTX Payload | Result |
|--------------|--------------|--------|
| LIGHT (40 bits) | SOUND (40 bits) | ✅ PASS |

**Observations**:
- Both modems operated independently
- OPTX: bit_index 10 → 22 → 34 → 40
- AOTX: bit_index 11 → 23 → 35 → 40
- No interference between systems
- LED flashing and buzzer tones simultaneous

---

## CLI Commands Reference

### Optical TX Commands
```
optx start <payload>  - Start transmitting payload as OOK light pulses
optx stop             - Stop transmission
optx status           - Get current status (running, mode, bit_index, repeat_count)
```

### Acoustic TX Commands
```
aotx start <payload>  - Start transmitting payload as FSK audio tones
aotx stop             - Stop transmission
aotx status           - Get current status (running, mode, bit_index, f0, f1)
```

### Example Status Responses
```json
// OPTX running
{"ok":true,"running":true,"mode":"ook","bit_index":22,"repeat_count":0}

// AOTX running
{"ok":true,"running":true,"mode":"fsk","bit_index":15,"f0":1000,"f1":2000}

// Either idle
{"ok":true,"running":false,"mode":"idle","bit_index":40,"repeat_count":1}
```

---

## Next Steps: Receiver Implementation

### For Optical RX (Light Receiver)

**Required Hardware**:
1. Photodiode or phototransistor
2. Amplifier circuit (optional for weak signals)
3. ADC-capable GPIO on ESP32

**Recommended Sensors**:
- BPW34 silicon photodiode
- TEPT5700 phototransistor (good for visible light)
- OPT101 integrated photodiode + amplifier

**Implementation Plan**:
1. Connect photodiode to ADC pin (e.g., GPIO6 or GPIO7)
2. Sample at 100Hz+ for reliable OOK detection
3. Implement threshold detection for on/off states
4. Decode bit stream using same timing as transmitter
5. Buffer bytes and output received data

### For Acoustic RX (Audio Receiver)

**Required Hardware**:
1. Electret microphone module (e.g., MAX4466 or MAX9814)
2. ADC-capable GPIO on ESP32

**Implementation Plan**:
1. Connect microphone to ADC pin
2. Sample at 8000Hz+ for FSK detection
3. Implement Goertzel algorithm for f0/f1 detection
4. Decode bit stream based on frequency detection
5. Buffer bytes and output received data

### Test Setup Without Additional Hardware

**Visual Verification (OPTX)**:
- Human observer can confirm LED flashing
- Camera with slow-motion can capture pulse patterns
- Oscilloscope on LED voltage can measure timing

**Audio Verification (AOTX)**:
- Human ear can distinguish 1000Hz vs 2000Hz tones
- Audio recording + spectrum analysis
- Oscilloscope on buzzer signal

---

## Known Limitations

1. **No Framing Protocol**: Raw bytes transmitted without start/stop markers
2. **No Error Detection**: No CRC or checksum
3. **Fixed Timing**: Rate cannot be changed mid-transmission
4. **No Acknowledgment**: One-way transmission only

## Future Enhancements

1. Add preamble pattern for synchronization
2. Implement Manchester encoding for clock recovery
3. Add CRC-8 or CRC-16 for error detection
4. Support configurable bit rates
5. Add receive functionality (OPRX, AORX)

---

## Files Modified

- `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino` - Added OPTX and AOTX functionality
- `minimal_mycobrain.py` - Python service supports modem commands
- Website API routes support optical/acoustic TX from UI

---

*This document serves as verification that the MycoBrain optical and acoustic modem transmitters are functioning correctly.*
