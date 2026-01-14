# Upgrade Implementation Changelog

**Date**: January 12, 2026  
**Version**: v2.1.0 (Upgrade Batch)

---

## Summary

This upgrade batch implements the validated upgrade knowledge base, adding significant new features across observability, UI/UX visualization, data pipeline integrations, and IoT device capabilities.

---

## P0 - Foundation (Observability Stack)

### Loki Port Conflict Resolution
- **Changed**: Loki port from `3100` → `3101` in `config/config.yaml`
- **Updated**: `PORT_ASSIGNMENTS.md` to reflect new port

### Docker Observability Stack
- **Added**: `docker/observability.yml` - Docker Compose for Loki/Promtail/Grafana
- **Added**: `docker/loki/loki-config.yml` - Loki log aggregation config
- **Added**: `docker/promtail/promtail-config.yml` - Log shipping config

### Prometheus Extended Configuration
- **Updated**: `prometheus.yml` with new scrape jobs:
  - `mycobrain-devices` - ESP32 device fleet
  - `sporebase-devices` - SporeBase device fleet
  - `mindex-api` - MINDEX backend
  - `loki` - Log aggregation health

### Alert Rules
- **Added**: `prometheus/alerts.yml` with comprehensive alert rules:
  - Device fleet alerts (DeviceDown, DeviceDegraded)
  - Environmental alerts (HighTemperature, LowTemperature, VOCSpike, HumidityOutOfRange)
  - Connectivity alerts (WeakWiFiSignal)
  - Service alerts (MINDEXDown, MycoBrainServiceDown, LokiDown)

### Grafana Configuration
- **Added**: `docker/grafana/provisioning/datasources/datasources.yml`
- **Added**: `docker/grafana/provisioning/dashboards/dashboards.yml`
- **Added**: `docker/grafana/dashboards/fleet-health.json`

---

## P1 - Cinematic Dashboard

### Route: `/dashboard/cinematic`

### New Components
- **Added**: `components/fx/EffectsRig.tsx`
  - Post-processing effects using @react-three/postprocessing
  - Bloom, Noise, Vignette, Tone Mapping
  
- **Added**: `components/widgets/HoloTokens.tsx`
  - GPU-instanced particle system
  - Animated holographic orbs with instanced meshes
  - Dual color gradients with dynamic rotation
  
- **Added**: `components/widgets/HUD.tsx`
  - Overlay HUD with glassmorphism design
  - Real-time stats: Devices, Agents, Network bandwidth
  - Live clock, temperature, humidity
  - Status bar with uptime and connection status

### Page Implementation
- **Added**: `app/dashboard/cinematic/page.tsx`
  - React Three Fiber canvas with on-demand frame loop
  - Power-efficient rendering with `frameloop="demand"`
  - Fullscreen toggle support
  - HoloCore visualization with floating rings

---

## P1 - deck.gl Live Map

### Route: `/natureos/live-map`

### New Components
- **Added**: `components/maps/DeviceTrips.tsx`
  - TripsLayer for animated GPS trails
  - ScatterplotLayer for device positions
  - PathLayer for historical tracks
  - Color coding by device type (mycobrain, sporebase, alarm)
  
- **Added**: `components/maps/TimeScrubber.tsx`
  - Time control with playback (play/pause)
  - Skip forward/back buttons
  - Speed control (1x, 2x, 5x, 10x)
  - Alert timeline with colored markers
  - Current time display with date

### Page Implementation
- **Added**: `app/natureos/live-map/page.tsx`
  - DeckGL with Mapbox basemap (dark-v11 style)
  - Real-time device position simulation
  - Historical track visualization
  - Device status legend
  - Selected device info panel

### Package Updates
- **Added**: `react-map-gl@8.1.0`
- **Added**: `mapbox-gl@3.9.0`

---

## P2 - Ancestry/Genetics Panel

### Route: `/ancestry`

### New Components
- **Added**: `components/ancestry/GraphCanvas.tsx`
  - Cytoscape.js network graph visualization
  - Cola.js force-directed layout
  - Node styling by taxonomic rank
  - Interactive node selection
  - Highlighted path animations

### API Endpoints
- **Added**: `app/api/ancestry/graph/route.ts`
  - Returns graph data (nodes + edges)
  - Supports MINDEX integration (mock for now)
  - Includes specimens and taxonomic relationships

### Page Updates
- **Updated**: `app/ancestry/page.tsx`
  - Added "Graph View" tab
  - Integrated GraphCanvas component
  - MINDEX API data loading
  - Node click handling for taxon selection

### Package Updates
- **Added**: `cytoscape@3.30.x`
- **Added**: `cytoscape-cola@2.5.x`

---

## P2 - Data Pipeline Extensions

### Index Fungorum Integration
- **Added**: `lib/index-fungorum-client.ts`
  - LSID resolution with caching
  - Name search by epithet and genus
  - Current name resolution
  - TypeScript interfaces for IF data

