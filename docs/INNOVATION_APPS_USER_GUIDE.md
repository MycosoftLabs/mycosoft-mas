# Innovation Apps User Guide

> Complete guide for using MYCOSOFT's Innovation Suite applications

**Version**: 2.0.0  
**Last Updated**: 2026-01-24  
**Status**: Production Ready

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Physics Simulator](#physics-simulator)
3. [Digital Twin Mycelium](#digital-twin-mycelium)
4. [Lifecycle Simulator](#lifecycle-simulator)
5. [Genetic Circuit Designer](#genetic-circuit-designer)
6. [Symbiosis Mapper](#symbiosis-mapper)
7. [Retrosynthesis Viewer](#retrosynthesis-viewer)
8. [Alchemy Lab](#alchemy-lab)
9. [Research Apps](#research-apps)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Accessing the Apps

1. Navigate to `https://mycosoft.io/apps` or your local development server at `http://localhost:3010/apps`
2. Select the **Innovation** tab to see all innovation apps
3. Click on any app card to launch it

### Authentication

All apps require NatureOS authentication:
- Log in at `/natureos/login`
- Your session persists across all apps
- User data is automatically saved to MINDEX for the Nature Learning Model

### System Requirements

- Modern browser (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- WebGL 2.0 support for 3D visualizations
- Minimum 4GB RAM recommended
- Stable internet connection for API calls

---

## Physics Simulator

**Location**: `/apps/physics-sim`  
**Theme**: Indigo/Purple (Quantum aesthetic)  
**Purpose**: Quantum-inspired molecular simulations

### Features

| Feature | Description |
|---------|-------------|
| QISE Engine | Quantum-Inspired Simulation Engine for molecular dynamics |
| Tensor Networks | Large molecular system approximations |
| Field Physics | Geomagnetic and atmospheric modeling |
| Property Calculator | Quantum property predictions |

### How to Use

#### Running a Molecular Dynamics Simulation

1. **Load a Molecule**
   - Click "Load Molecule" button
   - Enter molecule name or paste SMILES notation
   - Or select from the compound library

2. **Configure Simulation**
   - Set number of steps (10-10000)
   - Choose timestep (0.1-10 femtoseconds)
   - Select force field (Universal, AMBER, CHARMM)

3. **Run Simulation**
   - Click "Simulate" button
   - Watch the real-time trajectory visualization
   - View energy graphs as simulation progresses

4. **Analyze Results**
   - Export trajectory data (JSON/PDB format)
   - View final energy states
   - Compare with literature values

#### Calculating Quantum Properties

1. Load your molecule
2. Click "Calculate Properties"
3. View results:
   - HOMO-LUMO gap (eV)
   - Dipole moment (Debye)
   - Polarizability
   - Electronic configuration

### API Endpoint

```
POST /api/mindex/innovation/physics
Content-Type: application/json

{
  "action": "simulate",
  "molecule": {
    "name": "Psilocybin",
    "smiles": "CN(C)CCc1c[nH]c2cccc(OP(=O)(O)O)c12"
  },
  "parameters": {
    "steps": 100,
    "timestep": 1.0,
    "method": "qise"
  }
}
```

---

## Digital Twin Mycelium

**Location**: `/apps/digital-twin`  
**Theme**: Lime Green (Neural network aesthetic)  
**Purpose**: Real-time mycelial network modeling

### Features

| Feature | Description |
|---------|-------------|
| Network Visualization | Interactive graph of mycelium structure |
| Sensor Integration | Live MycoBrain data connection |
| Growth Prediction | ML-based growth forecasting |
| Anomaly Detection | Environmental stress identification |

### How to Use

#### Creating a New Digital Twin

1. **Initialize Twin**
   - Click "New Digital Twin"
   - Select species (P. cubensis, H. erinaceus, etc.)
   - Set initial biomass (grams)

2. **Configure Environment**
   - Set temperature (°C)
   - Set humidity (%)
   - Set CO2 level (ppm)

3. **View Network**
   - Nodes represent hyphal tips and junctions
   - Edges show connections
   - Colors indicate resource levels

#### Connecting MycoBrain Sensors

1. Go to Settings → Device Connection
2. Enter MycoBrain device ID
3. Click "Connect"
4. Data will stream automatically

#### Growth Prediction

1. Click "Predict Growth"
2. Set prediction window (1-168 hours)
3. View predictions:
   - Biomass trajectory
   - Network density
   - Fruiting probability
   - Recommendations

### API Endpoint

```
GET /api/mindex/innovation/digital-twin?species=psilocybe_cubensis
POST /api/mindex/innovation/digital-twin
{
  "action": "predict",
  "duration_hours": 24
}
```

---

## Lifecycle Simulator

**Location**: `/apps/lifecycle-sim`  
**Theme**: Green/Amber gradient (Growth aesthetic)  
**Purpose**: Fungal lifecycle modeling from spore to sporulation

### Lifecycle Stages

1. **Spore** - Dormant state
2. **Germination** - Breaking dormancy
3. **Hyphal Growth** - Initial filament extension
4. **Mycelial Network** - Colonization
5. **Primordial** - Pinning initiation
6. **Fruiting Body** - Mushroom development
7. **Sporulation** - Spore release
8. **Decay** - Senescence

### How to Use

#### Starting a Simulation

1. **Select Species**
   - Choose from preset profiles:
     - Golden Teacher (P. cubensis)
     - Lion's Mane (H. erinaceus)
     - Oyster (P. ostreatus)
     - Reishi (G. lucidum)
     - Cordyceps (C. militaris)

2. **Set Environment**
   - Temperature: Adjust slider (10-35°C)
   - Humidity: Adjust slider (40-100%)
   - CO2: Adjust slider (400-5000 ppm)
   - Light: Adjust hours per day (0-24)

3. **Run Simulation**
   - Click "Start" to begin
   - Use "Advance 1 Day" for step-by-step
   - Use "Fast Forward" for quick simulation

4. **Monitor Progress**
   - Stage indicator shows current phase
   - Progress bar shows completion
   - Health meter shows organism vitality
   - Biomass graph tracks growth

#### Predicting Harvest Date

1. Run simulation to at least mycelial network stage
2. Click "Predict Harvest"
3. View estimated date and confidence

### API Endpoint

```
POST /api/mindex/innovation/lifecycle
{
  "action": "advance",
  "species": "psilocybe_cubensis",
  "hours": 24,
  "environment": {
    "temperature": 24,
    "humidity": 90,
    "co2": 800,
    "light_hours": 12
  }
}
```

---

## Genetic Circuit Designer

**Location**: `/apps/genetic-circuit`  
**Theme**: Purple/Cyan (DNA bioluminescent aesthetic)  
**Purpose**: Gene regulatory network simulation

### Pre-built Circuits

| Circuit | Species | Product |
|---------|---------|---------|
| Psilocybin Pathway | P. cubensis | Psilocybin |
| Hericenone Pathway | H. erinaceus | Hericenone A |
| Ganoderic Pathway | G. lucidum | Ganoderic Acid A |
| Cordycepin Pathway | C. militaris | Cordycepin |

### How to Use

#### Loading a Circuit

1. Click "Load Circuit"
2. Select from preset pathways
3. View the gene network diagram

#### Running Simulation

1. **Set Parameters**
   - Simulation steps (10-1000)
   - Timestep (0.01-1.0)
   - Stress level (0-100%)
   - Nutrient level (0-100%)

2. **Apply Modifications**
   - Click on any gene node
   - Use slider to modify expression (-50 to +50)
   - Changes are highlighted in real-time

3. **Run**
   - Click "Simulate"
   - Watch gene expression dynamics
   - View metabolite accumulation

#### Analyzing Results

- **Trajectory Plot**: Expression levels over time
- **Bottleneck Analysis**: Identifies rate-limiting genes
- **Flux Rate**: Metabolite production efficiency
- **Optimization Suggestions**: Recommendations for improvement

### API Endpoint

```
POST /api/mindex/innovation/genetic-circuit
{
  "action": "simulate",
  "circuit_id": "psilocybin_pathway",
  "steps": 100,
  "modifications": {
    "psiD": 20,
    "psiM": -10
  }
}
```

---

## Symbiosis Mapper

**Location**: `/apps/symbiosis`  
**Theme**: Forest Green (Ecosystem aesthetic)  
**Purpose**: Inter-species relationship mapping

### Relationship Types

| Type | Color | Description |
|------|-------|-------------|
| Mycorrhizal | Green | Mutualistic root association |
| Parasitic | Red | One organism harmed |
| Saprotrophic | Orange | Decomposition relationship |
| Endophytic | Blue | Living within plant tissues |
| Lichen | Purple | Fungi-algae partnership |
| Predatory | Dark Red | Capturing other organisms |

### How to Use

#### Creating a Network

1. **Add Organisms**
   - Click "Add Organism"
   - Enter name and type (fungus, plant, bacteria, animal, algae)
   - Position is automatically arranged

2. **Add Relationships**
   - Click source organism
   - Click target organism
   - Select relationship type
   - Set strength (0.1-1.0)

3. **View Network**
   - Nodes are colored by organism type
   - Edges show relationship type and strength
   - Hover for detailed information

#### Network Analysis

1. Click "Analyze Network"
2. View metrics:
   - Keystone species (most connected)
   - Community structure
   - Relationship breakdown
   - Network density

#### Exporting

- **JSON**: Full network data
- **GeoJSON**: For Earth Simulator integration
- **CSV**: For spreadsheet analysis

### API Endpoint

```
GET /api/mindex/innovation/symbiosis
POST /api/mindex/innovation/symbiosis
{
  "action": "analyze"
}
```

---

## Retrosynthesis Viewer

**Location**: `/apps/retrosynthesis`  
**Theme**: Amber/Orange (Chemical aesthetic)  
**Purpose**: Biosynthetic pathway analysis

### How to Use

#### Analyzing a Compound

1. **Enter Target Compound**
   - Type compound name (e.g., "Psilocybin")
   - Or paste SMILES notation
   - Or select from MINDEX library

2. **Run Analysis**
   - Click "Analyze Pathway"
   - Wait for retrosynthesis computation
   - View step-by-step pathway

3. **Explore Results**
   - Each step shows:
     - Precursor compound
     - Reaction type
     - Enzyme involved
     - Confidence score
   - Click any step for details

#### Pathway Visualization

- **Node View**: Compounds as nodes, reactions as edges
- **Flow View**: Linear pathway representation
- **Tree View**: Alternative pathways branching

#### Predicting Precursors

1. Select any compound in the pathway
2. Click "Predict Precursors"
3. View alternative precursor suggestions

### API Endpoint

```
GET /api/mindex/innovation/retrosynthesis?compound=psilocybin
```

---

## Alchemy Lab

**Location**: `/apps/alchemy-lab`  
**Theme**: Violet/Gold (Mystical aesthetic)  
**Purpose**: Virtual compound design

### How to Use

#### Designing a New Compound

1. **Select Scaffold**
   - Tryptamine (psychedelics, neuroactives)
   - Steroid (anti-inflammatory, hormonal)
   - Triterpene (anticancer, hepatoprotective)
   - Polyketide (antimicrobial, cytotoxic)
   - Peptide (antimicrobial, immunomodulatory)
   - Polysaccharide (immunomodulatory, antioxidant)

2. **Add Modifications**
   - Hydroxyl (increases hydrophilicity)
   - Methyl (increases lipophilicity)
   - Amino (increases basicity)
   - Phosphate (prodrug conversion)
   - Acetyl (improves stability)
   - Fluorine (metabolic stability)

3. **Set Target Properties**
   - Molecular weight range
   - Target activities
   - Toxicity constraints

4. **Generate**
   - Click "Design Compound"
   - View predicted properties
   - See activity predictions

#### Virtual Screening

1. Click "Virtual Screening"
2. Set target activity
3. Set number of compounds (5-50)
4. Review ranked results

#### Optimization

1. Load a designed compound
2. Click "Optimize for Activity"
3. Select target activity
4. View optimization suggestions

### API Endpoint

```
POST /api/mindex/innovation/alchemy
{
  "action": "design",
  "scaffold": "tryptamine",
  "modifications": ["hydroxyl", "methyl"],
  "target_activities": ["psychedelic", "neurotrophic"],
  "mw_range": [200, 400]
}
```

---

## Research Apps

### Petri Dish Simulator (`/apps/petri-dish-sim`)

Simulates fungal colony growth on agar plates.

**Controls**:
- Click to add spore inoculation points
- Adjust temperature, humidity, nutrients
- Watch colony expansion over time
- Measure growth rate in mm/day

### Mushroom Simulator (`/apps/mushroom-sim`)

3D visualization of mushroom development.

**Controls**:
- Select species for accurate morphology
- Adjust environmental parameters
- View development stages
- Export 3D models

### Compound Analyzer (`/apps/compound-sim`)

Analyze chemical compounds from MINDEX.

**Features**:
- Search MINDEX compound library
- Search ChemSpider directly
- View molecular structure
- See bioactivity predictions
- Enrich data from external sources

### Spore Tracker (`/apps/spore-tracker`)

Global spore distribution monitoring.

**Features**:
- Interactive world map
- Real-time spore data
- Seasonal patterns
- Alert configuration

### Ancestry Database (`/ancestry`)

Fungal phylogenetic relationships.

**Features**:
- Species search
- Phylogenetic tree view
- Chemistry tab for compounds
- Research papers integration

### Growth Analytics (`/apps/growth-analytics`)

ML-powered growth predictions.

**Features**:
- Historical data analysis
- Trend prediction
- Optimization recommendations
- Export reports

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| App won't load | Clear browser cache, check internet connection |
| Simulation runs slow | Reduce step count, close other tabs |
| No data appearing | Check API connection, verify authentication |
| 3D view not working | Enable WebGL in browser settings |
| Results not saving | Check login status, verify MINDEX connection |

### Error Messages

| Error Code | Meaning | Fix |
|------------|---------|-----|
| `MINDEX_UNAVAILABLE` | Database connection failed | Retry in 30 seconds |
| `AUTH_EXPIRED` | Session timed out | Re-login at /natureos/login |
| `RATE_LIMIT` | Too many requests | Wait 1 minute |
| `INVALID_INPUT` | Bad parameter format | Check input values |

### Getting Help

- **Documentation**: `/docs` in the codebase
- **API Reference**: `/api/docs` (Swagger UI)
- **Support**: Contact MYCOSOFT support team
- **Community**: Discord/Slack channels

---

## Appendix: Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Start/Pause simulation |
| `R` | Reset simulation |
| `S` | Save current state |
| `E` | Export results |
| `?` | Show help |
| `Esc` | Close dialogs |

---

*Document generated by MYCOSOFT MAS v2.0*
