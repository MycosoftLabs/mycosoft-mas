# MYCA Dashboard Components & Integrations
## February 3, 2026

## Overview

This document details all dashboard components, widgets, pages, hooks, and services created to integrate with the MYCA Autonomous Scientific Architecture.

**IMPORTANT**: The main website is located at:
- **Local Development**: `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\`
- **URL**: http://localhost:3010
- **Scientific Section**: http://localhost:3010/scientific

Note: The `unifi-dashboard` in the MAS repository is deprecated.

---

## Dashboard Pages

### Scientific Section (`/scientific`)

| Route | Component | Description |
|-------|-----------|-------------|
| `/scientific` | `ScientificPage` | Main overview with stats, tabs for all subsections |
| `/scientific/lab` | `LabPage` | Laboratory instrument control, protocols, samples |
| `/scientific/simulation` | `SimulationPage` | Simulation center with GPU monitoring, job queue |
| `/scientific/experiments` | `ExperimentsPage` | Closed-loop experiment tracking and management |
| `/scientific/bio` | `BioPage` | FCI control, MycoBrain, signal analysis, genomics |
| `/scientific/devices` | `DevicesPage` | NatureOS device grid, telemetry, commands |
| `/scientific/memory` | `MemoryPage` | Conversation history, facts, knowledge graph |

### Layout

The scientific section uses a dedicated layout (`layout.tsx`) with:
- Sidebar navigation for all scientific subsections
- Quick stats panel showing active experiments, simulations, devices
- Responsive design (sidebar hidden on mobile)

---

## Widget Components

### Device Widgets (`components/widgets/devices/`)

| Component | Props | Description |
|-----------|-------|-------------|
| `DeviceCard` | `device`, `onSelect`, `onConfigure` | Card displaying device info, status, and controls |
| `DeviceGrid` | `onDeviceSelect` | Filterable grid of all devices with search |
| `TelemetryChart` | `deviceId`, `sensorType`, `title`, `height` | Real-time telemetry visualization |

**Usage:**
```tsx
import { DeviceCard, DeviceGrid, TelemetryChart } from "@/components/widgets/devices";

<DeviceGrid onDeviceSelect={(id) => setSelectedDevice(id)} />
<TelemetryChart deviceId={selectedDevice} sensorType="temperature" />
```

### Bio Widgets (`components/widgets/bio/`)

| Component | Props | Description |
|-----------|-------|-------------|
| `FCIMonitor` | - | Active FCI session monitoring with controls |
| `ElectrodeMap` | `rows`, `cols`, `electrodes`, `onElectrodeClick` | Interactive electrode array visualization |
| `SignalVisualizer` | `sessionId`, `channels`, `sampleRate` | Real-time signal waveform display |

**Usage:**
```tsx
import { FCIMonitor, ElectrodeMap, SignalVisualizer } from "@/components/widgets/bio";

<FCIMonitor />
<ElectrodeMap rows={8} cols={8} onElectrodeClick={(idx) => console.log(idx)} />
<SignalVisualizer channels={4} sampleRate={1000} />
```

### Simulation Widgets (`components/widgets/simulation/`)

| Component | Props | Description |
|-----------|-------|-------------|
| `SimulationProgress` | - | Active simulation list with progress and controls |
| `MyceliumNetworkViz` | `width`, `height` | Interactive mycelium network growth visualization |

**Usage:**
```tsx
import { SimulationProgress, MyceliumNetworkViz } from "@/components/widgets/simulation";

<SimulationProgress />
<MyceliumNetworkViz width={800} height={500} />
```

### NatureOS Widgets (`components/widgets/natureos/`)

| Component | Props | Description |
|-----------|-------|-------------|
| `EnvironmentDashboard` | - | Environmental metrics overview (temp, humidity, CO2, VOC) |
| `EventFeed` | - | Real-time event feed with severity indicators |
| `CommandCenter` | - | Device command interface with history |

**Usage:**
```tsx
import { EnvironmentDashboard, EventFeed, CommandCenter } from "@/components/widgets/natureos";

<EnvironmentDashboard />
<EventFeed />
<CommandCenter />
```

### Memory Widgets (`components/widgets/memory/`)

| Component | Props | Description |
|-----------|-------|-------------|
| `ConversationHistory` | - | Browse and view past conversations |
| `FactBrowser` | - | Search and filter stored facts |

**Usage:**
```tsx
import { ConversationHistory, FactBrowser } from "@/components/widgets/memory";

