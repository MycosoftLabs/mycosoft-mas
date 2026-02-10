# Fungi Compute Application

**Created:** February 9, 2026  
**Status:** Complete Implementation  
**Location:** `/natureos/fungi-compute`

## Overview

Fungi Compute is Mycosoft's flagship biological computing visualization platform. It provides real-time monitoring, analysis, and interaction with Fungal Computer Interface (FCI) devices, enabling users to observe and interpret bioelectric signals from mycelium networks.

## Key Features

### 1. Real-Time Signal Visualization
- **Oscilloscope**: Multi-channel waveform display with CRT glow effects, configurable time/voltage divisions
- **Spectrum Analyzer**: FFT-based frequency analysis with GFST band markers and waterfall spectrogram
- **Signal Fingerprint**: Unique identity visualization with radar charts and pattern matching

### 2. SDR-Style Signal Processing
- Bandpass filtering (0.01-100 Hz configurable)
- 50/60 Hz notch filtering with harmonics
- EMF rejection presets (motor noise, fluorescent, HVAC, switching supply)
- RF rejection presets (broadband, cellular, WiFi, Bluetooth)
- Adaptive artifact rejection
- Automatic gain control (AGC)

### 3. Pattern Detection
Based on Global Fungi Symbiosis Theory (GFST), recognizes 10+ distinct patterns:
- **Metabolic**: baseline, active_growth, nutrient_seeking
- **Environmental**: temperature_stress, chemical_stress
- **Communication**: network_communication, action_potential
- **Predictive**: seismic_precursor
- **Defensive**: defense_activation
- **Reproductive**: sporulation_initiation

### 4. Bi-Directional Stimulation
Send electrical stimuli to mycelium via:
- Configurable waveforms (sine, square, triangle, pulse)
- Adjustable frequency (0.1-50 Hz), amplitude (0-5 mV), duration (0.1-10s)
- Multi-channel support (4 channels)
- Safety limits enforced

### 5. NLM Integration
Nature Learning Model analysis provides:
- Growth phase identification
- Bioactivity predictions (compound production)
- Environmental correlation analysis
- AI-generated recommendations

### 6. External System Integration
- **Earth2 Simulator**: Weather, barometric, seismic correlations
- **CREP Dashboard**: Environmental sensor data overlay
- **Petri Dish Simulator**: Virtual growth sync and overlay
- **M-Wave**: Seismic event correlation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Fungi Compute Frontend                  │
│                    (Next.js / React / Canvas)               │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Oscilloscope │ │  Spectrum    │ │ Signal Fingerprint   │ │
│  │   (Canvas)   │ │  Analyzer    │ │    (SVG Radar)       │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ Event Mempool│ │ Pattern      │ │ SDR Filter Panel     │ │
│  │ (Blockchain) │ │ Timeline     │ │                      │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                     WebSocket Client                        │
│                   (Real-time Streaming)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     MAS Backend (192.168.0.188:8001)        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐   │
│  │              FCI WebSocket Router                     │   │
│  │  - Real-time signal streaming                        │   │
│  │  - SDR config updates                                │   │
│  │  - Stimulation command dispatch                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              SDR Pipeline (bio/sdr_pipeline.py)       │   │
│  │  - Biquad IIR filters (LP, HP, notch)                │   │
│  │  - FFT spectrum analysis                             │   │
│  │  - GFST pattern classification                       │   │
│  │  - Spike detection                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              FCI API Router                           │   │
│  │  - Device registration                               │   │
│  │  - Signal processing                                 │   │
│  │  - Pattern library                                   │   │
│  │  - HPL execution                                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                MINDEX Database (192.168.0.189)              │
│  - Signal time-series storage (PostgreSQL + TimescaleDB)   │
│  - Pattern vectors (pgvector)                              │
│  - Event correlation cache (Redis)                         │
└─────────────────────────────────────────────────────────────┘
```

## File Structure

### Frontend (website repo)

```
website/
├── app/natureos/fungi-compute/
│   ├── page.tsx                    # Main page entry
│   └── loading.tsx                 # Loading skeleton
├── components/fungi-compute/
│   ├── index.ts                    # Component exports
│   ├── dashboard.tsx               # Main dashboard layout
│   ├── oscilloscope.tsx            # Waveform visualization
│   ├── spectrum-analyzer.tsx       # FFT display
│   ├── signal-fingerprint.tsx      # Radar chart identity
│   ├── event-mempool.tsx           # Event log (blockchain-style)
│   ├── pattern-timeline.tsx        # Pattern history
│   ├── sdr-filter-panel.tsx        # SDR controls
│   ├── stimulation-panel.tsx       # Waveform generator
│   ├── nlm-panel.tsx               # NLM analysis display
│   ├── device-selector.tsx         # Device picker
│   ├── connection-status.tsx       # WebSocket status
│   ├── device-map.tsx              # Location map
│   ├── petri-dish-link.tsx         # Petri Dish sync
│   ├── earth-correlation.tsx       # Earth2/CREP correlation
│   └── glass-panel.tsx             # Glass UI components
├── lib/fungi-compute/
│   ├── index.ts                    # Library exports
│   ├── types.ts                    # TypeScript interfaces
│   ├── hooks.ts                    # React hooks
│   └── websocket-client.ts         # WebSocket manager
└── app/api/fci/
    ├── devices/route.ts            # Device list/register
    ├── fingerprint/[deviceId]/route.ts
    ├── nlm/[deviceId]/route.ts
    ├── stimulate/route.ts
    ├── events/route.ts
    ├── ws-status/route.ts
    ├── gfst/route.ts
    ├── patterns/route.ts
    └── telemetry/route.ts
