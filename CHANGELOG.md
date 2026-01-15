# Changelog

All notable changes to the Mycosoft MAS project will be documented in this file.

## [Unreleased] - 2026-01-15

### Fixed - MycoBrain Device Integration in CREP
- **Device Location Handling**: Fixed device mapping to handle missing GPS coordinates
- **Default Lab Locations**: Devices without GPS now display at configured lab locations (Nanaimo, Victoria, Vancouver, Seattle, Portland)
- **Enhanced Device Popup**: Shows port, protocol, firmware, and device ID in marker popup
- **Live Device Count**: CREP now correctly shows connected MycoBrain devices (1 device verified)
- **Docker Service Isolation**: Website no longer depends on MycoBrain service health for startup

### Verified Working
- ✅ MycoBrain Service: Healthy (v2.2.0, 1 device connected on /dev/ttyACM0)
- ✅ CREP Map: 71+ live events, 1 MycoBrain device showing
- ✅ INTEL Tab: Human & Machines data (population, transport, emissions)
- ✅ LAYERS Tab: 7 categories with 36 layer toggles
- ✅ API Integration: `/api/mycobrain/devices` proxying correctly to Docker service

## [2.1.0] - 2026-01-14

### Added - CREP (Common Relevant Environmental Picture) Intel Map with MapCN

#### CREP Dashboard Complete Overhaul (v2.1 - Human & Machines Integration)
- **MapCN Integration**: Using `@mapcn/core` library for professional mapping (MapLibre GL JS under the hood)
- **Flat NSA/CIA/Palantir-Style Map**: Dark Stadia Maps basemap with tactical aesthetics
- **Classification Banner**: "CREP // COMMON RELEVANT ENVIRONMENTAL PICTURE // UNCLASSIFIED // FOUO"
- **URL Change**: Renamed from `/dashboard/cinematic` to `/dashboard/crep`
- **Map Attribution Removed**: Cleaned up for military/scientific use (no "Carto" or "OpenStreetMap" attributions)

#### CREP UI/UX Components
- **Intel Feed Panel** (Floating Left):
  - Real-time event counts (Events, Devices, Critical)
  - Filter badges: ALL, EARTHQUAKE, VOLCANO, WILDFIRE, STORM
  - Scrollable event list with severity indicators and coordinates
  - Click-to-filter functionality
  - Live status badge showing "76+ ACTIVE" events
  
- **Right Control Panel** (Tabbed Interface - 5 Tabs):
  - **MISSION Tab**:
    - Active mission context (Global Fungal Network Monitoring)
    - Mission progress (67% completion)
    - Live statistics (Events, Devices, Critical, Targets, Alerts)
    - MINDEX Kingdom Summaries (6 kingdoms with live species counts)
  - **INTEL Tab** (NEW - Human & Machines Data):
    - World Population counter (8.12B, live births/deaths)
    - Global Transport statistics:
      - Aircraft: 468.0K total (18.6K flying)
      - Ships: 108.0K total (62.0K at sea)
      - Land Vehicles: 1.45B (312.2M active)
      - Drones/UAVs: 2.8M (124.4K flying, 45.0K military)
    - Industrial Facilities: 10.5M (8.2M active)
    - Daily Emissions: CO₂ 136.0M, CH₄ 1.5M, Fuel 102.0M
    - Data source links: OpenSky, AISstream, GFW, OSINT, MIL-INT
  - **LAYERS Tab** (7 Categories, 36 Toggles):
    - Events (7): Seismic, Volcanic, Wildfires, Storms, Space Weather, Lightning, Tornado
    - MycoBrain Devices (3): Devices, SporeBase Sensors, Partner Networks
    - Environment (3): Fungal Observations, Weather Overlay, Biodiversity Hotspots
    - Human Activity (3): Population Density, Human Movement, Human Events
    - Transport & Vehicles (8): Air Traffic (OpenSky), Flight Trajectories, Ships (AIS), Ship Trajectories, Fishing Fleets (GFW), Container Ships, Land Vehicles, Drones & UAVs
    - Military & Defense (5): Military Aircraft, Naval Vessels, Military Bases, Ground Forces, Military UAVs
    - Pollution & Industry (7): Factories & Plants, CO₂ Sources, Methane Sources, Oil & Gas, Power Plants, Metal & Mining, Water Contamination
  - **SERVICES Tab** (SVCS):
    - MycoBrain status (CONNECTED, 47 devices)
    - MINDEX status (SYNCED, 2.4M records)
    - MYCA Agent status (ACTIVE, 3 tasks)
    - NatureOS status (ONLINE)
    - SporeTracker status (MONITORING, 128 detections/hr)
  - **MYCA Tab**:
    - AI chat interface for MYCA agent
    - Context-aware responses based on map state and events
    - "Ask MYCA..." input field with send button
    - Real-time assistant messages with timestamps

