# MycoBrain Comprehensive Test Plan
**Date**: December 31, 2025, 12:30 AM PST  
**Device**: ESP32-S3 MycoBrain v1 on COM5  
**Firmware**: 3.3.5  
**Protocol**: MDP v1 + NDJSON Machine Mode  

## 🎯 Testing Objectives

Verify ALL new features work correctly:
1. ✅ **Basic Controls** - NeoPixel LED, Buzzer (DONE)
2. 🔄 **NDJSON Machine Mode** - Optical TX, Acoustic TX
3. 🔄 **Color Patterns** - Rainbow, Chase, Breathe, etc.
4. 🔄 **Buzzer Presets** - coin, bump, power, one-up, morg.io
5. 🔄 **Custom Tones** - Duration and frequency adjustment
6. 🔄 **Optical TX** - Camera OOK, Manchester, Spatial Modulation
7. 🔄 **Acoustic TX** - Sound-based data transmission
8. 🔄 **Communications** - LoRa, Wi-Fi, BLE, Mesh

## 📋 Test Categories

### Category 1: NeoPixel LED Controls

#### Test 1.1: Basic Colors (✅ VERIFIED)
```bash
# Red
curl -X POST http://localhost:8003/devices/mycobrain-COM5/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "led rgb 255 0 0"}}'

# Green  
curl -X POST http://localhost:8003/devices/mycobrain-COM5/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "led rgb 0 255 0"}}'

# Blue
curl -X POST http://localhost:8003/devices/mycobrain-COM5/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "led rgb 0 0 255"}}'

# Expected: LED changes to specified color immediately
```

#### Test 1.2: Color Patterns
```bash
# Solid
led pattern solid

# Blink
led pattern blink

# Breathe
led pattern breathe

# Rainbow
led pattern rainbow

# Chase
led pattern chase

# Sparkle
led pattern sparkle

# Expected: LED displays specified pattern
```

#### Test 1.3: Brightness Control
```bash
# 25% brightness
led brightness 25

# 50% brightness
led brightness 50

# 100% brightness
led brightness 100

# Expected: LED brightness adjusts visibly
```

### Category 2: Buzzer/Sound Controls

#### Test 2.1: Preset Sounds (TO TEST)
```bash
# Coin sound
curl -X POST http://localhost:8003/devices/mycobrain-COM5/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "coin"}}'

# Bump sound
curl -X POST http://localhost:8003/devices/mycobrain-COM5/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "bump"}}'

# Power sound
curl -X POST http://localhost:8003/devices/mycobrain-COM5/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "power"}}'

# One-up sound
curl -X POST http://localhost:8003/devices/mycobrain-COM5/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "oneup"}}'

# Morg.io sound
curl -X POST http://localhost:8003/devices/mycobrain-COM5/command \
  -H "Content-Type: application/json" \
  -d '{"command": {"cmd": "morgio"}}'

# Expected: Distinct sound plays for each preset
```

#### Test 2.2: Custom Tones (REPORTED NOT WORKING)
```bash
# Test frequency range
buzzer freq 200 duration 500   # Low tone
buzzer freq 1000 duration 500  # Mid tone
buzzer freq 5000 duration 500  # High tone

# Test duration
buzzer freq 1000 duration 100  # Short
buzzer freq 1000 duration 1000 # Long

# Expected: Buzzer plays tone at specified frequency and duration
# Status: NEEDS INVESTIGATION if not working
```

#### Test 2.3: Preset Musical Tones
```bash
# C4 (261.63 Hz)
buzzer note C4

# E4 (329.63 Hz)
buzzer note E4

# G4 (392.00 Hz)
buzzer note G4

# C5 (523.25 Hz)
buzzer note C5

# Expected: Musical note plays
# Status: UI shows buttons but need to verify firmware support
```

### Category 3: Optical TX (Light Communication)

#### Test 3.1: Camera OOK (On-Off Keying)
```bash
# Initialize machine mode first
machine init

# Send data via Optical TX - Camera OOK profile
optical tx profile camera_ook payload "HELLO" rate_hz 10 repeat 3

# Expected:
# - LED flashes in OOK pattern
# - Data encoded as on/off pulses
# - Camera can decode the pattern
```

#### Test 3.2: Camera Manchester Encoding
```bash
# Manchester encoding for cameras
optical tx profile camera_manchester payload "TEST123" rate_hz 10 repeat 3

# Expected:
# - LED uses Manchester encoding (transitions encode bits)
# - More reliable than OOK
# - Camera with decoder can read data
```

#### Test 3.3: Spatial Modulation
```bash
# Use LED array spatial patterns
optical tx profile spatial_sm payload "SPATIAL" rate_hz 5 repeat 3

# Expected:
# - If multiple LEDs: creates spatial patterns
# - Different positions encode different data
# - Advanced optical communication
```

### Category 4: Acoustic TX (Sound Communication)

#### Test 4.1: Acoustic Modem
```bash
# Initialize machine mode
machine init

# Send data via acoustic modem
acoustic tx payload "SOUND_DATA" rate_hz 10 repeat 3

# Expected:
# - Buzzer emits high-frequency tones
# - Data encoded in audio frequency shifts (FSK)
# - Microphone can decode with proper software

# Status: User reports "doesn't seem like anything is happening"
# Investigation needed:
# - Is firmware compiled with acoustic TX support?
# - Is buzzer capable of required frequencies?
# - Is the encoding audible or ultrasonic?
```

