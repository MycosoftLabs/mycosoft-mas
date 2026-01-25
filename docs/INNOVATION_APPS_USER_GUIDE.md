# Innovation Apps User Guide

**Version**: 1.0  
**Date**: 2026-01-24  
**Author**: Mycosoft Engineering Team

## Overview

This guide covers all innovation applications in the Mycosoft platform. These apps leverage the Nature Learning Model (NLM) for advanced physics, biology, and chemistry computations.

---

## Table of Contents

1. [Physics Simulator (QISE)](#1-physics-simulator-qise)
2. [Digital Twin Mycelium](#2-digital-twin-mycelium)
3. [Lifecycle Simulator](#3-lifecycle-simulator)
4. [Genetic Circuit Designer](#4-genetic-circuit-designer)
5. [Symbiosis Network Mapper](#5-symbiosis-network-mapper)
6. [Retrosynthesis Pathway Viewer](#6-retrosynthesis-pathway-viewer)
7. [Computational Alchemy Lab](#7-computational-alchemy-lab)
8. [API Integration](#8-api-integration)

---

## 1. Physics Simulator (QISE)

**URL**: `/apps/physics-sim`

### Purpose
Perform quantum-inspired molecular simulations using the QISE (Quantum-Inspired Simulation Engine) to calculate ground state energies, molecular properties, and field physics correlations.

### Features
- **QISE Mode**: Variational quantum eigensolver for ground state calculation
- **Molecular Dynamics**: Real-time MD simulations with force field support
- **Tensor Network**: Matrix Product States for large (50+ atom) systems
- **Field Physics**: Geomagnetic, lunar, and atmospheric influence analysis

### How to Use

1. **Select a Molecule**: Choose from predefined fungal compounds (Psilocybin, Muscimol, etc.)
2. **Choose Simulation Method**:
   - QISE: Best for ground state energy calculation
   - Molecular Dynamics: Best for trajectory analysis
   - Tensor Network: Best for large molecular systems
3. **Adjust Parameters** (if applicable):
   - Simulation steps
   - Timestep (for MD)
   - Bond dimension (for Tensor Networks)
4. **Run Simulation**: Click the run button and wait for results
5. **View Results**: Ground state energy, HOMO-LUMO gap, dipole moment, polarizability

### Field Physics Tab
- Enter latitude, longitude, and altitude
- Get geomagnetic field vectors (Bx, By, Bz)
- View lunar phase and gravitational influence
- Receive fruiting probability predictions based on environmental conditions

### Integration Points
- Exports data for Earth Simulator visualization
- Connects to MINDEX compound database
- Uses NLM physics layer (`nlm/physics/`)

---

## 2. Digital Twin Mycelium

**URL**: `/apps/digital-twin`

### Purpose
Create real-time digital representations of mycelial networks that can be fed with MycoBrain sensor data for predictive modeling and growth optimization.

### Features
- **Live Network Visualization**: See mycelial network topology in real-time
- **MycoBrain Integration**: Connect to physical sensors for data updates
- **Growth Prediction**: Forecast biomass and network density
- **Signal Propagation**: Visualize electrical and chemical signals moving through the network

### How to Use

1. **Connect to MycoBrain** (optional):
   - Enter device ID (e.g., MB-001)
   - Click "Connect" to receive live sensor data
2. **View Network Visualization**:
   - Green dots = hyphal tips
   - Blue dots = junctions
   - Orange dots = fruiting body initiation sites
   - Lines = hyphal connections with signal activity
3. **Monitor Sensor Data**:
   - Temperature, humidity, CO2, light, pH, electrical conductivity
   - Auto-update toggle for continuous monitoring
4. **Run Growth Predictions**:
   - Set prediction window (6-168 hours)
   - View predicted biomass, density, and fruiting probability
   - Follow recommendations for optimal conditions

### Key Metrics
- **Biomass**: Total mycelial mass in grams
- **Network Density**: Interconnectedness (0-100%)
- **Resource Level**: Available nutrients
- **Signal Activity**: Electrical/chemical communication intensity

### Integration Points
- Connects to MycoBrain devices via WebSocket
- Exports GeoJSON for Earth Simulator
- Uses NLM biology layer (`nlm/biology/digital_twin.py`)

---

## 3. Lifecycle Simulator

**URL**: `/apps/lifecycle-sim`

### Purpose
Simulate the complete fungal lifecycle from spore germination to fruiting body development and sporulation, with environmental optimization recommendations.

### Features
- **7-Stage Lifecycle**: Spore → Germination → Hyphal Growth → Mycelial Network → Primordial → Fruiting → Sporulation
- **Species Profiles**: Pre-configured settings for common species
- **Environmental Controls**: Temperature, humidity, light, CO2
- **Harvest Prediction**: Estimated dates and yields

### How to Use

1. **Select Species**: Choose from:
   - *Psilocybe cubensis*
   - *Hericium erinaceus*
   - *Pleurotus ostreatus*
   - *Ganoderma lucidum*
   - *Cordyceps militaris*
   - *Trametes versicolor*
2. **Start Simulation**: Click Play to begin
3. **Adjust Environment**:
   - Match conditions to species requirements
   - Watch health score for optimization feedback
4. **Monitor Progress**:
   - Current stage and progress
   - Days elapsed
   - Biomass accumulation
5. **Speed Control**: Adjust simulation speed (0.5x - 10x)

### Environmental Guidelines
| Parameter | Typical Range | Effect on Growth |
|-----------|---------------|------------------|
| Temperature | 15-28°C | Species-specific optimum |
| Humidity | 85-95% | Higher = faster growth |
| Light Hours | 0-24h | Required for fruiting |
| CO2 | 200-2000 ppm | Lower = better fruiting |

### Integration Points
- Uses species data from MINDEX
- Connects to MycoBrain for real-world validation
- Uses NLM biology layer (`nlm/biology/lifecycle.py`)

---

## 4. Genetic Circuit Designer

**URL**: `/apps/genetic-circuit`

### Purpose
Simulate gene regulatory networks and metabolic pathways to understand and optimize biosynthesis of fungal compounds.

### Features
- **Pre-built Pathways**: Psilocybin, Hericenone, Ganoderic Acid, Cordycepin
- **Gene Expression Visualization**: Real-time expression levels
- **Modification System**: Overexpress or knockdown genes
- **Flux Analysis**: Metabolite production rates

### How to Use

1. **Select Genetic Circuit**: Choose a biosynthetic pathway
2. **View Pathway Visualization**:
   - Colored bars show gene expression levels
   - Green = activated, Blue = basal, Red = repressed
   - Orange circle = product accumulation
3. **Start Simulation**: Click Play
4. **Apply Gene Modifications**:
   - Use sliders to overexpress (+) or knockdown (-) genes
   - Observe effects on metabolite production
5. **Adjust Environmental Stress**:
   - Increase stress to simulate unfavorable conditions
   - Adjust nutrient levels

### Key Metrics
- **Metabolite Level**: Target compound concentration
- **Flux Rate**: Production velocity
- **Bottleneck Gene**: Rate-limiting step in pathway
- **Average Expression**: Overall pathway activity

### Integration Points
- Connects to Retrosynthesis Viewer for pathway details
- Links to Alchemy Lab for compound design
- Uses NLM biology layer (`nlm/biology/genetic_circuit.py`)

---

## 5. Symbiosis Network Mapper

**URL**: `/apps/symbiosis`

### Purpose
Map and analyze symbiotic relationships between fungi and other organisms to understand ecosystem dynamics.

### Features
- **Relationship Types**: Mycorrhizal, Parasitic, Saprotrophic, Endophytic, Lichen, Predatory
- **Interactive Network**: Click to explore organisms and connections
- **Filtering**: View specific relationship types
- **Statistics**: Network analysis metrics

### How to Use

1. **Explore the Network**:
   - Green nodes = Fungi
   - Light green = Plants
   - Cyan = Bacteria
   - Red = Animals
   - Teal = Algae
2. **Click on Organisms**: View details and relationships
3. **Filter by Relationship Type**: Use dropdown to focus on specific interactions
4. **Analyze Statistics**:
   - Total organisms and relationships
   - Average connectivity

### Relationship Types Explained

| Type | Color | Description |
|------|-------|-------------|
| Mycorrhizal | Green | Mutualistic root association |
| Parasitic | Red | Harmful to host organism |
| Saprotrophic | Orange | Decomposing dead matter |
| Endophytic | Blue | Living within plant tissues |
| Lichen | Purple | Fungi-algae partnership |
| Predatory | Red | Nematode-trapping, etc. |

### Integration Points
- Exports GeoJSON for Earth Simulator
- Uses MINDEX species data
- Uses NLM biology layer (`nlm/biology/symbiosis.py`)

---

## 6. Retrosynthesis Pathway Viewer

**URL**: `/apps/retrosynthesis`

### Purpose
Analyze biosynthetic pathways from target compound back to precursor molecules, identifying enzymes and conditions required for production.

### Features
- **Pathway Analysis**: Step-by-step biosynthesis routes
- **Enzyme Mapping**: Identify all enzymes in the pathway
- **Yield Calculation**: Overall and per-step yields
- **Cultivation Notes**: Practical growing recommendations

### How to Use

1. **Select Target Compound**: Choose from:
   - Psilocybin, Muscimol, Hericenone A, Cordycepin, Ganoderic Acid A, Ergotamine
2. **Analyze Pathway**: Click search button
3. **Explore Steps**:
   - Click each step to expand details
   - View substrate, product, enzyme, conditions
   - Check yield percentages
4. **Review Cultivation Notes**: Practical tips for production

### Pathway Metrics
- **Rate-Limiting Step**: Lowest yield step
- **Reversible Steps**: Steps that can go backward
- **Cofactor Requirements**: ATP, NADPH, etc.

### Integration Points
- Opens compounds in Alchemy Lab
- Links to Genetic Circuit Designer
- Uses NLM chemistry layer (`nlm/chemistry/retrosynthesis.py`)

---

## 7. Computational Alchemy Lab

**URL**: `/apps/alchemy-lab`

### Purpose
Design novel fungal compounds by combining molecular scaffolds with functional groups and predict their properties using AI.

### Features
- **Scaffold Library**: Indole, Ergoline, β-Carboline, Lanostane, Macrolide
- **Functional Groups**: Hydroxyl, Amino, Methyl, Phosphate, Acetyl, Phenyl
- **Property Prediction**: Drug-likeness, synthesizability, toxicity, bioactivity
- **Synthesis Planning**: Step-by-step production routes

### How to Use

1. **Select Scaffold**: Base molecular structure
2. **Add Modifications**:
   - Choose position (1-6)
   - Select functional group
   - Add up to 6 modifications
3. **Name Compound** (optional)
4. **Design & Predict**: Generate AI predictions
5. **View Results**:
   - Molecular weight, logP
   - Drug-likeness score
   - Synthesizability score
   - Safety score
   - Predicted bioactivities
6. **Plan Synthesis**: Get a production route with yields and costs

### Scoring Explained
| Score | Description |
|-------|-------------|
| Drug-Likeness | How similar to known drugs |
| Synthesizability | Ease of production |
| Safety | Inverse of toxicity risk |
| Bioactivities | Predicted biological effects |

### Integration Points
- Connects to ChemSpider for compound data
- Links to MINDEX compound database
- Uses NLM chemistry layer (`nlm/chemistry/alchemy.py`)

---

## 8. API Integration

All innovation apps connect to backend APIs for data and computation:

### MINDEX API Endpoints

```
GET  /api/compounds                    - List all compounds
GET  /api/compounds/{id}               - Get compound details
GET  /api/compounds/for-taxon/{id}     - Get compounds for species
POST /api/compounds/enrich             - Enrich from ChemSpider
GET  /api/compounds/chemspider/search  - Search ChemSpider
```

### NLM Physics API Endpoints

```
POST /api/physics/molecular/simulate   - QISE simulation
POST /api/physics/molecular/dynamics   - MD simulation
POST /api/physics/field/conditions     - Field physics data
POST /api/physics/field/fruiting-prediction - Fruiting forecast
```

### Environment Variables Required

```env
NEXT_PUBLIC_MINDEX_API_URL=https://mindex.mycosoft.com
CHEMSPIDER_API_KEY=your_key_here
NEXT_PUBLIC_CHEMSPIDER_API_KEY=your_key_here
```

### Local Development

1. Start MINDEX API:
   ```bash
   cd MINDEX/mindex
   docker-compose up -d
   ```

2. Start Website:
   ```bash
   cd WEBSITE/website
   npm run dev
   ```

3. Access apps at `http://localhost:3010/apps`

---

## Troubleshooting

### Common Issues

1. **"Failed to connect to MINDEX"**
   - Check MINDEX API is running
   - Verify `NEXT_PUBLIC_MINDEX_API_URL` is set

2. **"ChemSpider API key not configured"**
   - Add `CHEMSPIDER_API_KEY` to environment

3. **Simulation not running**
   - Select required inputs (molecule, species, etc.)
   - Check browser console for errors

4. **Network visualization blank**
   - Enable JavaScript/Canvas in browser
   - Check for WebGL support

### Support

- Technical docs: `/docs/INNOVATION_IMPLEMENTATION_SUMMARY.md`
- API reference: `/docs/API_ENDPOINTS_REFERENCE.md`
- Architecture: `/docs/NLM_IMPLEMENTATION_PLAN.md`

---

*Document Version 1.0 | Last Updated: 2026-01-24*
