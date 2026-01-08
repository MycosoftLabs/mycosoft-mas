# MycoBrain Hybrid Firmware Integration Plan
**Date**: January 8, 2026  
**Status**: Planning Phase  
**Goal**: Merge ScienceComms features into working DeviceManager firmware

---

## Executive Summary

This plan outlines the systematic integration of ScienceComms features (optical modem, acoustic modem, stimulus engine) into the currently working MycoBrain_DeviceManager firmware. Each feature will be implemented, tested, and verified before moving to the next.

---

## Current Issues to Fix First

### Priority 1: UI/API Issues (Fix Before Firmware Changes)

| Issue | Root Cause | Fix Location | Status |
|-------|------------|--------------|--------|
| Legacy brightness slider does nothing | `control/route.ts` ignores brightness param | API route | ⏳ Pending |
| LED Control widget brightness sends on every slider move | No debounce | Widget | ⏳ Pending |
| Sensor banner shows "2x BME688" always | Hardcoded value | UI component | ⏳ Pending |
| Optical TX shows "Idle" | Feature not in firmware | Firmware | Phase 2 |
| Acoustic TX shows "Idle" | Feature not in firmware | Firmware | Phase 3 |

### Priority 2: API Alignment

| API Route | Current Behavior | Expected Behavior |
|-----------|------------------|-------------------|
| `/api/mycobrain/[port]/led` | ✅ Sends CLI commands | Working |
| `/api/mycobrain/[port]/buzzer` | ✅ Sends CLI commands | Working |
| `/api/mycobrain/[port]/control` | ❌ Ignores brightness | Fix needed |
| `/api/mycobrain/[port]/control` | ❌ Melody sends beep | Should send "morgio" |

---

## Phase 1: UI/API Fixes (No Firmware Changes)

### 1.1 Fix Legacy Brightness in Control Route

**File**: `app/api/mycobrain/[port]/control/route.ts`

**Current Code** (line 56-57):
```typescript
// Note: brightness not supported by board, just set manual mode and RGB
payload = { command: { cmd: `led rgb ${r} ${g} ${b}` } }
```

**Fixed Code**:
```typescript
// Set brightness first, then RGB
const brightness = Math.round((data.brightness || 128) * 100 / 255) // Convert 0-255 to 0-100
// Send brightness command first
await fetch(`${MYCOBRAIN_SERVICE_URL}${endpoint}`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ command: { cmd: `led brightness ${brightness}` } }),
})
// Then send RGB
payload = { command: { cmd: `led rgb ${r} ${g} ${b}` } }
```

### 1.2 Fix Melody Button in Control Route

**Current Code** (line 68-70):
```typescript
if (action === "melody") {
  payload = { command: { cmd: "beep 523 100" } }
}
```

**Fixed Code**:
```typescript
if (action === "melody") {
  payload = { command: { cmd: "morgio" } }
}
```

### 1.3 Fix Sensor Banner

**Files to Update**:
- `mycobrain-device-manager.tsx` - Main sensor display
- `mycobrain-device-card.tsx` - Card sensor display
- `mycobrain-overview-widget.tsx` - Overview widget

**Change**: Use `device.capabilities?.bme688_count` or I2C scan results instead of hardcoded value

---

## Phase 2: Optical Modem (Firmware + API + UI)

### 2.1 Firmware Changes

Add to `MycoBrain_DeviceManager.ino`:

**New State Variables**:
```cpp
// Optical Modem State
enum OptxMode { OPTX_IDLE = 0, OPTX_OOK, OPTX_MANCHESTER, OPTX_PATTERN };
static OptxMode gOptxMode = OPTX_IDLE;
static String gOptxPayload = "";
static uint32_t gOptxRateHz = 10;
static uint32_t gOptxRepeat = 1;
static uint32_t gOptxBitIndex = 0;
static uint32_t gOptxRepeatCount = 0;
static uint32_t gOptxLastSymbol = 0;
```

**New Commands** (from ScienceComms cli.cpp):
```cpp
// CLI Commands:
// optx start <profile> <payload_base64> [rate_hz] [repeat]
// optx stop
// optx status

// JSON Commands:
// {"cmd":"optical.tx.start","profile":"camera_ook","payload":"base64...","rate_hz":10,"repeat":1}
// {"cmd":"optical.tx.stop"}
// {"cmd":"optical.tx.status"}
```

**Transmission Loop** (in main loop):
```cpp
if (gOptxMode != OPTX_IDLE) {
  uint32_t now = millis();
  uint32_t symbolPeriod = 1000 / gOptxRateHz;
  if (now - gOptxLastSymbol >= symbolPeriod) {
    optxNextSymbol();
    gOptxLastSymbol = now;
  }
}
```

### 2.2 API Route Update

**File**: `app/api/mycobrain/[port]/led/route.ts`

Already has `optical_tx` case, but needs to send proper CLI command:
```typescript
case "optical_tx":
  const profile = body.profile || "camera_ook"
  const payload = body.payload || ""
  const rate = body.rate_hz || 10
  const repeat = body.repeat || 1
  const payloadB64 = Buffer.from(payload).toString("base64")
  cmd = `optx start ${profile} ${payloadB64} ${rate} ${repeat}`
  response = await sendCommand(deviceId, cmd)
  break
```

