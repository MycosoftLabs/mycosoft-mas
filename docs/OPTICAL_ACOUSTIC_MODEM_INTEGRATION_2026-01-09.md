# Optical & Acoustic Modem TX Integration

**Date**: January 9, 2026  
**Author**: Claude AI + Human Review  
**Status**: ✅ TX COMPLETE, RX PENDING

---

## Executive Summary

This document details the integration of optical (LED-based LiFi) and acoustic (buzzer-based FSK) modem transmission capabilities into the MycoBrain Device Manager firmware. These features were ported from the `MycoBrain_ScienceComms` firmware with careful attention to avoid the configuration issues that previously caused board failures.

---

## Features Overview

### Optical TX (OPTX)
- **Method**: On-Off Keying (OOK) via NeoPixel LED
- **Hardware**: SK6805 RGB LED on GPIO15
- **Rate**: ~10-12 bits/second (configurable)
- **Use Case**: Short-range light-based data transmission

### Acoustic TX (AOTX)
- **Method**: Frequency-Shift Keying (FSK) via buzzer
- **Hardware**: Passive buzzer on GPIO16 (LEDC PWM)
- **Frequencies**: f0=1000Hz (bit 0), f1=2000Hz (bit 1)
- **Use Case**: Audible data transmission for testing

---

## Firmware Implementation

### File: `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino`

### Optical TX State Variables
```cpp
// Optical TX state
static bool optxMode = false;
static String gOptxPayload = "";
static int gOptxRateHz = 10;
static int gOptxRepeat = 1;
static int gOptxBitIndex = 0;
static int gOptxRepeatCount = 0;
static unsigned long gOptxLastSymbol = 0;
static uint8_t gOptxSavedR = 0, gOptxSavedG = 0, gOptxSavedB = 0;
```

### Acoustic TX State Variables
```cpp
// Acoustic TX state
static bool aotxMode = false;
static String gAotxPayload = "";
static int gAotxSymbolMs = 100;
static int gAotxF0 = 1000;  // Frequency for bit 0
static int gAotxF1 = 2000;  // Frequency for bit 1
static int gAotxRepeat = 1;
static int gAotxBitIndex = 0;
static int gAotxRepeatCount = 0;
static unsigned long gAotxSymbolStart = 0;
```

### Optical TX Functions
```cpp
void optxStart(const String& payload, int rateHz = 10, int repeat = 1) {
  gOptxPayload = payload;
  gOptxRateHz = rateHz > 0 ? rateHz : 10;
  gOptxRepeat = repeat > 0 ? repeat : 1;
  gOptxBitIndex = 0;
  gOptxRepeatCount = 0;
  gOptxLastSymbol = 0;
  
  // Save current LED state
  gOptxSavedR = gLedR;
  gOptxSavedG = gLedG;
  gOptxSavedB = gLedB;
  
  optxMode = true;
  Serial.println("{\"ok\":true,\"optx\":\"started\",\"payload_len\":" + String(payload.length()) + "}");
}

void optxStop() {
  optxMode = false;
  // Restore saved LED state
  ledWriteRGB(gOptxSavedR, gOptxSavedG, gOptxSavedB);
  Serial.println("{\"ok\":true,\"optx\":\"stopped\"}");
}

void optxUpdate() {
  if (!optxMode) return;
  
  unsigned long now = millis();
  unsigned long symbolDuration = 1000 / gOptxRateHz;
  
  if (now - gOptxLastSymbol < symbolDuration) return;
  gOptxLastSymbol = now;
  
  int totalBits = gOptxPayload.length() * 8;
  
  if (gOptxBitIndex >= totalBits) {
    gOptxRepeatCount++;
    if (gOptxRepeatCount >= gOptxRepeat) {
      optxStop();
      return;
    }
    gOptxBitIndex = 0;
  }
  
  // Get current bit
  int byteIndex = gOptxBitIndex / 8;
  int bitInByte = 7 - (gOptxBitIndex % 8);  // MSB first
  char c = gOptxPayload[byteIndex];
  bool bitValue = (c >> bitInByte) & 1;
  
  // OOK: LED on for 1, off for 0
  if (bitValue) {
    ledWriteRGB(255, 255, 255);  // White for 1
  } else {
    ledWriteRGB(0, 0, 0);  // Off for 0
  }
  
  gOptxBitIndex++;
}
```