#### Test 4.2: Acoustic Parameters
```bash
# Test different rates
acoustic tx payload "SLOW" rate_hz 5
acoustic tx payload "FAST" rate_hz 20

# Test different modulation
acoustic tx payload "DATA" modulation fsk
acoustic tx payload "DATA" modulation ook

# Expected: Variations in sound pattern
```

### Category 5: Communications (LoRa, Wi-Fi, BLE, Mesh)

#### Test 5.1: LoRa Radio
```bash
# Check LoRa status
lora status

# Send LoRa packet
lora send "HELLO_LORA"

# Configure LoRa parameters
lora freq 915.0  # North America frequency
lora power 20    # dBm
lora sf 7        # Spreading factor

# Expected:
# - LoRa module initializes
# - Can send/receive packets
# - Status shows RSSI, SNR

# Status: UI shows "Init" - needs investigation
```

#### Test 5.2: Wi-Fi
```bash
# Scan Wi-Fi networks
wifi scan

# Connect to network
wifi connect ssid "YourNetwork" password "YourPassword"

# Check status
wifi status

# Expected:
# - Shows available networks
# - Can connect to AP
# - Shows IP address, RSSI
```

#### Test 5.3: BLE (Bluetooth Low Energy)
```bash
# Start BLE advertising
ble start name "MycoBrain-COM5"

# Send BLE notification
ble notify "SENSOR_DATA"

# Expected:
# - BLE service advertises
# - Can be discovered by phone/computer
# - Notifications send data
```

#### Test 5.4: Mesh Networking
```bash
# Join mesh network
mesh join network_id "myco_mesh"

# Send mesh message
mesh send "HELLO_MESH"

# Expected:
# - Joins ESP-NOW or other mesh protocol
# - Can communicate with other nodes
# - Multi-hop routing works
```

## 🔍 Investigation Items

### Issue 1: Custom Tone Duration/Frequency Not Working
**Symptom**: UI shows controls but no sound  
**Possible Causes**:
- Firmware doesn't support variable duration
- Command format incorrect
- Buzzer hardware limitations (fixed frequency only?)
- UI not sending correct command format

**Tests Needed**:
```bash
# Test if duration parameter is supported
buzzer 1000 100   # 1000Hz for 100ms
buzzer 1000 500   # 1000Hz for 500ms

# Check firmware capabilities
status  # Get full device capabilities
```

### Issue 2: Acoustic TX "Doesn't Seem to Work"
**Symptom**: UI says "running" but no audible output  
**Possible Causes**:
- Ultrasonic frequencies (above human hearing range)
- Very quiet output
- Firmware not compiled with acoustic TX support
- Requires machine mode initialization first

**Tests Needed**:
```bash
# Verify machine mode is active
machine status

# Try different payload sizes
acoustic tx payload "A"       # Single char
acoustic tx payload "TEST"    # Short
acoustic tx payload "LONG_DATA_STRING"  # Long

# Record with microphone app to verify inaudible tones
```

### Issue 3: LoRa Shows "Init" But Not Operational
**Symptom**: Status shows "Init" instead of active state  
**Possible Causes**:
- LoRa module not connected
- Initialization failed
- Wrong GPIO pins configured
- Module not detected on SPI bus

**Tests Needed**:
```bash
# Check SPI devices
spi scan

# Manual LoRa init
lora init

# Check GPIO configuration
gpio status
```

## 📝 Test Execution Plan

### Phase 1: NDJSON Machine Mode (30 min)
1. Initialize machine mode in UI
2. Test optical TX profiles (all 3)
3. Test acoustic TX
4. Document which features work
5. Identify firmware limitations

### Phase 2: LED Patterns (15 min)
1. Test all 6 patterns
2. Verify smooth transitions
3. Test brightness levels
4. Test color accuracy
5. Test pattern switching

### Phase 3: Buzzer/Sound (30 min)
1. Test all 5 presets (coin, bump, power, oneup, morgio)
2. Test frequency adjustment (200-5000 Hz)
3. Test duration adjustment (100-2000 ms)
4. Test preset musical tones (C4-C5)
5. Identify which features work
6. Document firmware capabilities

### Phase 4: Communications (45 min)
1. Test LoRa initialization and transmission
2. Test Wi-Fi scan and connect
3. Test BLE advertising and notifications
4. Test Mesh network join and messaging
5. Document working protocols
6. Identify hardware dependencies

### Phase 5: Integration Testing (30 min)
1. Test UI → API → Firmware chain
2. Verify all buttons send correct commands
3. Test error handling
4. Test concurrent operations
5. Stress test with rapid commands

## 🛠️ Test Automation Script

Create `scripts/test_mycobrain_features.ps1`:
```powershell
# Automated MycoBrain feature test suite
# Tests all features systematically and logs results
```

## 📊 Expected Outcomes

### Fully Working Features
- [x] Basic LED RGB control
- [x] LED preset colors
- [x] Basic buzzer (beep at 1000Hz)
- [ ] LED patterns (to test)
- [ ] Optical TX (to test)
- [ ] Acoustic TX (to investigate)
- [ ] Buzzer presets (to test)
- [ ] Custom tones (to fix or document as unsupported)
- [ ] Communications protocols (to test)

### Features That May Not Work
- Custom tone duration/frequency (may require firmware update)
- Acoustic TX (may be ultrasonic or disabled)
- LoRa (may require hardware module)
- Wi-Fi (may require configuration)
- BLE (may require enabling)
- Mesh (may require other nodes)

---
**Next**: Create test scripts and execute comprehensive testing