### 2.3 UI Already Ready

`led-control-widget.tsx` has Optical TX tab with:
- Profile selector
- Payload input
- Rate slider
- Repeat slider
- Start/Stop buttons

---

## Phase 3: Acoustic Modem (Firmware + API + UI)

### 3.1 Firmware Changes

Add to `MycoBrain_DeviceManager.ino`:

**New State Variables**:
```cpp
// Acoustic Modem State
enum AotxMode { AOTX_IDLE = 0, AOTX_FSK, AOTX_SWEEP, AOTX_CHIRP };
static AotxMode gAotxMode = AOTX_IDLE;
static String gAotxPayload = "";
static uint32_t gAotxSymbolMs = 100;
static uint32_t gAotxF0 = 1000;
static uint32_t gAotxF1 = 2000;
static uint32_t gAotxRepeat = 1;
static uint32_t gAotxBitIndex = 0;
static uint32_t gAotxRepeatCount = 0;
static uint32_t gAotxSymbolStart = 0;
```

**New Commands**:
```cpp
// CLI Commands:
// aotx start <profile> <payload_base64> [symbol_ms] [f0] [f1] [repeat]
// aotx stop
// aotx status

// JSON Commands:
// {"cmd":"acoustic.tx.start","profile":"simple_fsk","payload":"base64...","symbol_ms":100,"f0":1000,"f1":2000,"repeat":1}
// {"cmd":"acoustic.tx.stop"}
// {"cmd":"acoustic.tx.status"}
```

### 3.2 API Route Already Ready

`buzzer/route.ts` has `acoustic_tx` case that sends JSON command

### 3.3 UI Widget Needed

Create `buzzer-control-widget.tsx` Acoustic TX tab similar to LED Optical TX tab

---

## Phase 4: Stimulus Engine (Future)

This phase integrates the stimulus patterns from ScienceComms for automated experiments.

**Deferred** - Lower priority than basic modem features

---

## Testing Checklist

### For Each Feature:

1. [ ] Verify firmware compiles with Arduino CLI
2. [ ] Flash to board on COM7
3. [ ] Test command via terminal (PowerShell serial)
4. [ ] Verify service API passes command correctly
5. [ ] Verify website UI triggers correct behavior
6. [ ] Document any issues found

### Terminal Test Commands:

```powershell
# Connect to service
$body = @{ command = @{ cmd = "status" } } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM7/command" -Method POST -Body $body -ContentType "application/json"

# Test optical TX (after implementation)
$body = @{ command = @{ cmd = "optx start camera_ook SGVsbG8= 10 1" } } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM7/command" -Method POST -Body $body -ContentType "application/json"

# Test acoustic TX (after implementation)
$body = @{ command = @{ cmd = "aotx start simple_fsk SGVsbG8= 100 1000 2000 1" } } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8003/devices/mycobrain-COM7/command" -Method POST -Body $body -ContentType "application/json"
```

---

## Arduino IDE Settings Reference

These settings MUST be used for flashing to prevent boot loops:

```
Board: ESP32-S3 Dev Module
USB CDC on Boot: Enabled
USB DFU on Boot: Enabled
USB Mode: Hardware CDC and JTAG
JTAG Adapter: Integrated USB JTAG
PSRAM: OPI PSRAM
CPU Frequency: 240 MHz
Flash Mode: QIO 80MHz
Flash Size: 16MB (128Mb)
Partition Scheme: 16M Flash (3MB APP / 9.9MB FATFS)
Upload Speed: 921600
```

**Arduino CLI FQBN**:
```
esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=cdc,DFUOnBoot=dfu,FlashMode=qio,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=opi,DebugLevel=none
```

---

## Rollback Plan

If any phase breaks the board:

1. Stop MycoBrain service: `Stop-Process -Name python -Force`
2. Hold BOOT button, press RESET, release BOOT
3. Flash known-good firmware:
   ```powershell
   arduino-cli upload -p COM7 --fqbn esp32:esp32:esp32s3:... --input-dir firmware/MycoBrain_DeviceManager/build
   ```
4. Restart service: `python minimal_mycobrain.py`

---

## Files to Modify

| Phase | File | Changes |
|-------|------|---------|
| 1 | `app/api/mycobrain/[port]/control/route.ts` | Add brightness support, fix melody |
| 1 | `components/mycobrain/mycobrain-device-manager.tsx` | Fix sensor banner |
| 2 | `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino` | Add optx commands |
| 2 | `app/api/mycobrain/[port]/led/route.ts` | Update optical_tx case |
| 3 | `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino` | Add aotx commands |
| 3 | `components/mycobrain/widgets/buzzer-control-widget.tsx` | Add Acoustic TX tab |

---

## Success Criteria

1. ✅ All basic LED/Buzzer controls work from website
2. ⏳ Legacy brightness slider dims LED
3. ⏳ Sensor banner shows correct sensor count
4. ⏳ Optical TX transmits data and UI shows "Running"
5. ⏳ Acoustic TX transmits data and UI shows "Running"
6. ⏳ No boot loops or brownout resets

---

**Document Version**: 1.0  
**Author**: Claude AI  
**Next Step**: Implement Phase 1 fixes (UI/API only)