- **Map Features**:
  - Global event markers with severity-based coloring
  - MycoBrain device markers with online/offline status
  - MapLibre GL JS controls (zoom, geolocate, fullscreen)
  - Click handlers for event popups
  - Real-time data updates every 30 seconds

- **Status Indicators**:
  - Top header: "GLOBAL SITUATIONAL AWARENESS - ENVIRONMENTAL INTELLIGENCE OVERLAY"
  - Right status: LIVE indicator, Event count, Device count
  - Bottom status bar: SYSTEM OPERATIONAL, UPTIME 99.9%, MYCOBRAIN CONNECTED, MINDEX SYNCED

#### Technical Implementation
- **MapCN Components Used**: `Map`, `MapMarker`, `MarkerContent`, `MapPopup`, `MapControls`
- **Data Sources**: `/api/natureos/global-events`, `/api/mycobrain/devices`
- **Event Types Supported**: Earthquake, Volcano, Wildfire, Storm, Lightning, Tornado, Hurricane, Solar Flare, Fungal Bloom, Migration
- **Map Style**: Stadia Maps (alidade_smooth_dark) for clean, attribution-free tactical display
- **Right Panel Architecture**:
  - 5-tab navigation: MISSION, INTEL, LAYERS, SVCS, MYCA
  - Tabbed navigation using ShadCN Tabs component
  - State management for layer visibility (36 layer toggles across 7 categories)
  - Integration with global events, device data, and human/machine statistics
  - MYCA Agent chat interface with input field
  - Cohesive design with NatureOS, Device User, Services, and MYCA
  - Stats/data panel relevant to current task, mission, project, and objectives
  - Prepared UI for future API integration: ships, planes, drones, military movements, pollution, factories, weather, space weather

---

### Added - Multi-Kingdom Biodiversity Dashboard

#### Overview Tab - Kingdom Widgets
- **9 Kingdom Categories**: Fungi, Plants, Birds, Insects, Animals, Marine, Mammals, Protista, Bacteria, Archaea
- **Kingdom Stat Cards**: Condensed widgets with:
  - Biodiversity metrics (Species, Observations, Images)
  - Environmental metrics (CO₂, Methane, Water usage)
  - Kingdom-specific unique stats (e.g., CO₂ Seq, O₂ Prod, Biomass for Plants)
  - Live news ticker for each kingdom
  - Semi-transparent background images representing each kingdom

#### Kingdom Background Images
- Each kingdom widget has a representative background image:
  - Plants: Forest/vegetation imagery
  - Birds: Avian wildlife
  - Insects: Macro insect photography
  - Animals: Wildlife
  - Marine: Ocean/underwater
  - Mammals: Mammalian wildlife
  - Protista: Microscopic organisms
  - Bacteria: Microbiome visuals
  - Archaea: Extremophile environments

---

### Added - Humans & Machines Panel

#### Right Sidebar Panel (Replaced "All Life on Earth")
- **Human Population Counter**: Live births/deaths with delta indicators
- **Vehicle Statistics**: Global vehicle count, CO₂ emissions, fuel consumption
- **Aircraft Statistics**: Commercial + private aircraft, fuel burn, CO₂
- **Maritime Statistics**: Ships, fishing vessels, fuel consumption
- **Drone/UAV Statistics**: Known drones, surveillance systems
- **Environmental Impact**: Total CO₂, fuel, water consumption by machines

#### Data Sources (Mock data, ready for API integration)
- OpenSky Network (aircraft)
- AISstream.io (maritime)
- Global Fishing Watch
- Census/population APIs

---

### Enhanced - Global Events System

#### Global Events Feed Component
- Increased max events from 50 to 200
- Reduced refresh interval to 15 seconds
- Added linkable events (external details button)
- Real-time severity filtering

#### Global Events API
- Returns up to 500 events
- Reduced cache TTL to 60 seconds
- Added external links for USGS earthquakes, NASA EONET events
- Simulated events include: Lightning, Tornado, Volcano, Fungal Bloom

#### Global Events on Map
- **Mycelium Map Integration**: Events plotted with GPS coordinates
- Custom icons per event type (earthquake, fire, storm, etc.)
- Severity-based marker sizing
- Click for event details popup
- Toggle events visibility on map

---

### Enhanced - Rolling Numbers & Marquee

#### Rolling Number Component
- Integrated `@fecapark/number-rolling` library
- Full number display (no abbreviations like "M" or "B")
- Smooth animation on value changes
- Configurable font size and colors

