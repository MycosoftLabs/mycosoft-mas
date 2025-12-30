# Science Communication Features

## Overview

MycoBrain Advanced includes specialized features for scientific experimentation and unconventional data communication:

1. **Optical Modem (LiFi)** - Data transmission via visible light
2. **Acoustic Modem** - Data transmission via sound
3. **Stimulus Engine** - Controlled stimuli for organism experiments

These features are designed to be:
- Non-blocking (don't interfere with sensor readings)
- Timing-accurate (millisecond precision)
- Configurable (parameters can be tuned for different scenarios)
- Documented (event logging for reproducibility)

---

## Optical Modem (LiFi)

### Concept

The optical modem transmits data by modulating the NeoPixel LED on/off states. This creates a "visible light communication" (VLC) channel that can be received by:

- Smartphone cameras (using video analysis)
- Photodiodes or light sensors
- Other MycoBrain devices with appropriate sensors

### Profiles

#### 1. Camera OOK (On-Off Keying)

**Best for:** Smartphone cameras, webcams

The simplest encoding where:
- LED ON = bit 1
- LED OFF = bit 0

**Rate:** 5-20 Hz (limited by camera frame rate)

**Usage:**
```json
{
  "cmd": "optx.start",
  "profile": "camera_ook",
  "rate_hz": 10,
  "payload_b64": "SGVsbG8=",
  "rgb": [255, 255, 255]
}
```

#### 2. Camera Manchester

**Best for:** Better synchronization, error resilience

Manchester encoding provides a transition for every bit:
- Bit 1 = Low-to-High transition
- Bit 0 = High-to-Low transition

This doubles the symbol rate but provides built-in clock recovery.

**Usage:**
```json
{
  "cmd": "optx.start",
  "profile": "camera_manchester",
  "rate_hz": 10,
  "payload_b64": "SGVsbG8=",
  "rgb": [0, 255, 0]
}
```

### Frame Structure

```
[Preamble] [Length] [Payload] [CRC16]
```

- **Preamble:** 8 alternating bits (0xAA) for sync
- **Length:** 1 byte payload length
- **Payload:** Variable length data
- **CRC16:** 2 bytes for error detection

### Receiving Data

To receive optical modem data, you can use:

1. **Smartphone camera + analysis app**
   - Record video at highest frame rate
   - Process frames to detect LED state changes
   - Decode Manchester/OOK symbols

2. **Photodiode connected to another MycoBrain**
   - Use analog input to detect light levels
   - Apply threshold to determine on/off
   - Decode bit stream

3. **Dedicated optical receiver module**
   - Fast response photodiode
   - Comparator circuit
   - Digital output for microcontroller

---

## Acoustic Modem

### Concept

The acoustic modem transmits data using audio tones from the buzzer. This creates an "audio data link" receivable by microphones.

Inspired by:
- **ggwave** - Audio-based data transmission library
- **gibberlink** - AI voice-to-data experiments
- **DTMF** - Dual-tone multi-frequency signaling

### Profiles

#### 1. Simple FSK (Frequency Shift Keying)

**Best for:** Reliability, simplicity

Uses two frequencies to represent bits:
- f0 (e.g., 1800 Hz) = bit 0
- f1 (e.g., 2400 Hz) = bit 1

**Symbol rate:** 20-50 symbols/second typical

**Usage:**
```json
{
  "cmd": "aotx.start",
  "profile": "simple_fsk",
  "symbol_ms": 30,
  "f0": 1800,
  "f1": 2400,
  "payload_b64": "SGVsbG8=",
  "preamble_ms": 200
}
```

#### 2. ggwave-like (Planned)

Multi-tone encoding for higher bandwidth and robustness:
- Multiple carrier frequencies
- Error correction codes
- Better ambient noise rejection

### Frame Structure

```
[Preamble] [Sync] [Length] [Payload] [CRC16]
```

- **Preamble:** 200ms alternating tones for sync
- **Sync:** Specific tone sequence for frame start
- **Length:** 1 byte payload length
- **Payload:** FSK-encoded data
- **CRC16:** Error detection

### Receiving Data

1. **Microphone + FFT analysis**
   - Sample audio at 8kHz+
   - Apply FFT to detect dominant frequency
   - Map frequency to bit value
   - Decode bit stream

2. **Another MycoBrain with microphone module**
   - I2S microphone peripheral
   - Real-time frequency detection
   - Protocol decoder

---

## Stimulus Engine

### Concept

The stimulus engine provides controlled, repeatable light and sound patterns for experiments with organisms (fungi, plants, insects, etc.).

**Key difference from modems:**
- Stimuli are designed for biological response, not data transmission
- Patterns are simple and repeatable
- Precise timing with logging for reproducibility

### Light Stimulus

Configure periodic light pulses with precise timing:

```json
{
  "cmd": "stim.light",
  "rgb": [255, 0, 0],
  "on_ms": 500,
  "off_ms": 2000,
  "ramp_ms": 100,
  "repeat": 100,
  "delay_ms": 5000
}
```

**Parameters:**
- `rgb`: Color of light stimulus
- `on_ms`: Duration LED is on
- `off_ms`: Duration LED is off
- `ramp_ms`: Fade in/out time (0 = instant on/off)
- `repeat`: Number of cycles (0 = infinite)
- `delay_ms`: Initial delay before starting

**Applications:**
- Circadian rhythm studies
- Phototropism experiments
- Bioluminescence triggering
- Fungal light response research

### Sound Stimulus

Configure periodic sound pulses:

```json
{
  "cmd": "stim.sound",
  "hz": 440,
  "on_ms": 100,
  "off_ms": 900,
  "sweep_hz": 0,
  "repeat": 50,
  "delay_ms": 0
}
```

**Parameters:**
- `hz`: Base frequency
- `on_ms`: Duration tone is on
- `off_ms`: Silence duration
- `sweep_hz`: Frequency modulation range
- `repeat`: Number of cycles
- `delay_ms`: Initial delay

**Applications:**
- Acoustic response studies
- Vibrational communication research
- Sound-triggered behaviors
- Frequency preference testing

### Combined Stimulus

Run synchronized light and sound stimuli:

```json
{
  "cmd": "stim.combined",
  "light": {
    "rgb": [0, 255, 0],
    "on_ms": 200,
    "off_ms": 800
  },
  "sound": {
    "hz": 1000,
    "on_ms": 200,
    "off_ms": 800
  },
  "sync": true
}
```

### Event Logging

Enable logging for experiment documentation:

```
stim logging on
```

Events are recorded with timestamps:
```json
{
  "type": "stimulus_log",
  "count": 10,
  "events": [
    {"t": 5000, "e": "light_start"},
    {"t": 5000, "e": "light_on"},
    {"t": 5500, "e": "light_off"},
    {"t": 6500, "e": "light_on"},
    ...
  ]
}
```

---

## Example Applications

### 1. Fungal Light Response Study

```json
// Blue light stimulus, 30 minutes
{
  "cmd": "stim.light",
  "rgb": [0, 0, 255],
  "on_ms": 60000,
  "off_ms": 60000,
  "repeat": 15,
  "delay_ms": 0
}
```

### 2. Plant Growth Monitoring + Data Backhaul

Use optical modem to send sensor data to a camera-equipped monitoring station:

```json
// Every minute, transmit sensor summary
{
  "cmd": "optx.start",
  "profile": "camera_manchester",
  "rate_hz": 10,
  "payload_b64": "eyJ0IjoyNS41LCJoIjo2NX0=",
  "rgb": [255, 255, 255]
}
```

### 3. Mycelial Network Communication Research

Use acoustic modem between MycoBrain nodes buried in soil:

```json
{
  "cmd": "aotx.start",
  "profile": "simple_fsk",
  "f0": 200,
  "f1": 400,
  "symbol_ms": 50,
  "payload_b64": "cGluZw=="
}
```

Low frequencies propagate better through dense media.

---

## Best Practices

1. **Isolation:** Keep stimulus mode and modem mode separate to avoid confusing organisms with data patterns

2. **Calibration:** Test optical modem range and reliability before deploying

3. **Documentation:** Always enable logging for reproducible experiments

4. **Non-blocking:** All operations are non-blocking; sensor readings continue during transmission

5. **Power considerations:** Extended LED/buzzer use increases power consumption

