# CREP Data Source APIs & Feeds - Redundancy Master List

**Generated:** January 15, 2026  
**Purpose:** Comprehensive list of APIs and data feeds for CREP integration with vast source redundancy

---

## 🛩️ 1. AVIATION / AIRCRAFT TRACKING

### Primary Sources

| API / Service | Data Provided | Access Method | Primary Sources |
|---------------|---------------|---------------|-----------------|
| **FlightAware AeroAPI** | Real-time & historical flight status, positions, tracks, ETAs, alerts | REST API + Firehose streaming | Terrestrial ADS-B (~41,000 stations), Space-based ADS-B (Aireon), ACARS/SATCOM, ANSP radar feeds |
| **OpenSky Network** | Live & historical ADS-B/Mode-S/FLARM data, state vectors | REST API (free for research) | Volunteer ground ADS-B receivers globally |
| **ADS-B Exchange** | Unfiltered live ADS-B data (2Hz updates), trajectory history | Enterprise REST API | Community ADS-B ground stations |
| **Flightradar24** | Live flight tracking, schedules, aircraft metadata | Commercial REST API | ADS-B ground network, MLAT, satellite ADS-B, radar feeds |
| **Aviation Edge** | Flight tracker, schedules, routes, satellite tracking | REST API | Aggregated from airlines, airports, authorities |
| **AirLabs** | Real-time ADS-B flight positions | REST API | Ground ADS-B network |
| **Aviationstack** | Global flight status, schedules, airlines | REST API | Aggregated aviation sources |
| **ADSBDB** | Aircraft lookup (ICAO24, registration) | Open REST API | Public aircraft registries |
| **RadarBox (AirNav)** | Live/historical flight data, streaming | ODAPI + Firehose | ADS-B ground/satellite network |

### Endpoints & Integration

```typescript
// FlightAware AeroAPI
const FLIGHTAWARE_API = "https://aeroapi.flightaware.com/aeroapi";
// Headers: { "x-apikey": process.env.FLIGHTAWARE_API_KEY }

// OpenSky Network (Free)
const OPENSKY_API = "https://opensky-network.org/api";
// Endpoints: /states/all, /flights/aircraft, /flights/arrival, /flights/departure

// ADS-B Exchange
const ADSBX_API = "https://adsbexchange.com/api/aircraft/v2";
// Enterprise: https://api.adsbexchange.com

// Aviation Edge
const AVIATION_EDGE_API = "https://aviation-edge.com/v2/public/flights";
// Params: key={API_KEY}&status=en-route
```

---

## 🚢 2. MARITIME / VESSEL TRACKING

### Primary Sources

| API / Service | Data Provided | Access Method | Primary Sources |
|---------------|---------------|---------------|-----------------|
| **MarineTraffic** | Real-time AIS positions, vessel info, port data | REST API | Terrestrial AIS receivers, satellite AIS |
| **AISstream** | Live AIS data streaming | WebSocket | Ground AIS network |
| **Global Fishing Watch** | Vessel tracks, fishing activity, SAR detections | REST API | AIS + VMS + Satellite imagery |
| **Spire Maritime** | Global satellite + terrestrial AIS | GraphQL API | 600K+ vessels, satellite constellation |
| **VesselFinder** | Live AIS, vessel particulars, port calls | REST API | AIS networks |
| **NavAPI** | AIS positions, routing, weather, 6-year history | REST API | Terrestrial + Satellite AIS |
| **Datalastic** | Ship tracking, zone-based queries | REST API | ~750,000 vessels via AIS |
| **DataDocked** | Real-time vessel positions for 800K+ vessels | REST API | Satellite + terrestrial AIS |
| **SeaVantage** | Enriched AIS, event detection | REST API | AIS + carrier feeds |
| **exactEarth** | Satellite-AIS for remote ocean tracking | API | Satellite constellation |
| **SafeCube.ai** | Container vessel intelligence | REST API | AIS + registries |
| **AIS Hub** | Free public AIS data | REST API | Community receivers |

### Endpoints & Integration

```typescript
// MarineTraffic
const MARINETRAFFIC_API = "https://services.marinetraffic.com/api";
// Endpoints: /exportvessels, /vesseltrack, /portcalls

// AISstream WebSocket
const AISSTREAM_WS = "wss://stream.aisstream.io/v0/stream";
// Subscribe with API key and bounding box

// Global Fishing Watch
const GFW_API = "https://gateway.api.globalfishingwatch.org/v2";
// Endpoints: /vessels, /events, /map/activity

// Spire Maritime
const SPIRE_API = "https://api.spire.com/graphql";
// GraphQL queries for vessels
```

