# NVIDIA Earth-2 Integration Guide
## February 4, 2026

This document provides a comprehensive guide to the NVIDIA Earth-2 integration in the Mycosoft MAS system.

## Overview

NVIDIA Earth-2 has been fully integrated into the Mycosoft MAS (Multi-Agent System) to provide:
- AI-powered weather forecasting (0-15 days)
- Nowcasting for severe weather (0-6 hours)
- High-resolution downscaling
- Data assimilation
- Spore dispersal modeling for FUSARIUM

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                      MYCOSOFT FUSARIUM                          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚ CREP        â”‚  â”‚ Earth       â”‚  â”‚ PersonaPlex             â”‚ â”‚
â”‚  â”‚ Dashboard   â”‚  â”‚ Simulator   â”‚  â”‚ Voice Interface         â”‚ â”‚
â”‚  â”‚ (2D Map)    â”‚  â”‚ (3D Globe)  â”‚  â”‚                         â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚         â”‚                â”‚                      â”‚               â”‚
â”‚         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜               â”‚
â”‚                          â”‚                                      â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚                    MAS API (FastAPI)                       â”‚ â”‚
â”‚  â”‚  /api/earth2/forecast  /api/earth2/nowcast                â”‚ â”‚
â”‚  â”‚  /api/earth2/spore-dispersal  /api/earth2/layers          â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                          â”‚                                      â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚                  Earth-2 Agents (MAS)                      â”‚ â”‚
â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚ â”‚
â”‚  â”‚  â”‚ Orchestrator â”‚ â”‚ Forecast     â”‚ â”‚ Spore Dispersal  â”‚   â”‚ â”‚
â”‚  â”‚  â”‚ Agent        â”‚ â”‚ Agent        â”‚ â”‚ Agent            â”‚   â”‚ â”‚
â”‚  â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚ â”‚
â”‚  â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                        â”‚ â”‚
â”‚  â”‚  â”‚ Nowcast      â”‚ â”‚ Climate Sim  â”‚                        â”‚ â”‚
â”‚  â”‚  â”‚ Agent        â”‚ â”‚ Agent        â”‚                        â”‚ â”‚
â”‚  â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                        â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                          â”‚                                      â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚               Earth2Studio Service                         â”‚ â”‚
â”‚  â”‚  - run_forecast()  - run_nowcast()                        â”‚ â”‚
â”‚  â”‚  - run_downscale() - run_assimilation()                   â”‚ â”‚
â”‚  â”‚  - run_spore_dispersal()                                  â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                          â”‚                                      â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚              NVIDIA Earth-2 Models (GPU)                   â”‚ â”‚
â”‚  â”‚  Atlas | StormScope | CorrDiff | HealDA | FourCastNet     â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                                                                 â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚                    MINDEX Database                         â”‚ â”‚
â”‚  â”‚  earth2.model_runs | earth2.forecasts | earth2.nowcasts   â”‚ â”‚
â”‚  â”‚  earth2.spore_dispersal | earth2.visualization_layers     â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Components Created

### 1. Earth2Studio Service Wrapper
**File:** `mycosoft_mas/earth2/earth2_service.py`

Asynchronous wrapper for NVIDIA Earth2Studio library:
- `run_forecast()` - Medium-range forecasts using Atlas
- `run_nowcast()` - Short-range nowcasts using StormScope
- `run_downscale()` - High-resolution downscaling using CorrDiff
- `run_assimilation()` - Data assimilation using HealDA
- `run_spore_dispersal()` - Combined weather + spore modeling

### 2. Pydantic Data Models
**File:** `mycosoft_mas/earth2/models.py`

Strongly-typed models for:
- `ForecastParams` / `ForecastResult` - Medium-range forecast I/O
- `NowcastParams` / `NowcastResult` - Nowcast I/O
- `DownscaleParams` / `DownscaleResult` - Downscaling I/O
- `SporeDispersalParams` / `SporeDispersalResult` - Spore modeling I/O
- `WeatherVariable` - Enum for weather variables (t2m, u10, v10, tp, etc.)
- `Earth2Model` - Enum for available models

### 3. MINDEX Database Schema
**File:** `migrations/016_earth2_integration.sql`

PostgreSQL schema extension:
- `earth2.model_runs` - Track all Earth-2 model executions
- `earth2.forecasts` - Store forecast outputs
- `earth2.nowcasts` - Store nowcast outputs
- `earth2.spore_dispersal` - Combined weather + spore data
- `earth2.visualization_layers` - Layers for CREP/Earth Simulator

### 4. MAS Agents
**File:** `mycosoft_mas/agents/v2/earth2_agents.py`

Specialized agents:
- `Earth2OrchestratorAgent` - Manages model runs and GPU scheduling
- `WeatherForecastAgent` - Runs Atlas medium-range forecasts
- `NowcastAgent` - Runs StormScope nowcasts
- `ClimateSimulationAgent` - Long-term climate scenarios
- `SporeDispersalAgent` - Combines Earth-2 with MINDEX spore data

### 5. LLM Tools
**File:** `mycosoft_mas/llm/earth2_tools.py`