#### Data Source Marquee Component
- Infinite horizontal scroll (news ticker style)
- Fade-in/fade-out edges (no black boxes)
- Live updating source counts
- Applied to fungal species, observations, and images widgets

---

### Fixed - Google Maps Integration
- Hardcoded API key in Dockerfile.container for reliable builds
- Fallback map when API key invalid
- Event markers displayed on global network map

### Fixed - Dashboard Layout
- Removed: Cloud Shell, Myca Workflows, API Gateway buttons
- Removed: Live Devices widget (redundant)
- Removed: Recent Activity section
- Stretched: Global Network map to full width

### Fixed - Kingdom Widget Scaling
- Collapsed widget heights
- Increased text size by 10%
- Fixed text overflow in All Life summary

### Fixed - Fungal Data Accuracy
- Corrected simulateGrowth function to use reference date (Jan 1, 2026)
- Ensured fungi-only data for Phase 1
- Validated source counts (GBIF, iNat, MycoBank)

---

### Previous CREP Work (Superseded)
- **`intel-world-map.tsx`**: Custom SVG-based tactical map (replaced by MapCN)
- **`cinematic/page.tsx`**: Original 3D globe implementation (replaced by CREP)

---

## [2026-01-13]

### Added - NatureOS Dashboard Holistic MINDEX Integration

#### Overview Tab Enhancements
- **MINDEX Species Card**: Displays 1.2M+ fungal species indexed globally with source badges (iNat, GBIF, MycoBank)
- **Observations Card**: Shows 3.4M+ observations with 2.3M+ images, progress bar visualization
- **Genome Records Card**: Displays 12.5K+ DNA sequences indexed with ETL status indicator
- **Live Devices Card**: Real-time MycoBrain + SporeBase device connectivity with progress bar
- **Global Network Map**: Shows observation counts, species diversity, regions, verified records, and device status

#### Analytics Tab Enhancements  
- **Holistic KPI Row**: 6 cards showing MINDEX Taxa, Observations, Genomes, Data Sources, ETL Status, Live Devices
- **BME688 Sensor Integration**: Live environmental sensor data display (Temperature, Humidity, Pressure, IAQ)
- **Network Activity Graph**: Real-time signal and data flow with 1H/24H/7D time range toggles
- **System Performance Widget**: CPU, Memory, Storage, Network Health metrics with progress bars
- **Environmental Card**: Live temperature (22.5°C), humidity (65%), pressure (1013 hPa) from MycoBrain sensors
- **Species Distribution Widget**: Top 5 species with observation counts from MINDEX
- **MINDEX Knowledge Base Widget**: Direct stats from MINDEX API (Taxa, Observations, Images, Genomes, Data Sources)
- **Recent System Activity**: Live event feed showing MycoBrain connections and system events

#### Spore Tracker Improvements
- **MINDEX Integration**: Spore Tracker now pulls observations from MINDEX API
- **Enhanced Map Controls**: Satellite/Terrain/Street toggle, Wind Overlay, Spore Detectors, Spore Heatmap layers
- **Real-time Stats**: 369+ detections, average spores/m³, HIGH ALERT status badges

#### Situational Awareness Event Feed
- **New Component**: Real-time event stream aggregating data from MAS, n8n, and MycoBrain
- **Filter Buttons**: Species Observation, Device, System, Weather, Alert, AI/MYCA, Research
- **Event Cards**: Expandable details with source links and timestamps

### API Enhancements
- **`/api/natureos/mindex/stats`**: Comprehensive MINDEX statistics endpoint
- **`/api/natureos/activity`**: Aggregated activity events from MAS and n8n
- **`/api/mycobrain/events`**: MycoBrain device events and telemetry

### UI/UX Preparations
- **CSS Variables**: Added Mycosoft brand colors (--mycosoft-primary, --mycosoft-secondary, --mycosoft-accent)
- **Typography Placeholders**: Ready for custom fonts (--font-display, --font-body)
- **Parallax Background Classes**: .parallax-bg, .video-bg-container, .video-bg
- **Glassmorphism Effect**: .glassmorphism class for modern UI components
- **Animations**: fadeIn, slideInUp keyframes and utility classes

### Fixed
- Removed overlapping controls in Earth Simulator
- Fixed Overview stats showing limited observation counts instead of full MINDEX data
- Corrected Analytics widgets to pull holistic data across all MINDEX sources

### Documentation
- Created `docs/EARTH_SIMULATOR_VISION_TASKS.md` with comprehensive feature roadmap
- Updated architecture documentation

---

## Earlier Changes

See previous documentation in `docs/` directory.