---

## 🛰️ 3. SATELLITE & SPACE OBJECT TRACKING

### Primary Sources

| API / Service | Data Provided | Access Method | Primary Sources |
|---------------|---------------|---------------|-----------------|
| **CelesTrak** | TLE data, GP elements, active satellites | Public REST | NORAD catalog, 18th Space Control Squadron |
| **Space-Track.org** | Official TLE catalog, debris tracking | REST API (account required) | 18th SCS, US Space Force |
| **AstriaGraph (UT Austin)** | Space debris, orbital objects visualization | Web/API | Academic research, Space-Track data |
| **N2YO.com** | Satellite positions, pass predictions | REST API | NORAD TLEs |
| **Aviation Edge Satellite API** | Real-time positions, TLEs, metadata | REST API | Partner networks, public TLEs |
| **Zenith API** | Real-time satellite/ISS tracking | REST API | TLE databases |
| **SatNOGS** | Ground station observations, transmitter data | Public API | Community ground stations |
| **SatChecker** | Satellite predictions, illumination | REST API | CelesTrak/Space-Track TLEs |
| **NASA GHRC DAAC** | Satellite TLEs, metadata | REST API | NASA archives |
| **SatelliteMap.space** | Visual satellite tracking | Web interface | CelesTrak TLEs |

### Endpoints & Integration

```typescript
// CelesTrak (FREE - Primary)
const CELESTRAK_API = "https://celestrak.org/NORAD/elements";
// Endpoints: /gp.php?GROUP=active&FORMAT=json
// Categories: stations, starlink, weather, gnss, gps-ops, debris

// Space-Track.org (Account Required)
const SPACETRACK_API = "https://www.space-track.org/basicspacedata/query";
// Requires authentication

// N2YO
const N2YO_API = "https://api.n2yo.com/rest/v1/satellite";
// Endpoints: /tle/{id}, /positions/{id}/{observer_lat}/{observer_lng}/{observer_alt}/{seconds}

// AstriaGraph
const ASTRIAGRAPH_URL = "http://astria.tacc.utexas.edu/AstriaGraph/";
// Academic visualization, data from Space-Track
```

---

## 🌡️ 4. SPACE WEATHER & SOLAR DATA

### Primary Sources

| API / Service | Data Provided | Access Method | Primary Sources |
|---------------|---------------|---------------|-----------------|
| **NOAA SWPC** | Solar flares, geomagnetic storms, indices, alerts | REST API (JSON/XML) | GOES satellites, ground observatories |
| **NASA DONKI** | Space weather notifications, CME data | REST API | NASA heliophysics |
| **WSA-Enlil Model** | Solar wind forecasts, CME predictions | NOAA/NASA outputs | Modeling centers |
| **NOAA NCEI SPOT** | Space weather archive, searchable portal | REST API | Historical space weather data |

### Endpoints & Integration

```typescript
// NOAA SWPC (FREE - Primary)
const SWPC_API = "https://services.swpc.noaa.gov";
// Endpoints:
// /products/noaa-scales.json - Current scales (R, S, G)
// /products/solar-wind/plasma-7-day.json - Solar wind plasma
// /products/solar-wind/mag-7-day.json - Magnetic field
// /products/alerts.json - Active alerts
// /products/summary/10cm-flux.json - Solar flux

// NASA DONKI
const DONKI_API = "https://api.nasa.gov/DONKI";
// Endpoints: /CME, /FLR, /GST, /IPS
// Params: api_key=DEMO_KEY (or registered key)
```

---

## 🏭 5. POLLUTION & EMISSIONS TRACKING

### Primary Sources

| API / Service | Data Provided | Access Method | Primary Sources |
|---------------|---------------|---------------|-----------------|
| **Carbon Mapper** | Methane/CO2 plumes, point sources | Data portal + API | Satellite hyperspectral imaging |
| **EPA FLIGHT** | US facility emissions | REST API | EPA regulatory data |
| **Climate TRACE** | Global emissions by sector | Data downloads | Satellite + ground observations |
| **Sentinel-5P** | Atmospheric composition (NO2, SO2, CH4) | Copernicus API | ESA satellite |

### Endpoints & Integration

