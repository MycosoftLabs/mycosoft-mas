# 2026-01-31 Earth-2 and PersonaPlex Integration Report for CREP, FUSARIUM, and Earth Simulator

## Purpose
Define the full integration plan to incorporate NVIDIA Earth-2 and PersonaPlex into:
- CREP dashboard (2D map) within FUSARIUM
- Earth Simulator (3D globe) and related scientific workflows
- The broader Mycosoft platform: NatureOS, Website, Mycosoft-MAS, MINDEX, and MycoBrain

This report is intentionally free of mock data. All integrations must use real datasets,
real device telemetry, and real model outputs with verifiable provenance.

## References (requested sources)
- https://nvidia.com/earth-2
- https://blogs.nvidia.com/blog/nvidia-a100-gpu-automate-particle-physics/
- https://github.com/NVIDIA/earth2studio
- https://huggingface.co/collections/nvidia/earth-2

## Scope and non-negotiables
1. No mock data in any path. Use real data, real model outputs, and real device telemetry.
2. One shared geospatial and time model across CREP and Earth Simulator.
3. Earth-2 model outputs and Earth2Studio pipelines are first-class data sources.
4. PersonaPlex is integrated across CREP, Earth Simulator, and the Mycosoft platform.
5. All layers support provenance, timestamps, and confidence or quality metadata.
6. Production safety: access control, rate limits, and observability on every endpoint.

## Current platform anchors (from existing docs)
- NatureOS is the core simulation and data platform.
- MINDEX is the system of record for events, devices, and observations.
- Existing external sources listed in docs include NOAA, USGS, NASA EONET,
  CelesTrak, OpenSky, AISstream, and fungal databases such as FungiDB,
  iNaturalist, MycoBank, ChemPub, and Science Direct.

## Integration architecture overview
### A. Earth-2 and Earth2Studio integration (core compute)
- Run Earth2Studio pipelines as a first-class compute service with GPU scheduling.
- Persist model outputs into MINDEX with:
  - dataset_id
  - model_id
  - spatial_extent
  - time_range
  - resolution
  - provenance and run metadata
- Expose Earth-2 outputs through NatureOS APIs and streaming channels.

### B. Unified data layer in MINDEX
Create or extend containers (logical domains) for:
- earth2_models
- earth2_forecasts
- earth2_assimilation
- geospatial_tiles
- device_tracks
- spore_tracks
- environmental_events
- aircraft_tracks
- vessel_tracks
- satellite_tracks
- flora_fauna_funga_events

Every record must include:
- geometry (point, line, polygon, or raster reference)
- timestamp or time_range
- source_system
- quality or confidence metadata

### C. CREP (2D map) integration
CREP must render a single, consistent layer stack:
- Earth-2 forecasts and nowcasts
- Spore tracking and dispersion modeling
- Device tracking (MycoBrain, Mushroom 1, spore detectors, stations)
- Environmental events (weather, seismic, wildfire, air quality)
- Airplanes, boats, and satellites
- Flora, fauna, and funga occurrences and events

Core UX requirements:
- time slider with cross-layer synchronization
- filter by source_system, model_id, and confidence
- layer groups and layer presets for workflows
- drill-down to raw dataset provenance and MINDEX record detail

### D. Earth Simulator (3D globe) integration
Earth Simulator must display the same datasets as CREP with 3D context:
- Cesium/OpenUSD visualization stack for volumetric and surface layers
- Earth-2 gridded outputs and volumetric fields
- Multi-scale tiling for performance with time-sliced assets
- Shared map styling and legend definitions with CREP

### E. PersonaPlex integration (full duplex)
PersonaPlex must be the conversational and control plane across:
- CREP dashboard (map and data commands)
- Earth Simulator (3D navigation, model queries, and playback)
- Website and Mycosoft services (system-level queries and actions)

Capabilities required:
- full-duplex streaming of prompts and responses
- tool calls for Earth-2 model runs and dataset fetch
- secure execution with audit trails
- shared memory of user sessions and prior runs

## Cross-repo integration responsibilities
### NatureOS (this repo)
- Earth2Studio orchestration service integration
- New MINDEX schemas for Earth-2 model outputs and tracks
- APIs and real-time streams for CREP and Earth Simulator
- Provenance, audit logging, and data quality gates

### Website repo
- CREP dashboard map layers and UX
- PersonaPlex UI integration and voice controls
- Cross-layer filtering and time controls

### Mycosoft-MAS
- Workflow orchestration for model runs and data ingestion
- PersonaPlex tool registry and safety policies
- Task scheduling for Earth-2 compute and refresh cycles

### MINDEX
- Container definitions and indexing strategy
- Geospatial and time-series optimization
- Access patterns for high volume raster and vector layers

### MycoBrain
- Device and spore detector telemetry as real data sources
- Track aggregation and quality scoring
- Bidirectional control via PersonaPlex where appropriate

## Data ingestion and provenance requirements
1. Each dataset must include provenance fields: source, access method, and run context.
2. All ingestion jobs must write a data quality score and validation status.
3. All events must be timestamped in a consistent UTC format.
4. All geospatial data must include a declared coordinate reference system.

## Earth-2 feature coverage checklist
The integration must expose Earth-2 features through both CREP and Earth Simulator:
- Earth-2 open model family outputs
- Earth2Studio pipeline outputs
- Model run metadata, versioning, and reproducibility
- Visualization of gridded and volumetric fields
- Real-time or near-real-time updates as supported by available datasets

## Implementation plan (phased)
### Phase 1: Foundation and data contracts
- Confirm Earth-2 access and licensing terms
- Define MINDEX schemas for Earth-2 outputs and tracks
- Implement ingestion services with provenance and validation
- Establish shared map layer definitions for CREP and Earth Simulator

### Phase 2: CREP map integration
- Add Earth-2 layers and timeline controls
- Integrate spore and device tracking overlays
- Cross-filtering and drill-down to provenance
- PersonaPlex actions for layer control and model queries

### Phase 3: Earth Simulator integration
- Add Earth-2 layers to 3D globe
- Implement volumetric and time-sliced rendering
- Synchronize time controls with CREP
- PersonaPlex navigation and model interrogation

### Phase 4: Platform-wide PersonaPlex
- Integrate PersonaPlex into website, Earth Simulator, and CREP
- Tooling to trigger Earth-2 runs and fetch outputs
- Session memory and audit trail integration

## Definition of done
- CREP and Earth Simulator both render Earth-2 layers using real data
- Shared layer catalog and time controls are consistent across products
- PersonaPlex can query and control Earth-2 data and visualizations
- All data in MINDEX includes provenance and quality metadata
- No mock data exists in any newly added integration surface

## Open inputs required
To proceed with implementation, confirm:
- Earth-2 model selection and Earth2Studio deployment targets
- PersonaPlex API and tool schema details
- GPU compute environment and scheduling constraints
- Data source access credentials for all live feeds
