# Fungal Computer Interface (FCI) System Documentation
**Date:** February 6, 2026  
**Version:** 2.0  
**Status:** Production Ready

---

## Overview

The Fungal Computer Interface (FCI) is a bio-electronic system that enables communication with living mycelium networks. It provides real-time signal recording, stimulation capabilities, and data analysis for fungal computing research.

---

## Components

### 1. FCI Monitor (`fci-monitor.tsx`)
Main interface for managing FCI recording sessions.

**Features:**
- Start new recording sessions with species and strain metadata
- Real-time session status (recording, stimulating, idle, paused)
- Control actions: pause, resume, stop, stimulate
- Signal quality indicator
- Toast notifications for all user actions

**User Actions:**
| Action | Description | Feedback |
|--------|-------------|----------|
| New Session | Start recording from fungal specimen | Loading toast → Success/Error |
| Pause | Pause active recording | Toast notification |
| Resume | Resume paused session | Toast notification |
| Stop | End session completely | Toast notification |
| Stimulate | Send electrical stimulation | Toast notification |
| Refresh | Reload session data | Animated spinner |

---

### 2. Electrode Map (`electrode-map.tsx`)
Visual representation of the electrode array interfacing with mycelium.

**Features:**
- 8x8 electrode grid (configurable)
- Color-coded status:
  - 🟢 Green: Low signal (normal)
  - 🟡 Yellow: Medium signal
  - 🔴 Red: High signal (active area)
  - ⚪ Gray: Inactive
- Electrode selection for batch operations
- Impedance and signal tooltips on hover
- Active electrode count display

---

## API Endpoints

### FCI Sessions
```
GET  /api/bio/fci              → List all FCI sessions
POST /api/bio/fci              → Start new session
POST /api/bio/fci/{id}/pause   → Pause session
POST /api/bio/fci/{id}/start   → Resume session
POST /api/bio/fci/{id}/stop    → Stop session
POST /api/bio/fci/{id}/stimulate → Trigger stimulation
```

### Backend (MAS)
```
GET  /bio/fci/sessions         → All sessions with electrode data
POST /bio/fci/sessions         → Create session
POST /bio/fci/sessions/{id}/{action} → Control session
```

---

## Data Hook

**File:** `hooks/scientific/use-fci.ts`

```typescript
const { 
  sessions,           // Array of FCI sessions
  electrodeStatus,    // Array of electrode states
  signalQuality,      // Overall signal quality (0-100)
  isLive,             // API connectivity status
  isLoading,          // Loading state
  startSession,       // Function to start new session
  controlSession,     // Function to control session
  refresh             // Manual refresh function
} = useFCI()
```

**Refresh Interval:** 2 seconds (for real-time signal updates)

---

## Data Types

### FCI Session
```typescript
interface FCISession {
  id: string
  species: string              // e.g., "Pleurotus ostreatus"
  strain?: string              // e.g., "PO-001"
  status: 'recording' | 'stimulating' | 'idle' | 'paused'
  duration: number             // seconds
  electrodesActive: number     // number of active electrodes
  totalElectrodes: number      // total electrodes in array
  sampleRate: number           // Hz
}
```

### Electrode Status
```typescript
interface ElectrodeStatus {
  active: boolean
  signal: number       // 0-100 (intensity)
  impedance?: number   // kΩ
}
```

---

## Usage Example

```tsx
import { FCIMonitor } from '@/components/scientific/fci-monitor'
import { ElectrodeMap } from '@/components/scientific/electrode-map'

export function FCIPage() {
  return (
    <div className="grid grid-cols-2 gap-6">
      <FCIMonitor />
      <ElectrodeMap rows={8} cols={8} />
    </div>
  )
}
```

---

## Future Enhancements

1. **Real-time Signal Visualization**
   - Waveform display for each electrode
   - FFT analysis for frequency components
   - Spike detection and marking

2. **Stimulation Protocols**
   - Custom stimulation patterns
   - Frequency and amplitude control
   - Protocol library

3. **Data Export**
   - Export recordings to standard formats
   - Integration with analysis tools
   - Cloud backup to MINDEX

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cached" badge showing | MAS backend not responding |
| No sessions displayed | Backend offline or no active sessions |
| Stimulation not working | Check electrode connectivity |
| Low signal quality | Verify mycelium sample placement |

---

## Related Documentation
- [Scientific Systems Overview](./SCIENTIFIC_SYSTEMS_COMPLETE_FEB06_2026.md)
- [Bio-Compute Dashboard](./BIO_COMPUTE_FEB06_2026.md)
- [MAS Orchestrator Setup](./MAS_SETUP.md)