```typescript
// Carbon Mapper Data Portal
const CARBONMAPPER_URL = "https://data.carbonmapper.org";
// API endpoints for plume data (check portal for specifics)

// EPA FLIGHT
const EPA_FLIGHT_API = "https://ghgdata.epa.gov/ghgp/service";
// Facility emissions data

// Climate TRACE
const CLIMATETRACE_API = "https://api.climatetrace.org";
// Sector-specific emissions
```

---

## 🚂 6. RAIL & GROUND TRANSPORT

### Primary Sources

| API / Service | Data Provided | Access Method | Primary Sources |
|---------------|---------------|---------------|-----------------|
| **OpenRailwayMap** | Railway infrastructure, tracks, stations | Overpass API | OpenStreetMap contributors |
| **OSM Railway Data** | Rail network geometry | Overpass/OSM API | Community mapping |

### Endpoints & Integration

```typescript
// OpenRailwayMap (via Overpass API)
const OVERPASS_API = "https://overpass-api.de/api/interpreter";
// Query: [out:json];way["railway"](bbox);out geom;

// OpenStreetMap
const OSM_API = "https://api.openstreetmap.org/api/0.6";
```

---

## 🍄 7. BIODIVERSITY & FUNGAL OBSERVATIONS

### Primary Sources

| API / Service | Data Provided | Access Method | Primary Sources |
|---------------|---------------|---------------|-----------------|
| **iNaturalist** | Species observations, photos, taxonomy | REST API | Citizen scientists globally |
| **GBIF** | Global biodiversity records | REST API | Museums, institutions, iNaturalist |
| **Mushroom Observer** | Fungal observations (imports to iNaturalist) | API | Mycology community |
| **eBird** | Bird observations | REST API | Citizen scientists |

### Endpoints & Integration

```typescript
// iNaturalist (FREE - Primary for Fungi)
const INATURALIST_API = "https://api.inaturalist.org/v1";
// Endpoints:
// /observations?taxon_id=47170 - Kingdom Fungi
// /observations?iconic_taxa=Fungi
// /taxa/47170 - Fungi taxon info
// Params: per_page, lat, lng, radius, quality_grade

// GBIF
const GBIF_API = "https://api.gbif.org/v1";
// Endpoints: /occurrence/search, /species
```

---

## 🌋 8. GEOPHYSICAL EVENTS

### Primary Sources

| API / Service | Data Provided | Access Method | Primary Sources |
|---------------|---------------|---------------|-----------------|
| **USGS Earthquake** | Real-time earthquake events | REST/GeoJSON | Global seismic network |
| **NASA EONET** | Natural events (fires, storms, volcanoes) | REST API | Multiple satellites |
| **GDACS** | Disaster alerts | REST/RSS | UN OCHA, EC JRC |
| **FIRMS (NASA)** | Active fire data | REST API | MODIS/VIIRS satellites |

### Endpoints & Integration

```typescript
// USGS Earthquake (FREE)
const USGS_API = "https://earthquake.usgs.gov/fdsnws/event/1/query";
// Params: format=geojson, starttime, endtime, minmagnitude

// NASA EONET
const EONET_API = "https://eonet.gsfc.nasa.gov/api/v3/events";
// Categories: wildfires, severeStorms, volcanoes

// NASA FIRMS
const FIRMS_API = "https://firms.modaps.eosdis.nasa.gov/api/area";
// Active fire hotspots
```

---

## 🌤️ 9. WEATHER & ATMOSPHERIC DATA

### Primary Sources

| API / Service | Data Provided | Access Method | Primary Sources |
|---------------|---------------|---------------|-----------------|
| **OpenWeatherMap** | Current/forecast weather, map tiles | REST API | Global weather stations |
| **NOAA Weather** | US weather data, forecasts | REST API | NWS stations |
| **DTN Marine Weather** | Marine-specific conditions | REST API | Maritime observations |
| **Windy API** | Weather visualization data | REST API | Multiple models (ECMWF, GFS) |

---

## 📊 10. INTEGRATION ARCHITECTURE

### Recommended Redundancy Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    CREP DATA LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  AIRCRAFT    │  │   VESSELS    │  │  SATELLITES  │          │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤          │
│  │ Primary:     │  │ Primary:     │  │ Primary:     │          │
│  │ - FlightAware│  │ - AISstream  │  │ - CelesTrak  │          │
│  │ - OpenSky    │  │ - Spire      │  │ - Space-Track│          │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤          │
│  │ Fallback:    │  │ Fallback:    │  │ Fallback:    │          │
│  │ - ADS-B Exch │  │ - NavAPI     │  │ - N2YO       │          │
│  │ - RadarBox   │  │ - VesselFind │  │ - SatNOGS    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ SPACE WX     │  │  POLLUTION   │  │   FUNGI      │          │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤          │
│  │ Primary:     │  │ Primary:     │  │ Primary:     │          │
│  │ - NOAA SWPC  │  │ - CarbonMap  │  │ - iNaturalist│          │
│  │ - NASA DONKI │  │ - EPA FLIGHT │  │ - MINDEX     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Architecture

