# Laboratory Monitoring System Documentation
**Date:** February 6, 2026  
**Version:** 2.0  
**Status:** Production Ready

---

## Overview

The Laboratory Monitoring System provides real-time visibility into all laboratory instruments, simulations, experiments, hypotheses, and safety metrics. It serves as the central nervous system for the MYCA scientific platform.

---

## Core Components

### 1. Lab Monitor (`lab-monitor.tsx`)
Real-time laboratory instrument status and control.

**Features:**
- Instrument status display (online, offline, calibrating, error)
- Last calibration timestamp
- Active experiment assignments
- One-click calibration with loading feedback
- Auto-refresh every 5 seconds

**Instrument Types:**
| Type | Description |
|------|-------------|
| Spectrometer | Optical analysis |
| Incubator | Temperature-controlled growth |
| Microscope | Visual inspection |
| Sensor Array | Environmental monitoring |
| Bioreactor | Cultivation systems |

---

### 2. Simulation Panel (`simulation-panel.tsx`)
Create and manage scientific simulations.

**Features:**
- Create new simulations with name and type
- Control simulation state (pause, resume, cancel)
- Real-time progress tracking
- Result visualization when complete

**Simulation Types:**
| Type | Description |
|------|-------------|
| Growth Model | Mycelium growth prediction |
| Network Flow | Signal propagation modeling |
| Environmental | Climate and habitat simulation |
| Molecular | Protein and enzyme modeling |

---

### 3. Experiment Tracker (`experiment-tracker.tsx`)
Full lifecycle experiment management.

**Features:**
- Create experiments with detailed metadata
- Track through phases (planning → running → completed)
- Phase-by-phase progress visualization
- Control actions (start, pause, stop)

**Experiment Phases:**
1. Planning
2. Preparation
3. Execution
4. Data Collection
5. Analysis
6. Reporting

---

### 4. Hypothesis Board (`hypothesis-board.tsx`)
AI-assisted hypothesis generation and testing.

**Features:**
- Create hypotheses with predictions
- Confidence level tracking
- One-click hypothesis testing
- Results and validation display

**Status Flow:**
```
Proposed → Testing → Validated/Rejected
```

---

### 5. Safety Monitor (`safety-monitor.tsx`)
Real-time safety metrics and alerts.

**Features:**
- Overall safety status badge
- Individual metric cards with progress bars
- Color-coded alerts (green/yellow/red)
- Auto-refresh with cached data indication

**Monitored Metrics:**
| Metric | Safe Range |
|--------|-----------|
| Temperature | 20-26°C |
| Humidity | 60-90% |
| CO2 Levels | < 1000 ppm |
| Air Quality | > 80% |
| Equipment Status | All Online |

---

## API Endpoints

### Lab Instruments
```
GET  /api/scientific/lab                    → List instruments
POST /api/scientific/lab/{id}/calibrate     → Calibrate instrument
```

### Simulations
```
GET  /api/scientific/simulation             → List simulations
POST /api/scientific/simulation             → Create simulation
POST /api/scientific/simulation/{id}/{action} → Control simulation
```

### Experiments
```
GET  /api/scientific/experiments            → List experiments
POST /api/scientific/experiments            → Create experiment
POST /api/scientific/experiments/{id}/{action} → Control experiment
```

### Hypotheses
```
GET  /api/scientific/hypotheses             → List hypotheses
POST /api/scientific/hypotheses             → Create hypothesis
POST /api/scientific/hypotheses/{id}/test   → Test hypothesis
```

### Safety
```
GET  /api/scientific/safety                 → Safety status
```

---

## Data Hooks

### useLabInstruments
```typescript
const { instruments, isLive, isLoading, calibrate, refresh } = useLabInstruments()
```

### useSimulations
```typescript
const { simulations, isLive, isLoading, create, control, refresh } = useSimulations()
```

### useExperiments
```typescript
const { experiments, isLive, isLoading, create, control, refresh } = useExperiments()
```

### useHypotheses
```typescript
const { hypotheses, isLive, isLoading, create, test, refresh } = useHypotheses()
```

### useSafety
```typescript
const { overallStatus, metrics, isLive, isLoading, refresh } = useSafety()
```

---

## Dashboard Page (`scientific/page.tsx`)

The main dashboard aggregates data from all components:

```tsx
// Stats fetched from /api/scientific/stats
{
  activeExperiments: 5,
  runningSimulations: 3,
  pendingHypotheses: 12,
  instrumentsOnline: 8,
  safetyStatus: 'nominal'
}
```

### Layout
```
┌─────────────────────────────────────────────────────────────┐
│                    Summary Stats Cards                       │
├─────────────────────┬───────────────────────────────────────┤
│   Lab Monitor       │          Simulation Panel              │
├─────────────────────┼───────────────────────────────────────┤
│ Experiment Tracker  │         Hypothesis Board               │
├─────────────────────┴───────────────────────────────────────┤
│                    Safety Monitor                            │
└─────────────────────────────────────────────────────────────┘
```

---

## User Experience Features

### Toast Notifications
All user actions provide immediate feedback:
- **Loading**: Shows progress indicator
- **Success**: Green confirmation message
- **Error**: Red error message with details

### Loading States
- Buttons disable during operations
- Spinners indicate processing
- Progress bars show long operations

### Cached Data Indicators
When backend is unavailable:
- Yellow "Cached" badge appears
- Last known data is displayed
- User can still trigger refresh

### Auto-Refresh
Components refresh automatically:
- Lab instruments: 5 seconds
- Simulations: 5 seconds
- Experiments: 5 seconds
- Safety: 5 seconds
- FCI: 2 seconds (high-frequency signals)

---

## Usage Example

```tsx
import { LabMonitor } from '@/components/scientific/lab-monitor'
import { SimulationPanel } from '@/components/scientific/simulation-panel'
import { ExperimentTracker } from '@/components/scientific/experiment-tracker'
import { HypothesisBoard } from '@/components/scientific/hypothesis-board'
import { SafetyMonitor } from '@/components/scientific/safety-monitor'

export default function ScientificDashboard() {
  return (
    <div className="grid grid-cols-2 gap-6">
      <LabMonitor />
      <SimulationPanel />
      <ExperimentTracker />
      <HypothesisBoard />
      <div className="col-span-2">
        <SafetyMonitor />
      </div>
    </div>
  )
}
```

---

## Integration with Backend

### MAS Orchestrator
All data flows through the MAS Orchestrator:
```
Frontend → Next.js API Route → MAS Orchestrator → PostgreSQL/MINDEX
```

### Environment Variables
```env
NEXT_PUBLIC_MAS_URL=http://192.168.0.188:8001
NEXT_PUBLIC_WS_URL=ws://192.168.0.188:8001/ws
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| All "Cached" badges | MAS Orchestrator not running |
| Calibration fails | Check instrument connectivity |
| Simulation stuck | Verify compute resources |
| Safety warning | Check environmental controls |
| Data not updating | Clear browser cache, refresh |

---

## Related Documentation
- [Scientific Systems Overview](./SCIENTIFIC_SYSTEMS_COMPLETE_FEB06_2026.md)
- [FCI System](./FCI_SYSTEM_FEB06_2026.md)
- [Bio-Compute](./BIO_COMPUTE_FEB06_2026.md)
- [Autonomous Experiments](./AUTONOMOUS_EXPERIMENTS_FEB06_2026.md)
