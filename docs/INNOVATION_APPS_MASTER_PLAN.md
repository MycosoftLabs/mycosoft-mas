# 🔬 INNOVATION APPS MASTER PLAN

**Version**: 1.0  
**Date**: 2026-01-24  
**Classification**: Internal Technical Specification  
**Author**: Mycosoft Engineering

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [App 1: Physics Simulator (QISE)](#2-physics-simulator-qise)
3. [App 2: Digital Twin Mycelium](#3-digital-twin-mycelium)
4. [App 3: Lifecycle Simulator](#4-lifecycle-simulator)
5. [App 4: Genetic Circuit Designer](#5-genetic-circuit-designer)
6. [App 5: Symbiosis Network Mapper](#6-symbiosis-network-mapper)
7. [App 6: Retrosynthesis Pathway Viewer](#7-retrosynthesis-pathway-viewer)
8. [App 7: Computational Alchemy Lab](#8-computational-alchemy-lab)
9. [Holistic System Integration](#9-holistic-system-integration)
10. [User Data Architecture](#10-user-data-architecture)
11. [CREP & Fusarium Integration](#11-crep--fusarium-integration)
12. [Technology Roadmap](#12-technology-roadmap)

---

# 1. EXECUTIVE SUMMARY

## Purpose

The Innovation Apps suite represents Mycosoft's cutting-edge computational biology and chemistry platform. These seven interconnected applications provide:

- **Physics-first computation** for molecular understanding
- **Digital twin technology** for real-time organism modeling
- **Biosynthetic pathway analysis** for compound production
- **Ecosystem relationship mapping** for environmental intelligence
- **User-driven data collection** for NLM training

## Why We Have These Apps

| App | Strategic Purpose |
|-----|-------------------|
| Physics Simulator | Ground-truth molecular properties for drug discovery and environmental sensing |
| Digital Twin | Real-time cultivation monitoring and optimization |
| Lifecycle Simulator | Predictive agriculture and harvest optimization |
| Genetic Circuit | Synthetic biology and metabolic engineering |
| Symbiosis Mapper | Ecosystem intelligence and conservation |
| Retrosynthesis | Biosynthetic production pathway planning |
| Alchemy Lab | Novel compound design for therapeutics |

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTIONS                            │
│  Physics │ Digital Twin │ Lifecycle │ Genetic │ Symbiosis │ Retro  │
└────┬─────────┬────────────┬──────────┬─────────┬──────────┬─────────┘
     │         │            │          │         │          │
     ▼         ▼            ▼          ▼         ▼          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    USER SESSION DATA LAYER                           │
│              (Per-user logging, preferences, history)                │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MINDEX DATABASE                              │
│   Compounds │ Taxa │ Telemetry │ Observations │ User Sessions       │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│       NLM       │   │      CREP/FUSARIUM  │   │    MYCA/MAS AGENTS  │
│ Nature Learning │   │  Defense Systems    │   │   AI Orchestration  │
│     Model       │   │                     │   │                     │
└─────────────────┘   └─────────────────────┘   └─────────────────────┘
```

---

# 2. PHYSICS SIMULATOR (QISE)

## 2.1 Overview

**URL**: `/apps/physics-sim`  
**Status**: Active  
**NLM Layer**: Physics (`nlm/physics/`)

### What It Does

The Physics Simulator provides quantum-inspired molecular simulations that calculate ground state energies, electronic properties, and environmental field correlations. This is the foundation layer for all chemistry and biology computations.

### Why We Have It

1. **Drug Discovery**: Accurate molecular properties predict bioactivity
2. **Environmental Sensing**: Field physics correlate with fungal behavior
3. **Validation**: Ground-truth data for NLM training
4. **Research**: Publication-quality computational data

---

## 2.2 User Instructions & Walkthrough

### Step-by-Step Guide

#### Molecular Simulation Tab

1. **Select a Molecule**
   - Click the dropdown labeled "Target Molecule"
   - Choose from: Psilocybin, Muscimol, Ergotamine, Hericenone, Ganoderic Acid, Cordycepin
   - The canvas will display an animated orbital visualization

2. **Choose Simulation Method**
   - **QISE** (Quantum-Inspired Simulation Engine): Best for ground state energy. Uses variational algorithms to approximate quantum states on classical hardware.
   - **Molecular Dynamics**: Best for trajectory analysis. Simulates atomic motion over time using force fields.
   - **Tensor Network**: Best for large systems (50+ atoms). Uses Matrix Product States for efficient computation.

3. **Configure Parameters** (method-dependent)
   - For MD: Set steps (10-1000) and timestep (0.01-1.0 fs)
   - For Tensor: Set max bond dimension (8-128)

4. **Run Simulation**
   - Click "Run [METHOD] Simulation"
   - Watch progress bar (typically 2-5 seconds)
   - View results in the right panel

5. **Interpret Results**
   - **Ground State Energy** (eV): Lower is more stable
   - **HOMO-LUMO Gap** (eV): Predicts reactivity and color
   - **Dipole Moment** (Debye): Polarity affects solubility
   - **Polarizability** (Å³): Response to electric fields

#### Field Physics Tab

1. **Enter Location**
   - Latitude (-90 to 90)
   - Longitude (-180 to 180)
   - Altitude in meters

2. **Click "Analyze Field Conditions"**

3. **View Results**
   - **Geomagnetic Field**: Bx, By, Bz components in nanotesla
   - **Lunar Influence**: Current phase and gravitational force
   - **Atmospheric**: Temperature, pressure, humidity
   - **Fruiting Prediction**: Probability and optimal date

---

## 2.3 Controls Reference

| Control | Location | Function |
|---------|----------|----------|
| Molecule Dropdown | Top left | Select compound for simulation |
| Method Buttons | Below dropdown | Choose QISE/MD/Tensor |
| Steps Slider | Parameters section | MD simulation duration |
| Timestep Slider | Parameters section | MD time increment |
| Bond Dimension | Parameters section | Tensor network accuracy |
| Run Button | Bottom of control panel | Execute simulation |
| Reset Button | Results panel | Clear current results |
| Export Button | Results panel | Download data as JSON |

---

## 2.4 Use Cases

| Use Case | Method | Expected Output |
|----------|--------|-----------------|
| Predict drug reactivity | QISE | HOMO-LUMO gap indicates redox potential |
| Model protein-ligand binding | MD | Trajectory shows binding dynamics |
| Calculate large molecule | Tensor | Ground state for 50+ atoms |
| Predict mushroom flush | Field Physics | Fruiting probability based on conditions |
| Validate sensor placement | Field Physics | Geomagnetic anomaly detection |

---

## 2.5 Database Requirements

### Tables Required

```sql
-- Physics simulation results
CREATE TABLE nlm.physics_simulation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    compound_id UUID REFERENCES bio.compound(id),
    method VARCHAR(20) NOT NULL, -- 'qise', 'md', 'tensor'
    parameters JSONB NOT NULL,
    results JSONB NOT NULL,
    execution_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Field physics observations
CREATE TABLE nlm.field_observation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    location GEOGRAPHY(POINT, 4326),
    altitude FLOAT,
    timestamp TIMESTAMPTZ NOT NULL,
    geomagnetic JSONB,
    lunar JSONB,
    atmospheric JSONB,
    fruiting_prediction JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_physics_sim_user ON nlm.physics_simulation(user_id);
CREATE INDEX idx_physics_sim_compound ON nlm.physics_simulation(compound_id);
CREATE INDEX idx_field_obs_location ON nlm.field_observation USING GIST(location);
```

### Data Dependencies

| Data Source | Purpose | Update Frequency |
|-------------|---------|------------------|
| bio.compound | Molecular structures (SMILES, formula) | On-demand from ChemSpider |
| core.taxon | Species associations | Daily ETL |
| External: NOAA IGRF | Geomagnetic model | Annual |
| External: Navy Observatory | Lunar ephemeris | Monthly |
| External: OpenWeather | Atmospheric data | Real-time |

---

## 2.6 Tooling Requirements

### Current Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Frontend | Next.js + Canvas API | ✅ Implemented |
| Visualization | Raw Canvas 2D | ✅ Implemented |
| API | FastAPI (MINDEX) | ⚠️ Partially implemented |
| Computation | Python + NumPy | ⚠️ Placeholder |

### Required Libraries

```python
# NLM Physics Layer
numpy>=1.24.0        # Matrix operations
scipy>=1.10.0        # Scientific computing
networkx>=3.0        # Graph algorithms
pyscf>=2.4.0         # Quantum chemistry (future)
openmm>=8.0          # Molecular dynamics (future)
```

```typescript
// Frontend
three.js             // 3D molecular visualization (future)
@react-three/fiber   // React integration for Three.js
rdkit-js             // Client-side chemistry (future)
```

---

## 2.7 UI/UX Design Specification

### Color Theme: Electric Blue + Cyan

```css
/* Physics Simulator Theme */
:root {
  --physics-primary: #3b82f6;      /* Electric blue */
  --physics-secondary: #06b6d4;     /* Cyan */
  --physics-accent: #8b5cf6;        /* Purple for quantum effects */
  --physics-bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
  --physics-glow: 0 0 20px rgba(59, 130, 246, 0.5);
  --physics-card: rgba(30, 41, 59, 0.8);
}

/* Molecular visualization canvas */
.physics-canvas {
  background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);
  border: 1px solid var(--physics-primary);
  box-shadow: var(--physics-glow);
}

/* Atom colors by type */
.atom-carbon { fill: #22c55e; }
.atom-nitrogen { fill: #3b82f6; }
.atom-oxygen { fill: #ef4444; }
.atom-phosphorus { fill: #f59e0b; }
.atom-hydrogen { fill: #e2e8f0; }

/* Simulation progress */
.physics-progress {
  background: linear-gradient(90deg, var(--physics-primary), var(--physics-secondary));
}
```

### UX Improvements Needed

1. **3D Molecular Viewer**: Replace 2D canvas with Three.js WebGL renderer
2. **Real-time Updates**: WebSocket for streaming simulation progress
3. **History Panel**: Show previous simulations with comparison
4. **Export Options**: PDB, XYZ, MOL2 file formats
5. **Keyboard Shortcuts**: Space=pause, R=reset, E=export

---

## 2.8 Technology Upgrades Required

### Phase 1: Backend Integration (Q1 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| MINDEX API routes | High | 2 weeks | `/api/physics/*` endpoints |
| PostgreSQL schema | High | 1 week | Simulation result storage |
| User session tracking | High | 1 week | Log all simulations per user |
| Result caching | Medium | 1 week | Redis cache for repeated queries |

### Phase 2: Computation Enhancement (Q2 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| PySCF integration | High | 4 weeks | Real quantum chemistry calculations |
| OpenMM integration | High | 4 weeks | Production MD simulations |
| GPU acceleration | Medium | 2 weeks | CUDA for tensor operations |
| Distributed compute | Low | 4 weeks | Celery task queue for long jobs |

### Phase 3: Visualization (Q3 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Three.js viewer | High | 3 weeks | 3D molecular visualization |
| Trajectory player | Medium | 2 weeks | Animate MD trajectories |
| VR support | Low | 4 weeks | WebXR for immersive view |

---

## 2.9 Frontend vs Backend Components

### Frontend (Next.js)

```
website/app/apps/physics-sim/
├── page.tsx              # Main page component
├── components/
│   ├── MoleculeSelector.tsx
│   ├── SimulationCanvas.tsx
│   ├── ParameterControls.tsx
│   ├── ResultsPanel.tsx
│   ├── FieldPhysicsForm.tsx
│   └── ExportDialog.tsx
├── hooks/
│   ├── useSimulation.ts  # Simulation state management
│   ├── usePhysicsAPI.ts  # API calls
│   └── useCanvas.ts      # Canvas rendering
└── lib/
    ├── molecules.ts      # Molecule definitions
    └── visualization.ts  # Drawing utilities
```

### Backend (MINDEX API)

```
mindex/mindex_api/routers/
└── physics.py
    ├── POST /physics/molecular/simulate
    ├── POST /physics/molecular/dynamics
    ├── GET  /physics/molecular/{simulation_id}
    ├── POST /physics/field/conditions
    └── POST /physics/field/fruiting-prediction

mindex/mindex_etl/sources/
└── field_physics.py
    ├── IGRFClient          # Geomagnetic field
    ├── LunarEphemeris      # Moon position/phase
    └── WeatherClient       # OpenWeather integration
```

### NLM Layer

```
NLM/nlm/physics/
├── __init__.py
├── qise.py              # Quantum-inspired eigensolver
├── tensor_network.py    # Matrix product states
├── molecular_dynamics.py # MD engine
├── field_physics.py     # Environmental fields
└── quantum_simulator.py # Future: real quantum
```

---

## 2.10 Scientific Foundations

### QISE Algorithm

The Quantum-Inspired Simulation Engine uses the Variational Quantum Eigensolver (VQE) approach on classical hardware:

```
Algorithm: Variational Ground State Estimation
─────────────────────────────────────────────

1. Initialize ansatz parameters θ randomly
2. For iteration i = 1 to max_iterations:
   a. Construct trial wavefunction |ψ(θ)⟩
   b. Compute expectation value E(θ) = ⟨ψ(θ)|H|ψ(θ)⟩
   c. Compute gradient ∇E(θ)
   d. Update θ using optimizer (e.g., BFGS)
   e. If |E(θ_i) - E(θ_{i-1})| < tolerance: break
3. Return E(θ) as ground state energy estimate

Complexity: O(n⁴) for n-electron system
Accuracy: Typically within 1-5% of full CI
```

### Molecular Dynamics

Classical MD uses Newton's equations with force fields:

```
Algorithm: Velocity Verlet Integration
──────────────────────────────────────

1. Initialize positions r(0), velocities v(0)
2. Compute forces F(0) = -∇V(r(0))
3. For timestep t = 0 to T:
   a. r(t+Δt) = r(t) + v(t)Δt + ½a(t)Δt²
   b. F(t+Δt) = -∇V(r(t+Δt))
   c. a(t+Δt) = F(t+Δt)/m
   d. v(t+Δt) = v(t) + ½[a(t) + a(t+Δt)]Δt
4. Return trajectory {r(t), v(t)}

Timestep: 0.5-2.0 fs (femtoseconds)
Energy conservation: < 0.1% drift over ns
```

### Field Physics Correlation

Environmental fields correlate with fungal fruiting events:

| Field Type | Mechanism | Correlation Strength |
|------------|-----------|---------------------|
| Geomagnetic | Cryptochrome magnetoreception | Moderate (r=0.4) |
| Lunar gravitational | Water table fluctuation | Strong (r=0.6) |
| Barometric pressure | Gas exchange optimization | Strong (r=0.7) |
| Humidity | Spore release timing | Very strong (r=0.9) |

---

# 3. DIGITAL TWIN MYCELIUM

## 3.1 Overview

**URL**: `/apps/digital-twin`  
**Status**: Active  
**NLM Layer**: Biology (`nlm/biology/digital_twin.py`)

### What It Does

Creates real-time digital representations of mycelial networks that mirror physical cultivations. The twin ingests MycoBrain sensor data and simulates network growth, resource distribution, and signal propagation.

### Why We Have It

1. **Cultivation Optimization**: Predict optimal conditions before physical changes
2. **Remote Monitoring**: Track farms without physical presence
3. **Research Platform**: Test hypotheses in silico
4. **Training Data**: Generate synthetic data for NLM
5. **Anomaly Detection**: Identify contamination or stress early

---

## 3.2 User Instructions & Walkthrough

### Initial Setup

1. **Launch App**
   - Navigate to `/apps/digital-twin`
   - A pre-generated network appears on the canvas

2. **Connect to MycoBrain** (optional)
   - Enter device ID (format: `MB-XXX`)
   - Click "Connect"
   - Live sensor data will appear in the feed

3. **Understand the Visualization**
   - **Green dots**: Hyphal tips (actively growing)
   - **Blue dots**: Junctions (branching points)
   - **Orange dots**: Fruiting body initiation sites
   - **Lines**: Hyphal connections
   - **Pulses**: Signal propagation through network

### Operating the Twin

1. **Toggle Simulation**
   - Click Play/Pause to start/stop animation
   - Signal pulses travel along hyphae when active

2. **Regenerate Network**
   - Click Reset to create a new random network
   - Useful for testing different topologies

3. **Monitor Sensor Data**
   - View real-time readings if connected to MycoBrain
   - Enable "Auto-update" for continuous refresh

4. **Run Predictions**
   - Set prediction window (6-168 hours)
   - Click "Predict Growth"
   - View biomass projection, density, fruiting probability

5. **Export Data**
   - Click "Export GeoJSON" for Earth Simulator integration
   - Data includes node positions and connection strengths

---

## 3.3 Controls Reference

| Control | Location | Function |
|---------|----------|----------|
| Device ID Input | Sensor section | Enter MycoBrain device identifier |
| Connect Button | Sensor section | Establish WebSocket connection |
| Auto-update Toggle | Sensor section | Enable continuous data refresh |
| Play/Pause Button | Visualization header | Toggle network animation |
| Reset Button | Visualization header | Generate new network |
| Prediction Slider | Side panel | Set forecast window (hours) |
| Predict Button | Side panel | Run growth prediction |
| Export Button | Bottom | Download GeoJSON |

---

## 3.4 Use Cases

| Use Case | Configuration | Output |
|----------|---------------|--------|
| Monitor production farm | Connect MycoBrain, auto-update | Live environmental data |
| Predict harvest date | Set species, run prediction | Estimated date + yield |
| Detect contamination | Analyze network density drops | Anomaly alerts |
| Optimize FAE schedule | Compare CO₂ vs. growth rate | Timing recommendations |
| Research signal propagation | Play simulation, observe pulses | Network behavior patterns |

---

## 3.5 Database Requirements

### Tables Required

```sql
-- Digital twin instances
CREATE TABLE nlm.digital_twin (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    device_id VARCHAR(20) REFERENCES devices.mycobrain(device_id),
    species_id UUID REFERENCES core.taxon(id),
    name VARCHAR(100),
    state JSONB NOT NULL, -- Current network state
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Twin history snapshots
CREATE TABLE nlm.twin_snapshot (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    twin_id UUID REFERENCES nlm.digital_twin(id) ON DELETE CASCADE,
    state JSONB NOT NULL,
    sensor_data JSONB,
    timestamp TIMESTAMPTZ NOT NULL
);

-- Twin predictions
CREATE TABLE nlm.twin_prediction (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    twin_id UUID REFERENCES nlm.digital_twin(id) ON DELETE CASCADE,
    prediction_window_hours INTEGER,
    predicted_biomass FLOAT,
    predicted_density FLOAT,
    fruiting_probability FLOAT,
    recommendations JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_twin_user ON nlm.digital_twin(user_id);
CREATE INDEX idx_twin_device ON nlm.digital_twin(device_id);
CREATE INDEX idx_snapshot_twin ON nlm.twin_snapshot(twin_id);
CREATE INDEX idx_snapshot_time ON nlm.twin_snapshot(timestamp);
```

### Data Dependencies

| Data Source | Purpose | Update Frequency |
|-------------|---------|------------------|
| devices.telemetry | Sensor readings | Real-time (WebSocket) |
| core.taxon | Species growth profiles | On-demand |
| nlm.twin_snapshot | Historical state | Every 15 minutes |
| External: Weather | Environmental forecast | Hourly |

---

## 3.6 Tooling Requirements

### Current Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Frontend | Next.js + Canvas API | ✅ Implemented |
| Visualization | Canvas 2D + Animation | ✅ Implemented |
| WebSocket | Native WebSocket API | ⚠️ Placeholder |
| State Management | React useState | ✅ Implemented |

### Required Libraries

```python
# NLM Biology Layer
numpy>=1.24.0        # Matrix operations
networkx>=3.0        # Graph algorithms
scipy>=1.10.0        # Differential equations
shapely>=2.0         # Geometric operations
```

```typescript
// Frontend
socket.io-client     // Real-time communication
zustand             // State management upgrade
d3-force            // Force-directed layout (future)
```

---

## 3.7 UI/UX Design Specification

### Color Theme: Organic Green + Teal

```css
/* Digital Twin Theme */
:root {
  --twin-primary: #22c55e;         /* Organic green */
  --twin-secondary: #14b8a6;        /* Teal */
  --twin-accent: #f59e0b;           /* Orange for fruiting */
  --twin-junction: #3b82f6;         /* Blue for junctions */
  --twin-bg-gradient: linear-gradient(135deg, #0f1a0f 0%, #0f172a 100%);
  --twin-glow: 0 0 15px rgba(34, 197, 94, 0.4);
  --twin-signal: rgba(34, 197, 94, 0.8);
}

/* Network canvas */
.twin-canvas {
  background: radial-gradient(ellipse at center, #1a2e1a 0%, #0f172a 100%);
  border: 1px solid var(--twin-primary);
}

/* Node types */
.node-tip { 
  fill: var(--twin-primary); 
  filter: drop-shadow(0 0 4px var(--twin-primary));
}
.node-junction { 
  fill: var(--twin-junction); 
  filter: drop-shadow(0 0 6px var(--twin-junction));
}
.node-fruiting { 
  fill: var(--twin-accent); 
  filter: drop-shadow(0 0 8px var(--twin-accent));
}

/* Signal pulse animation */
@keyframes signal-pulse {
  0% { opacity: 1; transform: scale(1); }
  100% { opacity: 0; transform: scale(2); }
}
.signal-particle {
  animation: signal-pulse 1s ease-out infinite;
}

/* Sensor data cards */
.sensor-card {
  background: rgba(20, 184, 166, 0.1);
  border: 1px solid rgba(20, 184, 166, 0.3);
}
```

### UX Improvements Needed

1. **Time-lapse Mode**: Play back historical snapshots
2. **Comparison View**: Side-by-side twins
3. **Annotation Tools**: Mark areas of interest
4. **Alert Configuration**: Custom thresholds for notifications
5. **Mobile Responsive**: Touch controls for tablet use

---

## 3.8 Technology Upgrades Required

### Phase 1: Real-time Infrastructure (Q1 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| WebSocket server | High | 2 weeks | Socket.io for real-time data |
| Redis pub/sub | High | 1 week | Message broker for sensor data |
| Database streaming | Medium | 2 weeks | PostgreSQL LISTEN/NOTIFY |
| Auto-snapshot | Medium | 1 week | Scheduled state persistence |

### Phase 2: Prediction Enhancement (Q2 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| ML growth model | High | 4 weeks | Train on historical data |
| Environmental fusion | High | 2 weeks | Integrate weather forecasts |
| Anomaly detection | Medium | 3 weeks | Isolation forest for contamination |
| Recommendation engine | Medium | 2 weeks | Action suggestions |

### Phase 3: Visualization (Q3 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| D3 force layout | Medium | 2 weeks | Physics-based positioning |
| WebGL renderer | Medium | 3 weeks | Handle 10k+ nodes |
| AR overlay | Low | 4 weeks | Camera-based positioning |

---

## 3.9 Frontend vs Backend Components

### Frontend (Next.js)

```
website/app/apps/digital-twin/
├── page.tsx              # Main page component
├── components/
│   ├── NetworkCanvas.tsx     # Main visualization
│   ├── SensorFeed.tsx        # MycoBrain data display
│   ├── NetworkStats.tsx      # Node/edge counts
│   ├── PredictionPanel.tsx   # Growth forecast
│   ├── DeviceConnector.tsx   # MycoBrain connection
│   └── ExportDialog.tsx      # GeoJSON export
├── hooks/
│   ├── useWebSocket.ts       # Real-time connection
│   ├── useNetworkState.ts    # Network data
│   └── usePrediction.ts      # Forecast API
└── lib/
    ├── network-generator.ts  # Random network creation
    └── geojson-export.ts     # Export utilities
```

### Backend (MINDEX API)

```
mindex/mindex_api/routers/
└── digital_twin.py
    ├── POST /twins                    # Create new twin
    ├── GET  /twins/{twin_id}          # Get twin state
    ├── PUT  /twins/{twin_id}          # Update twin
    ├── POST /twins/{twin_id}/predict  # Run prediction
    ├── GET  /twins/{twin_id}/history  # Get snapshots
    └── WS   /twins/{twin_id}/stream   # Real-time updates
```

### NLM Layer

```
NLM/nlm/biology/
├── digital_twin.py
│   ├── DigitalTwinMycelium
│   │   ├── update_from_sensors()
│   │   ├── predict_growth()
│   │   ├── detect_anomalies()
│   │   └── export_geojson()
│   └── NetworkTopologyAnalyzer
```

---

## 3.10 Scientific Foundations

### Mycelial Growth Model

The digital twin uses a modified branching model:

```
Algorithm: Hyphal Extension Simulation
──────────────────────────────────────

1. For each hyphal tip:
   a. Compute growth direction (tropism + random)
   b. Calculate extension rate:
      rate = base_rate × temp_factor × humidity_factor × resource_factor
   c. Extend tip by rate × Δt
   d. If random() < branch_probability:
      - Create new branch at angle θ
   e. If tip intersects existing hypha:
      - Create anastomosis (junction)

2. Resource distribution:
   a. Nutrients flow from sources to sinks
   b. Use Kirchhoff's laws for network flow
   c. Update node resource levels

3. Signal propagation:
   a. Action potentials travel at ~0.5 mm/s
   b. Calcium waves: 0.1-1.0 mm/s
   c. Decay with distance (exponential)

Parameters calibrated from: Fricker et al. (2017), Fungal Biology Reviews
```

### Environmental Response Functions

| Factor | Response Curve | Optimal | Range |
|--------|---------------|---------|-------|
| Temperature | Gaussian | 22°C | 10-30°C |
| Humidity | Sigmoid | >85% | 50-100% |
| CO₂ | Inhibitory | <800 ppm | 400-5000 ppm |
| Light | Species-specific | 12h/12h | 0-24h |
| pH | Narrow Gaussian | 6.0 | 4.0-8.0 |

---

# 4. LIFECYCLE SIMULATOR

## 4.1 Overview

**URL**: `/apps/lifecycle-sim`  
**Status**: Active  
**NLM Layer**: Biology (`nlm/biology/lifecycle.py`)

### What It Does

Simulates the complete fungal lifecycle from spore germination through fruiting body development and sporulation. Users can adjust environmental conditions and observe effects on growth progression.

### Why We Have It

1. **Education**: Teach fungal biology interactively
2. **Cultivation Planning**: Predict schedules and yields
3. **Research**: Model lifecycle under various conditions
4. **Training Data**: Generate synthetic lifecycle data
5. **Optimization**: Find optimal conditions for each stage

---

## 4.2 User Instructions & Walkthrough

### Getting Started

1. **Select Species**
   - Choose from 6 pre-configured species
   - Each has unique temperature, humidity, and timing requirements

2. **Observe Timeline**
   - 7 stages displayed horizontally
   - Progress fills from left to right
   - Current stage highlighted

3. **Start Simulation**
   - Click Play to begin
   - Watch stage progress bar fill
   - Day counter increases

### Adjusting Conditions

1. **Temperature Slider**
   - Range: 10-35°C
   - Optimal value shown below slider
   - Affects growth rate and health

2. **Humidity Slider**
   - Range: 50-100%
   - Most species prefer 85-95%
   - Critical for fruiting

3. **Light Hours Slider**
   - Range: 0-24h
   - Affects primordial formation
   - Many species need light cycle shift

4. **CO₂ Level Slider**
   - Range: 200-2000 ppm
   - Low CO₂ triggers fruiting
   - High CO₂ promotes mycelium

5. **Simulation Speed**
   - Range: 0.5x-10x
   - Faster for quick demonstrations
   - Slower for detailed observation

### Monitoring Results

1. **Growth Metrics** (right panel)
   - Biomass accumulation
   - Health percentage
   - Days elapsed
   - Current stage number

2. **Predictions**
   - Next stage transition date
   - Estimated harvest date
   - Expected yield in grams

3. **Recommendations**
   - Context-aware suggestions
   - Based on current conditions vs. optimal

---

## 4.3 Controls Reference

| Control | Location | Function |
|---------|----------|----------|
| Species Dropdown | Top | Select fungal species |
| Play/Pause | Timeline header | Toggle simulation |
| Reset | Timeline header | Restart from spore |
| Temperature | Environmental section | Set incubation temp |
| Humidity | Environmental section | Set relative humidity |
| Light Hours | Environmental section | Set photoperiod |
| CO₂ Level | Environmental section | Set carbon dioxide |
| Speed Slider | Bottom of controls | Simulation speed multiplier |

---

## 4.4 Use Cases

| Use Case | Configuration | Output |
|----------|---------------|--------|
| Plan cultivation schedule | Select species, run to completion | Timeline with dates |
| Find optimal fruiting temp | Vary temperature, observe health | Best temperature identified |
| Compare species growth rates | Run multiple simulations | Side-by-side comparison |
| Train cultivation staff | Walk through lifecycle | Educational demonstration |
| Debug cultivation problems | Match real conditions, observe | Identify stress factors |

---

## 4.5 Database Requirements

### Tables Required

```sql
-- Lifecycle simulations
CREATE TABLE nlm.lifecycle_simulation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    species_id UUID REFERENCES core.taxon(id),
    initial_conditions JSONB NOT NULL,
    final_state JSONB,
    completed BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Lifecycle stages history
CREATE TABLE nlm.lifecycle_stage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id UUID REFERENCES nlm.lifecycle_simulation(id) ON DELETE CASCADE,
    stage VARCHAR(30) NOT NULL,
    progress FLOAT,
    conditions JSONB,
    health FLOAT,
    biomass FLOAT,
    timestamp TIMESTAMPTZ DEFAULT now()
);

-- Species lifecycle profiles
CREATE TABLE bio.species_lifecycle_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    taxon_id UUID REFERENCES core.taxon(id) UNIQUE,
    germination_temp_optimal FLOAT,
    fruiting_temp_optimal FLOAT,
    humidity_optimal FLOAT,
    germination_days_min INTEGER,
    germination_days_max INTEGER,
    mycelium_days_min INTEGER,
    mycelium_days_max INTEGER,
    fruiting_days_min INTEGER,
    fruiting_days_max INTEGER,
    growth_rate_mm_per_day FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_lifecycle_user ON nlm.lifecycle_simulation(user_id);
CREATE INDEX idx_lifecycle_species ON nlm.lifecycle_simulation(species_id);
```

### Data Dependencies

| Data Source | Purpose | Update Frequency |
|-------------|---------|------------------|
| core.taxon | Species information | On-demand |
| bio.species_lifecycle_profile | Growth parameters | Manual curation |
| nlm.lifecycle_stage_log | Historical simulations | Per simulation |

---

## 4.6 Tooling Requirements

### Current Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Frontend | Next.js + Canvas | ✅ Implemented |
| State Machine | React useState | ✅ Implemented |
| Animation | setInterval | ✅ Implemented |

### Required Libraries

```python
# NLM Biology Layer
numpy>=1.24.0        # Numerical computing
scipy>=1.10.0        # ODE integration
pandas>=2.0          # Data analysis
```

```typescript
// Frontend (future)
framer-motion        // Stage transitions
recharts             // Growth charts
```

---

## 4.7 UI/UX Design Specification

### Color Theme: Growth Green + Golden Yellow

```css
/* Lifecycle Simulator Theme */
:root {
  --lifecycle-primary: #22c55e;     /* Growth green */
  --lifecycle-secondary: #eab308;    /* Golden yellow */
  --lifecycle-fruiting: #f59e0b;     /* Orange fruiting */
  --lifecycle-spore: #9ca3af;        /* Gray spore */
  --lifecycle-bg: linear-gradient(180deg, #14532d 0%, #0f172a 100%);
  --lifecycle-timeline: linear-gradient(90deg, #22c55e, #eab308, #f59e0b);
}

/* Stage indicators */
.stage-complete { background: var(--lifecycle-primary); }
.stage-active { 
  background: var(--lifecycle-secondary); 
  animation: pulse 1.5s infinite;
}
.stage-pending { background: var(--lifecycle-spore); }

/* Timeline progress */
.timeline-bar {
  background: var(--lifecycle-timeline);
  border-radius: 9999px;
  height: 4px;
}

/* Environmental controls */
.env-slider-temp { accent-color: #ef4444; }
.env-slider-humidity { accent-color: #3b82f6; }
.env-slider-light { accent-color: #fbbf24; }
.env-slider-co2 { accent-color: #22c55e; }

/* Stage icons */
.stage-spore { color: var(--lifecycle-spore); }
.stage-germination { color: #84cc16; }
.stage-hyphal { color: #22c55e; }
.stage-mycelial { color: #14b8a6; }
.stage-primordial { color: #eab308; }
.stage-fruiting { color: #f59e0b; }
.stage-sporulation { color: #a855f7; }
```

### UX Improvements Needed

1. **Visual Stage Illustrations**: Show mushroom development images
2. **Condition Alerts**: Warning when conditions are suboptimal
3. **Comparison Mode**: Run two species side-by-side
4. **Calendar Integration**: Export to iCal/Google Calendar
5. **Batch Simulation**: Run multiple parameter sets

---

## 4.8 Technology Upgrades Required

### Phase 1: Data Integration (Q1 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Species profiles DB | High | 2 weeks | Load from MINDEX |
| User simulation storage | High | 1 week | Save/load simulations |
| MycoBrain validation | Medium | 2 weeks | Compare sim vs. real |

### Phase 2: Model Enhancement (Q2 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| ODE-based growth | High | 3 weeks | Differential equations |
| Stochastic variation | Medium | 2 weeks | Monte Carlo sampling |
| Contamination modeling | Medium | 2 weeks | Failure scenarios |

### Phase 3: Visualization (Q3 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| 3D mushroom growth | Medium | 4 weeks | Animated development |
| Stage photography | Low | 1 week | Real photos for each stage |
| Time-lapse export | Low | 2 weeks | Video generation |

---

## 4.9 Frontend vs Backend Components

### Frontend (Next.js)

```
website/app/apps/lifecycle-sim/
├── page.tsx              # Main page component
├── components/
│   ├── SpeciesSelector.tsx
│   ├── LifecycleTimeline.tsx
│   ├── StageProgress.tsx
│   ├── EnvironmentControls.tsx
│   ├── MetricsPanel.tsx
│   ├── PredictionCard.tsx
│   └── RecommendationList.tsx
├── hooks/
│   ├── useLifecycleSimulation.ts
│   └── useSpeciesProfile.ts
└── lib/
    ├── species-profiles.ts
    └── growth-calculations.ts
```

### Backend (MINDEX API)

```
mindex/mindex_api/routers/
└── lifecycle.py
    ├── GET  /lifecycle/species              # List species profiles
    ├── GET  /lifecycle/species/{id}         # Get specific profile
    ├── POST /lifecycle/simulate             # Run simulation
    ├── GET  /lifecycle/simulations          # User's simulations
    └── GET  /lifecycle/simulations/{id}     # Get simulation details
```

### NLM Layer

```
NLM/nlm/biology/
├── lifecycle.py
│   ├── SporeLifecycleSimulator
│   │   ├── advance_stage()
│   │   ├── calculate_growth_rate()
│   │   ├── predict_harvest()
│   │   └── get_recommendations()
│   └── LifecycleStage (Enum)
```

---

## 4.10 Scientific Foundations

### Growth Kinetics

Fungal growth follows modified logistic kinetics:

```
dB/dt = μ_max × B × (1 - B/K) × f(T) × f(H) × f(CO₂)

Where:
  B = biomass
  μ_max = maximum specific growth rate
  K = carrying capacity
  f(T) = temperature response function
  f(H) = humidity response function
  f(CO₂) = carbon dioxide response function

Temperature Response (Cardinal Model):
f(T) = ((T - T_min) / (T_opt - T_min))^α × ((T_max - T) / (T_max - T_opt))^β

Stage Transition Probability:
P(transition) = 1 - exp(-k × (B - B_threshold) × Δt)
```

### Stage Duration Parameters (Example: P. cubensis)

| Stage | Duration | Trigger |
|-------|----------|---------|
| Spore | 1-3 days | Hydration + temperature |
| Germination | 2-7 days | Nutrient detection |
| Hyphal Growth | 7-14 days | Biomass accumulation |
| Mycelial Network | 14-30 days | Substrate colonization |
| Primordial | 3-7 days | Light + low CO₂ |
| Fruiting | 5-10 days | Continued conditions |
| Sporulation | 2-5 days | Maturity |

---

# 5. GENETIC CIRCUIT DESIGNER

## 5.1 Overview

**URL**: `/apps/genetic-circuit`  
**Status**: Active  
**NLM Layer**: Biology (`nlm/biology/genetic_circuit.py`)

### What It Does

Simulates gene regulatory networks and biosynthetic pathways. Users can visualize gene expression dynamics, apply modifications (overexpression/knockdown), and observe effects on metabolite production.

### Why We Have It

1. **Synthetic Biology**: Design optimized production strains
2. **Research**: Understand pathway regulation
3. **Education**: Teach gene regulatory networks
4. **Drug Production**: Optimize biosynthesis routes
5. **Strain Engineering**: Plan genetic modifications

---

## 5.2 User Instructions & Walkthrough

### Getting Started

1. **Select Genetic Circuit**
   - Choose from pre-built pathways:
     - Psilocybin Biosynthesis (P. cubensis)
     - Hericenone Production (H. erinaceus)
     - Ganoderic Acid Synthesis (G. lucidum)
     - Cordycepin Biosynthesis (C. militaris)

2. **Understand the Visualization**
   - Genes shown as vertical bars
   - Bar height = expression level (0-100%)
   - Colors indicate regulation state:
     - Green: Activated (>70%)
     - Blue: Basal (30-70%)
     - Red: Repressed (<30%)
   - Orange circle = product accumulation

3. **Run Simulation**
   - Click Play to start
   - Gene expressions fluctuate dynamically
   - Product accumulates over time

### Applying Modifications

1. **Gene Overexpression/Knockdown**
   - Slider per gene (-50% to +50%)
   - Positive = overexpression
   - Negative = knockdown
   - Effects propagate through pathway

2. **Environmental Stress**
   - Slider 0-100%
   - Simulates unfavorable conditions
   - Reduces overall pathway activity

3. **Nutrient Level**
   - Slider 0-100%
   - Higher nutrients = more flux
   - Affects production rate

### Interpreting Results

1. **Metabolite Level**: Total product accumulated
2. **Flux Rate**: Current production velocity
3. **Bottleneck Gene**: Lowest-expressing gene (rate-limiting)
4. **Average Expression**: Pathway health indicator

---

## 5.3 Controls Reference

| Control | Location | Function |
|---------|----------|----------|
| Circuit Dropdown | Top | Select biosynthetic pathway |
| Play/Pause | Visualization header | Toggle simulation |
| Reset | Visualization header | Clear modifications |
| Gene Sliders | Control panel | Overexpress/knockdown genes |
| Stress Slider | Control panel | Apply environmental stress |
| Nutrient Slider | Control panel | Set nutrient availability |
| Export Button | Side panel | Download expression data |
| Design Experiment | Side panel | Generate lab protocol |

---

## 5.4 Use Cases

| Use Case | Configuration | Output |
|----------|---------------|--------|
| Identify bottleneck | Run sim, find lowest gene | Target for overexpression |
| Design production strain | Maximize key genes | Modification strategy |
| Study pathway regulation | Apply stress, observe | Stress response patterns |
| Optimize yield | Tune all parameters | Best conditions found |
| Generate hypothesis | Compare conditions | Testable predictions |

---

## 5.5 Database Requirements

### Tables Required

```sql
-- Genetic circuits (pathways)
CREATE TABLE bio.genetic_circuit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    species_id UUID REFERENCES core.taxon(id),
    description TEXT,
    pathway_type VARCHAR(50), -- 'biosynthetic', 'regulatory', 'signaling'
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Circuit components (genes/proteins)
CREATE TABLE bio.circuit_component (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    circuit_id UUID REFERENCES bio.genetic_circuit(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    component_type VARCHAR(20), -- 'gene', 'protein', 'metabolite'
    position INTEGER,
    initial_expression FLOAT DEFAULT 50,
    metadata JSONB
);

-- Component interactions
CREATE TABLE bio.circuit_interaction (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    circuit_id UUID REFERENCES bio.genetic_circuit(id) ON DELETE CASCADE,
    source_id UUID REFERENCES bio.circuit_component(id),
    target_id UUID REFERENCES bio.circuit_component(id),
    interaction_type VARCHAR(20), -- 'activates', 'represses', 'produces'
    strength FLOAT DEFAULT 1.0
);

-- User simulations
CREATE TABLE nlm.circuit_simulation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    circuit_id UUID REFERENCES bio.genetic_circuit(id),
    modifications JSONB,
    parameters JSONB,
    trajectory JSONB,
    final_metabolite FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_circuit_species ON bio.genetic_circuit(species_id);
CREATE INDEX idx_component_circuit ON bio.circuit_component(circuit_id);
CREATE INDEX idx_sim_user ON nlm.circuit_simulation(user_id);
```

### Data Dependencies

| Data Source | Purpose | Update Frequency |
|-------------|---------|------------------|
| bio.genetic_circuit | Pathway definitions | Manual curation |
| bio.circuit_component | Gene/protein info | Manual curation |
| External: KEGG | Pathway verification | Monthly sync |
| External: UniProt | Protein annotations | Monthly sync |

---

## 5.6 Tooling Requirements

### Current Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Frontend | Next.js + Canvas | ✅ Implemented |
| Animation | setInterval | ✅ Implemented |
| State | React useState | ✅ Implemented |

### Required Libraries

```python
# NLM Biology Layer
numpy>=1.24.0        # Matrix operations
scipy>=1.10.0        # ODE integration
networkx>=3.0        # Network analysis
tellurium>=2.2       # Systems biology (future)
```

```typescript
// Frontend (future)
cytoscape            // Network visualization
@react-spring/web    // Smooth animations
```

---

## 5.7 UI/UX Design Specification

### Color Theme: DNA Purple + Bio Blue

```css
/* Genetic Circuit Theme */
:root {
  --genetic-primary: #8b5cf6;       /* Purple (DNA) */
  --genetic-secondary: #3b82f6;      /* Blue (proteins) */
  --genetic-activated: #22c55e;      /* Green (active) */
  --genetic-repressed: #ef4444;      /* Red (repressed) */
  --genetic-product: #f59e0b;        /* Orange (metabolite) */
  --genetic-bg: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
}

/* Gene expression bars */
.gene-bar {
  transition: height 0.3s ease, background-color 0.3s ease;
}
.gene-bar.activated { 
  background: linear-gradient(180deg, var(--genetic-activated), #15803d);
}
.gene-bar.basal { 
  background: linear-gradient(180deg, var(--genetic-secondary), #1d4ed8);
}
.gene-bar.repressed { 
  background: linear-gradient(180deg, var(--genetic-repressed), #991b1b);
}

/* Pathway arrows */
.pathway-arrow {
  stroke: var(--genetic-secondary);
  stroke-width: 2;
  marker-end: url(#arrowhead);
}

/* Product indicator */
.metabolite-circle {
  fill: var(--genetic-product);
  filter: drop-shadow(0 0 10px var(--genetic-product));
}

/* Modification sliders */
.mod-slider-positive { accent-color: var(--genetic-activated); }
.mod-slider-negative { accent-color: var(--genetic-repressed); }
```

### UX Improvements Needed

1. **Interactive Network**: Click-drag gene rearrangement
2. **Feedback Loops**: Visualize regulatory interactions
3. **Sensitivity Analysis**: Automated parameter sweep
4. **SBML Export**: Standard format for modeling tools
5. **Collaboration**: Share circuits with team

---

## 5.8 Technology Upgrades Required

### Phase 1: Backend Integration (Q1 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Circuit database | High | 2 weeks | Load pathways from MINDEX |
| ODE solver | High | 3 weeks | Scipy integration |
| Simulation storage | Medium | 1 week | Save user experiments |

### Phase 2: Model Enhancement (Q2 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| SBML support | High | 3 weeks | Import/export standard format |
| Stochastic sim | Medium | 3 weeks | Gillespie algorithm |
| Metabolic flux | Medium | 4 weeks | FBA integration |

### Phase 3: Visualization (Q3 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Cytoscape.js | Medium | 3 weeks | Interactive network graph |
| Real-time charts | Medium | 2 weeks | Expression time series |
| 3D protein view | Low | 4 weeks | AlphaFold integration |

---

## 5.9 Frontend vs Backend Components

### Frontend (Next.js)

```
website/app/apps/genetic-circuit/
├── page.tsx
├── components/
│   ├── CircuitSelector.tsx
│   ├── PathwayCanvas.tsx
│   ├── GeneExpressionBar.tsx
│   ├── ModificationPanel.tsx
│   ├── MetricsDisplay.tsx
│   └── PathwayAnalysis.tsx
├── hooks/
│   ├── useCircuitSimulation.ts
│   └── useGeneExpression.ts
└── lib/
    ├── circuits.ts
    └── pathway-renderer.ts
```

### Backend (MINDEX API)

```
mindex/mindex_api/routers/
└── genetic_circuit.py
    ├── GET  /circuits                    # List all circuits
    ├── GET  /circuits/{id}               # Get circuit details
    ├── POST /circuits/{id}/simulate      # Run simulation
    ├── GET  /circuits/simulations        # User's simulations
    └── POST /circuits/{id}/export        # Export SBML
```

### NLM Layer

```
NLM/nlm/biology/
├── genetic_circuit.py
│   ├── GeneticCircuitSimulator
│   │   ├── run_simulation()
│   │   ├── apply_modification()
│   │   └── analyze_pathway()
│   └── CircuitComponent
```

---

## 5.10 Scientific Foundations

### Gene Regulatory Network Dynamics

Gene expression follows Hill function kinetics:

```
Expression Dynamics (ODE System):
────────────────────────────────

d[mRNA_i]/dt = α_i × f_i(regulators) - δ_mRNA × [mRNA_i]
d[Protein_i]/dt = β × [mRNA_i] - δ_protein × [Protein_i]

Hill Function (Activation):
f(x) = V_max × (x^n / (K^n + x^n))

Hill Function (Repression):
f(x) = V_max × (K^n / (K^n + x^n))

Where:
  α = transcription rate
  β = translation rate
  δ = degradation rate
  K = half-saturation constant
  n = Hill coefficient (cooperativity)
```

### Metabolic Flux Analysis

Steady-state flux through pathway:

```
Flux Balance Analysis (FBA):
────────────────────────────

Maximize: c^T × v (objective function, e.g., product synthesis)
Subject to:
  S × v = 0           (steady-state)
  v_min ≤ v ≤ v_max   (capacity constraints)

Where:
  S = stoichiometric matrix
  v = flux vector
  c = objective coefficients
```

---

# 6. SYMBIOSIS NETWORK MAPPER

## 6.1 Overview

**URL**: `/apps/symbiosis`  
**Status**: Active  
**NLM Layer**: Biology (`nlm/biology/symbiosis.py`)

### What It Does

Visualizes and analyzes symbiotic relationships between fungi and other organisms. Users can explore mycorrhizal associations, parasitic relationships, lichen partnerships, and predatory interactions.

### Why We Have It

1. **Ecosystem Intelligence**: Understand forest networks
2. **Conservation**: Identify keystone species
3. **Agriculture**: Optimize plant-fungal partnerships
4. **Research**: Study co-evolutionary patterns
5. **CREP Integration**: Map biological threat networks

---

## 6.2 User Instructions & Walkthrough

### Exploring the Network

1. **View Network Visualization**
   - Nodes = organisms (colored by type)
   - Lines = symbiotic relationships
   - Line color = relationship type
   - Line thickness = relationship strength

2. **Node Colors**
   - Green: Fungi
   - Light green: Plants
   - Cyan: Bacteria
   - Red: Animals
   - Teal: Algae

3. **Interact with Network**
   - Click node: Select and view details
   - Hover node: Highlight connections
   - Scroll: Zoom in/out

### Filtering Relationships

1. **Type Filter Dropdown**
   - All Relationships (default)
   - Mycorrhizal only
   - Parasitic only
   - Saprotrophic only
   - Endophytic only
   - Lichen only
   - Predatory only

2. **Click relationship type cards** to quick-filter

### Viewing Details

1. **Selected Organism Panel**
   - Scientific name
   - Organism type
   - List of symbiotic relationships
   - Partner organisms

2. **Network Statistics**
   - Total organisms count
   - Total relationships count
   - Average connectivity

---

## 6.3 Controls Reference

| Control | Location | Function |
|---------|----------|----------|
| Filter Dropdown | Visualization header | Filter by relationship type |
| Reset Button | Visualization header | Generate new network |
| Canvas Click | Main visualization | Select organism |
| Canvas Hover | Main visualization | Highlight connections |
| Export GeoJSON | Side panel | Download for Earth Simulator |
| View in Earth | Side panel | Open in Earth Simulator |

---

## 6.4 Use Cases

| Use Case | Configuration | Output |
|----------|---------------|--------|
| Map forest mycorrhizal network | Filter: Mycorrhizal | Tree-fungal connections |
| Identify parasitic threats | Filter: Parasitic | Host-parasite pairs |
| Study lichen partnerships | Filter: Lichen | Fungi-algae pairs |
| Find keystone species | Analyze statistics | Most-connected organisms |
| CREP threat mapping | Export GeoJSON | Geographic overlay |

---

## 6.5 Database Requirements

### Tables Required

```sql
-- Symbiotic relationships
CREATE TABLE bio.symbiosis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_taxon_id UUID REFERENCES core.taxon(id),
    target_taxon_id UUID REFERENCES core.taxon(id),
    relationship_type VARCHAR(30) NOT NULL,
    strength FLOAT DEFAULT 1.0,
    bidirectional BOOLEAN DEFAULT false,
    evidence_level VARCHAR(20), -- 'confirmed', 'reported', 'predicted'
    source TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Organism interaction observations
CREATE TABLE bio.symbiosis_observation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbiosis_id UUID REFERENCES bio.symbiosis(id),
    location GEOGRAPHY(POINT, 4326),
    observed_at TIMESTAMPTZ,
    observer_user_id UUID,
    notes TEXT,
    images JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- User network analyses
CREATE TABLE nlm.symbiosis_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    filter_type VARCHAR(30),
    network_snapshot JSONB,
    statistics JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_symbiosis_source ON bio.symbiosis(source_taxon_id);
CREATE INDEX idx_symbiosis_target ON bio.symbiosis(target_taxon_id);
CREATE INDEX idx_symbiosis_type ON bio.symbiosis(relationship_type);
CREATE INDEX idx_obs_location ON bio.symbiosis_observation USING GIST(location);
```

### Data Dependencies

| Data Source | Purpose | Update Frequency |
|-------------|---------|------------------|
| core.taxon | Organism information | Daily ETL |
| bio.symbiosis | Relationship data | Weekly curation |
| External: FungiDB | Verified relationships | Monthly sync |
| External: iNaturalist | Observation records | Real-time |

---

## 6.6 Tooling Requirements

### Current Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Frontend | Next.js + Canvas | ✅ Implemented |
| Interaction | Click/hover handlers | ✅ Implemented |
| Animation | requestAnimationFrame | ✅ Implemented |

### Required Libraries

```python
# NLM Biology Layer
networkx>=3.0        # Graph algorithms
python-igraph>=0.11  # Large-scale networks
scipy>=1.10.0        # Spatial analysis
```

```typescript
// Frontend (future)
d3-force             // Force-directed layout
cytoscape            // Network visualization
react-flow           // Interactive diagrams
```

---

## 6.7 UI/UX Design Specification

### Color Theme: Ecosystem Green + Earth Tones

```css
/* Symbiosis Mapper Theme */
:root {
  --symbiosis-primary: #22c55e;      /* Ecosystem green */
  --symbiosis-secondary: #14b8a6;     /* Teal */
  --symbiosis-fungus: #22c55e;
  --symbiosis-plant: #84cc16;
  --symbiosis-bacteria: #06b6d4;
  --symbiosis-animal: #ef4444;
  --symbiosis-algae: #10b981;
  --symbiosis-bg: linear-gradient(135deg, #0d2818 0%, #0f172a 100%);
}

/* Relationship colors */
.rel-mycorrhizal { stroke: #22c55e; }
.rel-parasitic { stroke: #ef4444; }
.rel-saprotrophic { stroke: #f59e0b; }
.rel-endophytic { stroke: #3b82f6; }
.rel-lichen { stroke: #8b5cf6; }
.rel-predatory { stroke: #ef4444; }

/* Node styling */
.organism-node {
  cursor: pointer;
  transition: transform 0.2s;
}
.organism-node:hover {
  transform: scale(1.5);
}
.organism-node.selected {
  stroke: white;
  stroke-width: 3;
}

/* Network canvas */
.symbiosis-canvas {
  background: radial-gradient(circle at 50% 50%, #1a3a2a 0%, #0f172a 100%);
}
```

### UX Improvements Needed

1. **Force-directed Layout**: Auto-arrange nodes
2. **Search Organisms**: Find specific species
3. **Path Finding**: Show connection paths between two organisms
4. **Cluster Detection**: Identify ecosystem communities
5. **Time Slider**: Show relationships over time

---

## 6.8 Technology Upgrades Required

### Phase 1: Data Integration (Q1 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| MINDEX symbiosis table | High | 2 weeks | Relationship database |
| iNaturalist sync | Medium | 3 weeks | Observation import |
| Force layout | Medium | 2 weeks | D3/Cytoscape integration |

### Phase 2: Analysis Enhancement (Q2 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Community detection | High | 3 weeks | Louvain algorithm |
| Keystone analysis | Medium | 2 weeks | Centrality metrics |
| Path finding | Medium | 1 week | Shortest path algorithms |

### Phase 3: Geographic Integration (Q3 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| GeoJSON export | High | 1 week | Map integration |
| Earth Simulator link | High | 2 weeks | Cross-app navigation |
| Observation overlay | Medium | 3 weeks | Real observation markers |

---

## 6.9 Frontend vs Backend Components

### Frontend (Next.js)

```
website/app/apps/symbiosis/
├── page.tsx
├── components/
│   ├── NetworkCanvas.tsx
│   ├── OrganismNode.tsx
│   ├── RelationshipEdge.tsx
│   ├── FilterDropdown.tsx
│   ├── OrganismDetails.tsx
│   ├── NetworkStatistics.tsx
│   └── RelationshipLegend.tsx
├── hooks/
│   ├── useNetworkData.ts
│   ├── useSelection.ts
│   └── useForceLayout.ts
└── lib/
    ├── network-generator.ts
    └── geojson-exporter.ts
```

### Backend (MINDEX API)

```
mindex/mindex_api/routers/
└── symbiosis.py
    ├── GET  /symbiosis                      # List relationships
    ├── GET  /symbiosis/organism/{taxon_id}  # Get relationships for organism
    ├── GET  /symbiosis/network              # Get full network
    ├── POST /symbiosis/analyze              # Run network analysis
    └── GET  /symbiosis/export/geojson       # Export for mapping
```

### NLM Layer

```
NLM/nlm/biology/
├── symbiosis.py
│   ├── SymbiosisNetworkMapper
│   │   ├── add_organism()
│   │   ├── add_relationship()
│   │   ├── analyze_network()
│   │   ├── find_keystone_species()
│   │   └── export_geojson()
│   └── RelationshipType (Enum)
```

---

## 6.10 Scientific Foundations

### Network Analysis Metrics

```
Centrality Measures:
────────────────────

Degree Centrality:
C_D(v) = deg(v) / (n-1)

Betweenness Centrality:
C_B(v) = Σ_{s≠v≠t} σ_st(v) / σ_st
Where σ_st = number of shortest paths from s to t
      σ_st(v) = paths passing through v

Closeness Centrality:
C_C(v) = (n-1) / Σ_t d(v,t)
Where d(v,t) = shortest path distance

Keystone Species Identification:
K(v) = C_B(v) × (unique_relationships / total_relationships)
```

### Relationship Type Definitions

| Type | Definition | Ecological Role |
|------|------------|-----------------|
| Mycorrhizal | Mutualistic root association | Nutrient exchange, plant health |
| Parasitic | One organism harmed | Population control, evolution |
| Saprotrophic | Decomposition of dead matter | Nutrient cycling |
| Endophytic | Living within plant tissues | Plant immunity, chemistry |
| Lichen | Fungi-algae/cyanobacteria | Pioneer species, indicator |
| Predatory | Capturing other organisms | Biocontrol, ecosystem balance |

---

# 7. RETROSYNTHESIS PATHWAY VIEWER

## 7.1 Overview

**URL**: `/apps/retrosynthesis`  
**Status**: Active  
**NLM Layer**: Chemistry (`nlm/chemistry/retrosynthesis.py`)

### What It Does

Analyzes biosynthetic pathways by working backward from target compounds to identify precursor molecules, enzymatic reactions, and production conditions.

### Why We Have It

1. **Bioproduction**: Plan manufacturing routes
2. **Research**: Understand biosynthesis mechanisms
3. **Drug Development**: Identify synthesis targets
4. **Strain Engineering**: Know which genes to modify
5. **Cost Estimation**: Predict production costs

---

## 7.2 User Instructions & Walkthrough

### Analyzing a Pathway

1. **Select Target Compound**
   - Choose from dropdown:
     - Psilocybin, Muscimol, Hericenone A
     - Cordycepin, Ganoderic Acid A, Ergotamine

2. **Click Search Button**
   - Analysis takes 2-3 seconds
   - Loading indicator shows progress

3. **View Pathway**
   - Steps displayed vertically
   - Arrow between each step
   - Click step to expand details

### Understanding Step Details

1. **Expanded Step View**
   - Substrate: Starting molecule
   - Product: Resulting molecule
   - Enzyme: Catalyzing protein
   - Enzyme Type: Class (e.g., decarboxylase)
   - Conditions: Temperature, pH, cofactors
   - Yield: Expected conversion percentage
   - Reversible: Whether reaction goes both ways

### Using Pathway Metrics

1. **Steps Count**: Total enzymatic steps
2. **Overall Yield**: Combined yield through pathway
3. **Rate-Limiting Step**: Lowest yield step (bottleneck)
4. **Reversible Steps**: Can run in both directions
5. **Cofactors Required**: ATP, NADPH needs

### Export Options

1. **Export Pathway Data**: Download as JSON
2. **Open in Alchemy Lab**: Design related compounds
3. **Open in Genetic Circuit**: See gene regulation

---

## 7.3 Controls Reference

| Control | Location | Function |
|---------|----------|----------|
| Compound Dropdown | Top | Select target molecule |
| Search Button | Next to dropdown | Analyze pathway |
| Step Expanders | Pathway list | Show/hide details |
| Export Data | Side panel | Download JSON |
| Open in Alchemy | Side panel | Cross-app navigation |
| Open in Genetic | Side panel | Cross-app navigation |

---

## 7.4 Use Cases

| Use Case | Configuration | Output |
|----------|---------------|--------|
| Plan fermentation | Analyze target compound | Production route |
| Identify bottlenecks | Find rate-limiting step | Optimization target |
| Estimate yield | Review overall yield | Production planning |
| Design strain | List required enzymes | Engineering targets |
| Cost analysis | Count cofactors | Resource requirements |

---

## 7.5 Database Requirements

### Tables Required

```sql
-- Biosynthetic pathways
CREATE TABLE bio.biosynthetic_pathway (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    compound_id UUID REFERENCES bio.compound(id),
    species_id UUID REFERENCES core.taxon(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    overall_yield FLOAT,
    difficulty VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Pathway steps
CREATE TABLE bio.pathway_step (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pathway_id UUID REFERENCES bio.biosynthetic_pathway(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    substrate_name VARCHAR(100) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    enzyme_name VARCHAR(100),
    enzyme_type VARCHAR(50),
    conditions TEXT,
    yield_fraction FLOAT,
    reversible BOOLEAN DEFAULT false,
    substrate_compound_id UUID REFERENCES bio.compound(id),
    product_compound_id UUID REFERENCES bio.compound(id),
    enzyme_gene_id UUID REFERENCES bio.circuit_component(id)
);

-- User pathway analyses
CREATE TABLE nlm.pathway_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    compound_id UUID REFERENCES bio.compound(id),
    pathway_id UUID REFERENCES bio.biosynthetic_pathway(id),
    analysis_result JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_pathway_compound ON bio.biosynthetic_pathway(compound_id);
CREATE INDEX idx_pathway_species ON bio.biosynthetic_pathway(species_id);
CREATE INDEX idx_step_pathway ON bio.pathway_step(pathway_id);
```

### Data Dependencies

| Data Source | Purpose | Update Frequency |
|-------------|---------|------------------|
| bio.compound | Molecule information | On-demand |
| bio.biosynthetic_pathway | Pathway data | Manual curation |
| External: KEGG | Pathway verification | Monthly |
| External: BRENDA | Enzyme data | Quarterly |

---

## 7.6 Tooling Requirements

### Current Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Frontend | Next.js | ✅ Implemented |
| Animation | Framer Motion | ✅ Implemented |
| State | React useState | ✅ Implemented |

### Required Libraries

```python
# NLM Chemistry Layer
rdkit>=2023.09       # Reaction prediction
networkx>=3.0        # Pathway graphs
pubchempy>=1.0.4     # Compound lookup
```

```typescript
// Frontend (future)
smiles-drawer        // 2D structure rendering
molstar              // 3D visualization
```

---

## 7.7 UI/UX Design Specification

### Color Theme: Chemistry Orange + Red

```css
/* Retrosynthesis Theme */
:root {
  --retro-primary: #f59e0b;         /* Chemistry orange */
  --retro-secondary: #ef4444;        /* Reaction red */
  --retro-enzyme: #3b82f6;           /* Enzyme blue */
  --retro-substrate: #22c55e;        /* Substrate green */
  --retro-product: #f59e0b;          /* Product orange */
  --retro-bg: linear-gradient(135deg, #451a03 0%, #0f172a 100%);
}

/* Step cards */
.pathway-step {
  border-left: 3px solid var(--retro-primary);
  transition: all 0.2s;
}
.pathway-step:hover {
  border-left-width: 5px;
  background: rgba(245, 158, 11, 0.05);
}
.pathway-step.expanded {
  border-left-color: var(--retro-secondary);
}

/* Step number badge */
.step-number {
  background: var(--retro-primary);
  color: white;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

/* Arrow between steps */
.step-arrow {
  color: var(--retro-primary);
  opacity: 0.5;
}

/* Yield indicator */
.yield-bar {
  background: linear-gradient(90deg, 
    var(--retro-secondary) 0%, 
    var(--retro-primary) 50%, 
    var(--retro-substrate) 100%
  );
}
```

### UX Improvements Needed

1. **2D Structure Drawings**: Show molecule structures
2. **Alternative Pathways**: Multiple route options
3. **Cost Calculator**: Estimate production costs
4. **Protocol Generator**: Lab-ready instructions
5. **Literature Links**: Connect to papers

---

## 7.8 Technology Upgrades Required

### Phase 1: Backend Integration (Q1 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| Pathway database | High | 3 weeks | Curated pathways |
| KEGG integration | High | 2 weeks | External pathway data |
| Enzyme lookup | Medium | 2 weeks | BRENDA integration |

### Phase 2: Prediction Enhancement (Q2 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| RDKit integration | High | 4 weeks | Reaction prediction |
| Alternative routes | Medium | 3 weeks | Multiple pathways |
| Yield prediction | Medium | 4 weeks | ML-based estimation |

### Phase 3: Visualization (Q3 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| 2D structure viewer | High | 3 weeks | SMILES rendering |
| Interactive diagram | Medium | 4 weeks | Clickable pathway |
| 3D enzyme viewer | Low | 4 weeks | AlphaFold integration |

---

## 7.9 Frontend vs Backend Components

### Frontend (Next.js)

```
website/app/apps/retrosynthesis/
├── page.tsx
├── components/
│   ├── CompoundSelector.tsx
│   ├── PathwayViewer.tsx
│   ├── PathwayStep.tsx
│   ├── StepDetails.tsx
│   ├── PathwayMetrics.tsx
│   ├── CultivationNotes.tsx
│   └── ExportOptions.tsx
├── hooks/
│   ├── usePathwayAnalysis.ts
│   └── useStepExpansion.ts
└── lib/
    ├── pathways.ts
    └── metrics-calculator.ts
```

### Backend (MINDEX API)

```
mindex/mindex_api/routers/
└── retrosynthesis.py
    ├── GET  /retrosynthesis/compounds       # List target compounds
    ├── POST /retrosynthesis/analyze         # Analyze pathway
    ├── GET  /retrosynthesis/pathway/{id}    # Get pathway details
    ├── GET  /retrosynthesis/alternatives    # Alternative routes
    └── POST /retrosynthesis/export          # Export pathway
```

### NLM Layer

```
NLM/nlm/chemistry/
├── retrosynthesis.py
│   ├── RetrosynthesisEngine
│   │   ├── analyze_pathway()
│   │   ├── predict_precursors()
│   │   ├── find_alternatives()
│   │   └── estimate_yield()
│   └── PathwayStep
```

---

## 7.10 Scientific Foundations

### Retrosynthetic Analysis

```
Algorithm: Biosynthetic Pathway Reconstruction
──────────────────────────────────────────────

1. Input: Target compound structure (SMILES/InChI)
2. Database lookup:
   a. Search known pathways for target
   b. If found, return curated pathway
3. If not found, computational prediction:
   a. Identify functional groups in target
   b. Match to known biosynthetic reactions
   c. Apply retro-rules (reverse transformations)
   d. Generate precursor candidates
   e. Recursively analyze precursors
   f. Stop when reaching primary metabolites
4. Score pathways by:
   - Thermodynamic feasibility (ΔG)
   - Enzyme availability
   - Substrate availability
   - Total step count
5. Return ranked pathway options

References: Hadadi & Hatzimanikatis (2015), Nature Chem. Biol.
```

### Yield Calculation

```
Overall Yield = ∏(step_yields)

Example Psilocybin Pathway:
Step 1: 85% (Tryptophan → Tryptamine)
Step 2: 70% (Tryptamine → 4-OH-Tryptamine)
Step 3: 75% (4-OH-Tryptamine → Norbaeocystin)
Step 4: 80% (Norbaeocystin → Psilocybin)

Overall: 0.85 × 0.70 × 0.75 × 0.80 = 0.357 = 35.7%
```

---

# 8. COMPUTATIONAL ALCHEMY LAB

## 8.1 Overview

**URL**: `/apps/alchemy-lab`  
**Status**: Active  
**NLM Layer**: Chemistry (`nlm/chemistry/alchemy.py`)

### What It Does

Enables virtual design of novel fungal compounds by combining molecular scaffolds with functional groups. AI predicts properties including drug-likeness, synthesizability, toxicity, and bioactivity.

### Why We Have It

1. **Drug Discovery**: Design new therapeutics
2. **Research**: Explore chemical space
3. **IP Development**: Novel compound invention
4. **Education**: Teach medicinal chemistry
5. **Optimization**: Improve existing compounds

---

## 8.2 User Instructions & Walkthrough

### Designing a Compound

1. **Select Molecular Scaffold**
   - Indole: Tryptamine-based (like psilocybin)
   - Ergoline: Ergot alkaloid base
   - β-Carboline: Harmine-like
   - Lanostane: Triterpene (like ganoderic acid)
   - Macrolide: Polyketide core

2. **Add Functional Groups**
   - Click "Add Group"
   - Select position (1-6 on scaffold)
   - Choose functional group:
     - Hydroxyl (-OH): Antioxidant
     - Amino (-NH₂): Antimicrobial
     - Methyl (-CH₃): Lipophilicity
     - Phosphate (-PO₄): Solubility
     - Acetyl (-COCH₃): Stability
     - Phenyl (-C₆H₅): Binding

3. **Name Compound** (optional)
   - Enter custom name
   - Or accept auto-generated ID

4. **Design & Predict**
   - Click purple button
   - Wait 2-3 seconds
   - View predictions

### Understanding Predictions

1. **Key Metrics**
   - Molecular Weight: Total mass
   - LogP: Lipophilicity (fat solubility)

2. **Scores**
   - Drug-Likeness: Similarity to approved drugs (0-100%)
   - Synthesizability: Ease of production (0-100%)
   - Safety Score: Inverse of toxicity (0-100%)

3. **Bioactivities**
   - Predicted biological effects
   - Confidence percentages
   - Higher = more likely

### Planning Synthesis

1. **Click "Plan Synthesis"**
2. **View Steps**
   - Each enzymatic transformation
   - Yield percentage per step
3. **See Totals**
   - Overall yield
   - Estimated cost
   - Difficulty rating

---

## 8.3 Controls Reference

| Control | Location | Function |
|---------|----------|----------|
| Scaffold Dropdown | Design panel | Choose base molecule |
| Add Group Button | Below dropdown | Add modification |
| Position Select | Modification row | Where to attach |
| Group Select | Modification row | What to attach |
| Delete Button | Modification row | Remove modification |
| Compound Name | Bottom of panel | Optional naming |
| Design Button | Bottom of panel | Generate predictions |
| Plan Synthesis | Results panel | Get production route |
| Download | Results panel | Export compound data |
| Share | Results panel | Share design |

---

## 8.4 Use Cases

| Use Case | Configuration | Output |
|----------|---------------|--------|
| Design new therapeutic | Select scaffold + modifications | Novel compound + predictions |
| Optimize existing compound | Mimic structure + improve | Better properties |
| Explore chemical space | Try many combinations | Structure-activity data |
| Plan production | Design + plan synthesis | Manufacturing route |
| Generate IP | Create unique structures | Patentable compounds |

---

## 8.5 Database Requirements

### Tables Required

```sql
-- Designed compounds
CREATE TABLE chem.designed_compound (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    name VARCHAR(100),
    scaffold_id VARCHAR(50) NOT NULL,
    modifications JSONB NOT NULL,
    smiles TEXT,
    molecular_weight FLOAT,
    logp FLOAT,
    drug_likeness FLOAT,
    synthesizability FLOAT,
    toxicity_risk FLOAT,
    bioactivities JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Synthesis plans
CREATE TABLE chem.synthesis_plan (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    compound_id UUID REFERENCES chem.designed_compound(id) ON DELETE CASCADE,
    steps JSONB NOT NULL,
    overall_yield FLOAT,
    estimated_cost FLOAT,
    difficulty VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- User design history
CREATE TABLE nlm.design_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    compounds_designed INTEGER DEFAULT 0,
    session_start TIMESTAMPTZ DEFAULT now(),
    session_end TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_designed_user ON chem.designed_compound(user_id);
CREATE INDEX idx_designed_scaffold ON chem.designed_compound(scaffold_id);
CREATE INDEX idx_synthesis_compound ON chem.synthesis_plan(compound_id);
```

### Data Dependencies

| Data Source | Purpose | Update Frequency |
|-------------|---------|------------------|
| Scaffold library | Base structures | Curated |
| Functional groups | Modification options | Curated |
| External: ChemBL | Drug-likeness training | Monthly |
| External: ToxCast | Toxicity training | Quarterly |

---

## 8.6 Tooling Requirements

### Current Stack

| Component | Technology | Status |
|-----------|------------|--------|
| Frontend | Next.js + Canvas | ✅ Implemented |
| Visualization | Canvas 2D | ✅ Implemented |
| State | React useState | ✅ Implemented |

### Required Libraries

```python
# NLM Chemistry Layer
rdkit>=2023.09       # Molecular operations
deepchem>=2.7        # ML predictions
openbabel>=3.1       # File format conversion
```

```typescript
// Frontend (future)
3dmol.js             # 3D molecular viewer
smiles-drawer        # 2D structure rendering
```

---

## 8.7 UI/UX Design Specification

### Color Theme: Alchemy Purple + Pink

```css
/* Alchemy Lab Theme */
:root {
  --alchemy-primary: #8b5cf6;        /* Purple */
  --alchemy-secondary: #ec4899;       /* Pink */
  --alchemy-design: #22c55e;          /* Design green */
  --alchemy-modification: #f59e0b;    /* Mod orange */
  --alchemy-bg: linear-gradient(135deg, #2e1065 0%, #0f172a 100%);
}

/* Canvas styling */
.alchemy-canvas {
  background: radial-gradient(circle at center, #1e1b4b 0%, #0a0a0a 100%);
  border: 1px solid var(--alchemy-primary);
  box-shadow: 0 0 30px rgba(139, 92, 246, 0.2);
}

/* Scaffold rendering */
.scaffold-ring {
  stroke: var(--alchemy-design);
  fill: none;
  stroke-width: 2;
}
.scaffold-atom {
  fill: var(--alchemy-design);
}

/* Modification rendering */
.modification-group {
  fill: var(--alchemy-modification);
  filter: drop-shadow(0 0 6px var(--alchemy-modification));
}
.modification-bond {
  stroke: var(--alchemy-modification);
}

/* Design button gradient */
.design-button {
  background: linear-gradient(135deg, var(--alchemy-primary), var(--alchemy-secondary));
}
.design-button:hover {
  background: linear-gradient(135deg, #7c3aed, #db2777);
}

/* Score indicators */
.score-high { color: #22c55e; }
.score-medium { color: #eab308; }
.score-low { color: #ef4444; }
```

### UX Improvements Needed

1. **Real 2D/3D Structure**: Replace abstract visualization
2. **SMILES Input**: Allow manual structure entry
3. **Similar Compounds**: Show known similar molecules
4. **Save Designs**: Persist to user account
5. **Export Formats**: SDF, MOL, PDB files

---

## 8.8 Technology Upgrades Required

### Phase 1: Real Chemistry (Q1 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| RDKit integration | High | 4 weeks | Real molecular operations |
| SMILES generation | High | 2 weeks | Generate valid structures |
| 2D rendering | High | 3 weeks | smiles-drawer integration |

### Phase 2: ML Predictions (Q2 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| DeepChem integration | High | 4 weeks | Property prediction |
| ChEMBL training | High | 4 weeks | Drug-likeness model |
| Toxicity prediction | Medium | 3 weeks | ToxCast integration |

### Phase 3: Advanced Features (Q3 2026)

| Upgrade | Priority | Effort | Description |
|---------|----------|--------|-------------|
| 3D visualization | Medium | 3 weeks | 3DMol.js viewer |
| Docking simulation | Medium | 4 weeks | Protein-ligand docking |
| Synthesis prediction | Low | 6 weeks | Retrosynthesis AI |

---

## 8.9 Frontend vs Backend Components

### Frontend (Next.js)

```
website/app/apps/alchemy-lab/
├── page.tsx
├── components/
│   ├── ScaffoldSelector.tsx
│   ├── ModificationPanel.tsx
│   ├── MoleculeCanvas.tsx
│   ├── CompoundPreview.tsx
│   ├── PredictionResults.tsx
│   ├── SynthesisPlan.tsx
│   └── DesignHistory.tsx
├── hooks/
│   ├── useDesign.ts
│   ├── usePrediction.ts
│   └── useSynthesis.ts
└── lib/
    ├── scaffolds.ts
    ├── functional-groups.ts
    └── canvas-renderer.ts
```

### Backend (MINDEX API)

```
mindex/mindex_api/routers/
└── alchemy.py
    ├── POST /alchemy/design             # Create compound
    ├── GET  /alchemy/design/{id}        # Get design
    ├── POST /alchemy/predict            # Predict properties
    ├── POST /alchemy/synthesis          # Plan synthesis
    ├── GET  /alchemy/history            # User's designs
    └── POST /alchemy/export             # Export compound
```

### NLM Layer

```
NLM/nlm/chemistry/
├── alchemy.py
│   ├── ComputationalAlchemyLab
│   │   ├── design_compound()
│   │   ├── predict_properties()
│   │   ├── plan_synthesis()
│   │   └── export_compound()
│   ├── MolecularScaffold
│   └── FunctionalGroup
```

---

## 8.10 Scientific Foundations

### Drug-Likeness Prediction

Based on Lipinski's Rule of Five and extensions:

```
Lipinski's Rule of Five:
───────────────────────
- MW ≤ 500 Da
- LogP ≤ 5
- H-bond donors ≤ 5
- H-bond acceptors ≤ 10

Quantitative Drug-Likeness Score:
─────────────────────────────────
QED = exp(Σ w_i × f_i(property_i))

Where f_i are desirability functions for:
- MW, LogP, TPSA, HBD, HBA, RotBonds, Aromatic rings, Alerts

Reference: Bickerton et al. (2012), Nature Chemistry
```

### Toxicity Prediction

```
Structural Alerts (SMARTS patterns):
───────────────────────────────────
- Nitro groups: [N+](=O)[O-]
- Epoxides: C1OC1
- Michael acceptors: C=C-C=O
- Quinones: O=C1C=CC(=O)C=C1
- Peroxides: OO

Tox21 Model:
────────────
Trained on 12 endpoints:
1. Nuclear receptor signaling (7 targets)
2. Stress response (5 targets)

Output: P(toxic) for each endpoint
Aggregate: Max toxicity risk
```

### Bioactivity Prediction

```
Target Fishing Algorithm:
─────────────────────────

1. Compute molecular fingerprint (ECFP4)
2. Compare to active compounds in ChEMBL
3. For each target class:
   - Find similar active compounds (Tanimoto > 0.6)
   - Weight by similarity and bioactivity
   - Output: P(active | target)
4. Return top-k predictions with confidence

Reference: Keiser et al. (2009), Nature Biotechnology
```

---

# 9. HOLISTIC SYSTEM INTEGRATION

## 9.1 Data Flow Architecture

```
                               ┌───────────────────────────────┐
                               │         USER LAYER            │
                               │  Physics │ Digital │ Lifecycle │
                               │  Genetic │ Symbiosis │ Retro  │
                               │        Alchemy Lab            │
                               └───────────────┬───────────────┘
                                               │
                                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           SESSION MANAGER                                 │
│  • User authentication (Supabase)                                        │
│  • Session tracking (Redis)                                              │
│  • Activity logging (PostgreSQL)                                         │
│  • Preference storage                                                    │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────────────┐
│       MINDEX API GATEWAY      │   │           REAL-TIME LAYER             │
│  /api/compounds               │   │  WebSocket Server (Socket.io)         │
│  /api/physics                 │   │  • Telemetry streaming                │
│  /api/lifecycle               │   │  • Digital twin updates               │
│  /api/genetic-circuit         │   │  • Collaboration sync                 │
│  /api/symbiosis               │   │  Redis Pub/Sub                        │
│  /api/retrosynthesis          │   │  • Event distribution                 │
│  /api/alchemy                 │   │  • Cache invalidation                 │
└───────────────────────────────┘   └───────────────────────────────────────┘
                    │                               │
                    ▼                               │
┌──────────────────────────────────────────────────┴───────────────────────┐
│                          MINDEX DATABASE                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │
│  │ core.taxon  │ │bio.compound │ │bio.symbiosis│ │ nlm.user_session   │ │
│  │ core.image  │ │bio.pathway  │ │bio.circuit  │ │ nlm.simulation     │ │
│  │ core.source │ │bio.activity │ │bio.profile  │ │ nlm.prediction     │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         COMPUTATION LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                          NLM ENGINE                                 │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────────┐ │ │
│  │  │  Physics  │  │  Biology  │  │ Chemistry │  │   AI/ML Models    │ │ │
│  │  │   QISE    │  │Digital Twin│  │Retrosyn   │  │ Bioactivity pred │ │ │
│  │  │    MD     │  │  Lifecycle │  │  Alchemy  │  │ Toxicity pred    │ │ │
│  │  │  Tensor   │  │  Genetic   │  │ Reaction  │  │ Property pred    │ │ │
│  │  │   Field   │  │ Symbiosis  │  │  Network  │  │ Species ID       │ │ │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
┌─────────────────────┐ ┌─────────────────────────────────────────────────┐
│   CREP INTEGRATION  │ │              MAS AGENT LAYER                    │
│  • Anomaly detection│ │  ┌─────────────────────────────────────────────┐│
│  • Threat assessment│ │  │              MYCA ORCHESTRATOR              ││
│  • Geographic overlay│ │  │  • Task distribution                       ││
│  • Alert generation │ │  │  • Agent coordination                       ││
│                     │ │  │  • Response generation                      ││
│   FUSARIUM SYSTEM   │ │  └─────────────────────────────────────────────┘│
│  • Military-grade   │ │  ┌─────────────────────────────────────────────┐│
│  • Encrypted comms  │ │  │            SPECIALIZED AGENTS               ││
│  • C2 integration   │ │  │  • ChemSpider Sync Agent                    ││
│  • Threat response  │ │  │  • Compound Enricher Agent                  ││
│                     │ │  │  • Bioactivity Predictor Agent              ││
│                     │ │  │  • Digital Twin Agent                       ││
│                     │ │  │  • CREP Analyst Agent                       ││
└─────────────────────┘ └─────────────────────────────────────────────────┘
```

## 9.2 API Route Structure

### Core Routes

```
MINDEX API Base: /api/v1

/api/v1/compounds
  GET    /                      # List compounds
  GET    /{id}                  # Get compound
  GET    /for-taxon/{taxon_id}  # Compounds for species
  POST   /enrich                # Enrich from ChemSpider
  GET    /chemspider/search     # Search ChemSpider

/api/v1/physics
  POST   /molecular/simulate    # QISE simulation
  POST   /molecular/dynamics    # MD simulation
  POST   /field/conditions      # Field physics
  POST   /field/fruiting        # Fruiting prediction

/api/v1/digital-twin
  POST   /                      # Create twin
  GET    /{id}                  # Get twin state
  PUT    /{id}                  # Update twin
  POST   /{id}/predict          # Run prediction
  WS     /{id}/stream           # Real-time updates

/api/v1/lifecycle
  GET    /species               # List species profiles
  POST   /simulate              # Run simulation
  GET    /simulations           # User's simulations

/api/v1/genetic-circuit
  GET    /circuits              # List circuits
  POST   /simulate              # Run simulation
  GET    /simulations           # User's simulations

/api/v1/symbiosis
  GET    /                      # List relationships
  GET    /network               # Full network
  POST   /analyze               # Network analysis
  GET    /export/geojson        # Export for mapping

/api/v1/retrosynthesis
  GET    /compounds             # Target compounds
  POST   /analyze               # Analyze pathway
  GET    /alternatives          # Alternative routes

/api/v1/alchemy
  POST   /design                # Create compound
  POST   /predict               # Predict properties
  POST   /synthesis             # Plan synthesis
  GET    /history               # User's designs
```

### Integration Routes

```
/api/v1/crep
  POST   /anomaly/detect        # Detect anomalies
  POST   /threat/assess         # Assess threats
  GET    /alerts                # Get active alerts
  POST   /alerts/acknowledge    # Acknowledge alert

/api/v1/fusarium
  POST   /secure/analyze        # Secure analysis
  POST   /secure/report         # Generate report
  GET    /secure/status         # System status
  [Requires military-grade auth]

/api/v1/user
  GET    /sessions              # User's sessions
  GET    /data                  # User's data export
  DELETE /data                  # Delete user data
  GET    /preferences           # User preferences
  PUT    /preferences           # Update preferences
```

## 9.3 Algorithm Integration

### NLM Learning Pipeline

```
User Action → Session Log → MINDEX → NLM Training Queue

Example Flow:
1. User designs compound in Alchemy Lab
2. Session logger captures:
   - Scaffold selection
   - Modification choices
   - Prediction results
   - Synthesis plan requests
3. Data stored in nlm.design_session
4. NLM training job processes:
   - Compound structure → property relationships
   - User preference patterns
   - Successful designs (by synthesis completion)
5. Model updates improve:
   - Property predictions
   - Scaffold recommendations
   - Synthesis route suggestions
```

### Cross-App Data Sharing

| Source App | Data Produced | Consumer Apps |
|------------|---------------|---------------|
| Physics | Molecular properties | Alchemy, Retrosynthesis |
| Digital Twin | Growth patterns | Lifecycle, CREP |
| Lifecycle | Stage timing | Digital Twin |
| Genetic Circuit | Expression data | Retrosynthesis |
| Symbiosis | Relationship data | CREP, Earth Sim |
| Retrosynthesis | Pathway data | Alchemy, Genetic |
| Alchemy | New compounds | Physics, Retrosynthesis |

---

# 10. USER DATA ARCHITECTURE

## 10.1 Data Collection Per App

### Physics Simulator

```json
{
  "session_id": "uuid",
  "user_id": "uuid",
  "app": "physics-sim",
  "events": [
    {
      "type": "molecule_selected",
      "timestamp": "2026-01-24T12:00:00Z",
      "data": { "molecule_id": "psilocybin" }
    },
    {
      "type": "simulation_run",
      "timestamp": "2026-01-24T12:01:00Z",
      "data": {
        "method": "qise",
        "parameters": { "max_iterations": 100 },
        "results": {
          "ground_state_energy": -156.78,
          "homo_lumo_gap": 3.45,
          "execution_time_ms": 2340
        }
      }
    },
    {
      "type": "field_analysis",
      "timestamp": "2026-01-24T12:05:00Z",
      "data": {
        "location": { "lat": 37.77, "lng": -122.41 },
        "conditions": { ... },
        "prediction": { "fruiting_probability": 0.72 }
      }
    }
  ]
}
```

### Digital Twin

```json
{
  "session_id": "uuid",
  "user_id": "uuid",
  "app": "digital-twin",
  "events": [
    {
      "type": "twin_created",
      "data": { "twin_id": "uuid", "species": "P. cubensis" }
    },
    {
      "type": "mycobrain_connected",
      "data": { "device_id": "MB-001" }
    },
    {
      "type": "sensor_data_received",
      "data": { "temperature": 22.5, "humidity": 85, ... }
    },
    {
      "type": "prediction_run",
      "data": { "window_hours": 48, "predicted_biomass": 250.5 }
    }
  ]
}
```

## 10.2 User Data Access

### User-Facing Data Portal

```
/account/data

Features:
1. View All Sessions
   - Filter by app, date range
   - See activity timeline
   - Download raw JSON

2. Export Data
   - Full export (all apps)
   - Per-app export
   - Date range export
   - Format: JSON, CSV, PDF report

3. Privacy Controls
   - Opt-out of NLM training
   - Delete specific sessions
   - Delete all data (GDPR)

4. Usage Analytics
   - Time spent per app
   - Most-used features
   - Compound designs saved
   - Simulations run
```

### Backend Access (Agents/Myca/MINDEX)

```python
# Agent Access API

from mindex_api.services.user_data import UserDataService

class CompoundEnricherAgent:
    def __init__(self):
        self.data_service = UserDataService()
    
    async def analyze_user_preferences(self, user_id: str):
        """Analyze user's compound design patterns."""
        sessions = await self.data_service.get_sessions(
            user_id=user_id,
            app="alchemy-lab",
            limit=100
        )
        
        # Extract design patterns
        scaffolds_used = Counter()
        modifications_used = Counter()
        
        for session in sessions:
            for event in session.events:
                if event.type == "compound_designed":
                    scaffolds_used[event.data.scaffold] += 1
                    for mod in event.data.modifications:
                        modifications_used[mod.group] += 1
        
        return {
            "preferred_scaffolds": scaffolds_used.most_common(3),
            "preferred_modifications": modifications_used.most_common(5),
            "total_designs": sum(scaffolds_used.values())
        }

# Myca Orchestrator Access

class MycaOrchestrator:
    async def get_user_context(self, user_id: str):
        """Get comprehensive user context for personalized responses."""
        return await self.data_service.get_user_summary(
            user_id=user_id,
            include_recent_sessions=True,
            include_preferences=True,
            include_saved_compounds=True
        )
```

## 10.3 NLM Training Data Pipeline

```
┌──────────────────┐
│  User Sessions   │
│  (Raw Events)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Data Processor  │
│  • Anonymize     │
│  • Validate      │
│  • Enrich        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Training Queue  │
│  (Redis)         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  NLM Trainer     │
│  • Batch process │
│  • Update models │
│  • Validate      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Model Registry  │
│  • Version       │
│  • A/B test      │
│  • Deploy        │
└──────────────────┘
```

---

# 11. CREP & FUSARIUM INTEGRATION

## 11.1 CREP Anomaly Detection

### Data Sources from Innovation Apps

| App | Data Type | CREP Use |
|-----|-----------|----------|
| Digital Twin | Mycelium network changes | Contamination detection |
| Symbiosis | Ecosystem disruptions | Invasive species alerts |
| Lifecycle | Abnormal growth patterns | Disease monitoring |
| Field Physics | Environmental anomalies | Pollution detection |

### Integration Points

```python
# CREP Anomaly Pipeline

class CREPAnomalyDetector:
    def __init__(self):
        self.digital_twin_client = DigitalTwinClient()
        self.symbiosis_client = SymbiosisClient()
        self.field_physics_client = FieldPhysicsClient()
    
    async def detect_biological_threats(self, location: GeoPoint):
        """Integrate innovation app data for threat detection."""
        
        # 1. Check digital twin for abnormal patterns
        twins = await self.digital_twin_client.get_twins_near(location)
        for twin in twins:
            anomaly = await self.analyze_twin_health(twin)
            if anomaly.severity > 0.7:
                yield BiologicalThreatAlert(
                    type="contamination",
                    source="digital_twin",
                    location=location,
                    severity=anomaly.severity,
                    details=anomaly.details
                )
        
        # 2. Check symbiosis network for disruptions
        network = await self.symbiosis_client.get_network_near(location)
        disruption = await self.analyze_network_stability(network)
        if disruption.detected:
            yield BiologicalThreatAlert(
                type="ecosystem_disruption",
                source="symbiosis",
                location=location,
                severity=disruption.severity,
                details=disruption.details
            )
        
        # 3. Check field physics for environmental anomalies
        conditions = await self.field_physics_client.get_conditions(location)
        env_anomaly = await self.analyze_conditions(conditions)
        if env_anomaly.detected:
            yield EnvironmentalAlert(
                type=env_anomaly.type,
                source="field_physics",
                location=location,
                severity=env_anomaly.severity
            )
```

## 11.2 Fusarium Military Integration

### Secure Data Pipeline

```
Innovation Apps → MINDEX → CREP → Fusarium Gateway → C2 System

Security Layers:
1. App-level encryption (TLS 1.3)
2. Database encryption (AES-256)
3. Fusarium gateway (mTLS + API keys)
4. C2 integration (SATCOM encrypted)
```

### Data Classification

| Classification | Data Type | Handling |
|---------------|-----------|----------|
| UNCLASSIFIED | General species data | Public access |
| CUI | User session data | Encrypted, access-controlled |
| SECRET | Threat assessments | Fusarium only, audit logged |
| TOP SECRET | C2 integration | Isolated network, HSM keys |

### Fusarium API Integration

```python
# Fusarium Integration (Military-Grade)

class FusariumIntegration:
    def __init__(self, api_key: str, mtls_cert: Path):
        self.client = SecureClient(
            base_url="https://fusarium.mil.mycosoft.com",
            api_key=api_key,
            client_cert=mtls_cert
        )
    
    async def submit_threat_report(self, alert: BiologicalThreatAlert):
        """Submit threat intelligence to Fusarium C2."""
        
        # Encrypt sensitive data
        encrypted_payload = self.encrypt_payload({
            "threat_type": alert.type,
            "location": alert.location.to_mgrs(),  # Military Grid Reference
            "severity": alert.severity,
            "source_app": alert.source,
            "timestamp": alert.timestamp.isoformat(),
            "confidence": alert.confidence,
            "recommended_action": self.generate_recommendation(alert)
        })
        
        # Submit with authentication
        response = await self.client.post(
            "/api/secure/threat-report",
            data=encrypted_payload,
            headers={"X-Classification": "SECRET"}
        )
        
        # Log for audit
        await self.audit_log.record(
            action="threat_report_submitted",
            classification="SECRET",
            report_id=response.report_id
        )
        
        return response
```

---

# 12. TECHNOLOGY ROADMAP

## 12.1 Immediate Priorities (Q1 2026)

### Week 1-2: Database Integration

| Task | App(s) | Priority |
|------|--------|----------|
| Create nlm schema | All | Critical |
| User session tables | All | Critical |
| Compound tables | Alchemy, Retro | High |
| Physics results tables | Physics | High |
| Digital twin tables | Twin | High |

### Week 3-4: API Development

| Task | App(s) | Priority |
|------|--------|----------|
| Core CRUD endpoints | All | Critical |
| User session endpoints | All | Critical |
| WebSocket infrastructure | Twin | High |
| ChemSpider integration | Alchemy, Retro | High |

### Week 5-6: Frontend Polish

| Task | App(s) | Priority |
|------|--------|----------|
| Apply CSS themes | All | High |
| Error handling | All | High |
| Loading states | All | Medium |
| Responsive design | All | Medium |

## 12.2 Short-Term (Q2 2026)

### Backend Computation

| Upgrade | Apps | Effort |
|---------|------|--------|
| RDKit integration | Alchemy, Retro | 4 weeks |
| PySCF/OpenMM | Physics | 6 weeks |
| NetworkX analysis | Symbiosis | 2 weeks |
| ODE solvers | Lifecycle, Genetic | 3 weeks |

### ML Model Training

| Model | Data Source | Accuracy Target |
|-------|-------------|-----------------|
| Drug-likeness | ChEMBL + user designs | >85% |
| Toxicity | ToxCast + ToxRef | >80% |
| Bioactivity | BindingDB | >75% |
| Species ID | iNaturalist | >90% |

## 12.3 Medium-Term (Q3-Q4 2026)

### Visualization Upgrades

| Upgrade | Apps | Technology |
|---------|------|------------|
| 3D molecular viewer | Physics, Alchemy | Three.js |
| Force-directed graphs | Symbiosis | D3-force |
| WebGL networks | Twin | Cytoscape |
| AR overlays | All | WebXR |

### Integration Completion

| Integration | Systems | Priority |
|-------------|---------|----------|
| Full CREP pipeline | All → CREP | High |
| Fusarium gateway | CREP → Fusarium | High |
| Earth Simulator links | Symbiosis, Twin | Medium |
| Myca orchestration | All | Medium |

## 12.4 Long-Term Vision (2027)

### Platform Evolution

1. **Federated Learning**: Train models on user data without centralization
2. **Quantum Integration**: Real QPU access for molecular simulation
3. **Autonomous Agents**: Self-improving compound design agents
4. **Global Network**: Connect cultivation facilities worldwide
5. **Open Science**: Publish validated computational models

---

# APPENDIX A: CSS THEME REFERENCE

## Complete Theme Variables

```css
/* ============================================
   INNOVATION APPS - COMPLETE THEME SYSTEM
   ============================================ */

/* Global Design Tokens */
:root {
  /* Typography */
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-display: 'Space Grotesk', 'Inter', sans-serif;
  --font-body: 'Inter', system-ui, sans-serif;
  
  /* Spacing Scale */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  
  /* Border Radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 1rem;
  --radius-full: 9999px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.2);
  --shadow-glow: 0 0 20px var(--glow-color);
}

/* Physics Simulator Theme */
[data-app="physics"] {
  --primary: #3b82f6;
  --secondary: #06b6d4;
  --accent: #8b5cf6;
  --glow-color: rgba(59, 130, 246, 0.5);
  --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
  --card-bg: rgba(30, 41, 59, 0.8);
  --canvas-bg: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);
}

/* Digital Twin Theme */
[data-app="digital-twin"] {
  --primary: #22c55e;
  --secondary: #14b8a6;
  --accent: #f59e0b;
  --glow-color: rgba(34, 197, 94, 0.4);
  --bg-gradient: linear-gradient(135deg, #0f1a0f 0%, #0f172a 100%);
  --card-bg: rgba(20, 83, 45, 0.3);
  --canvas-bg: radial-gradient(ellipse at center, #1a2e1a 0%, #0f172a 100%);
}

/* Lifecycle Simulator Theme */
[data-app="lifecycle"] {
  --primary: #22c55e;
  --secondary: #eab308;
  --accent: #f59e0b;
  --glow-color: rgba(234, 179, 8, 0.4);
  --bg-gradient: linear-gradient(180deg, #14532d 0%, #0f172a 100%);
  --card-bg: rgba(21, 128, 61, 0.2);
}

/* Genetic Circuit Theme */
[data-app="genetic"] {
  --primary: #8b5cf6;
  --secondary: #3b82f6;
  --accent-active: #22c55e;
  --accent-repressed: #ef4444;
  --glow-color: rgba(139, 92, 246, 0.4);
  --bg-gradient: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
  --card-bg: rgba(88, 28, 135, 0.2);
}

/* Symbiosis Mapper Theme */
[data-app="symbiosis"] {
  --primary: #22c55e;
  --secondary: #14b8a6;
  --glow-color: rgba(34, 197, 94, 0.3);
  --bg-gradient: linear-gradient(135deg, #0d2818 0%, #0f172a 100%);
  --card-bg: rgba(6, 78, 59, 0.3);
  --canvas-bg: radial-gradient(circle at 50% 50%, #1a3a2a 0%, #0f172a 100%);
}

/* Retrosynthesis Theme */
[data-app="retrosynthesis"] {
  --primary: #f59e0b;
  --secondary: #ef4444;
  --accent: #3b82f6;
  --glow-color: rgba(245, 158, 11, 0.4);
  --bg-gradient: linear-gradient(135deg, #451a03 0%, #0f172a 100%);
  --card-bg: rgba(120, 53, 15, 0.3);
}

/* Alchemy Lab Theme */
[data-app="alchemy"] {
  --primary: #8b5cf6;
  --secondary: #ec4899;
  --accent: #22c55e;
  --glow-color: rgba(139, 92, 246, 0.4);
  --bg-gradient: linear-gradient(135deg, #2e1065 0%, #0f172a 100%);
  --card-bg: rgba(88, 28, 135, 0.3);
  --canvas-bg: radial-gradient(circle at center, #1e1b4b 0%, #0a0a0a 100%);
}
```

---

# APPENDIX B: GLOSSARY

| Term | Definition |
|------|------------|
| QISE | Quantum-Inspired Simulation Engine |
| MD | Molecular Dynamics |
| VQE | Variational Quantum Eigensolver |
| HOMO-LUMO | Highest Occupied/Lowest Unoccupied Molecular Orbital |
| LogP | Partition coefficient (lipophilicity measure) |
| SMILES | Simplified Molecular Input Line Entry System |
| InChI | International Chemical Identifier |
| KEGG | Kyoto Encyclopedia of Genes and Genomes |
| FBA | Flux Balance Analysis |
| DTM | Digital Twin Mycelium |
| CREP | Common Relevant Environmental Picture |
| NLM | Nature Learning Model |
| MAS | Multi-Agent System |

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-24  
**Classification**: Internal Technical Specification  
**Maintainer**: Mycosoft Engineering Team