Tools for PersonaPlex voice interface:
- `earth2_forecast` - Get weather forecast for a location
- `earth2_nowcast` - Get short-range nowcast
- `earth2_spore_dispersal` - Run spore dispersal model
- `earth2_model_status` - Check model run status

### 6. API Endpoints
**File:** `mycosoft_mas/core/routers/earth2_api.py`

REST API endpoints:
- `GET /api/earth2/health` - Health check
- `GET /api/earth2/models` - List available models
- `POST /api/earth2/forecast` - Submit forecast request
- `POST /api/earth2/nowcast` - Submit nowcast request
- `POST /api/earth2/spore-dispersal` - Submit spore dispersal request
- `GET /api/earth2/runs/{run_id}` - Get run status
- `GET /api/earth2/layers` - List visualization layers

### 7. n8n Workflows
**Files:**
- `n8n/workflows/43_earth2_crep_simulator.json` - Original CREP workflow (updated)
- `n8n/workflows/48_earth2_weather_automation.json` - Scheduled forecast automation
- `n8n/workflows/49_earth2_spore_alert.json` - Hourly spore dispersal alerts
- `n8n/workflows/50_earth2_nowcast_alert.json` - 30-minute nowcast alerts

## Website Integration (TODO)

### CREP Dashboard Components
Create in `website/src/components/crep/earth2/`:

```tsx
// WeatherLayerControl.tsx
// Toggle Earth-2 weather layers on 2D map

// SporeDispersalLayer.tsx
// Visualize spore concentration heatmaps

// ForecastTimeline.tsx
// Timeline slider for forecast animation

// AlertPanel.tsx
// Display weather and spore alerts
```

### Earth Simulator 3D Components
Create in `website/src/components/earth-simulator/earth2/`:

```tsx
// WeatherVolumeLayer.tsx
// 3D volumetric weather visualization

// SporeParticleSystem.tsx
// 3D spore particle animation

// StormCellVisualization.tsx
// 3D storm cell rendering

// WindFieldArrows.tsx
// 3D wind vector visualization
```

## Configuration

### Environment Variables
```bash
# GPU Configuration
EARTH2_GPU_DEVICE=cuda:0

# Model Cache
EARTH2_MODEL_CACHE=/opt/mycosoft/earth2/models

# Output Storage
EARTH2_OUTPUT_PATH=/opt/mycosoft/earth2/outputs

# API Configuration
EARTH2_API_URL=http://192.168.0.188:8001/api/earth2
```

### Dependencies
```
nvidia-earth2studio>=0.3.0
torch>=2.0.0
xarray>=2024.1.0
zarr>=2.16.0
netCDF4>=1.6.0
```

## Usage Examples

### Python - Run Forecast
```python
from mycosoft_mas.earth2 import get_earth2_service, ForecastParams, Earth2Model, WeatherVariable
from datetime import datetime

service = get_earth2_service()

params = ForecastParams(
    model=Earth2Model.ATLAS_ERA5,
    start_time=datetime.now(),
    forecast_hours=168,  # 7 days
    step_hours=6,
    variables=[WeatherVariable.T2M, WeatherVariable.TP],
    ensemble_members=10
)

result = await service.run_forecast(params)
print(f"Forecast run ID: {result.run_id}")
```

### API - Submit Spore Dispersal
```bash
curl -X POST http://192.168.0.188:8001/api/earth2/spore-dispersal \
  -H "Content-Type: application/json" \
  -d '{
    "species": "Fusarium graminearum",
    "origin_lat": 41.5,
    "origin_lon": -93.0,
    "origin_concentration": 10000,
    "forecast_hours": 48
  }'
```

### Voice (PersonaPlex)
```
User: "What's the weather forecast for Chicago this week?"
MYCA: "Let me check the Earth-2 forecast for Chicago..."
      [Calls earth2_forecast tool]
      "The forecast shows temperatures ranging from 35-42Â°F with a 
       chance of precipitation on Thursday and Friday."
```

## Testing

Run the test suite:
```bash
cd mycosoft-mas
pytest tests/test_earth2_integration.py -v
```

## Next Steps

1. **Deploy Schema Migration**
   ```bash
   psql -h 192.168.0.188 -U mycosoft -d mindex -f migrations/016_earth2_integration.sql
   ```

2. **Install Earth2Studio**
   ```bash
   pip install nvidia-earth2studio
   ```

3. **Configure GPU Node**
   - Ensure CUDA 12.0+ is installed
   - Set up model cache directory
   - Configure output storage

4. **Import n8n Workflows**
   - Import workflows 48, 49, 50 into n8n
   - Configure webhook URLs
   - Set up notification channels

5. **Website Integration**
   - Create React components for CREP and Earth Simulator
   - Integrate with MAS API
   - Add Cesium/MapLibre layers

## Support

For issues or questions:
- MINDEX: https://github.com/MycosoftLabs/mindex
- NatureOS: https://github.com/MycosoftLabs/NatureOS
- Website: https://github.com/MycosoftLabs/website
