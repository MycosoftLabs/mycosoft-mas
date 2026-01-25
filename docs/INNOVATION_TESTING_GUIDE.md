# Innovation Apps Testing Guide

> Complete testing instructions for all innovation systems

**Version**: 1.0.0  
**Last Updated**: 2026-01-24

---

## Quick Start Testing

### Prerequisites

1. **Local Development Environment**
   ```powershell
   # Navigate to website directory
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
   
   # Install dependencies (if not already)
   npm install
   
   # Start development server on port 3010
   npm run dev -- -p 3010
   ```

2. **MINDEX API** (for full functionality)
   ```powershell
   # Navigate to MINDEX directory
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex
   
   # Start MINDEX API
   uvicorn mindex_api.main:app --reload --port 8000
   ```

3. **Environment Variables**
   Ensure `.env.local` contains:
   ```env
   NEXT_PUBLIC_MINDEX_API_URL=http://localhost:8000
   CHEMSPIDER_API_KEY=TSif8NaGxFixrCft4O581jGjIz2GnIo4TCQqM01h
   ```

---

## Testing Each App

### 1. Apps Portal Testing

**URL**: `http://localhost:3010/apps`

**Test Cases**:

| Test | Steps | Expected Result |
|------|-------|-----------------|
| Page Load | Navigate to /apps | Hero section with video loads |
| Tab Navigation | Click each tab (Research, Innovation, Defense, Developer) | Apps grid updates correctly |
| Theme Display | Observe app cards in Innovation tab | Each card has unique color theme |
| Card Hover | Hover over any card | Gradient overlay appears, icon scales |
| Card Click | Click any app card | Navigates to app page |

**Visual Check**:
- [ ] Physics Simulator card is indigo/purple
- [ ] Digital Twin card is lime green
- [ ] Lifecycle Simulator card is green/amber
- [ ] Genetic Circuit card is purple/cyan
- [ ] Symbiosis Mapper card is forest green
- [ ] Retrosynthesis card is amber/orange
- [ ] Alchemy Lab card is violet/gold

---

### 2. Physics Simulator Testing

**URL**: `http://localhost:3010/apps/physics-sim`

**API Test**:
```powershell
# Test Physics API endpoint
Invoke-RestMethod -Uri "http://localhost:3010/api/mindex/innovation/physics" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"action":"simulate","molecule":{"name":"Test Compound"},"parameters":{"steps":10}}'
```

**Expected Response**:
```json
{
  "simulation_id": "...",
  "trajectory": [...],
  "final_energy": 42.5,
  "quantum_properties": {
    "homo_lumo_gap": 3.2,
    "dipole_moment": 1.5
  }
}
```

**UI Test Cases**:
| Test | Steps | Expected |
|------|-------|----------|
| Page loads | Navigate to /apps/physics-sim | Canvas renders, controls visible |
| Molecule load | Enter "Psilocybin" in search | Molecule structure displays |
| Simulation run | Click "Simulate" | Progress indicator, animation plays |
| Export data | Click "Export" after simulation | JSON file downloads |

---

### 3. Digital Twin Mycelium Testing

**URL**: `http://localhost:3010/apps/digital-twin`

**API Test**:
```powershell
# GET - Fetch current state
Invoke-RestMethod -Uri "http://localhost:3010/api/mindex/innovation/digital-twin?species=psilocybe_cubensis"

# POST - Update with sensor data
Invoke-RestMethod -Uri "http://localhost:3010/api/mindex/innovation/digital-twin" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"action":"update","sensor_data":{"temperature_celsius":24,"humidity_percent":85}}'
```

**Expected Response**:
```json
{
  "biomass_grams": 5.2,
  "network_density": 0.35,
  "health": 100,
  "nodes": [...],
  "edges": [...]
}
```

**UI Test Cases**:
| Test | Steps | Expected |
|------|-------|----------|
| Initialize | Select species, click "Create" | Network graph appears |
| Node display | Observe canvas | 15+ nodes with connections |
| Sensor update | Enter temp/humidity, click "Update" | Biomass value changes |
| Prediction | Click "Predict 24h" | Prediction panel shows forecast |