### Acoustic TX Functions
```cpp
void aotxStart(const String& payload, int symbolMs = 100, int f0 = 1000, int f1 = 2000, int repeat = 1) {
  gAotxPayload = payload;
  gAotxSymbolMs = symbolMs > 0 ? symbolMs : 100;
  gAotxF0 = f0;
  gAotxF1 = f1;
  gAotxRepeat = repeat > 0 ? repeat : 1;
  gAotxBitIndex = 0;
  gAotxRepeatCount = 0;
  gAotxSymbolStart = 0;
  
  aotxMode = true;
  Serial.println("{\"ok\":true,\"aotx\":\"started\",\"payload_len\":" + String(payload.length()) + "}");
}

void aotxStop() {
  aotxMode = false;
  ledcWrite(BUZZER_LEDC_CHANNEL, 0);  // Stop buzzer
  Serial.println("{\"ok\":true,\"aotx\":\"stopped\"}");
}

void aotxUpdate() {
  if (!aotxMode) return;
  
  unsigned long now = millis();
  
  if (now - gAotxSymbolStart < gAotxSymbolMs) return;
  gAotxSymbolStart = now;
  
  int totalBits = gAotxPayload.length() * 8;
  
  if (gAotxBitIndex >= totalBits) {
    gAotxRepeatCount++;
    if (gAotxRepeatCount >= gAotxRepeat) {
      aotxStop();
      return;
    }
    gAotxBitIndex = 0;
  }
  
  // Get current bit
  int byteIndex = gAotxBitIndex / 8;
  int bitInByte = 7 - (gAotxBitIndex % 8);  // MSB first
  char c = gAotxPayload[byteIndex];
  bool bitValue = (c >> bitInByte) & 1;
  
  // FSK: f0 for 0, f1 for 1
  int freq = bitValue ? gAotxF1 : gAotxF0;
  ledcWriteTone(BUZZER_LEDC_CHANNEL, freq);
  
  gAotxBitIndex++;
}
```

### CLI Commands
```cpp
// In parseCliCommand():
else if (firstWord == "optx") {
  if (rest == "stop") {
    optxStop();
  } else if (rest.startsWith("start ")) {
    String payload = rest.substring(6);
    optxStart(payload);
  } else if (rest == "status") {
    cmdOptxStatus();
  } else {
    Serial.println("{\"error\":\"optx: start <payload> | stop | status\"}");
  }
}
else if (firstWord == "aotx") {
  if (rest == "stop") {
    aotxStop();
  } else if (rest.startsWith("start ")) {
    String payload = rest.substring(6);
    aotxStart(payload);
  } else if (rest == "status") {
    cmdAotxStatus();
  } else {
    Serial.println("{\"error\":\"aotx: start <payload> | stop | status\"}");
  }
}
```

### Main Loop Integration
```cpp
void loop() {
  // ... other updates ...
  
  // Update modem transmissions
  optxUpdate();
  aotxUpdate();
  
  // ... rest of loop ...
}
```

---

## CLI Command Reference

### Optical TX Commands
| Command | Description |
|---------|-------------|
| `optx start <payload>` | Start transmitting payload via LED |
| `optx stop` | Stop optical transmission |
| `optx status` | Get current OPTX state |

### Acoustic TX Commands
| Command | Description |
|---------|-------------|
| `aotx start <payload>` | Start transmitting payload via buzzer |
| `aotx stop` | Stop acoustic transmission |
| `aotx status` | Get current AOTX state |

### Status Response Format
```json
{
  "ok": true,
  "optx": {
    "running": true,
    "mode": "OOK",
    "payload_len": 5,
    "bit_index": 24,
    "rate_hz": 10,
    "repeat": 1,
    "repeat_count": 0
  }
}
```

---

## Testing Results

### Optical TX Test
```powershell
# Start optical transmission
$cliBody = @{ command = "optx start HELLO" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM7/cli" -Method POST -Body $cliBody

# Response: {"ok":true,"optx":"started","payload_len":5}

# Check status during transmission
$cliBody = @{ command = "optx status" } | ConvertTo-Json
# Response shows bit_index incrementing

# Visual confirmation: LED flashes white/off pattern
```

