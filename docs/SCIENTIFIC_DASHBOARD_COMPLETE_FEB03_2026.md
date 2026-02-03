# MYCA Scientific Dashboard - Complete Documentation
## February 3, 2026

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Backend Architecture](#backend-architecture)
3. [Frontend Architecture](#frontend-architecture)
4. [Integration Status](#integration-status)
5. [Critical Issues](#critical-issues)
6. [Upgrade Plan - Phase 1: Core Functionality](#upgrade-plan-phase-1)
7. [Upgrade Plan - Phase 2: Real Data Integration](#upgrade-plan-phase-2)
8. [Upgrade Plan - Phase 3: Advanced Features](#upgrade-plan-phase-3)
9. [Implementation Priority](#implementation-priority)

---

## Current State Analysis

### What Was Built

| Component | Status | Functionality |
|-----------|--------|---------------|
| Scientific Dashboard Page | Created | Displays stats cards and tabbed components |
| Lab Monitor | Created | Shows instruments, calibrate button |
| Simulation Panel | Created | Shows simulations, create/control buttons |
| Experiment Tracker | Created | Shows experiments, start/pause buttons |
| Hypothesis Board | Created | Shows hypotheses, test button |
| FCI Monitor | Created | Shows FCI sessions, control buttons |
| Electrode Map | Created | Visual electrode grid |
| Safety Monitor | Created | Safety metrics display |
| Bio Page | Created | FCI and MycoBrain overview |

### What Actually Works

| Feature | Works? | Notes |
|---------|--------|-------|
| Fetching data from APIs | Partial | Falls back to mock data when backend unavailable |
| Creating new items | No | Backend not running, returns mock response |
| Controlling items | No | Backend not running, simulated responses |
| Real-time updates | No | WebSocket not connected |
| Live telemetry | No | No real devices connected |
| MycoBrain compute | No | Backend simulation only |

### Why It Feels Useless

1. **No Real Backend Running**: The MAS Orchestrator at 192.168.0.188:8001 is not running or not accessible
2. **Mock Data Only**: All components show static fallback data
3. **No Actions Work**: Buttons trigger API calls but nothing persists
4. **No Real Devices**: No NatureOS devices sending telemetry
5. **No WebSocket**: No real-time updates flowing

---

## Backend Architecture

### MAS Orchestrator (192.168.0.188:8001)

```
mycosoft_mas/
├── core/
│   ├── myca_main.py              # FastAPI app entry point
│   ├── routers/
│   │   ├── scientific_api.py     # /scientific/* endpoints
│   │   ├── scientific_ws.py      # WebSocket /ws/scientific
│   │   ├── mindex_query.py       # /mindex/* endpoints
│   │   ├── platform_api.py       # /platform/* endpoints
│   │   ├── autonomous_api.py     # /autonomous/* endpoints
│   │   └── bio_api.py            # /bio/* endpoints
│   └── autonomous/
│       ├── experiment_engine.py  # Auto experiment logic
│       └── hypothesis_engine.py  # AI hypothesis generation
├── bio/
│   ├── mycobrain_production.py   # MycoBrain compute system
│   └── dna_storage.py            # DNA data storage
└── mindex/
    ├── database.py               # SQLite database
    └── memory_bridge.py          # PostgreSQL connection
```

### API Endpoints Created

| Prefix | Router | Endpoints |
|--------|--------|-----------|
| /scientific | scientific_api | Lab, Simulation, Experiments, Hypotheses, FCI, Safety |
| /ws/scientific | scientific_ws | WebSocket for real-time events |
| /mindex | mindex_query | Query, Vector Search, Knowledge Graph, Species |
| /platform | platform_api | Organizations, Members, Federation, Audit |
| /autonomous | autonomous_api | Auto Experiments, Hypothesis Generation, Literature |
| /bio | bio_api | MycoBrain Compute, DNA Storage |

### Data Storage

| System | Type | Location | Status |
|--------|------|----------|--------|
| MINDEX | SQLite | data/mindex/mindex.db | Exists |
| MINDEX | PostgreSQL | 192.168.0.188:5432 | Needs verification |
| Voice Feedback | SQLite | data/voice_feedback.db | Exists |
| Redis | Cache | 192.168.0.188:6379 | Needs verification |

---

## Frontend Architecture

### Website (localhost:3010)

```
website/
├── app/
│   ├── scientific/
│   │   ├── page.tsx              # Main dashboard
│   │   ├── layout.tsx            # Navigation sidebar
│   │   ├── lab/page.tsx          # Lab instruments page
│   │   ├── simulation/page.tsx   # Simulations page
│   │   ├── experiments/page.tsx  # Experiments page
│   │   ├── bio/page.tsx          # Bio interfaces page
│   │   ├── memory/page.tsx       # Memory systems page
│   │   ├── 3d/page.tsx           # 3D visualization
│   │   ├── autonomous/page.tsx   # Autonomous research
│   │   └── bio-compute/page.tsx  # Bio computing
│   └── api/
│       ├── scientific/           # Scientific API routes
│       ├── bio/                  # Bio API routes
│       ├── mindex/               # MINDEX API routes
│       └── autonomous/           # Autonomous API routes
├── components/
│   └── scientific/
│       ├── lab-monitor.tsx
│       ├── simulation-panel.tsx
│       ├── experiment-tracker.tsx
│       ├── hypothesis-board.tsx
│       ├── fci-monitor.tsx
│       ├── electrode-map.tsx
│       ├── safety-monitor.tsx
│       └── mycelium-network-viz.tsx
├── hooks/
│   └── scientific/
│       ├── use-lab-instruments.ts
│       ├── use-simulations.ts
│       ├── use-experiments.ts
│       ├── use-hypotheses.ts
│       ├── use-fci.ts
│       └── use-safety.ts
└── lib/
    └── api-config.ts             # API configuration
```

---

## Integration Status

### Current Data Flow

```
User Browser
    ↓
Website (localhost:3010)
    ↓
Next.js API Routes (/api/*)
    ↓
MAS Backend (192.168.0.188:8001) [NOT RUNNING]
    ↓
Returns fallback/mock data
```

### What's Missing

1. **MAS Backend Not Started**: Need to run `python -m mycosoft_mas.core.myca_main`
2. **No Database Seeding**: Tables exist but no real experiment/simulation data
3. **No Device Integration**: NatureOS devices not sending telemetry
4. **No WebSocket Connection**: Real-time updates disabled
5. **No Authentication Flow**: User sessions not connected to experiments

---

## Critical Issues

### Issue 1: Backend Not Running

**Problem**: MAS Orchestrator not accessible at 192.168.0.188:8001
**Impact**: All API calls return fallback mock data
**Solution**: 
```bash
ssh mycosoft@192.168.0.188
cd /opt/mycosoft/mas
python -m mycosoft_mas.core.myca_main
```

### Issue 2: No Real Data in Database

**Problem**: In-memory storage with sample data, no persistence
**Impact**: Created items disappear on restart
**Solution**: Connect to PostgreSQL/SQLite for real persistence

### Issue 3: Components Not Interactive

**Problem**: Buttons work but have no visible effect
**Impact**: User feels nothing happens
**Solution**: Add toast notifications, loading states, optimistic updates

### Issue 4: No Visual Feedback

**Problem**: No loading spinners on actions, no success/error messages
**Impact**: User confused about action results
**Solution**: Add toast system, loading overlays

### Issue 5: Static Electrode Map

**Problem**: Electrode colors don't change in real-time
**Impact**: Looks like a static image
**Solution**: Connect to WebSocket for live signal data

---

## Upgrade Plan - Phase 1: Core Functionality

### 1.1 Start and Verify Backend

**Priority**: CRITICAL
**Effort**: 1 hour

Tasks:
- [ ] SSH to 192.168.0.188 and start MAS Orchestrator
- [ ] Verify /health endpoint returns 200
- [ ] Test all /scientific/* endpoints
- [ ] Update .env.local with correct MAS_URL if different

### 1.2 Add Toast Notifications

**Priority**: HIGH
**Effort**: 2 hours

Files to modify:
- Install: `npm install sonner` in website
- Create: `components/ui/toaster.tsx`
- Update: All action handlers to show success/error toasts

Example:
```tsx
import { toast } from 'sonner'

const handleCalibrate = async (id: string) => {
  toast.loading('Calibrating instrument...')
  try {
    await calibrate(id)
    toast.success('Calibration started!')
  } catch (error) {
    toast.error('Calibration failed')
  }
}
```

### 1.3 Add Loading States to Actions

**Priority**: HIGH
**Effort**: 2 hours

Add to each button:
- Loading spinner while API call in progress
- Disable button during loading
- Show success checkmark briefly after success

### 1.4 Add Real-Time Status Indicators

**Priority**: HIGH
**Effort**: 3 hours

Add visual indicators:
- Green dot pulsing when WebSocket connected
- Red dot when disconnected
- Last updated timestamp on each panel
- Auto-retry connection with exponential backoff

---

## Upgrade Plan - Phase 2: Real Data Integration

### 2.1 Connect to Real PostgreSQL Database

**Priority**: HIGH
**Effort**: 4 hours

Tasks:
- [ ] Verify PostgreSQL running at 192.168.0.188:5432
- [ ] Update scientific_api.py to use real database queries
- [ ] Create migration scripts for experiments/simulations tables
- [ ] Seed with real initial data

### 2.2 Connect to NatureOS Devices

**Priority**: HIGH
**Effort**: 4 hours

Tasks:
- [ ] Query NatureOS API for device list
- [ ] Display real device telemetry in Lab Monitor
- [ ] Show actual temperature, humidity, CO2 readings
- [ ] Add device selection dropdown

### 2.3 Implement WebSocket Real-Time Updates

**Priority**: HIGH
**Effort**: 6 hours

Tasks:
- [ ] Start WebSocket server in MAS backend
- [ ] Connect frontend to ws://192.168.0.188:8001/ws/scientific
- [ ] Broadcast simulation progress updates
- [ ] Broadcast experiment step changes
- [ ] Update electrode map with live signals

### 2.4 Connect to MINDEX Database

**Priority**: MEDIUM
**Effort**: 4 hours

Tasks:
- [ ] Query real species data from MINDEX
- [ ] Show actual telemetry history
- [ ] Display knowledge graph connections
- [ ] Enable vector search for experiments

---

## Upgrade Plan - Phase 3: Advanced Features

### 3.1 Add Experiment Creation Wizard

**Priority**: MEDIUM
**Effort**: 6 hours

Features:
- Multi-step form with validation
- Species selection from MINDEX
- Parameter configuration
- Protocol template selection
- Preview before creation

### 3.2 Add Live Signal Visualization

**Priority**: MEDIUM
**Effort**: 8 hours

Features:
- Real-time waveform display (using canvas/WebGL)
- Frequency spectrum analysis
- Signal quality metrics
- Historical playback

### 3.3 Add MycoBrain Compute Interface

**Priority**: MEDIUM
**Effort**: 6 hours

Features:
- Problem type selection (graph, pattern, optimization)
- Input data upload
- Job queue monitoring
- Result visualization

### 3.4 Add Hypothesis AI Generation

**Priority**: LOW
**Effort**: 8 hours

Features:
- Context input for AI hypothesis generation
- Literature search integration
- Experiment suggestion based on hypothesis
- Confidence scoring

### 3.5 Add 3D Lab Digital Twin

**Priority**: LOW
**Effort**: 12 hours

Features:
- 3D model of lab environment
- Real-time device status overlay
- Click to select instruments
- AR marker placement

---

## Implementation Priority

### Immediate (Today)

| Task | Effort | Impact |
|------|--------|--------|
| Start MAS backend on VM | 30 min | Critical - enables all APIs |
| Add toast notifications | 1 hour | High - user feedback |
| Add loading states | 1 hour | High - UX improvement |

### This Week

| Task | Effort | Impact |
|------|--------|--------|
| Connect to PostgreSQL | 4 hours | High - real data persistence |
| Implement WebSocket | 6 hours | High - real-time updates |
| Connect NatureOS devices | 4 hours | High - live telemetry |
| Add experiment wizard | 4 hours | Medium - better creation flow |

### Next Week

| Task | Effort | Impact |
|------|--------|--------|
| Live signal visualization | 8 hours | Medium - FCI usability |
| MycoBrain compute UI | 6 hours | Medium - bio-computing |
| MINDEX knowledge graph | 4 hours | Medium - data exploration |
| 3D visualization polish | 8 hours | Low - visual appeal |

---

## Quick Start Commands

### Start Backend

```bash
# SSH to MAS VM
ssh mycosoft@192.168.0.188

# Start MAS Orchestrator
cd /opt/mycosoft/mas
source venv/bin/activate
python -m mycosoft_mas.core.myca_main

# Verify it's running
curl http://localhost:8001/health
```

### Test API Endpoints

```bash
# From local machine
curl http://192.168.0.188:8001/health
curl http://192.168.0.188:8001/scientific/lab/instruments
curl http://192.168.0.188:8001/scientific/experiments
curl http://192.168.0.188:8001/mindex/stats
```

---

## Recommended Next Steps

1. **Start the MAS backend** - This is the single most important step
2. **Add toast notifications** - Gives user immediate feedback
3. **Verify database connections** - Ensure data persists
4. **Test end-to-end flow** - Create experiment → Run → View results
5. **Add WebSocket** - Enable real-time updates

---

*Document generated: February 3, 2026*
*Author: MYCA Development System*