---

### 4. Lifecycle Simulator Testing

**URL**: `http://localhost:3010/apps/lifecycle-sim`

**API Test**:
```powershell
Invoke-RestMethod -Uri "http://localhost:3010/api/mindex/innovation/lifecycle" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"action":"advance","species":"psilocybe_cubensis","hours":24,"environment":{"temperature":24,"humidity":90}}'
```

**Expected Response**:
```json
{
  "stage": "germination",
  "stage_progress": 0.45,
  "day_count": 1,
  "biomass_grams": 0.15,
  "health": 100,
  "recommendations": ["Conditions are optimal"]
}
```

**UI Test Cases**:
| Test | Steps | Expected |
|------|-------|----------|
| Species select | Choose "Golden Teacher" | Profile loads |
| Environment set | Adjust sliders | Values update in real-time |
| Advance 1 day | Click "Advance 24h" | Stage progress increases |
| Fast forward | Click "Fast Forward" | Progresses through stages |
| Harvest predict | After mycelial stage, click "Predict" | Date displayed |

**Stage Progression Check**:
```
Spore → Germination → Hyphal → Mycelial → Primordial → Fruiting → Sporulation → Decay
```

---

### 5. Genetic Circuit Designer Testing

**URL**: `http://localhost:3010/apps/genetic-circuit`

**API Test**:
```powershell
Invoke-RestMethod -Uri "http://localhost:3010/api/mindex/innovation/genetic-circuit" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"action":"simulate","circuit_id":"psilocybin_pathway","steps":100}'
```

**Expected Response**:
```json
{
  "circuit_name": "Psilocybin Biosynthesis",
  "trajectory": [[...], [...]],
  "final_state": {"psiD": 65.2, "psiK": 48.1, "psiM": 55.3, "psiH": 42.0},
  "final_metabolite": 12.5,
  "bottleneck_gene": "psiH"
}
```

**UI Test Cases**:
| Test | Steps | Expected |
|------|-------|----------|
| Load circuit | Select "Psilocybin Pathway" | 4 gene nodes appear |
| Modify gene | Click gene, adjust slider | Value changes, color updates |
| Run simulation | Click "Simulate" | Graph animates, trajectory shows |
| View bottleneck | Check analysis panel | Bottleneck gene highlighted |

---

### 6. Symbiosis Mapper Testing

**URL**: `http://localhost:3010/apps/symbiosis`

**API Test**:
```powershell
# GET network
Invoke-RestMethod -Uri "http://localhost:3010/api/mindex/innovation/symbiosis"

# POST analyze
Invoke-RestMethod -Uri "http://localhost:3010/api/mindex/innovation/symbiosis" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"action":"analyze"}'
```

**Expected Response**:
```json
{
  "num_organisms": 30,
  "num_relationships": 45,
  "keystone_species": [{"name": "Fungus 5", "degree": 12}],
  "relationship_breakdown": {"mycorrhizal": 15, "parasitic": 8}
}
```

**UI Test Cases**:
| Test | Steps | Expected |
|------|-------|----------|
| Generate network | Click "Generate Sample" | 30 nodes appear |
| View relationships | Observe edges | Colored by type |
| Add organism | Click "Add", enter details | New node appears |
| Analyze | Click "Analyze" | Stats panel updates |
| Export GeoJSON | Click "Export GeoJSON" | File downloads |

---

### 7. Retrosynthesis Viewer Testing

**URL**: `http://localhost:3010/apps/retrosynthesis`

**API Test**:
```powershell
Invoke-RestMethod -Uri "http://localhost:3010/api/mindex/innovation/retrosynthesis?compound=psilocybin"
```

**Expected Response**:
```json
{
  "target": {"name": "Psilocybin"},
  "starting_material": "L-Tryptophan",
  "total_steps": 5,
  "steps": [
    {"precursor": "Tryptophan", "product": "Tryptamine", "enzyme": "TrpDC"},
    ...
  ],
  "pathway_type": "known"
}
```

