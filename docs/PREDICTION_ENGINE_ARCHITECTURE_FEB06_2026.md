# Prediction Engine Architecture - February 6, 2026

## Overview

The CREP Prediction Engine provides forward-looking position predictions for various entity types, enabling the timeline to extend into the future. The engine uses domain-specific algorithms ranging from physics-based orbit propagation to statistical migration models.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PREDICTION ENGINE ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         PREDICTION API (FastAPI)                          │   │
│  │  POST /prediction/predict  │  POST /prediction/batch  │  GET /*/entity   │   │
│  │  POST /prediction/weather  │  GET /prediction/storms  │  POST /wildfire  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                         │
│                                        ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                           BASE PREDICTOR                                  │   │
│  │  • Confidence decay (exponential)                                         │   │
│  │  • Uncertainty growth (linear)                                            │   │
│  │  • Prediction horizon limits                                              │   │
│  │  • Caching and validation                                                 │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                         │
│           ┌────────────────────────────┼────────────────────────────┐           │
│           │              │             │             │              │           │
│           ▼              ▼             ▼             ▼              ▼           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│  │  AIRCRAFT  │ │   VESSEL   │ │ SATELLITE  │ │  WILDLIFE  │ │   HAZARD   │    │
│  │  PREDICTOR │ │  PREDICTOR │ │  PREDICTOR │ │  PREDICTOR │ │  PREDICTOR │    │
│  ├────────────┤ ├────────────┤ ├────────────┤ ├────────────┤ ├────────────┤    │
│  │• Flight    │ │• Dest route│ │• SGP4/SDP4 │ │• Migration │ │• Aftershock│    │
│  │  plans     │ │• Course    │ │• TLE data  │ │  patterns  │ │• Fire sprd │    │
│  │• Vector    │ │  extrap    │ │• Orbital   │ │• Trajectory│ │• Storm trk │    │
│  │  extrap    │ │• Shipping  │ │  mechanics │ │• Random    │ │• Tsunami   │    │
│  │• ADS-B     │ │  lanes     │ │            │ │  walk      │ │• Ash cloud │    │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
│                                        │                                         │
│                                        ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        EARTH-2 FORECASTER                                 │   │
│  │  • Weather forecasts (FourCastNet, Pangu, GraphCast)                      │   │
│  │  • Storm track predictions                                                │   │
│  │  • Wildfire spread modeling                                               │   │
│  │  • Forecast tile generation                                               │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                         │
│                                        ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        PREDICTION STORE (MINDEX)                          │   │
│  │  • Store predictions as forecast timeline entries                         │   │
│  │  • Source flagging for visual differentiation                             │   │
│  │  • Automatic cleanup of outdated predictions                              │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Backend Components

### 1. Base Predictor (`mycosoft_mas/prediction/base_predictor.py`)

Abstract base class providing common functionality:

```python
class BasePredictor(ABC):
    entity_type: EntityType
    initial_confidence: float = 0.95
    confidence_half_life_seconds: float = 900  # 15 minutes
    max_prediction_horizon: timedelta = timedelta(hours=2)
    
    async def predict(self, request: PredictionRequest) -> PredictionResult
    def calculate_confidence(self, prediction_age_seconds: float) -> float
    def calculate_uncertainty(self, prediction_age_seconds: float) -> UncertaintyCone
```

**Features:**
- Exponential confidence decay over time
- Linear uncertainty cone growth
- Request validation and caching
- Automatic horizon clamping

### 2. Aircraft Predictor (`mycosoft_mas/prediction/aircraft_predictor.py`)

Predicts aircraft positions using multiple strategies:

| Strategy | Use Case | Confidence | Horizon |
|----------|----------|------------|---------|
| Flight Plan | Filed route available | 95% → 80% | 4 hours |
| ADS-B Intent | Near-term trajectory | 90% → 60% | 30 min |
| Vector Extrapolation | Fallback | 90% → 30% | 30 min |

**Algorithm:**
1. Check for flight plan data
2. If found: interpolate along waypoints
3. If not: extrapolate from current heading/speed
4. Apply turn rates and altitude changes
5. Increase uncertainty cone over time

### 3. Vessel Predictor (`mycosoft_mas/prediction/vessel_predictor.py`)

Predicts ship positions with longer horizons:

| Strategy | Use Case | Confidence | Horizon |
|----------|----------|------------|---------|
| Destination Routing | AIS destination | 90% → 60% | 48 hours |
| Course Extrapolation | No destination | 85% → 40% | 24 hours |

**Features:**
- Major port database for destination lookup
- Great circle route interpolation
- Speed estimation from vessel type

### 4. Satellite Predictor (`mycosoft_mas/prediction/satellite_predictor.py`)

Orbital mechanics-based prediction:

- Uses SGP4/SDP4 propagation from TLE data
- Very high accuracy (99%+) for days
- Calculates ground tracks and passes
- Falls back to simplified Keplerian model

**Libraries:**
- `sgp4` - Python SGP4 implementation
- `skyfield` (optional) - High-precision astronomy

### 5. Wildlife Predictor (`mycosoft_mas/prediction/wildlife_predictor.py`)

Behavior-based prediction with high uncertainty:

| Strategy | Use Case | Confidence |
|----------|----------|------------|
| Migration Model | Known migration season | 70% → 30% |
| Trajectory | Recent movement data | 60% → 20% |
| Random Walk | No data | 50% → 10% |

**Features:**
- Seasonal migration patterns database
- Species-specific movement speeds
- Behavioral noise modeling
- Habitat suitability integration (future)

### 6. Hazard Predictor (`mycosoft_mas/prediction/hazard_predictor.py`)

Environmental hazard evolution:

| Hazard Type | Model | Key Parameters |
|-------------|-------|----------------|
| Earthquake Aftershocks | Omori's Law | Magnitude, c, p |
| Wildfire Spread | Rothermel-like | Wind, fuel moisture |
| Storm Tracks | Climatology + extrapolation | Speed, heading, intensity |
| Tsunami | Wave propagation | Origin depth, magnitude |
| Volcanic Ash | Dispersion | Wind, plume height |

### 7. Earth-2 Forecaster (`mycosoft_mas/prediction/earth2_forecaster.py`)

Integration with NVIDIA Earth-2 AI weather models:

**Supported Models:**
- FourCastNet (FCN) - 25km resolution, 10-day forecasts
- Pangu-Weather - 25km resolution, 7-day forecasts
- GraphCast - 28km resolution, 10-day forecasts

**Forecast Types:**
- Point forecasts (temperature, precip, wind)
- Storm track predictions
- Wildfire spread projections
- Forecast map tiles

### 8. Prediction API (`mycosoft_mas/core/routers/prediction_api.py`)

REST API endpoints:

```
POST /prediction/predict         - Single entity prediction
POST /prediction/batch           - Batch predictions
GET  /prediction/aircraft/{id}   - Aircraft by ID
GET  /prediction/vessel/{id}     - Vessel by ID
GET  /prediction/satellite/{id}  - Satellite by NORAD ID
GET  /prediction/wildlife/{id}   - Wildlife entity
POST /prediction/weather         - Weather forecast
GET  /prediction/storms          - Storm predictions
POST /prediction/wildfire/spread - Wildfire spread
GET  /prediction/health          - Health check
```

## Frontend Components

### 1. Prediction Client (`WEBSITE/website/lib/prediction/prediction-client.ts`)

TypeScript client for the prediction API:

```typescript
const client = getPredictionClient()

// Single entity
const result = await client.predictAircraft("ABC123", 2, 60)

// Batch
const batch = await client.predictBatch([
  { entity_id: "ABC123", entity_type: "aircraft" },
  { entity_id: "XYZ789", entity_type: "vessel" },
])

// Weather
const weather = await client.getWeatherForecast(
  { lat: 37.7749, lng: -122.4194 },
  24, 1, "fcn"
)
```

### 2. React Hooks (`WEBSITE/website/hooks/usePrediction.ts`)

**usePrediction** - Single entity predictions:
```typescript
const { predictions, loading, error, refresh, getPositionAt } = usePrediction({
  entityId: "ABC123",
  entityType: "aircraft",
  hoursAhead: 2,
  autoRefresh: true,
})
```

**useWeatherForecast** - Weather forecasts:
```typescript
const { forecasts, loading, getForecastAt } = useWeatherForecast({
  location: { lat: 37.7, lng: -122.4 },
  hoursAhead: 24,
})
```

**useBatchPredictions** - Multiple entities:
```typescript
const { results, loading } = useBatchPredictions({
  entities: [
    { id: "ABC123", type: "aircraft" },
    { id: "SHIP42", type: "vessel" },
  ],
})
```

### 3. Prediction Layer (`WEBSITE/website/components/crep/layers/prediction-layer.tsx`)

SVG-based visualization component:

```tsx
<PredictionLayer
  predictions={predictions}
  entityType="aircraft"
  showTrail={true}
  showUncertainty={true}
  showMarkers={true}
  markerInterval={5}
  selectedTime={currentTime}
  mapProjection={mapRef.project}
  onMarkerClick={handleMarkerClick}
/>
```

**Features:**
- Animated dashed trail path
- Confidence gradient (opacity decreases with time)
- Uncertainty cone visualization
- Interactive markers with tooltips
- Time-based position selection

## Confidence & Uncertainty

### Confidence Decay Model

Exponential decay based on time since last known position:

```
C(t) = C₀ × (0.5)^(t / half_life)
```

| Entity Type | Initial C₀ | Half-Life | Min Confidence |
|-------------|------------|-----------|----------------|
| Aircraft | 0.95 | 10 min | 0.20 |
| Vessel | 0.90 | 60 min | 0.30 |
| Satellite | 0.99 | 24 hr | 0.80 |
| Wildlife | 0.70 | 60 min | 0.10 |

### Uncertainty Growth

Linear growth of lateral uncertainty:

```
U(t) = U₀ + rate × t
```

| Entity Type | Base U₀ | Growth Rate |
|-------------|---------|-------------|
| Aircraft | 50m | 0.5 m/s |
| Vessel | 200m | 0.2 m/s |
| Satellite | 10m | 0.001 m/s |
| Wildlife | 5000m | 2.0 m/s |

## Visual Differentiation

Predictions are visually distinct from historical data:

| Aspect | Historical | Predicted |
|--------|------------|-----------|
| Line Style | Solid | Dashed |
| Opacity | 100% | Gradient (100% → 30%) |
| Color | Standard | Same, with confidence overlay |
| Markers | Solid circles | Hollow circles |
| Uncertainty | None | Expanding cone |

## Data Flow

```
Timeline Request (future time)
        │
        ▼
┌───────────────────┐
│  Check MINDEX for │
│  existing forecast│
└────────┬──────────┘
         │
         ├─ Found → Return cached prediction
         │
         └─ Not found → Request new prediction
                │
                ▼
        ┌───────────────┐
        │ Get current   │
        │ entity state  │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │ Run predictor │
        │ algorithm     │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │ Apply         │
        │ confidence &  │
        │ uncertainty   │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │ Store in      │
        │ MINDEX        │
        └───────┬───────┘
                │
                ▼
        Return predictions
```

## Created Files

### Backend (MAS)

| File | Purpose |
|------|---------|
| `mycosoft_mas/prediction/__init__.py` | Module exports |
| `mycosoft_mas/prediction/prediction_types.py` | Type definitions |
| `mycosoft_mas/prediction/base_predictor.py` | Abstract base class |
| `mycosoft_mas/prediction/prediction_store.py` | MINDEX storage |
| `mycosoft_mas/prediction/aircraft_predictor.py` | Aircraft predictions |
| `mycosoft_mas/prediction/vessel_predictor.py` | Vessel predictions |
| `mycosoft_mas/prediction/satellite_predictor.py` | Satellite orbital predictions |
| `mycosoft_mas/prediction/wildlife_predictor.py` | Wildlife migration predictions |
| `mycosoft_mas/prediction/hazard_predictor.py` | Environmental hazard predictions |
| `mycosoft_mas/prediction/earth2_forecaster.py` | Earth-2 weather integration |
| `mycosoft_mas/core/routers/prediction_api.py` | REST API endpoints |

### Frontend (WEBSITE)

| File | Purpose |
|------|---------|
| `lib/prediction/prediction-client.ts` | API client |
| `lib/prediction/index.ts` | Module exports |
| `hooks/usePrediction.ts` | React hooks |
| `components/crep/layers/prediction-layer.tsx` | Map visualization |
| `components/crep/layers/index.ts` | Component exports |

## Configuration

### Environment Variables

```bash
# GPU Gateway for Earth-2
GPU_GATEWAY_URL=http://localhost:8100

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mycosoft

# Frontend
NEXT_PUBLIC_MAS_URL=http://192.168.0.188:8001
```

### Predictor Parameters

Each predictor can be customized:

```python
predictor = AircraftPredictor()
predictor.confidence_half_life_seconds = 600  # 10 minutes
predictor.max_prediction_horizon = timedelta(hours=4)
predictor.base_uncertainty_meters = 100
```

## Usage Examples

### Backend - Python

```python
from mycosoft_mas.prediction import (
    AircraftPredictor,
    EntityState,
    GeoPoint,
    Velocity,
    PredictionRequest,
)
from datetime import datetime, timedelta, timezone

# Create predictor
predictor = AircraftPredictor()

# Define current state
state = EntityState(
    entity_id="ABC123",
    entity_type=EntityType.AIRCRAFT,
    timestamp=datetime.now(timezone.utc),
    position=GeoPoint(lat=37.7749, lng=-122.4194, altitude=10000),
    velocity=Velocity(speed=450, heading=90, climb_rate=0),
)

# Request prediction
request = PredictionRequest(
    entity_id="ABC123",
    entity_type=EntityType.AIRCRAFT,
    from_time=datetime.now(timezone.utc),
    to_time=datetime.now(timezone.utc) + timedelta(hours=2),
    resolution_seconds=60,
)

# Get predictions
result = await predictor.predict(request)

for pred in result.predictions:
    print(f"{pred.timestamp}: {pred.position.lat}, {pred.position.lng} "
          f"(confidence: {pred.confidence:.1%})")
```

### Frontend - React

```tsx
import { usePrediction } from "@/hooks/usePrediction"
import { PredictionLayer } from "@/components/crep/layers"

function FlightTracker() {
  const { predictions, loading, error } = usePrediction({
    entityId: "ABC123",
    entityType: "aircraft",
    hoursAhead: 2,
  })

  if (loading) return <div>Loading predictions...</div>
  if (error) return <div>Error: {error}</div>

  return (
    <div className="relative">
      <Map>
        <PredictionLayer
          predictions={predictions}
          entityType="aircraft"
          showTrail
          showUncertainty
        />
      </Map>
    </div>
  )
}
```

## Performance Targets

| Metric | Target |
|--------|--------|
| Single prediction latency | < 50ms |
| Batch (10 entities) latency | < 200ms |
| Weather forecast latency | < 500ms |
| Satellite propagation (7 days) | < 100ms |
| Memory per prediction result | < 1KB |

## Future Enhancements

1. **Machine Learning Integration**
   - Train models on historical tracking data
   - Learn entity-specific behavior patterns
   - Improve confidence calibration

2. **Ensemble Predictions**
   - Combine multiple prediction methods
   - Weighted averaging based on historical accuracy

3. **Real-Time Updates**
   - WebSocket streaming of updated predictions
   - Automatic refresh when new data arrives

4. **Collaborative Filtering**
   - Use similar entity behavior for prediction
   - Fleet-level pattern recognition

5. **Terrain Integration**
   - Account for terrain in wildlife predictions
   - No-fly zones for aircraft

---

*Document created: February 6, 2026*
*Phase: 2 - Prediction Engine*
*Status: Complete*
