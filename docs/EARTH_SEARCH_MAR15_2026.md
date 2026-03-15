# Earth Search — Planetary-Scale Unified Search

**Created:** March 15, 2026
**Module:** `mycosoft_mas/earth_search/`
**API Prefix:** `/api/earth-search`
**Agent:** `EarthSearchAgent`

## Overview

Expands the original fungi-only MINDEX search into a comprehensive planetary-scale search system covering every searchable domain on Earth. All data is dual-pipelined: accessible via API for agents and rendered on CREP for map visualization.

## Architecture

```
User/Agent Query
    ↓
[Earth Search API: POST /api/earth-search/query]
    ↓
[Earth Search Orchestrator]
    ├─→ [MINDEX Local] (192.168.0.189:8000/earth) ← LOWEST LATENCY, pre-ingested
    │     └── 35 domains, 9 ETL connectors, all local Postgres
    │
    ├─→ [External Connectors] (parallel fan-out)
    │   ├── SpeciesConnector (iNaturalist, GBIF, CoL, EOL, ITIS, WoRMS, BOLD)
    │   ├── EnvironmentConnector (USGS, NASA EONET, NASA FIRMS)
    │   ├── ClimateConnector (OpenWeatherMap, AirNow, NASA CMR, NOAA)
    │   ├── TransportConnector (CREP ADS-B/AIS, Launch Library 2, Overpass)
    │   ├── SpaceConnector (CREP Satellites, NOAA SWPC, NASA DONKI)
    │   ├── InfrastructureConnector (OSM Overpass, EPA FRS)
    │   ├── TelecomConnector (OSM, TeleGeography submarine cables)
    │   ├── SensorConnector (MycoBrain IoT, USGS seismic)
    │   └── ScienceConnector (PubChem, GenBank, PubMed)
    │
    ├─→ [Merge & Deduplicate]
    ├─→ [CREP Command Generation] → map visualization
    ├─→ [LLM Synthesis] (optional)
    └─→ [Ingestion Pipeline] (fire-and-forget)
          ├── MINDEX Postgres (low-latency re-query)
          ├── Supabase (cloud persistence + web dashboard)
          └── NLM Training Sink (JSONL for model training)
```

## 67 Searchable Domains

### Life (12 domains)
all_species, fungi, plants, birds, mammals, reptiles, amphibians, insects, marine_life, fish, microorganisms, invertebrates

### Environmental Events (8 domains)
earthquakes, volcanoes, wildfires, storms, lightning, tornadoes, floods, tsunamis

### Climate/Atmosphere (9 domains)
weather, co2, methane, air_quality, ground_quality, ocean_temperature, modis, landsat, airs

### Transportation (6 domains)
flights, vessels, airports, shipping_ports, spaceports, railways

### Industrial Infrastructure (8 domains)
factories, power_plants, mining, oil_gas, dams, water_treatment, rivers, pollution_sources

### Space (7 domains)
satellites, space_weather, solar_flares, space_debris, launches, nasa_feeds, noaa_feeds

### Telecommunications (5 domains)
cell_towers, am_fm_antennas, wifi_hotspots, internet_cables, signal_maps

### Sensors (4 domains)
ocean_buoys, weather_stations, seismic_stations, mycobrain_devices

### Science/Knowledge (6 domains)
compounds, genetics, research, llm_synthesis, mathematics, physics

### Other (2 domains)
military_bases, webcams

## 40 Data Sources