<ConversationHistory />
<FactBrowser />
```

### Safety Widgets (`components/widgets/safety/`)

| Component | Props | Description |
|-----------|-------|-------------|
| `SafetyMonitor` | - | Overall safety status with all metrics |
| `AuditLog` | - | Searchable/filterable audit log |

**Usage:**
```tsx
import { SafetyMonitor, AuditLog } from "@/components/widgets/safety";

<SafetyMonitor />
<AuditLog />
```

### Voice Components (`components/voice/`)

| Component | Props | Description |
|-----------|-------|-------------|
| `UnifiedVoiceProvider` | `children` | Context provider for voice capabilities |
| `VoiceButton` | - | Floating voice activation button |
| `VoiceOverlay` | `isOpen`, `onClose` | Full-screen voice interface |

**Usage:**
```tsx
import { UnifiedVoiceProvider, VoiceButton } from "@/components/voice";

<UnifiedVoiceProvider>
  <App />
  <VoiceButton />
</UnifiedVoiceProvider>
```

### Scientific Components (`components/scientific/`)

| Component | Description |
|-----------|-------------|
| `LabMonitor` | Laboratory instruments and experiments overview |
| `SimulationPanel` | Simulation type selection and management |
| `ExperimentTracker` | Experiment step tracking with progress |
| `HypothesisBoard` | Hypothesis creation and validation |

---

## React Hooks (`hooks/scientific/`)

### useNatureOS

```tsx
const { devices, events, loading, error, fetchDevices, registerDevice, sendCommand, getTelemetry } = useNatureOS();

// Register a new device
await registerDevice("mushroom1", { name: "Mushroom1-Alpha" });

// Send a command
await sendCommand(deviceId, "calibrate", {});

// Get telemetry
const telemetry = await getTelemetry(deviceId, 100);
```

### useSimulation

```tsx
const { simulations, loading, fetchSimulations, startSimulation, controlSimulation, getResults } = useSimulation();

// Start a simulation
await startSimulation({ type: "protein", name: "AlphaFold Job", config: { sequence: "..." } });

// Control simulation
await controlSimulation(simId, "pause");
await controlSimulation(simId, "resume");
await controlSimulation(simId, "cancel");

// Get results
const results = await getResults(simId);
```

### useBio

```tsx
const { sessions, loading, fetchSessions, startSession, controlSession, getSignals } = useBio();

// Start FCI session
await startSession("Pleurotus ostreatus", "PO-001");

// Control session
await controlSession(sessionId, "start");
await controlSession(sessionId, "stimulate");
await controlSession(sessionId, "stop");

// Get signals
const signals = await getSignals(sessionId);
```

---

## API Service (`lib/services/mycaApi.ts`)

The `MYCAApiService` class provides a typed interface to all MYCA APIs:

```tsx
import { mycaApi } from "@/lib/services";

// NatureOS
await mycaApi.getDevices();
await mycaApi.registerDevice("mushroom1", { name: "..." });
await mycaApi.sendCommand(deviceId, "calibrate", {});
await mycaApi.getTelemetry(deviceId);

// Scientific
await mycaApi.getSimulations();
await mycaApi.startSimulation("protein", { sequence: "..." });
await mycaApi.getExperiments();
await mycaApi.createExperiment("Test Exp", { params: {} });
await mycaApi.getHypotheses();
await mycaApi.createHypothesis("If X then Y");

// Bio
await mycaApi.getFCISessions();
await mycaApi.startFCISession("Ganoderma lucidum");
await mycaApi.controlFCISession(sessionId, "stimulate");

// Memory
await mycaApi.getConversations();
await mycaApi.getFacts("temperature");
await mycaApi.storeFact("preference", { value: 25 }, "user");
```

---

## API Routes

### NatureOS API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/natureos/devices` | GET | List all devices |
| `/api/natureos/devices` | POST | Register new device |
| `/api/natureos/telemetry` | GET | Get device telemetry |
| `/api/natureos/telemetry` | POST | Ingest telemetry |

### Scientific API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/scientific/simulation` | GET | List simulations |
| `/api/scientific/simulation` | POST | Start simulation |
| `/api/scientific/hypothesis` | GET | List hypotheses |
| `/api/scientific/hypothesis` | POST | Create hypothesis |

