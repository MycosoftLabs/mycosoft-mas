# GPU Enrichment Strategy — March 14, 2026

**Status:** Approved (implementation reference)  
**Related:** `worldview_search_expansion_bcd26107.plan.md` Phase 7 (Phase 9 in plan workstreams)

---

## 1. Objective

Use existing GPU capacity (Earth2, PhysicsNeMo, PersonaPlex) for high-value world modeling now instead of waiting for more hardware. Define what each GPU service consumes from the worldstate and source backlog, and establish a staging plan that prefers lightweight workloads first.

---

## 2. Earth2 — Input Backlog and Ownership

Earth2 provides climate/weather simulation and prediction. It runs at `http://localhost:8220` and is proxied via MAS.

### 2.1 First-Priority Inputs (from P0/P1/P2 source backlog)

| Source | Domain | Use For |
|--------|--------|---------|
| **Open-Meteo** | Forecast, marine, air quality | Operational nowcast and short-horizon context seeding |
| **NOAA NWS** | Weather, alerts, hazards | US regional ground truth and alert overlays |
| **ERA5** (Copernicus CDS) | Reanalysis baseline | Training/comparison context, historical calibration |
| **GFS/GEFS** (NOAA NOMADS) | Forecast fields | Comparative forecasting, Earth2 vs operational model |
| **HRRR** (where appropriate) | High-res US forecast | Regional refinement when US focus |
| **Copernicus EO / Sentinel Hub** | EO imagery, STAC | Map analysis, event verification, Earth2 visual context |
| **NASA FIRMS** | Wildfire hotspots | Hazard event overlays, Earth2 event context |
| **IBTrACS** | Tropical cyclone tracks | Storm intelligence and simulation validation |

### 2.2 Integration Path

- Earth2 currently receives weather context via `earth2_bridge.get_weather_context()` and `WorldModel.predictions`.
- **Next step:** Feed worldstate summary (`/api/myca/world/summary`) and region (`/api/myca/world/region`) into Earth2 inference so it seeds from canonical worldstate rather than ad hoc bridge calls.
- **Owner:** earth2-ops; Earth2 inference server and MAS Earth2 proxy.

### 2.3 Staging

1. **Now:** Open-Meteo + NOAA NWS via existing EarthLIVE/CREP collectors.
2. **Next:** FIRMS overlays (already onboarded); IBTrACS for storm validation.
3. **Later:** ERA5, GFS, Copernicus EO when CDS/NOMADS adapters are built.

---

## 3. PhysicsNeMo — Input Backlog and Ownership

PhysicsNeMo provides physics simulation (fluid, heat, diffusion, reaction). It runs at `http://localhost:8400` and is proxied via `/api/physics/*`.

### 3.1 First-Priority Inputs

| Source | Domain | Use For |
|--------|--------|---------|
| **Environmental field normalization** | From CREP, NOAA, USGS, Open-Meteo | Temperature, pressure, humidity, streamflow as boundary conditions |
| **Forecast comparison** | GFS vs Earth2 vs Open-Meteo | Anomaly detection, model drift analysis |
| **Hydrology** | USGS NWIS, NOAA CO-OPS | Streamflow, tides, water levels as fluid/heat inputs |
| **Storm modeling** | EONET, IBTrACS, NOAA NWS | Hazard events as initial conditions for fluid/heat transfer |

### 3.2 Integration Path

- PhysicsNeMo today is called on-demand by simulation agents (petri dish, compound, growth, mycelium).
- **Next step:** Pass `WorldState` environmental slots (weather, water levels, hazards) as structured inputs to `/physics/simulate` and `/physics/fluid` so physics runs are grounded in real-world context.
- **Owner:** scientific-systems; PhysicsNeMo API and simulation agents.

### 3.3 Staging

1. **Now:** Use existing CREP/weather context from `WorldModel` when simulation agents invoke PhysicsNeMo.
2. **Next:** Add USGS water and NOAA CO-OPS as optional boundary inputs for hydrology-aware simulations.
3. **Later:** Forecast comparison and anomaly detection once GFS/ERA5 adapters exist.

---