| Source | Domains | Realtime | Key Required |
|--------|---------|----------|-------------|
| MINDEX Local | All 67 | - | No |
| iNaturalist | 11 species domains | - | No |
| GBIF | 12 species domains | - | No |
| Catalogue of Life | all_species | - | No |
| EOL | all_species | - | No |
| ITIS | all_species | - | No |
| WoRMS | marine_life, fish | - | No |
| BOLD Systems | genetics, all_species | - | No |
| MycoBank | fungi | - | No |
| FungiDB | fungi, genetics | - | No |
| GenBank/NCBI | genetics | - | No |
| PubChem | compounds | - | No |
| PubMed | research | - | No |
| USGS Earthquakes | earthquakes | Yes | No |
| Smithsonian GVP | volcanoes | - | No |
| NASA FIRMS | wildfires | Yes | Yes |
| NOAA Storms | storms, tornadoes, floods | Yes | No |
| NOAA NHC | storms | Yes | No |
| OpenWeatherMap | weather, air_quality | Yes | Yes |
| AirNow | air_quality | Yes | Yes |
| NOAA GML | co2, methane | - | No |
| NASA Earthdata | modis, landsat, airs | - | Yes |
| NOAA NDBC | ocean_buoys, weather_stations | Yes | No |
| CREP ADS-B | flights | Yes | No |
| CREP AIS | vessels, shipping_ports | Yes | No |
| CREP Satellites | satellites | Yes | No |
| OurAirports | airports | - | No |
| World Port Index | shipping_ports | - | No |
| NOAA SWPC | space_weather, solar_flares | Yes | No |
| NASA DONKI | space_weather, solar_flares | Yes | Yes |
| Launch Library 2 | launches, spaceports | - | No |
| OSM Overpass | 12 infra domains | - | No |
| EPA FRS | pollution_sources, factories | - | No |
| Global Energy Monitor | power_plants, oil_gas, mining | - | No |
| OpenCelliD | cell_towers, signal_maps | - | Yes |
| WiGLE | wifi_hotspots, cell_towers | - | Yes |
| TeleGeography | internet_cables | - | No |
| Windy Webcams | webcams | - | Yes |
| MycoBrain | mycobrain_devices | Yes | No |
| NVIDIA Earth2 | weather | - | Yes |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/earth-search/query` | Main search endpoint — returns results + CREP commands |
| GET | `/api/earth-search/domains` | List all 67 domains with source counts |
| GET | `/api/earth-search/sources` | List all 40 data sources |
| GET | `/api/earth-search/health` | System health check |
| POST | `/api/earth-search/crep` | Search + emit CREP map commands via Redis pub/sub |
| POST | `/api/earth-search/ingest` | Manual data ingestion |

## Agent Interface

```python
# From any MAS agent or orchestrator:
result = await earth_search_agent.process_task({
    "type": "earth_search",        # or species_search, environment_search, etc.
    "query": "earthquakes near Tokyo",
    "domain_groups": ["environment"],
    "geo": {"lat": 35.6762, "lng": 139.6503, "radius_km": 200},
    "include_crep": True,
    "include_llm": True,
})
```

## Files

| File | Purpose |
|------|---------|
| `earth_search/__init__.py` | Module entry, exports |
| `earth_search/models.py` | Pydantic models, 67 domains, domain groups |
| `earth_search/registry.py` | 40 data source registrations |
| `earth_search/orchestrator.py` | MINDEX-first parallel search engine |
| `earth_search/mindex_earth_client.py` | Client for MINDEX /earth endpoints |
| `earth_search/connectors/base.py` | Base connector with rate limiting |
| `earth_search/connectors/species.py` | iNaturalist, GBIF, MINDEX |
| `earth_search/connectors/environment.py` | USGS, EONET, FIRMS |
| `earth_search/connectors/climate.py` | OWM, NASA CMR, NOAA |
| `earth_search/connectors/transport.py` | CREP flights/vessels, Launch Library |
| `earth_search/connectors/space.py` | CREP satellites, SWPC, DONKI |
| `earth_search/connectors/infrastructure.py` | OSM Overpass, EPA FRS |
| `earth_search/connectors/telecom.py` | Cell towers, submarine cables |
| `earth_search/connectors/sensors.py` | MycoBrain, seismic stations |
| `earth_search/connectors/science.py` | PubChem, GenBank, PubMed |
| `earth_search/ingestion/__init__.py` | Ingestion module |
| `earth_search/ingestion/pipeline.py` | MINDEX + Supabase + NLM sink |
| `core/routers/earth_search_api.py` | FastAPI router (6 endpoints) |
| `agents/earth_search_agent.py` | Agent for orchestrator access |
| `migrations/025_earth_search.sql` | Postgres schema (3 tables) |
| `tests/test_earth_search.py` | Unit tests |

## Database

### Postgres Tables (migration 025)
- `earth_search_results` — individual results with geospatial indexing
- `earth_search_queries` — query audit log for analytics + training
- `earth_search_sources` — data source health tracking

### Supabase Table
- `earth_search_results` — cloud backup, same schema as Postgres

### MINDEX Integration
MAS connects to MINDEX's new earth-scale endpoints:
- `GET /earth` — unified search across 35 domains
- `GET /earth/nearby` — radius search
- `GET /earth/domains` — domain listing
- `GET /earth/map/bbox` — CREP spatial queries
- `GET /earth/map/layers` — available map layers
- `POST /earth/crep/sync` — push data to CREP unified_entities
- `GET /earth/stats` — entity counts

## Integration with Existing Systems

- **Search Orchestrator** (`consciousness/search_orchestrator.py`) — now includes Earth Search in step 3, results flow into specialist_results["earth_search"]
- **CREP** — search results generate CREP commands (showLayer, flyTo, getEntityDetails)
- **NLM Training** — all results appended to JSONL training sink
- **MYCA** — can search and explain any domain via consciousness pipeline
- **Agents** — any agent can call EarthSearchAgent via orchestrator
