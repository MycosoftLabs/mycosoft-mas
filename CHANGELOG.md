# Changelog

All notable changes to the Mycosoft MAS project will be documented in this file.

## [Unreleased] - 2026-01-13

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