## 4. PersonaPlex — Worldstate Context Envelope

PersonaPlex (Moshi voice, Bridge) provides MYCA voice. It should consume a defined worldstate context envelope instead of ad hoc prompt text.

### 4.1 Context Envelope (from WorldState / ExperiencePacket)

| Slot | Source | Max Tokens | Purpose |
|------|--------|------------|---------|
| **Hazard summaries** | EONET, FIRMS, USGS quakes, NOAA NWS | 200 | "Active fires, earthquakes, storms" |
| **Regional environmental** | Open-Meteo, NOAA CO-OPS, USGS water | 150 | "Weather, tides, streamflow" |
| **Moving-entity summaries** | CREP (flights, vessels, satellites) | 150 | "Flights over Pacific, vessels in port" |
| **Infrastructure and device alerts** | MycoBrain, presence | 100 | "Devices online, pending alerts" |

### 4.2 Integration Path

- PersonaPlex currently receives context from `llm_brain._build_live_context()` which calls CREP, Earth2, MycoBrain, etc. directly.
- **Next step:** Replace ad hoc bridge fan-out with a single call to `/api/myca/world/summary` (or `WorldModel.get_cached_context()`) and format the result into PersonaPlex's context window using the envelope above.
- **Owner:** myca-voice, voice-engineer; PersonaPlex bridge and llm_brain.

### 4.3 Staging

1. **Now:** Ensure `get_cached_context()` includes hazards, environment, moving entities, devices.
2. **Next:** Add a `format_for_voice_context()` helper that produces a compact, token-bounded string from WorldState.
3. **Later:** Feed ExperiencePacket-derived context when EP becomes primary grounding object.

---

## 5. Staging Plan — Lightweight First

| Phase | Workload | GPU | Priority |
|-------|----------|-----|----------|
| 1 | Summarization of worldstate for PersonaPlex context | None (CPU) | Now |
| 2 | Earth2 inference with Open-Meteo/NOAA seeding | Earth2 | Now |
| 3 | PhysicsNeMo with CREP/weather boundary conditions | PhysicsNeMo | Next |
| 4 | FIRMS/IBTrACS overlays for Earth2 | Earth2 | Next |
| 5 | USGS/NOAA CO-OPS as PhysicsNeMo inputs | PhysicsNeMo | Later |
| 6 | ERA5, GFS, Copernicus EO for Earth2 | Earth2 | Later |
| 7 | Multimodal fusion (EO + forecast + hazard) | Earth2 + PhysicsNeMo | After core pipelines stable |

### 5.1 Resource Guardrails

- **PersonaPlex + Earth2 + PhysicsNeMo** together can exceed VRAM. Prefer: Earth2 + PhysicsNeMo when doing simulation; PersonaPlex + Earth2 when doing voice.
- See `PHYSICSNEMO_INTEGRATION_FEB09_2026.md`: "PersonaPlex voice should remain off in that mode if VRAM pressure rises."

---

## 6. Source Prioritization Rules for GPU-Backed Enrichments

1. **Operational nowcast and short-horizon first** — Open-Meteo, NOAA NWS, CREP, FIRMS.
2. **Historical reanalysis second** — ERA5 when needed for calibration.
3. **Heavier multimodal fusion after core pipelines are stable** — Copernicus EO, GFS fields, IBTrACS.

---

## 7. Verification Checklist

- [ ] Earth2 and PhysicsNeMo have a concrete input backlog and owner list. (This document.)
- [ ] PersonaPlex has a defined worldstate context envelope rather than ad hoc prompt text. (Section 4.)
- [ ] Staging plan prefers lightweight inference first. (Section 5.)
- [ ] Source prioritization rules are documented. (Section 6.)

---

## 8. Related Documents

- `GROUNDING_ARCHITECTURE_LOCKED_MAR14_2026.md` — Packet path, WorldModel, llm_brain
- `PHYSICSNEMO_INTEGRATION_FEB09_2026.md` — PhysicsNeMo API, MAS proxy, VRAM notes
- `worldview_search_expansion_bcd26107.plan.md` — Phase 6 source backlog, Phase 7/9 GPU strategy