### Provenance Library
- **Added**: `lib/provenance.ts`
  - JSON-LD schema for data provenance
  - PROV-O vocabulary support
  - Schema.org integration
  - Builder functions for common provenance patterns
  - Support for GBIF, iNaturalist, Index Fungorum sources

---

## P2 - ESP32 Oscilloscope Diagnostics

### Firmware Updates
- **Updated**: `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino`

### New Commands
```
scope status              - View scope configuration
scope capture [samples]   - Capture ADC waveform
scope export              - Export waveform as JSON
scope channel <0-7>       - Set ADC channel
scope samples <N>         - Set sample count
scope rate <Hz>           - Set sample rate
scope trigger <mode> <level> - Configure trigger
diag                      - Full system diagnostics
```

### Diagnostic Output
- ESP32 chip info and features
- Memory status (heap, PSRAM)
- WiFi connection details
- Sensor readings
- Task stack watermarks
- GPIO states

---

## P3 - WiFi Sensing (Phase 0)

### Route: `/natureos/wifisense`

### Backend (Python)
- **Added**: `mycosoft_mas/mindex/wifisense/__init__.py`
- **Added**: `mycosoft_mas/mindex/wifisense/models.py`
  - Pydantic models for RSSI readings
  - Zone configuration schema
  - Event models (presence, motion)
  
- **Added**: `mycosoft_mas/mindex/wifisense/processor.py`
  - RSSI-based presence detection
  - Configurable thresholds per zone
  - Event emission for presence/motion changes

### API Endpoints
- **Added**: `app/api/mindex/wifisense/route.ts`
  - GET: Retrieve zone configurations and status
  - POST: Submit RSSI readings for processing
  - Zone management with device assignments

### Frontend
- **Added**: `app/natureos/wifisense/page.tsx`
  - Zone status dashboard
  - Real-time event log
  - Device count and presence indicators
  - Motion detection visualization

---

## Testing Verification

### Routes Tested ✅
- [x] `/dashboard/cinematic` - R3F canvas + HUD overlay
- [x] `/natureos/live-map` - deck.gl map with timeline
- [x] `/ancestry` - Taxonomy tree + Graph view
- [x] `/natureos/wifisense` - WiFiSense dashboard

### API Endpoints Tested ✅
- [x] `/api/ancestry/graph` - Returns graph JSON
- [x] `/api/mindex/wifisense` - Returns zone config

### Configuration Files ✅
- [x] `docker/observability.yml` - Valid compose config
- [x] `prometheus/alerts.yml` - Valid alert rules
- [x] `docker/loki/loki-config.yml` - Loki config
- [x] `docker/promtail/promtail-config.yml` - Promtail config
- [x] `docker/grafana/provisioning/*` - Grafana provisioning

---

## Known Issues

1. **Mapbox Token Required**: The live map requires `NEXT_PUBLIC_MAPBOX_TOKEN` env variable
2. **WebGL in Headless**: Cinematic dashboard 3D rendering may not appear in headless browser testing
3. **Index Fungorum API**: Currently using mock data; real SOAP API integration pending

---

## Files Added/Modified

### New Files (25+)
- `docker/observability.yml`
- `docker/loki/loki-config.yml`
- `docker/promtail/promtail-config.yml`
- `docker/grafana/provisioning/datasources/datasources.yml`
- `docker/grafana/provisioning/dashboards/dashboards.yml`
- `docker/grafana/dashboards/fleet-health.json`
- `prometheus/alerts.yml`
- `components/fx/EffectsRig.tsx`
- `components/widgets/HoloTokens.tsx`
- `components/widgets/HUD.tsx`
- `app/dashboard/cinematic/page.tsx`
- `components/maps/DeviceTrips.tsx`
- `components/maps/TimeScrubber.tsx`
- `app/natureos/live-map/page.tsx`
- `components/ancestry/GraphCanvas.tsx`
- `app/api/ancestry/graph/route.ts`
- `lib/index-fungorum-client.ts`
- `lib/provenance.ts`
- `mycosoft_mas/mindex/wifisense/__init__.py`
- `mycosoft_mas/mindex/wifisense/models.py`
- `mycosoft_mas/mindex/wifisense/processor.py`
- `app/api/mindex/wifisense/route.ts`
- `app/natureos/wifisense/page.tsx`

### Modified Files
- `config/config.yaml` - Loki port update
- `PORT_ASSIGNMENTS.md` - Added Loki port documentation
- `prometheus.yml` - Added device scraping jobs
- `app/ancestry/page.tsx` - MINDEX integration + Graph view
- `firmware/MycoBrain_DeviceManager/MycoBrain_DeviceManager.ino` - Scope commands

---

## Next Steps

1. Configure Mapbox API token in `.env.local`
2. Deploy observability stack: `docker-compose -f docker/observability.yml up -d`
3. Import Grafana dashboards
4. Test firmware scope commands via serial
5. Implement real Index Fungorum SOAP API integration
