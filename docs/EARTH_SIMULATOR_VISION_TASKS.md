# Earth Simulator & NatureOS Vision - Comprehensive Task List

> **Vision**: Merge iNaturalist + Google Earth + NLM (Nature Learning Model) + Situational Awareness
> into the most powerful biological observation, prediction, and learning platform.

## Reference Implementation
- [HipCityReg Situation Monitor](https://hipcityreg-situation-monitor.vercel.app/) - Event tracking, real-time monitoring

---

## 🗺️ PHASE 1: OVERVIEW/GLOBAL NETWORK MAP FIXES

### 1.1 Data Accuracy Issues (CRITICAL)
- [ ] **Fix observations count** - Currently miscalculated, needs accurate MINDEX pull
- [ ] **Fix species count** - Pull real count from MINDEX `/api/mindex/stats`
- [ ] **Fix regions count** - Calculate from actual observation locations
- [ ] **Fix verified count** - Track research-grade observations from iNaturalist
- [ ] **Fix devices count** - Pull real count from MycoBrain service + MINDEX devices

### 1.2 Real-Time Data Integration
- [ ] Connect overview stats to MINDEX API endpoints:
  - `/api/mindex/stats` → taxa, observations, images
  - `/api/mindex/mycobrain/devices` → device count
  - `/api/natureos/devices/telemetry` → live device data
- [ ] Add WebSocket/SSE for real-time updates
- [ ] Show ETL sync status (last updated time)
- [ ] Add data freshness indicators

### 1.3 Remove Misplaced Tabs
- [ ] Remove "Petri Dish Simulator" from Overview tabs
- [ ] Remove "Earth Simulator" from Overview tabs
- [ ] These should only be in `/apps/` routes

---

## 🌍 PHASE 2: EARTH SIMULATOR OVERHAUL

### 2.1 Control Panel Redesign
- [ ] Fix overlapping controls
- [ ] Remove useless/redundant controls
- [ ] Group controls logically:
  - **View Controls**: Terrain, Satellite, Street, Hybrid
  - **Data Layers**: Observations, Species Density, Verified Only
  - **Environmental**: Wind, Weather, Temperature, Humidity
  - **Fungal**: Spore Density, Mycelium Networks, Growth Zones
  - **Device Network**: MycoBrain devices, SporeBase, Sensors

### 2.2 iNaturalist Integration (Additive, not reductive)
- [ ] Full observation layer with ALL iNat data
- [ ] Species occurrence heatmaps
- [ ] Observation timeline slider
- [ ] Filter by taxonomic rank (Kingdom → Species)
- [ ] Research-grade vs casual filter
- [ ] Observer/identifier network visualization

### 2.3 Google Earth Engine Integration
- [ ] Satellite imagery layers (Landsat, Sentinel)
- [ ] NDVI vegetation index overlay
- [ ] Soil moisture data
- [ ] Land cover classification
- [ ] Historical imagery comparison
- [ ] Climate data layers

### 2.4 MycoBrain Device Layer
- [ ] Real-time device markers on map
- [ ] Click device → show live telemetry
- [ ] Device status indicators (online/offline)
- [ ] Coverage area visualization
- [ ] Sensor range circles
- [ ] FCI (Fungal Condition Index) from devices

### 2.5 MINDEX Knowledge Layer
- [ ] Taxa distribution polygons
- [ ] Compound distribution (psilocybin, medicinal)
- [ ] Genetic diversity zones
- [ ] Ecological niche modeling
- [ ] Species interaction networks
- [ ] Publication/research hotspots

### 2.6 NLM (Nature Learning Model) Integration
- [ ] AI-powered species prediction
- [ ] Mushroom interaction cascades
- [ ] Environmental event correlation
- [ ] User interaction learning
- [ ] Pattern recognition alerts
- [ ] Predictive fruiting models

---

## 🔬 PHASE 3: SITUATIONAL AWARENESS FEATURES

### 3.1 Event Observation System (like HipCityReg)
- [ ] Real-time event feed panel
- [ ] Event categories:
  - Fungal fruiting events
  - Weather alerts (rain = mushrooms)
  - Species sightings
  - Device anomalies
  - Environmental changes
  - Earthquake/geological events
- [ ] Event timeline visualization
- [ ] Event clustering by location
- [ ] Event severity indicators

### 3.2 Prediction Engine
- [ ] Machine learning fruiting predictions
- [ ] Weather-based spore dispersal
- [ ] Species migration patterns
- [ ] Disease/pathogen spread modeling
- [ ] Climate impact projections
- [ ] Seasonal pattern analysis

### 3.3 Pattern Analysis
- [ ] Time-series analysis widgets
- [ ] Correlation discovery (weather↔fruiting)
- [ ] Anomaly detection alerts
- [ ] Trend visualization
- [ ] Historical pattern matching
- [ ] Predictive confidence scores

### 3.4 Notification System
- [ ] Event-based alerts
- [ ] Custom watch areas
- [ ] Species appearance notifications
- [ ] Device alert forwarding
- [ ] Email/push notification integration
- [ ] Alert severity levels

---

## 🧫 PHASE 4: SPORE TRACKER ENHANCEMENTS

### 4.1 Map Controls
- [ ] Terrain view toggle
- [ ] Street view toggle
- [ ] Wind overlay (animated arrows)
- [ ] Weather overlay (precipitation, clouds)
- [ ] Fungal distribution overlay
- [ ] iNaturalist observations layer

### 4.2 MINDEX Integration
- [ ] Connect to `/api/mindex/taxa` for spore species
- [ ] Pull spore-specific observations
- [ ] Show spore distribution heatmaps
- [ ] Spore seasonality data
- [ ] Spore size/morphology data

### 4.3 SporeBase Device Network
- [ ] Future SporeBase device markers
- [ ] MycoBrain spore sensors
- [ ] Real-time spore count from devices
- [ ] Spore concentration alerts
- [ ] Air quality correlation

### 4.4 Missing Tools
- [ ] Spore calendar (seasonal peaks)
- [ ] Wind trajectory modeling
- [ ] Dispersal prediction
- [ ] Collection site recommendations
- [ ] Spore viability indicators

---

## 📊 PHASE 5: ANALYTICS PAGE

### 5.1 Real Data Integration
- [ ] Connect all widgets to real APIs
- [ ] Remove mock/placeholder data
- [ ] Add loading states for all widgets
- [ ] Error handling for failed fetches

### 5.2 Enhanced Widgets
- [ ] Taxa growth over time chart (from MINDEX)
- [ ] Observation velocity (new obs/day)
- [ ] Device health dashboard
- [ ] ETL pipeline metrics
- [ ] API usage statistics
- [ ] User activity metrics

### 5.3 New Analytics
- [ ] Species discovery rate
- [ ] Geographic coverage expansion
- [ ] Image quality metrics
- [ ] Verification rate trends
- [ ] Device uptime statistics
- [ ] NLM learning progress

---

## 📄 PHASE 6: ABOUT PAGE IMPROVEMENTS

### 6.1 Content Overhaul
- [ ] Company mission and vision
- [ ] SporeBase product introduction
- [ ] Spore tracking technology explanation
- [ ] MycoBrain device showcase
- [ ] Team section improvements
- [ ] Partnership/integration highlights

### 6.2 Video Demo Preparation
- [ ] Placeholder for SporeBase demo video
- [ ] Device gallery section
- [ ] Interactive product feature cards
- [ ] Use case scenarios
- [ ] Customer testimonials area
- [ ] Call-to-action sections

### 6.3 Visual Improvements
- [ ] Product images section
- [ ] Device specification cards
- [ ] Technology diagram
- [ ] Network architecture visual
- [ ] Parallax background sections

---

## 🌐 PHASE 7: BIOLOGICAL MODULES (NLM)

### 7.1 Core Module: Funga (Fungi)
- [ ] Mushroom species tracking
- [ ] Mycelium network visualization
- [ ] Spore dispersal modeling
- [ ] Compound detection
- [ ] Decomposition role mapping

### 7.2 Module: Flora (Plants)
- [ ] Plant species observations
- [ ] Mycorrhizal associations
- [ ] Pollination networks
- [ ] Phenology tracking
- [ ] Vegetation indices

### 7.3 Module: Fauna (Animals)
- [ ] Animal observations
- [ ] Habitat overlap analysis
- [ ] Species interaction mapping
- [ ] Migration patterns
- [ ] Population dynamics

### 7.4 Specialized Modules
- [ ] **Insects** - Pollinator tracking, pest detection
- [ ] **Birds** - Migration, nesting, feeding patterns
- [ ] **Marine Life** - Ocean observations, coastal fungi
- [ ] **Weather** - Climate data, precipitation, temperature
- [ ] **Machines** - MycoBrain, SporeBase, sensor network

---

## 🔗 PHASE 8: DATA SCRAPING & INTEGRATION

### 8.1 Keep MINDEX Up-to-Date
- [ ] Verify ETL scheduler running (60s interval)
- [ ] Add more data sources to ETL
- [ ] Implement incremental syncing
- [ ] Add scraping status dashboard
- [ ] Retry logic for failed fetches

### 8.2 External Data Sources
- [ ] iNaturalist API (observations, taxa)
- [ ] GBIF (Global Biodiversity)
- [ ] Mushroom Observer
- [ ] NOAA weather data
- [ ] USGS earthquake data
- [ ] NASA satellite imagery
- [ ] Air quality APIs

### 8.3 Situational Awareness Sources
- [ ] Emergency alert systems
- [ ] Weather warnings
- [ ] Environmental sensors
- [ ] News/event aggregation
- [ ] Social media monitoring (species sightings)

---

## 🎯 PRIORITY ORDER

1. **CRITICAL (This Week)**
   - Fix overview stats accuracy (observations, species, devices)
   - Remove misplaced tabs from overview
   - Connect Spore Tracker to MINDEX

2. **HIGH (Next 2 Weeks)**
   - Earth Simulator control overhaul
   - Analytics real data integration
   - Event observation system

3. **MEDIUM (Month 1)**
   - NLM integration framework
   - Prediction engine basics
   - About page improvements

4. **FUTURE (Ongoing)**
   - Biological modules (Flora, Fauna, etc.)
   - Full situational awareness
   - Machine learning predictions

---

## 📝 NOTES

- Reference: [HipCityReg Situation Monitor](https://hipcityreg-situation-monitor.vercel.app/)
- All data should flow from MINDEX as single source of truth
- Device data from MycoBrain service at localhost:8003
- Google Maps API key: `<redacted-google-maps-api-key>`
- Future Supabase integration for user data, auth, realtime

