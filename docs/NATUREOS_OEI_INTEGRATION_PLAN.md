# NatureOS OEI / Earth Simulator Integration Plan

**Version**: 1.0.0  
**Date**: 2026-01-14  
**Author**: MYCA Integration System  
**Status**: PLANNING - Awaiting Approval  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Audit Results](#system-audit-results)
3. [Architecture Design](#architecture-design)
4. [Canonical Schemas](#canonical-schemas)
5. [Implementation Phases](#implementation-phases)
6. [Database Schema](#database-schema)
7. [Environment Variables](#environment-variables)
8. [File Manifest](#file-manifest)
9. [Priority Timeline](#priority-timeline)
10. [Open Questions](#open-questions)
11. [References](#references)

---

## Executive Summary

This document outlines the comprehensive integration plan for the **NatureOS OEI (Environmental Common Operating Picture)** / **Earth Simulator** system. The goal is to transform NatureOS into a unified spatiotemporal operating picture by integrating:

- **Public data sources**: Weather alerts, earthquakes, volcanoes, aircraft, ships, biodiversity
- **Device ingestion ecosystem**: MQTT, HTTP webhooks, LoRaWAN, Home Assistant bridges
- **Professional map stack**: MapLibre GL JS, deck.gl, CesiumJS
- **Canonical data model**: Entity, Observation, Event primitives with provenance tracking

### Key Principles

1. **Additive Implementation**: No breaking changes to existing working code
2. **Single Source of Truth**: All data normalizes to canonical schemas
3. **Connector Pattern**: Standardized interface for all data sources
4. **Provenance Tracking**: Every data point tracks source, method, confidence

---

## System Audit Results

### What Already Exists (DO NOT REBUILD)

Based on comprehensive codebase audit performed 2026-01-14.

#### Existing API Routes (WORKING)

| Component | Location | Status | Description |
|-----------|----------|--------|-------------|
| **iNaturalist Client** | `lib/inaturalist-client.ts` | ✅ COMPLETE | Fungal observations, bounds search, research-grade filtering |
| **Space Weather API** | `app/api/mas/space-weather/route.ts` | ✅ COMPLETE | NASA DONKI (CME, flares, storms), NOAA SWPC (solar wind, Kp index, aurora) |
| **Environmental API** | `app/api/mas/environmental/route.ts` | ✅ COMPLETE | OpenAQ air quality, EPA AirNow current/forecast |
| **Earth Science API** | `app/api/mas/earth-science/route.ts` | ✅ COMPLETE | USGS earthquakes, NOAA tides, NDBC buoys, USGS streamflow |
| **Grid Calculator** | `lib/earth-simulator/grid-calculator.ts` | ✅ COMPLETE | 1ft grid cells, Web Mercator projection, viewport calculations |
| **Earth Simulator Layers** | `app/api/earth-simulator/layers/route.ts` | ⚠️ PARTIAL | Layer aggregation scaffolded, needs more sources |
| **MycoBrain Integration** | `app/api/mycobrain/*` | ✅ COMPLETE | Device management, telemetry, MDP v1 protocol |

#### Existing Infrastructure (WORKING)

| Service | Port | Status | Notes |
|---------|------|--------|-------|
| **Website** | 3000 | ✅ ACTIVE | Primary website - all new features here |
| **MAS Dashboard** | 3001 | ⚠️ DEPRECATED | Do not add features here |
| **MINDEX API** | 8000 | ✅ ACTIVE | Fungal knowledge database |
| **MAS Orchestrator** | 8001 | ✅ ACTIVE | FastAPI agent orchestration |
| **MycoBrain Service** | 8003 | ✅ ACTIVE | Device management API |
| **PostgreSQL/PostGIS** | 5432 | ✅ ACTIVE | Primary database |
| **Redis** | 6379 | ✅ ACTIVE | Caching, messaging |
| **Qdrant** | 6333 | ✅ ACTIVE | Vector database |
| **n8n** | 5678 | ✅ ACTIVE | Workflow automation |
| **Prometheus** | 9090 | ✅ ACTIVE | Metrics |
| **Grafana** | 3002 | ✅ ACTIVE | Dashboards |

#### Existing UI Components (WORKING)

| Component | Location | Status |
|-----------|----------|--------|
| Layer Manager | `components/earth-simulator/layer-manager.tsx` | ⚠️ PARTIAL |
| Mycelium Layer | `components/earth-simulator/mycelium-layer.tsx` | ✅ WORKING |
| Heat Layer | `components/earth-simulator/heat-layer.tsx` | ✅ WORKING |
| Organism Layer | `components/earth-simulator/organism-layer.tsx` | ✅ WORKING |
| Weather Layer | `components/earth-simulator/weather-layer.tsx` | ✅ WORKING |
| Device Markers | `components/earth-simulator/device-markers.tsx` | ✅ WORKING |
| Controls | `components/earth-simulator/controls.tsx` | ✅ WORKING |

#### Existing Documentation (REFERENCE)

| Document | Location | Purpose |
|----------|----------|---------|
| Master Architecture | `docs/MASTER_ARCHITECTURE.md` | System overview, ports, repos |
| Agent Registry | `docs/AGENT_REGISTRY.md` | 215+ agents documented |
| Earth Simulator Vision | `docs/EARTH_SIMULATOR_VISION_TASKS.md` | Feature roadmap |
| System Integrations | `docs/SYSTEM_INTEGRATIONS.md` | Integration patterns |
| N8N Integration | `docs/N8N_INTEGRATION_GUIDE.md` | Workflow setup |
| ENV Integrations | `docs/ENV_INTEGRATIONS.md` | API keys reference |
| MycoBrain Integration | `docs/integrations/MYCOBRAIN_INTEGRATION.md` | Device protocol |

### What's Missing (NEEDS IMPLEMENTATION)

#### Connectors NOT Yet Built

| Connector | API Source | Priority | Output Type |
|-----------|------------|----------|-------------|
| **NWS Alerts** | api.weather.gov | 🔴 HIGH | Event |
| **USGS Volcanoes** | volcanoes.usgs.gov | 🔴 HIGH | Entity + Event |
| **OpenSky ADS-B** | opensky-network.org | 🟡 MEDIUM | Entity + Observation |
| **AIS Ships** | aisstream.io | 🟡 MEDIUM | Entity + Observation |
| **GBIF Occurrences** | gbif.org | 🔴 HIGH | Observation |
| **OBIS Marine** | obis.org | 🟡 MEDIUM | Observation |
| **eBird** | ebird.org | 🟡 MEDIUM | Observation |
| **Global Fishing Watch** | globalfishingwatch.org | 🟢 LOW | Entity + Event |
| **STAC Catalog** | stacspec.org | 🟡 MEDIUM | Observation |
| **NASA CMR** | earthdata.nasa.gov | 🟢 LOW | Observation |

#### Infrastructure NOT Yet Built

| Component | Priority | Current State |
|-----------|----------|---------------|
| **Canonical Entity/Observation/Event Schemas** | 🔴 HIGH | Not implemented |
| **Connector Hub Pattern** | 🔴 HIGH | No standardization |
| **Normalizer Service** | 🔴 HIGH | No normalization layer |
| **Event Bus (Redis Streams)** | 🟡 MEDIUM | Redis exists, streams not used |
| **TimescaleDB** | 🟡 MEDIUM | PostgreSQL only |
| **Device Onboarding Lanes** | 🟡 MEDIUM | MycoBrain only |

#### Map Stack NOT Yet Integrated

| Library | Priority | Purpose |
|---------|----------|---------|
| **MapLibre GL JS** | 🔴 HIGH | 2D vector tile rendering |
| **deck.gl** | 🔴 HIGH | GPU geospatial layers |
| **CesiumJS** | 🟡 MEDIUM | 3D globe visualization |
| **kepler.gl** | 🟢 LOW | Analytics UI (optional) |

---

## Architecture Design

### Current vs. Target Architecture

```
CURRENT STATE:
┌─────────────────────────────────────────────────────────────┐
│  Scattered API routes → Direct database writes              │
│  No canonical schemas → Inconsistent data models            │
│  No event bus → Synchronous processing only                 │
│  Basic map components → Limited visualization               │
└─────────────────────────────────────────────────────────────┘

TARGET STATE:
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                              │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐           │
│  │ NWS │ │USGS │ │iNat │ │GBIF │ │Ships│ │Plane│           │
│  └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘           │
│     └───────┴───────┴───────┴───────┴───────┘               │
│                         │                                    │
│              ┌──────────▼──────────┐                        │
│              │   CONNECTOR HUB     │                        │
│              │  Pull/Stream/Bridge │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│              ┌──────────▼──────────┐                        │
│              │    NORMALIZER       │                        │
│              │ Raw → Entity/Obs/Evt│                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│     ┌───────────────────┼───────────────────┐               │
│     ▼                   ▼                   ▼               │
│  ┌─────┐           ┌─────┐           ┌─────┐               │
│  │Redis│           │Redis│           │Redis│               │
│  │raw.*│           │entity│          │event│               │
│  └──┬──┘           └──┬──┘           └──┬──┘               │
│     └───────────────────┴───────────────┘                   │
│                         │                                    │
│     ┌───────────────────┼───────────────────┐               │
│     ▼                   ▼                   ▼               │
│ ┌───────┐         ┌─────────┐         ┌───────┐            │
│ │PostGIS│         │Timescale│         │PostGIS│            │
│ │Entity │         │  Obs    │         │ Event │            │
│ └───┬───┘         └────┬────┘         └───┬───┘            │
│     └───────────────────┴─────────────────┘                 │
│                         │                                    │
│              ┌──────────▼──────────┐                        │
│              │    QUERY API        │                        │
│              │ Spatial + Temporal  │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│     ┌───────────────────┼───────────────────┐               │
│     ▼                   ▼                   ▼               │
│ ┌───────┐         ┌─────────┐         ┌───────┐            │
│ │MapLibre│        │ deck.gl │         │Cesium │            │
│ │  2D   │         │ Layers  │         │  3D   │            │
│ └───────┘         └─────────┘         └───────┘            │
│                                                              │
│              ┌──────────────────────┐                       │
│              │  NATUREOS DASHBOARD  │                       │
│              │    (Port 3000)       │                       │
│              └──────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow Patterns

#### Pattern 1: Pull Connector (Scheduled API Calls)
```
Schedule Trigger (n8n/cron)
    → Connector.pull()
    → Raw payload to Redis raw.<source>
    → Normalizer consumes
    → Canonical objects to entity/obs/event topics
    → DB writers persist
```

#### Pattern 2: Stream Connector (WebSocket/SSE)
```
WebSocket connection established
    → Connector.stream()
    → Real-time messages to Redis raw.<source>
    → Normalizer processes immediately
    → Push to UI via SSE
```

#### Pattern 3: Bridge Connector (Device Ingestion)
```
Device publishes (MQTT/HTTP)
    → Gateway receives
    → Connector.bridge() validates
    → Normalized Observation
    → Write to DB + broadcast
```

---

## Canonical Schemas

All external data MUST normalize into these three primitives.

### Entity Schema

Represents "things with identity" - aircraft, ships, volcanoes, sensors, organisms.

```typescript
// lib/natureos-oei/schemas/entity.ts

export type EntityType = 
  | 'aircraft'      // OpenSky ADS-B
  | 'ship'          // AIS
  | 'drone'         // Future
  | 'sensor'        // MycoBrain, SporeBase
  | 'animal_group'  // Wildlife tracking
  | 'storm_cell'    // Weather systems
  | 'sat_asset'     // Satellites
  | 'volcano'       // USGS volcanoes
  | 'station'       // Weather/buoy stations
  | 'other';

export type Affiliation = 'civil' | 'unknown' | 'friendly' | 'hostile' | 'neutral';
export type EntityStatus = 'active' | 'inactive' | 'lost' | 'estimated';

export interface Entity {
  id: string;                           // Unique identifier
  type: EntityType;                     // Classification
  name: string;                         // Human-readable name
  affiliation: Affiliation;             // Trust classification
  geometry: GeoJSON.Point | GeoJSON.Polygon;
  alt_m?: number;                       // Altitude in meters
  vel_mps?: number;                     // Velocity in m/s
  heading_deg?: number;                 // Heading 0-360
  status: EntityStatus;                 // Current state
  last_seen: string;                    // ISO 8601 timestamp
  provenance: Provenance;               // Source tracking
  metadata?: Record<string, unknown>;   // Type-specific data
}
```

### Observation Schema

Represents "measurements at time+place" - telemetry, sightings, readings.

```typescript
// lib/natureos-oei/schemas/observation.ts

export type ObservationType = 
  | 'position'      // Location update
  | 'telemetry'     // Sensor readings
  | 'chemistry'     // Air/water quality
  | 'biology'       // Species observation
  | 'imagery_meta'  // Satellite image metadata
  | 'weather'       // Weather readings
  | 'other';

export interface Observation {
  id: string;                           // Unique identifier
  entity_id?: string;                   // Optional linked entity
  obs_type: ObservationType;            // Classification
  ts: string;                           // ISO 8601 timestamp
  geometry: GeoJSON.Point;              // Location
  fields: Record<string, number | string | boolean>;  // Measurements
  provenance: Provenance;               // Source tracking
}

// Example fields by obs_type:
// telemetry: { temp_c: 21.2, humidity_pct: 65, voc_ppm: 0.18 }
// biology: { species_name: "Agaricus bisporus", taxon_id: 12345, quality_grade: "research" }
// weather: { wind_speed_mps: 5.2, wind_dir_deg: 180, pressure_hpa: 1013 }
```

### Event Schema

Represents "something happened" - alerts, detections, anomalies.

```typescript
// lib/natureos-oei/schemas/event.ts

export type EventType = 
  | 'nws_alert'       // Weather alerts
  | 'earthquake'      // Seismic events
  | 'volcano'         // Volcanic activity
  | 'space_weather'   // Solar/geomagnetic
  | 'ais_anomaly'     // Ship behavior
  | 'species_sighting'// Notable observation
  | 'device_alert'    // Sensor threshold
  | 'custom';

export type EventSeverity = 'info' | 'watch' | 'warning' | 'critical';

export interface OEIEvent {
  id: string;                           // Unique identifier
  event_type: EventType;                // Classification
  ts_start: string;                     // Event start (ISO 8601)
  ts_end?: string;                      // Event end (optional)
  geometry: GeoJSON.Point | GeoJSON.Polygon;  // Affected area
  severity: EventSeverity;              // Impact level
  summary: string;                      // Human-readable description
  details: Record<string, unknown>;     // Type-specific data
  provenance: Provenance;               // Source tracking
}
```

### Provenance Schema

Tracks source, method, and confidence for every data point.

```typescript
// lib/natureos-oei/schemas/provenance.ts

export type IngestionMethod = 'api' | 'mqtt' | 'webhook' | 'radio' | 'manual' | 'etl';

export interface Provenance {
  source: string;                       // e.g., "opensky", "nws", "mycobrain-001"
  method: IngestionMethod;              // How data was received
  confidence: number;                   // 0.0 to 1.0
  ingested_at: string;                  // When we received it (ISO 8601)
  raw_ref?: string;                     // Reference to raw data (URL or ID)
  sensor_id?: string;                   // For device data
  update_latency_ms?: number;           // Time from source to ingest
}
```

---

## Implementation Phases

### Phase 0: Foundation (Week 1)

**Goal**: Create canonical schemas and connector infrastructure.

#### Tasks

| # | Task | File(s) | Estimate |
|---|------|---------|----------|
| 0.1 | Create schema directory structure | `lib/natureos-oei/` | 1h |
| 0.2 | Implement Entity schema + validators | `lib/natureos-oei/schemas/entity.ts` | 2h |
| 0.3 | Implement Observation schema + validators | `lib/natureos-oei/schemas/observation.ts` | 2h |
| 0.4 | Implement Event schema + validators | `lib/natureos-oei/schemas/event.ts` | 2h |
| 0.5 | Implement Provenance schema | `lib/natureos-oei/schemas/provenance.ts` | 1h |
| 0.6 | Create base connector interface | `lib/natureos-oei/connectors/base-connector.ts` | 3h |
| 0.7 | Implement Redis Streams event bus | `lib/natureos-oei/event-bus.ts` | 4h |
| 0.8 | Create database migrations | `migrations/001_oei_tables.sql` | 2h |
| 0.9 | Create OEI query service | `lib/natureos-oei/query-service.ts` | 4h |

#### Deliverables
- [ ] `lib/natureos-oei/schemas/` - All canonical schemas with Zod validation
- [ ] `lib/natureos-oei/connectors/base-connector.ts` - Connector interface
- [ ] `lib/natureos-oei/event-bus.ts` - Redis Streams wrapper
- [ ] `migrations/001_oei_tables.sql` - Database schema
- [ ] Tests for all schemas

---

### Phase 1: Hazards MVP (Week 2)

**Goal**: Implement high-value operational feeds first.

#### 1.1 NWS Alerts Connector

**API Documentation**: https://www.weather.gov/documentation/services-web-alerts

```typescript
// lib/natureos-oei/connectors/nws-alerts.ts

export class NWSAlertsConnector implements Connector {
  name = 'nws_alerts';
  mode: ConnectorMode = 'pull';
  
  async pull(): Promise<OEIEvent[]> {
    // Fetch from api.weather.gov/alerts/active
    // Parse CAP/ATOM format
    // Normalize to OEIEvent[]
  }
}
```

**API Route**: `app/api/earth-simulator/nws-alerts/route.ts`

| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| GET | `/api/earth-simulator/nws-alerts` | `?state=CA&severity=warning` | `OEIEvent[]` |
| GET | `/api/earth-simulator/nws-alerts/active` | `?bounds=north,south,east,west` | `OEIEvent[]` |

#### 1.2 USGS Volcanoes Connector

**API Documentation**: https://volcanoes.usgs.gov/vsc/api/

```typescript
// lib/natureos-oei/connectors/usgs-volcano.ts

export class USGSVolcanoConnector implements Connector {
  name = 'usgs_volcano';
  mode: ConnectorMode = 'pull';
  
  async pull(): Promise<{ entities: Entity[], events: OEIEvent[] }> {
    // Fetch volcano list, status, alerts
    // Create Entity for each volcano
    // Create OEIEvent for active alerts
  }
}
```

**API Route**: `app/api/earth-simulator/volcanoes/route.ts`

#### 1.3 Earthquake Normalizer

**Existing API**: `app/api/mas/earth-science/route.ts` (already fetches USGS data)

```typescript
// lib/natureos-oei/normalizers/earthquake-normalizer.ts

export function normalizeEarthquake(usgsFeature: USGSFeature): OEIEvent {
  return {
    id: `eq-${usgsFeature.id}`,
    event_type: 'earthquake',
    ts_start: new Date(usgsFeature.properties.time).toISOString(),
    geometry: usgsFeature.geometry,
    severity: magnitudeToSeverity(usgsFeature.properties.mag),
    summary: `M${usgsFeature.properties.mag} - ${usgsFeature.properties.place}`,
    details: { magnitude: usgsFeature.properties.mag, depth_km: usgsFeature.properties.depth },
    provenance: { source: 'usgs', method: 'api', confidence: 0.99, ingested_at: new Date().toISOString() }
  };
}
```

#### Tasks

| # | Task | File(s) | Estimate |
|---|------|---------|----------|
| 1.1 | Implement NWS Alerts connector | `lib/natureos-oei/connectors/nws-alerts.ts` | 4h |
| 1.2 | Create NWS Alerts API route | `app/api/earth-simulator/nws-alerts/route.ts` | 2h |
| 1.3 | Implement USGS Volcano connector | `lib/natureos-oei/connectors/usgs-volcano.ts` | 4h |
| 1.4 | Create Volcanoes API route | `app/api/earth-simulator/volcanoes/route.ts` | 2h |
| 1.5 | Create earthquake normalizer | `lib/natureos-oei/normalizers/earthquake-normalizer.ts` | 2h |
| 1.6 | Add hazards to layer aggregation | Update `app/api/earth-simulator/layers/route.ts` | 2h |
| 1.7 | Create Hazards UI component | `components/earth-simulator/hazards-layer.tsx` | 4h |

---

### Phase 2: Mobility Layer (Week 3)

**Goal**: Add aircraft and ship tracking.

#### 2.1 OpenSky ADS-B Connector

**API Documentation**: https://openskynetwork.github.io/opensky-api/

```typescript
// lib/natureos-oei/connectors/opensky-adsb.ts

export class OpenSkyConnector implements Connector {
  name = 'opensky';
  mode: ConnectorMode = 'pull'; // Can upgrade to stream with websocket
  
  async pull(bounds?: BoundingBox): Promise<{ entities: Entity[], observations: Observation[] }> {
    // Fetch /api/states/all with bounding box
    // Each aircraft becomes an Entity
    // Position history becomes Observations
  }
}
```

**API Route**: `app/api/earth-simulator/aircraft/route.ts`

| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| GET | `/api/earth-simulator/aircraft` | `?bounds=lamin,lomin,lamax,lomax` | `Entity[]` |
| GET | `/api/earth-simulator/aircraft/[icao24]` | - | `Entity + Observation[]` |

#### 2.2 AIS Ships Connector

**API Documentation**: https://aisstream.io/documentation

```typescript
// lib/natureos-oei/connectors/aisstream.ts

export class AISStreamConnector implements Connector {
  name = 'aisstream';
  mode: ConnectorMode = 'stream';
  
  async stream(onMessage: (data: Entity | Observation) => void): Promise<void> {
    // Connect to WebSocket wss://stream.aisstream.io/v0/stream
    // Subscribe to bounding box
    // Parse AIS messages → Entity + Observation
  }
}
```

**API Route**: `app/api/earth-simulator/ships/route.ts`

#### Tasks

| # | Task | File(s) | Estimate |
|---|------|---------|----------|
| 2.1 | Implement OpenSky connector | `lib/natureos-oei/connectors/opensky-adsb.ts` | 4h |
| 2.2 | Create Aircraft API route | `app/api/earth-simulator/aircraft/route.ts` | 2h |
| 2.3 | Implement AISstream connector | `lib/natureos-oei/connectors/aisstream.ts` | 6h |
| 2.4 | Create Ships API route | `app/api/earth-simulator/ships/route.ts` | 2h |
| 2.5 | Create Aircraft layer component | `components/earth-simulator/aircraft-layer.tsx` | 4h |
| 2.6 | Create Ships layer component | `components/earth-simulator/ships-layer.tsx` | 4h |
| 2.7 | Add track history visualization | `components/earth-simulator/track-layer.tsx` | 4h |

---

### Phase 3: Biodiversity Layer (Week 4)

**Goal**: Expand biological observation sources.

#### 3.1 GBIF Connector

**API Documentation**: https://techdocs.gbif.org/en/openapi/v1/occurrence

```typescript
// lib/natureos-oei/connectors/gbif.ts

export class GBIFConnector implements Connector {
  name = 'gbif';
  mode: ConnectorMode = 'pull';
  
  async pull(params: GBIFParams): Promise<Observation[]> {
    // Fetch occurrences with geometry filter
    // Normalize to Observation[]
  }
}
```

#### 3.2 OBIS Marine Connector

**API Documentation**: https://obis.org/manual/api/

```typescript
// lib/natureos-oei/connectors/obis.ts

export class OBISConnector implements Connector {
  name = 'obis';
  mode: ConnectorMode = 'pull';
  
  async pull(params: OBISParams): Promise<Observation[]> {
    // Fetch marine occurrences
    // Normalize to Observation[]
  }
}
```

#### 3.3 eBird Connector

**API Documentation**: https://documenter.getpostman.com/view/664302/S1ENwy59

```typescript
// lib/natureos-oei/connectors/ebird.ts

export class EBirdConnector implements Connector {
  name = 'ebird';
  mode: ConnectorMode = 'pull';
  
  async pull(params: EBirdParams): Promise<Observation[]> {
    // Fetch recent observations
    // Get hotspots
    // Normalize to Observation[]
  }
}
```

#### 3.4 iNaturalist Normalizer

Upgrade existing `lib/inaturalist-client.ts` output to canonical schema.

```typescript
// lib/natureos-oei/normalizers/inaturalist-normalizer.ts

export function normalizeINatObservation(inat: iNaturalistObservation): Observation {
  return {
    id: `inat-${inat.id}`,
    obs_type: 'biology',
    ts: inat.observed_on,
    geometry: { type: 'Point', coordinates: [inat.longitude, inat.latitude] },
    fields: {
      species_name: inat.taxon?.name,
      taxon_id: inat.taxon_id,
      quality_grade: inat.quality_grade,
      user: inat.user?.login
    },
    provenance: { source: 'inaturalist', method: 'api', confidence: qualityToConfidence(inat.quality_grade), ingested_at: new Date().toISOString() }
  };
}
```

#### Tasks

| # | Task | File(s) | Estimate |
|---|------|---------|----------|
| 3.1 | Implement GBIF connector | `lib/natureos-oei/connectors/gbif.ts` | 4h |
| 3.2 | Create GBIF API route | `app/api/earth-simulator/gbif/route.ts` | 2h |
| 3.3 | Implement OBIS connector | `lib/natureos-oei/connectors/obis.ts` | 4h |
| 3.4 | Create OBIS API route | `app/api/earth-simulator/obis/route.ts` | 2h |
| 3.5 | Implement eBird connector | `lib/natureos-oei/connectors/ebird.ts` | 4h |
| 3.6 | Create eBird API route | `app/api/earth-simulator/ebird/route.ts` | 2h |
| 3.7 | Create iNaturalist normalizer | `lib/natureos-oei/normalizers/inaturalist-normalizer.ts` | 2h |
| 3.8 | Create unified biodiversity layer | `components/earth-simulator/biodiversity-layer.tsx` | 6h |

---

### Phase 4: Map Stack Upgrade (Week 5)

**Goal**: Professional geospatial visualization.

#### 4.1 Dependencies

```bash
npm install maplibre-gl @deck.gl/core @deck.gl/layers @deck.gl/geo-layers cesium resium
npm install @types/maplibre-gl --save-dev
```

#### 4.2 MapLibre Base Map

```typescript
// components/earth-simulator/maps/maplibre-map.tsx

export function MapLibreMap({ center, zoom, layers, onViewportChange }: MapLibreMapProps) {
  // Initialize MapLibre GL JS
  // Handle viewport state
  // Render deck.gl layers on top
}
```

#### 4.3 deck.gl Layers

```typescript
// components/earth-simulator/maps/deckgl-layers.tsx

export function DeckGLLayers({ entities, observations, events }: DeckGLLayersProps) {
  return (
    <>
      <IconLayer data={entities} ... />
      <ScatterplotLayer data={observations} ... />
      <GeoJsonLayer data={events} ... />
      <HeatmapLayer data={observationDensity} ... />
      <TripsLayer data={tracks} ... />
    </>
  );
}
```

#### 4.4 CesiumJS 3D Globe

```typescript
// components/earth-simulator/maps/cesium-globe.tsx

export function CesiumGlobe({ entities, observations, events, time }: CesiumGlobeProps) {
  // Initialize Cesium Viewer
  // Add Entity billboards
  // Add polyline tracks
  // Time slider integration
}
```

#### Tasks

| # | Task | File(s) | Estimate |
|---|------|---------|----------|
| 4.1 | Install map dependencies | `package.json` | 1h |
| 4.2 | Create MapLibre base component | `components/earth-simulator/maps/maplibre-map.tsx` | 6h |
| 4.3 | Create deck.gl layer components | `components/earth-simulator/maps/deckgl-layers.tsx` | 8h |
| 4.4 | Create entity icon layer | `components/earth-simulator/maps/entity-layer.tsx` | 4h |
| 4.5 | Create event polygon layer | `components/earth-simulator/maps/event-layer.tsx` | 4h |
| 4.6 | Create heatmap layer | `components/earth-simulator/maps/heatmap-layer.tsx` | 4h |
| 4.7 | Create CesiumJS globe | `components/earth-simulator/maps/cesium-globe.tsx` | 8h |
| 4.8 | Create 2D/3D toggle | `components/earth-simulator/view-toggle.tsx` | 2h |

---

### Phase 5: Device Onboarding (Week 6)

**Goal**: Make NatureOS the best sink for hobbyist devices.

#### 5.1 MQTT Ingestion Lane

```typescript
// lib/natureos-oei/ingestion/mqtt-lane.ts

export class MQTTLane {
  // Topic schema: natureos/<org>/<device_id>/<obs_type>
  // e.g., natureos/mycosoft/mycobrain-001/telemetry
  
  async handleMessage(topic: string, payload: Buffer): Promise<Observation> {
    // Parse topic for metadata
    // Validate payload against schema
    // Create Observation with provenance
  }
}
```

#### 5.2 HTTP Webhook Lane

```typescript
// app/api/devices/ingest/route.ts

export async function POST(request: NextRequest) {
  // Validate API key header
  // Parse body as Observation or raw telemetry
  // Normalize and store
}
```

#### 5.3 Home Assistant Bridge

```typescript
// lib/natureos-oei/bridges/home-assistant.ts

export class HomeAssistantBridge {
  // Map HA MQTT discovery topics to NatureOS schema
  // homeassistant/sensor/<device>/state → natureos/<org>/<device>/telemetry
}
```

#### Tasks

| # | Task | File(s) | Estimate |
|---|------|---------|----------|
| 5.1 | Implement MQTT lane | `lib/natureos-oei/ingestion/mqtt-lane.ts` | 6h |
| 5.2 | Create HTTP ingest route | `app/api/devices/ingest/route.ts` | 3h |
| 5.3 | Implement Home Assistant bridge | `lib/natureos-oei/bridges/home-assistant.ts` | 4h |
| 5.4 | Create device registration flow | `app/api/devices/register/route.ts` | 3h |
| 5.5 | Add MQTT to docker-compose | Docker config | 2h |
| 5.6 | Create Node-RED flow templates | `n8n/templates/device-ingest.json` | 4h |

---

### Phase 6: UI Dashboard Integration (Week 7)

**Goal**: Wire everything into the NatureOS dashboard.

#### 6.1 Event Inbox Component

```typescript
// components/natureos/event-inbox.tsx

export function EventInbox({ events, onEventClick, filters }: EventInboxProps) {
  // Real-time event feed
  // Filter by type/severity
  // Click to zoom on map
}
```

#### 6.2 Entity Inspector

```typescript
// components/natureos/entity-inspector.tsx

export function EntityInspector({ entity, observations }: EntityInspectorProps) {
  // Entity details panel
  // Track history
  // Provenance chain
  // Related events
}
```

#### 6.3 Time Slider

```typescript
// components/earth-simulator/time-slider.tsx

export function TimeSlider({ range, value, onChange, playback }: TimeSliderProps) {
  // Scrub through time
  // Playback controls
  // Speed adjustment
}
```

#### 6.4 Layer Controls Upgrade

Update existing `components/earth-simulator/layer-controls.tsx`:

```typescript
// Add new layer toggles:
// - Hazards (NWS Alerts, Earthquakes, Volcanoes)
// - Mobility (Aircraft, Ships)
// - Biodiversity (iNat, GBIF, OBIS, eBird)
// - Devices (MycoBrain, external sensors)
// - Space Weather (aurora, solar wind)
```

#### Tasks

| # | Task | File(s) | Estimate |
|---|------|---------|----------|
| 6.1 | Create Event Inbox component | `components/natureos/event-inbox.tsx` | 6h |
| 6.2 | Create Entity Inspector | `components/natureos/entity-inspector.tsx` | 6h |
| 6.3 | Create Time Slider | `components/earth-simulator/time-slider.tsx` | 4h |
| 6.4 | Upgrade Layer Controls | `components/earth-simulator/layer-controls.tsx` | 4h |
| 6.5 | Create unified Earth Simulator page | `app/apps/earth-simulator/page.tsx` | 6h |
| 6.6 | Add SSE for real-time updates | `app/api/earth-simulator/stream/route.ts` | 4h |

---

## Database Schema

### Migration: 001_oei_tables.sql

```sql
-- migrations/001_oei_tables.sql
-- NatureOS OEI Database Schema
-- Run after ensuring PostGIS extension is enabled

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- =============================================================================
-- ENTITIES TABLE
-- Represents "things with identity": aircraft, ships, sensors, volcanoes, etc.
-- =============================================================================

CREATE TABLE IF NOT EXISTS oei_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255),                    -- Source system ID (e.g., ICAO24, MMSI)
    entity_type VARCHAR(50) NOT NULL,            -- aircraft, ship, sensor, volcano, etc.
    name VARCHAR(255),                           -- Human-readable name
    affiliation VARCHAR(20) DEFAULT 'unknown',   -- civil, unknown, friendly, hostile, neutral
    geometry GEOMETRY(GEOMETRY, 4326) NOT NULL,  -- Current position (Point or Polygon)
    altitude_m FLOAT,                            -- Altitude in meters
    velocity_mps FLOAT,                          -- Speed in m/s
    heading_deg FLOAT,                           -- Heading 0-360
    status VARCHAR(20) DEFAULT 'active',         -- active, inactive, lost, estimated
    last_seen TIMESTAMPTZ NOT NULL,              -- Last observation timestamp
    provenance JSONB NOT NULL,                   -- Source tracking
    metadata JSONB,                              -- Type-specific data
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for entities
CREATE INDEX IF NOT EXISTS idx_entities_geometry ON oei_entities USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_entities_type ON oei_entities (entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_status ON oei_entities (status);
CREATE INDEX IF NOT EXISTS idx_entities_last_seen ON oei_entities (last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_entities_external_id ON oei_entities (external_id);

-- =============================================================================
-- OBSERVATIONS TABLE
-- Represents "measurements at time+place": telemetry, sightings, readings
-- =============================================================================

CREATE TABLE IF NOT EXISTS oei_observations (
    id UUID DEFAULT uuid_generate_v4(),
    entity_id UUID REFERENCES oei_entities(id) ON DELETE SET NULL,
    obs_type VARCHAR(50) NOT NULL,               -- position, telemetry, chemistry, biology, etc.
    ts TIMESTAMPTZ NOT NULL,                     -- Observation timestamp
    geometry GEOMETRY(POINT, 4326) NOT NULL,     -- Location
    fields JSONB NOT NULL,                       -- Measurement data
    provenance JSONB NOT NULL,                   -- Source tracking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, ts)
);

-- Indexes for observations
CREATE INDEX IF NOT EXISTS idx_observations_entity ON oei_observations (entity_id);
CREATE INDEX IF NOT EXISTS idx_observations_type ON oei_observations (obs_type);
CREATE INDEX IF NOT EXISTS idx_observations_geometry ON oei_observations USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_observations_ts ON oei_observations (ts DESC);

-- If TimescaleDB is available, convert to hypertable:
-- SELECT create_hypertable('oei_observations', 'ts', if_not_exists => TRUE);

-- =============================================================================
-- EVENTS TABLE
-- Represents "something happened": alerts, detections, anomalies
-- =============================================================================

CREATE TABLE IF NOT EXISTS oei_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255),                    -- Source system ID (e.g., NWS alert ID)
    event_type VARCHAR(50) NOT NULL,             -- nws_alert, earthquake, volcano, etc.
    ts_start TIMESTAMPTZ NOT NULL,               -- Event start time
    ts_end TIMESTAMPTZ,                          -- Event end time (optional)
    geometry GEOMETRY(GEOMETRY, 4326) NOT NULL,  -- Affected area
    severity VARCHAR(20) NOT NULL,               -- info, watch, warning, critical
    summary TEXT NOT NULL,                       -- Human-readable description
    details JSONB,                               -- Type-specific data
    provenance JSONB NOT NULL,                   -- Source tracking
    is_active BOOLEAN DEFAULT TRUE,              -- Whether event is ongoing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for events
CREATE INDEX IF NOT EXISTS idx_events_geometry ON oei_events USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_events_type ON oei_events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_severity ON oei_events (severity);
CREATE INDEX IF NOT EXISTS idx_events_ts ON oei_events (ts_start DESC);
CREATE INDEX IF NOT EXISTS idx_events_active ON oei_events (is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_events_external_id ON oei_events (external_id);

-- =============================================================================
-- DEVICE REGISTRY TABLE
-- Extends existing MycoBrain device management
-- =============================================================================

CREATE TABLE IF NOT EXISTS oei_devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL UNIQUE,      -- Unique device identifier
    device_type VARCHAR(50) NOT NULL,            -- mycobrain, sporebase, home_assistant, etc.
    name VARCHAR(255),                           -- Human-readable name
    owner_org VARCHAR(100),                      -- Organization ID
    geometry GEOMETRY(POINT, 4326),              -- Fixed location (if applicable)
    is_mobile BOOLEAN DEFAULT FALSE,             -- Whether device moves
    capabilities JSONB,                          -- What observations it can produce
    status VARCHAR(20) DEFAULT 'offline',        -- online, offline, error
    last_seen TIMESTAMPTZ,                       -- Last communication
    api_key_hash VARCHAR(64),                    -- Hashed API key for authentication
    metadata JSONB,                              -- Additional device info
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_devices_device_id ON oei_devices (device_id);
CREATE INDEX IF NOT EXISTS idx_devices_type ON oei_devices (device_type);
CREATE INDEX IF NOT EXISTS idx_devices_status ON oei_devices (status);
CREATE INDEX IF NOT EXISTS idx_devices_org ON oei_devices (owner_org);

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_entities_updated_at BEFORE UPDATE ON oei_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON oei_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_devices_updated_at BEFORE UPDATE ON oei_devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## Environment Variables

Add to `.env.local` (and update `docs/ENV_INTEGRATIONS.md`):

```env
# =============================================================================
# NatureOS OEI - New Environment Variables
# =============================================================================

# NWS Alerts (No API key required - free public API)
# Recommended: Set User-Agent for identification
NWS_USER_AGENT=mycosoft-natureos-1.0

# OpenSky Network (free tier: 400 credits/day, authenticated: 4000/day)
# Get credentials: https://opensky-network.org/index.php?option=com_users&view=registration
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password

# AISstream.io (free tier available)
# Get API key: https://aisstream.io/
AISSTREAM_API_KEY=your_aisstream_api_key

# GBIF (no key required for occurrence search)
# Optional: Username for higher rate limits
GBIF_USERNAME=your_username

# eBird (free API key required)
# Get key: https://ebird.org/api/keygen
EBIRD_API_KEY=your_ebird_api_key

# OBIS (no key required - free public API)
# No configuration needed

# Global Fishing Watch (requires registration)
# Get token: https://globalfishingwatch.org/our-apis/
GFW_API_TOKEN=your_gfw_token

# Home Assistant Bridge (optional)
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=your_long_lived_access_token

# MQTT Broker (for device ingestion)
# Use existing or add new broker
MQTT_BROKER_URL=mqtt://localhost:1883
MQTT_USERNAME=optional_username
MQTT_PASSWORD=optional_password

# Redis Streams (use existing Redis)
# Already configured: REDIS_URL in existing env

# TimescaleDB (optional - use existing PostgreSQL if not available)
# TIMESCALE_ENABLED=true
```

---

## File Manifest

Complete list of files to create/modify.

### New Files to Create

```
lib/natureos-oei/
├── schemas/
│   ├── entity.ts
│   ├── observation.ts
│   ├── event.ts
│   ├── provenance.ts
│   └── index.ts
├── connectors/
│   ├── base-connector.ts
│   ├── nws-alerts.ts
│   ├── usgs-volcano.ts
│   ├── opensky-adsb.ts
│   ├── aisstream.ts
│   ├── gbif.ts
│   ├── obis.ts
│   ├── ebird.ts
│   └── index.ts
├── normalizers/
│   ├── earthquake-normalizer.ts
│   ├── inaturalist-normalizer.ts
│   └── index.ts
├── ingestion/
│   ├── mqtt-lane.ts
│   ├── http-lane.ts
│   └── index.ts
├── bridges/
│   ├── home-assistant.ts
│   └── index.ts
├── event-bus.ts
├── query-service.ts
└── index.ts

app/api/earth-simulator/
├── nws-alerts/
│   └── route.ts
├── volcanoes/
│   └── route.ts
├── aircraft/
│   └── route.ts
├── ships/
│   └── route.ts
├── gbif/
│   └── route.ts
├── obis/
│   └── route.ts
├── ebird/
│   └── route.ts
└── stream/
    └── route.ts

app/api/devices/
├── ingest/
│   └── route.ts
└── register/
    └── route.ts

components/earth-simulator/
├── maps/
│   ├── maplibre-map.tsx
│   ├── deckgl-layers.tsx
│   ├── cesium-globe.tsx
│   ├── entity-layer.tsx
│   ├── event-layer.tsx
│   └── heatmap-layer.tsx
├── hazards-layer.tsx
├── aircraft-layer.tsx
├── ships-layer.tsx
├── biodiversity-layer.tsx
├── track-layer.tsx
├── time-slider.tsx
└── view-toggle.tsx

components/natureos/
├── event-inbox.tsx
└── entity-inspector.tsx

migrations/
└── 001_oei_tables.sql
```

### Files to Modify

| File | Modification |
|------|--------------|
| `app/api/earth-simulator/layers/route.ts` | Add new layer sources |
| `components/earth-simulator/layer-controls.tsx` | Add new layer toggles |
| `components/earth-simulator/layer-manager.tsx` | Include new layers |
| `app/apps/earth-simulator/page.tsx` | Integrate new components |
| `docs/ENV_INTEGRATIONS.md` | Add new API key documentation |
| `package.json` | Add map dependencies |

---

## Priority Timeline

### Week 1: Foundation
- [x] System audit (COMPLETE)
- [ ] Create canonical schemas
- [ ] Create connector interface
- [ ] Set up Redis Streams
- [ ] Database migrations

### Week 2: Hazards MVP
- [ ] NWS Alerts connector
- [ ] USGS Volcanoes connector
- [ ] Earthquake normalizer
- [ ] Hazards UI layer

### Week 3: Mobility Layer
- [ ] OpenSky ADS-B connector
- [ ] AISstream connector
- [ ] Aircraft/Ships UI layers

### Week 4: Biodiversity Layer
- [ ] GBIF connector
- [ ] OBIS connector
- [ ] eBird connector
- [ ] iNaturalist normalizer

### Week 5: Map Stack
- [ ] MapLibre integration
- [ ] deck.gl layers
- [ ] CesiumJS 3D globe

### Week 6: Device Onboarding
- [ ] MQTT ingestion lane
- [ ] HTTP webhook lane
- [ ] Home Assistant bridge

### Week 7: UI Integration
- [ ] Event Inbox
- [ ] Entity Inspector
- [ ] Time Slider
- [ ] Full dashboard integration

---

## Open Questions - RESOLVED

All questions have been answered (2026-01-16):

### 1. Website Codebase Location ✅ ANSWERED

**Decision**: The website is ALWAYS at `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`

This means:
- **UI Components** (Earth Simulator, maps, dashboards) → WEBSITE repo
- **Backend APIs** (connectors, normalizers, event bus) → mycosoft-mas repo
- **Shared Types** → Published as package or copied

### 2. TimescaleDB Setup ✅ ANSWERED

**Decision**: Use existing PostgreSQL, add TimescaleDB later as needed

- Start with standard PostgreSQL time-indexed tables
- Add TimescaleDB extension when data volume requires it
- No additional containers needed initially

### 3. Map Library Priority ✅ ANSWERED

**Decision**: Use existing map implementation, add new capabilities incrementally

- Keep current map components working
- Add MapLibre/deck.gl/CesiumJS progressively
- Don't break existing functionality

### 4. Event Bus Implementation ✅ ANSWERED

**Decision**: Use existing Redis, document everything thoroughly

- Redis Streams for event bus (already have Redis)
- Document all topic schemas and patterns
- Upgrade to Redpanda/Kafka only if Redis becomes bottleneck

---

## References

### API Documentation

| API | Documentation URL |
|-----|-------------------|
| NWS Alerts | https://www.weather.gov/documentation/services-web-alerts |
| USGS Earthquakes | https://earthquake.usgs.gov/fdsnws/event/1/ |
| USGS Volcanoes | https://volcanoes.usgs.gov/vsc/api/ |
| OpenSky Network | https://openskynetwork.github.io/opensky-api/ |
| AISstream | https://aisstream.io/documentation |
| iNaturalist | https://www.inaturalist.org/pages/api+reference |
| GBIF | https://techdocs.gbif.org/en/openapi/v1/occurrence |
| OBIS | https://obis.org/manual/api/ |
| eBird | https://documenter.getpostman.com/view/664302/S1ENwy59 |
| NASA DONKI | https://ccmc.gsfc.nasa.gov/tools/DONKI/ |
| NOAA SWPC | https://www.swpc.noaa.gov/products-and-data |
| Global Fishing Watch | https://globalfishingwatch.org/our-apis/documentation |

### Map Libraries

| Library | Documentation URL |
|---------|-------------------|
| MapLibre GL JS | https://maplibre.org/maplibre-gl-js/docs/ |
| deck.gl | https://deck.gl/docs |
| CesiumJS | https://cesium.com/learn/cesiumjs-learn/ |
| kepler.gl | https://docs.kepler.gl/ |

### Related Documents

| Document | Location |
|----------|----------|
| Master Architecture | `docs/MASTER_ARCHITECTURE.md` |
| Earth Simulator Vision | `docs/EARTH_SIMULATOR_VISION_TASKS.md` |
| System Integrations | `docs/SYSTEM_INTEGRATIONS.md` |
| ENV Integrations | `docs/ENV_INTEGRATIONS.md` |
| N8N Integration | `docs/N8N_INTEGRATION_GUIDE.md` |
| MycoBrain Integration | `docs/integrations/MYCOBRAIN_INTEGRATION.md` |

---

## Codebase Split Clarification

Based on the decision that the website is at `WEBSITE/website`, here is where each component should be implemented:

### WEBSITE Repo (`C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website`)

**UI Components**:
- `components/earth-simulator/maps/` - MapLibre, deck.gl, CesiumJS
- `components/earth-simulator/*-layer.tsx` - All layer components
- `components/natureos/event-inbox.tsx` - Event feed panel
- `components/natureos/entity-inspector.tsx` - Entity detail modal
- `app/apps/earth-simulator/page.tsx` - Earth Simulator page
- `app/natureos/*` - NatureOS dashboard pages

**API Routes** (proxies to MAS or direct external calls):
- `app/api/earth-simulator/*` - Earth simulator endpoints
- `app/api/natureos/*` - NatureOS endpoints

### MAS Repo (`C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas`)

**Backend Services**:
- `lib/natureos-oei/schemas/` - Canonical schemas (shared types)
- `lib/natureos-oei/connectors/` - All data source connectors
- `lib/natureos-oei/normalizers/` - Data normalization
- `lib/natureos-oei/event-bus.ts` - Redis Streams
- `lib/natureos-oei/query-service.ts` - Database queries

**Backend API Routes** (FastAPI or Next.js API):
- Device ingestion endpoints
- Connector orchestration
- Database writes

**Database**:
- `migrations/001_oei_tables.sql` - OEI database schema

**Documentation**:
- This planning document
- Integration guides
- API documentation

### Shared Between Repos

The canonical schemas (Entity, Observation, Event, Provenance) should be:
1. Defined in `mycosoft-mas/lib/natureos-oei/schemas/`
2. Copied or published to WEBSITE repo as needed
3. Keep in sync via documentation

---

## Approval

- [x] Architecture approved
- [x] Schema design approved
- [x] Phase order approved
- [x] Open questions answered
- [x] Ready for implementation

**Approved by**: User (2026-01-16)
**Implementation may begin**: Phase 0 - Foundation

---

*Document generated by MYCA Integration System - 2026-01-14*
*Updated with decisions - 2026-01-16*