**UI Test Cases**:
| Test | Steps | Expected |
|------|-------|----------|
| Search compound | Enter "Psilocybin" | Pathway loads |
| View steps | Observe diagram | 5 steps shown |
| Click step | Click any reaction | Details panel opens |
| Unknown compound | Enter "Novel Compound X" | Predicted pathway generated |

---

### 8. Alchemy Lab Testing

**URL**: `http://localhost:3010/apps/alchemy-lab`

**API Test**:
```powershell
Invoke-RestMethod -Uri "http://localhost:3010/api/mindex/innovation/alchemy" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"action":"design","scaffold":"tryptamine","modifications":["hydroxyl"],"target_activities":["psychedelic"]}'
```

**Expected Response**:
```json
{
  "id": "MYCO-12345",
  "name": "Tryptamine Derivative MYCO-12345",
  "formula": "C10H12N2",
  "molecular_weight": 176.22,
  "predicted_activities": [
    {"activity_name": "Psychedelic", "confidence": 0.85}
  ],
  "optimization_score": 0.72
}
```

**UI Test Cases**:
| Test | Steps | Expected |
|------|-------|----------|
| Select scaffold | Choose "Tryptamine" | Base structure loads |
| Add modification | Check "Hydroxyl" | MW increases |
| Set target | Select "Psychedelic" | Target highlighted |
| Design | Click "Design Compound" | New compound generated |
| Screen | Click "Virtual Screening", set count | Multiple compounds ranked |

---

## API Endpoint Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/mindex/innovation/physics` | GET/POST | Physics simulations |
| `/api/mindex/innovation/digital-twin` | GET/POST | Mycelium digital twin |
| `/api/mindex/innovation/lifecycle` | POST | Lifecycle advancement |
| `/api/mindex/innovation/genetic-circuit` | GET/POST | Gene circuit simulation |
| `/api/mindex/innovation/symbiosis` | GET/POST | Symbiosis network |
| `/api/mindex/innovation/retrosynthesis` | GET | Pathway analysis |
| `/api/mindex/innovation/alchemy` | POST | Compound design |

---

## Automated Testing Script

Save as `test-innovation-apps.ps1`:

```powershell
# Innovation Apps API Test Script
# Run from project root

$baseUrl = "http://localhost:3010"
$results = @()

Write-Host "=== INNOVATION APPS API TESTING ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Physics Simulator
Write-Host "Testing Physics Simulator..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/mindex/innovation/physics" -Method POST `
        -ContentType "application/json" `
        -Body '{"action":"simulate","molecule":{"name":"Test"},"parameters":{"steps":5}}'
    Write-Host "  ✓ Physics API responded" -ForegroundColor Green
    $results += @{Name="Physics"; Status="PASS"}
} catch {
    Write-Host "  ✗ Physics API failed: $($_.Exception.Message)" -ForegroundColor Red
    $results += @{Name="Physics"; Status="FAIL"}
}

# Test 2: Digital Twin
Write-Host "Testing Digital Twin..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/mindex/innovation/digital-twin?species=test"
    Write-Host "  ✓ Digital Twin API responded" -ForegroundColor Green
    $results += @{Name="Digital Twin"; Status="PASS"}
} catch {
    Write-Host "  ✗ Digital Twin API failed: $($_.Exception.Message)" -ForegroundColor Red
    $results += @{Name="Digital Twin"; Status="FAIL"}
}

# Test 3: Lifecycle
Write-Host "Testing Lifecycle Simulator..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/mindex/innovation/lifecycle" -Method POST `
        -ContentType "application/json" `
        -Body '{"action":"advance","species":"test","hours":1}'
    Write-Host "  ✓ Lifecycle API responded" -ForegroundColor Green
    $results += @{Name="Lifecycle"; Status="PASS"}
} catch {
    Write-Host "  ✗ Lifecycle API failed: $($_.Exception.Message)" -ForegroundColor Red
    $results += @{Name="Lifecycle"; Status="FAIL"}
}

# Test 4: Genetic Circuit
Write-Host "Testing Genetic Circuit..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/mindex/innovation/genetic-circuit" -Method POST `
        -ContentType "application/json" `
        -Body '{"action":"simulate","circuit_id":"psilocybin_pathway","steps":10}'
    Write-Host "  ✓ Genetic Circuit API responded" -ForegroundColor Green
    $results += @{Name="Genetic Circuit"; Status="PASS"}
} catch {
    Write-Host "  ✗ Genetic Circuit API failed: $($_.Exception.Message)" -ForegroundColor Red
    $results += @{Name="Genetic Circuit"; Status="FAIL"}
}

# Test 5: Symbiosis
Write-Host "Testing Symbiosis Mapper..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/mindex/innovation/symbiosis"
    Write-Host "  ✓ Symbiosis API responded" -ForegroundColor Green
    $results += @{Name="Symbiosis"; Status="PASS"}
} catch {
    Write-Host "  ✗ Symbiosis API failed: $($_.Exception.Message)" -ForegroundColor Red
    $results += @{Name="Symbiosis"; Status="FAIL"}
}

# Test 6: Retrosynthesis
Write-Host "Testing Retrosynthesis..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/mindex/innovation/retrosynthesis?compound=psilocybin"
    Write-Host "  ✓ Retrosynthesis API responded" -ForegroundColor Green
    $results += @{Name="Retrosynthesis"; Status="PASS"}
} catch {
    Write-Host "  ✗ Retrosynthesis API failed: $($_.Exception.Message)" -ForegroundColor Red
    $results += @{Name="Retrosynthesis"; Status="FAIL"}
}

# Test 7: Alchemy Lab
Write-Host "Testing Alchemy Lab..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/mindex/innovation/alchemy" -Method POST `
        -ContentType "application/json" `
        -Body '{"action":"design","scaffold":"tryptamine"}'
    Write-Host "  ✓ Alchemy Lab API responded" -ForegroundColor Green
    $results += @{Name="Alchemy Lab"; Status="PASS"}
} catch {
    Write-Host "  ✗ Alchemy Lab API failed: $($_.Exception.Message)" -ForegroundColor Red
    $results += @{Name="Alchemy Lab"; Status="FAIL"}
}

# Summary
Write-Host ""
Write-Host "=== TEST SUMMARY ===" -ForegroundColor Cyan
$passed = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failed = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
Write-Host "Passed: $passed / $($results.Count)" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
if ($failed -gt 0) {
    Write-Host "Failed: $failed" -ForegroundColor Red
}
```

---

## Browser-Based Testing

### Using Browser DevTools

1. Open any app page
2. Press F12 to open DevTools
3. Go to **Network** tab
4. Perform actions in the app
5. Verify API calls are successful (200 status)

### Console Commands

In browser console, test API directly:

```javascript
// Test Physics API
fetch('/api/mindex/innovation/physics', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({action: 'simulate', molecule: {name: 'Test'}, parameters: {steps: 5}})
}).then(r => r.json()).then(console.log)

// Test Digital Twin
fetch('/api/mindex/innovation/digital-twin?species=test')
  .then(r => r.json()).then(console.log)
```

---

## Performance Benchmarks

| App | Load Time | API Response | Simulation (100 steps) |
|-----|-----------|--------------|------------------------|
| Physics Sim | < 2s | < 500ms | < 3s |
| Digital Twin | < 1.5s | < 300ms | N/A |
| Lifecycle Sim | < 1s | < 200ms | < 1s |
| Genetic Circuit | < 1.5s | < 400ms | < 2s |
| Symbiosis | < 2s | < 300ms | N/A |
| Retrosynthesis | < 1s | < 500ms | N/A |
| Alchemy Lab | < 1.5s | < 600ms | < 2s |

---

## Reporting Issues

When reporting bugs, include:

1. **App name and URL**
2. **Steps to reproduce**
3. **Expected vs actual behavior**
4. **Browser console errors** (F12 → Console)
5. **Network request failures** (F12 → Network)
6. **Screenshots if applicable**

Submit to: `github.com/mycosoft/issues` or internal bug tracker

---

*Testing Guide v1.0 - MYCOSOFT Innovation Team*