### Bio API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/bio/fci` | GET | List FCI sessions |
| `/api/bio/fci` | POST | Start FCI session |

---

## Integration Points

### Backend Services

The dashboard components connect to these MAS services:

| Service | Port | Description |
|---------|------|-------------|
| MAS Orchestrator | 8001 | Main API gateway |
| NatureOS Platform | 8010 | Device management |
| Signal Processor | 8011 | Biological signals |
| FCI Service | 8020 | FCI sessions |
| MycoBrain Service | 8021 | Neuromorphic compute |
| AlphaFold Service | 8030 | Protein prediction |
| Mycelium Simulator | 8031 | Network simulation |

### Environment Variables

```env
NEXT_PUBLIC_MAS_URL=http://192.168.0.188:8001
MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001
```

---

## File Structure

```
unifi-dashboard/src/
├── app/
│   ├── scientific/
│   │   ├── page.tsx           # Main overview
│   │   ├── layout.tsx         # Sidebar navigation
│   │   ├── lab/page.tsx       # Laboratory
│   │   ├── simulation/page.tsx # Simulations
│   │   ├── experiments/page.tsx # Experiments
│   │   ├── bio/page.tsx       # Bio interfaces
│   │   ├── devices/page.tsx   # NatureOS devices
│   │   └── memory/page.tsx    # Memory system
│   └── api/
│       ├── natureos/
│       │   ├── devices/route.ts
│       │   └── telemetry/route.ts
│       ├── scientific/
│       │   ├── simulation/route.ts
│       │   └── hypothesis/route.ts
│       └── bio/
│           └── fci/route.ts
├── components/
│   ├── scientific/
│   │   ├── LabMonitor.tsx
│   │   ├── SimulationPanel.tsx
│   │   ├── ExperimentTracker.tsx
│   │   └── HypothesisBoard.tsx
│   ├── voice/
│   │   ├── UnifiedVoiceProvider.tsx
│   │   ├── VoiceButton.tsx
│   │   └── VoiceOverlay.tsx
│   └── widgets/
│       ├── devices/
│       │   ├── DeviceCard.tsx
│       │   ├── DeviceGrid.tsx
│       │   ├── TelemetryChart.tsx
│       │   └── index.ts
│       ├── bio/
│       │   ├── FCIMonitor.tsx
│       │   ├── ElectrodeMap.tsx
│       │   ├── SignalVisualizer.tsx
│       │   └── index.ts
│       ├── simulation/
│       │   ├── SimulationProgress.tsx
│       │   ├── MyceliumNetworkViz.tsx
│       │   └── index.ts
│       ├── natureos/
│       │   ├── EnvironmentDashboard.tsx
│       │   ├── EventFeed.tsx
│       │   ├── CommandCenter.tsx
│       │   └── index.ts
│       ├── memory/
│       │   ├── ConversationHistory.tsx
│       │   ├── FactBrowser.tsx
│       │   └── index.ts
│       └── safety/
│           ├── SafetyMonitor.tsx
│           ├── AuditLog.tsx
│           └── index.ts
├── hooks/
│   └── scientific/
│       ├── useNatureOS.ts
│       ├── useSimulation.ts
│       ├── useBio.ts
│       └── index.ts
└── lib/
    └── services/
        ├── mycaApi.ts
        └── index.ts
```

---

## Component Count Summary

| Category | Count |
|----------|-------|
| Dashboard Pages | 7 |
| Scientific Components | 4 |
| Voice Components | 3 |
| Device Widgets | 3 |
| Bio Widgets | 3 |
| Simulation Widgets | 2 |
| NatureOS Widgets | 3 |
| Memory Widgets | 2 |
| Safety Widgets | 2 |
| React Hooks | 3 |
| API Routes | 5 |
| Service Classes | 1 |
| **Total** | **38** |

---

## Next Steps

1. **Testing**: Add Jest/React Testing Library tests for all components
2. **Storybook**: Create Storybook stories for component documentation
3. **WebSocket**: Add real-time updates via WebSocket for live data
4. **Charts**: Integrate Recharts for advanced telemetry visualization
5. **3D Visualization**: Add Three.js for protein structure and network visualization

---

*Documentation created: February 3, 2026*