```
External APIs ──► Connector Services ──► Local Cache (Redis/SQLite)
                        │                        │
                        ▼                        ▼
                  MINDEX Logging         API Routes (/api/oei/*)
                        │                        │
                        ▼                        ▼
                  Telemetry DB           CREP Dashboard
```

### Service Container Structure

```yaml
services:
  aircraft-service:
    image: crep-aircraft
    environment:
      - FLIGHTAWARE_KEY
      - OPENSKY_USER
    volumes:
      - aircraft-cache:/data
    
  vessel-service:
    image: crep-vessels
    environment:
      - AISSTREAM_KEY
      - SPIRE_TOKEN
    volumes:
      - vessel-cache:/data
    
  satellite-service:
    image: crep-satellites
    environment:
      - SPACETRACK_USER
      - SPACETRACK_PASS
    volumes:
      - satellite-cache:/data
    
  weather-service:
    image: crep-weather
    environment:
      - NOAA_SWPC_ENABLED=true
    volumes:
      - weather-cache:/data
```

---

## 🔑 API KEYS REQUIRED

| Service | Environment Variable | Free Tier |
|---------|---------------------|-----------|
| FlightAware | `FLIGHTAWARE_API_KEY` | Limited |
| OpenSky | `OPENSKY_USERNAME`, `OPENSKY_PASSWORD` | Yes (rate limited) |
| ADS-B Exchange | `ADSBX_API_KEY` | Limited |
| AISstream | `AISSTREAM_API_KEY` | Yes |
| Spire | `SPIRE_TOKEN` | No |
| MarineTraffic | `MARINETRAFFIC_KEY` | No |
| Space-Track | `SPACETRACK_USER`, `SPACETRACK_PASS` | Yes (registration) |
| N2YO | `N2YO_API_KEY` | Yes |
| iNaturalist | None required for read | Yes |
| NOAA SWPC | None required | Yes |
| USGS | None required | Yes |
| NASA | `NASA_API_KEY` | Yes (DEMO_KEY works) |

---

## 📋 IMPLEMENTATION CHECKLIST

### Phase 1: Core Data (Current)
- [x] CelesTrak satellite TLEs
- [x] NOAA SWPC space weather
- [x] iNaturalist fungal observations
- [x] Sample AIS vessel data
- [x] Sample FlightRadar24 data

### Phase 2: Enhanced Sources
- [ ] FlightAware AeroAPI integration
- [ ] OpenSky Network live data
- [ ] Space-Track.org official TLEs
- [ ] Real AISstream WebSocket connection
- [ ] Global Fishing Watch integration

### Phase 3: Full Redundancy
- [ ] Multiple aircraft sources with failover
- [ ] Multiple vessel sources with failover
- [ ] Carbon Mapper pollution overlay
- [ ] OpenRailwayMap integration
- [ ] AstriaGraph space debris

### Phase 4: Microservices
- [ ] Containerized aircraft service
- [ ] Containerized vessel service
- [ ] Containerized satellite service
- [ ] Local caching layer (Redis)
- [ ] Historical data storage

---

## 📚 REFERENCE LINKS

### Documentation
- FlightAware AeroAPI: https://flightaware.com/commercial/aeroapi/
- OpenSky Network: https://openskynetwork.github.io/opensky-api/
- CelesTrak: https://celestrak.org/NORAD/documentation/
- NOAA SWPC: https://www.swpc.noaa.gov/products-and-data
- iNaturalist: https://www.inaturalist.org/pages/api+reference
- MarineTraffic: https://www.marinetraffic.com/en/ais-api-services

### Visualization References
- FlightRadar24: https://www.flightradar24.com/
- MarineTraffic: https://www.marinetraffic.com/
- AstriaGraph: http://astria.tacc.utexas.edu/AstriaGraph/
- SatelliteMap.space: https://satellitemap.space/
- Carbon Mapper: https://data.carbonmapper.org/
- OpenRailwayMap: https://www.openrailwaymap.org/

---

*This document serves as the master reference for CREP data source integration and redundancy planning.*