### Acoustic TX Test
```powershell
# Start acoustic transmission
$cliBody = @{ command = "aotx start AB" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM7/cli" -Method POST -Body $cliBody

# Response: {"ok":true,"aotx":"started","payload_len":2}

# Audio confirmation: Alternating 1kHz/2kHz tones
```

### Simultaneous Operation Test
Both OPTX and AOTX can operate concurrently:
- LED flashes for optical data
- Buzzer plays FSK tones for acoustic data
- No interference observed

---

## Website UI Integration

### LED Control Widget
**File**: `components/mycobrain/widgets/led-control-widget.tsx`

Added optical TX controls:
```typescript
const startOpticalTx = async (payload: string) => {
  await fetch(`/api/mycobrain/${port}/control`, {
    method: "POST",
    body: JSON.stringify({ 
      peripheral: "led", 
      action: "optical_tx",
      payload 
    })
  })
}

const stopOpticalTx = async () => {
  await fetch(`/api/mycobrain/${port}/control`, {
    method: "POST",
    body: JSON.stringify({ 
      peripheral: "led", 
      action: "optical_stop" 
    })
  })
}
```

### Buzzer Control Widget
**File**: `components/mycobrain/widgets/buzzer-control-widget.tsx`

Added acoustic TX controls:
```typescript
const startAcousticTx = async (payload: string) => {
  await fetch(`/api/mycobrain/${port}/buzzer`, {
    method: "POST",
    body: JSON.stringify({ 
      action: "acoustic_tx",
      payload 
    })
  })
}

const stopAcousticTx = async () => {
  await fetch(`/api/mycobrain/${port}/buzzer`, {
    method: "POST",
    body: JSON.stringify({ action: "stop" })
  })
}
```

### API Routes
**Files**:
- `app/api/mycobrain/[port]/led/route.ts`
- `app/api/mycobrain/[port]/buzzer/route.ts`
- `app/api/mycobrain/[port]/control/route.ts`

---

## Receiver Implementation (Future)

### Optical RX Requirements
- **Hardware**: Photodiode or phototransistor on ADC pin
- **Firmware**: 
  - ADC sampling at 2x symbol rate
  - Threshold detection for OOK decoding
  - Byte reconstruction from bit stream
- **Challenges**: Ambient light interference, timing synchronization

### Acoustic RX Requirements
- **Hardware**: Microphone module (MAX9814 or similar) on ADC/I2S
- **Firmware**:
  - Audio sampling at 8kHz+ 
  - Goertzel algorithm for FSK detection
  - Bandpass filtering for noise rejection
- **Challenges**: Ambient noise, echo handling

---

## Known Limitations

1. **No RX Support**: Current implementation is TX-only
2. **Fixed OOK**: Optical uses simple on/off keying (no advanced modulation)
3. **No Error Correction**: Raw payload transmission without FEC
4. **Manual Rate**: Symbol rate is hardcoded, not adaptive
5. **Single Payload**: Cannot queue multiple transmissions

---

## Files Modified

- `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino`
- `app/api/mycobrain/[port]/led/route.ts`
- `app/api/mycobrain/[port]/buzzer/route.ts`
- `app/api/mycobrain/[port]/control/route.ts`
- `components/mycobrain/widgets/led-control-widget.tsx`
- `components/mycobrain/widgets/buzzer-control-widget.tsx`

---

## Comparison with ScienceComms Firmware

### Why ScienceComms Failed
1. **Wrong Board Settings**: Used incorrect partition scheme
2. **BSEC Dependency**: Required BSEC2 library with strict initialization
3. **PlatformIO vs Arduino IDE**: Build configuration mismatch
4. **Missing Error Handling**: Crashed when sensors not present

### DeviceManager Improvements
1. **Correct Arduino IDE Settings**: Documented in memory
2. **Optional Sensors**: Graceful handling of missing BME688
3. **Standalone Modem**: Works without sensor initialization
4. **Incremental Testing**: Each feature tested before next addition

---

## References

- ScienceComms firmware source: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\firmware\MycoBrain_ScienceComms`
- BSEC Library documentation: Bosch BSEC2 Arduino library
- ESP32 LEDC documentation: ESP32 Arduino Core