```

### Backend (MAS repo)

```
mycosoft_mas/
├── bio/
│   ├── fci.py                      # FCI session management
│   └── sdr_pipeline.py             # SDR filter pipeline
└── core/routers/
    ├── fci_api.py                  # FCI REST endpoints
    └── fci_websocket.py            # WebSocket streaming
```

## API Endpoints

### REST API (via Next.js proxies)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/fci/devices` | List all FCI devices |
| POST | `/api/fci/devices` | Register new device |
| GET | `/api/fci/fingerprint/{deviceId}` | Get signal fingerprint |
| GET | `/api/fci/nlm/{deviceId}` | Get NLM analysis |
| POST | `/api/fci/stimulate` | Send stimulation command |
| GET | `/api/fci/events` | Get recent events |
| GET | `/api/fci/gfst/patterns` | Get GFST pattern library |
| GET | `/api/fci/ws-status` | WebSocket connection status |

### WebSocket API

Connect to: `ws://192.168.0.188:8001/api/fci/ws/stream/{device_id}`

**Messages from server:**
- `{"type": "sample", "timestamp": "...", "channels": [...]}`
- `{"type": "spectrum", "data": {...}}`
- `{"type": "pattern", "data": {...}}`
- `{"type": "event", "data": {...}}`

**Messages to server:**
- `{"type": "sdr_config", "config": {...}}`
- `{"type": "stimulate", "command": {...}}`
- `{"type": "set_pattern", "pattern": "..."}`  *(dev mode)*

## UI/UX Design

### Visual Theme
- **Glass Material Design**: `backdrop-blur-xl`, translucent panels, cyan/emerald accents
- **Tron-Inspired Retro**: CRT scanlines, glow effects, neon borders
- **Dark Theme**: Navy background (#0A1929), cyan text (#00C8FF)

### Color Palette
```typescript
const FUNGI_COLORS = {
  bg: "#0A1929",
  border: "#0F3460",
  glow: "#00FF88",
  text: "#00C8FF",
  metabolic: "#00FF88",
  ch1: "#00C8FF",
  ch2: "#FF6B35",
  ch3: "#9B59B6",
  ch4: "#F1C40F",
}
```

## SDR Filter Presets

| Preset | Bandpass | Notch | EMF | RF | Use Case |
|--------|----------|-------|-----|----|----|
| Lab | 0.01-50 Hz | 50+60 Hz | Fluorescent | None | Clean lab |
| Field | 0.1-30 Hz | 50+60 Hz | Motor | Broadband | Outdoor |
| Urban | 0.1-20 Hz | 50+60 Hz | Switching | Cellular | High-EMF |
| Clean Room | 0.01-100 Hz | None | None | None | Minimal |

## GFST Pattern Categories

| Category | Patterns | Frequency Range | Description |
|----------|----------|-----------------|-------------|
| Metabolic | baseline, active_growth, nutrient_seeking | 0.1-5 Hz | Growth and metabolism |
| Environmental | temperature_stress, chemical_stress | 0.2-10 Hz | Stress responses |
| Communication | network_communication, action_potential | 0.1-20 Hz | Signaling |
| Predictive | seismic_precursor | 0.01-0.1 Hz | Early warning |
| Defensive | defense_activation | 2-8 Hz | Defense response |
| Reproductive | sporulation_initiation | 0.5-2 Hz | Reproduction |

## Dependencies

### Frontend
- React 18+, Next.js 15
- Shadcn UI, Radix UI
- Tailwind CSS
- HTML5 Canvas (oscilloscope, spectrum)
- WebSocket API

### Backend
- Python 3.11+
- FastAPI
- NumPy (FFT, signal processing)
- Pydantic (data validation)

## Development

### Start Frontend
```bash
cd website
npm run dev:next-only
# Visit http://localhost:3010/natureos/fungi-compute
```

### Test WebSocket
```javascript
const ws = new WebSocket('ws://192.168.0.188:8001/api/fci/ws/stream/test-device')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

## Future Enhancements

1. **MapLibre Integration**: Replace SVG map with full MapLibre GL JS
2. **3D Mycelium Visualization**: WebGL-based network rendering
3. **Machine Learning**: TensorFlow.js for client-side pattern detection
4. **Multi-Device Correlation**: Cross-device signal analysis
5. **Historical Playback**: Time-travel through recorded sessions
6. **Alert System**: Real-time notifications for significant patterns

## Related Documentation

- [FCI Implementation Guide](./FCI_IMPLEMENTATION_FEB09_2026.md)
- [SDR Pipeline Technical Reference](./SDR_PIPELINE_FEB09_2026.md)
- [GFST Theory Background](./GFST_THEORY_FEB03_2026.md)
- [Mycorrhizae Protocol](./MYCORRHIZAE_PROTOCOL_FEB09_2026.md)
- [NatureOS Overview](./NATUREOS_OVERVIEW.md)

---

*Fungi Compute represents the cutting edge of biological computing interfaces, providing an unprecedented window into the electrical activity of mycelium networks.*
