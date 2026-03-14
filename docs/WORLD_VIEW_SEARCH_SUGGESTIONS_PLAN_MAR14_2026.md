# World View Search Suggestions and MINDEX/SEARCH/MYCA/NATUREOS Cohesion Plan

**Date**: March 14, 2026  
**Status**: Draft  
**Author**: MYCA  

## Overview

Shift Mycosoft from fungi-focused search and marketing to a **full world view platform** serving humans, AI agents, bots, and machines. Search suggestions, placeholders, and data must cover all nature (fungi, flora, fauna), environment, weather, human movements, machines, vehicles, planes, satellites, boats, ports, dams, rivers, freeways—anything needed for holistic spatio-temporal awareness of Earth.

**Primary customers**: Agents and bots; secondary: humans seeking world view.

---

## Vision: World View for All

| Audience | Why They Need Mycosoft |
|----------|------------------------|
| **Humans** | Know what's happening on Earth: weather, species, natural events, human/machine activity |
| **AI agents** | Grounded real-time data for reasoning, planning, and tool use |
| **Bots** | Environmental and operational awareness for autonomous decisions |
| **Machines** | Sensor fusion, telemetry, and cross-system coordination |

**World view** = spatial + temporal + global awareness of:
- **Nature**: Fungi, flora, fauna, biodiversity, natural events
- **Environment**: Weather, climate, Earth2 simulations, MODIS/EONET
- **Human activity**: Movements, traffic, ports, freeways, dams
- **Machine activity**: Planes, ships, satellites, vehicles, IoT devices
- **Signals**: CREP (Common Relevant Environmental Picture), telemetry, sensor data

---

## Current State

### Homepage Search (hero-search.tsx)

| Component | Current (Fungi-Focused) | Location |
|-----------|-------------------------|----------|
| **Try: buttons** | Amanita, Psilocybin, Mycelium, ITS Sequence, Reishi, Muscarine | `components/home/hero-search.tsx` L346-352 |
| **Fallback placeholder** | "Search fungi, compounds..." | L236 |
| **Typing placeholder** | DEFAULT_SUGGESTIONS: fungi, compounds, genetics, mycelium, etc. | `hooks/use-typing-placeholder.ts` L14-26 |

### Search Flow

- Homepage search → `/search?q={query}` → FluidSearchCanvas (tablet+) or MobileSearchChat (mobile)
- Fluid search widgets: Species, Chemistry, Genetics, Research, Answers, Media, Location, News, Map, **Crep**, **Earth2**
- CREP widget: planes, ships, satellites, weather
- Earth2 widget: climate/weather simulation
- MYCA suggestions: dynamic from MAS intention API (can be fungal-biased in backend)

### MINDEX Data Today

- Species, compounds, genetics, research, observations
- MycoBrain telemetry, WiFi sense, drone
- CREP fungal observations route
- Earth2 integration (planned/partial)

### Gaps

1. **Suggestions** are fungal-only; no rotation; no world-view coverage
2. **Placeholders** reinforce fungi; no agent/bot/machine framing
3. **MINDEX** does not yet ingest: aviation, maritime, satellite, human movement, machine/vehicle data at scale
4. **CREP** has fungal route; broader CREP (planes, ships, satellites) exists but search suggestions don't surface it
5. **Marketing/copy** across search and home is fungi-first; needs world-view framing

---

## Plan: Phases and Tasks

### Phase 1: Rotating Try: Suggestions (Website — Quick Win)

**Goal**: Replace static fungal suggestions with rotating, world-view suggestions.

**Tasks**:

1. **Create shared suggestion constants** (`lib/search/world-view-suggestions.ts`)
   - Define categories: fungi, flora, fauna, weather, CREP (planes/ships/sats), Earth2, environment, human/machine activity
   - Example terms:
     - Fungi: Amanita, Psilocybin, Mycelium, Reishi
     - Flora: Oak, Fern, Lichen
     - Fauna: Butterfly, Bird migration
     - Weather: Pacific storm, Temperature anomaly
     - CREP: Flights over Pacific, Ships in port, Satellite passes
     - Earth2: Climate forecast, Hurricane track
     - Environment: River levels, Dam status
     - Human/machine: Freeway congestion, Port activity

2. **Implement rotation logic**
   - Client-side: on mount, pick N random suggestions from full pool (e.g. 6 visible, 3 on mobile)
   - Option: time-based rotation (change every 30s) for variety
   - Ensure at least one from each major category per rotation cycle

3. **Update hero-search.tsx**
   - Import from `lib/search/world-view-suggestions`
   - Replace hardcoded array with rotated suggestions
   - Keep `phoneVisible` logic for responsive display

**Files**: `components/home/hero-search.tsx`, `lib/search/world-view-suggestions.ts` (new)

---

### Phase 2: Typing Placeholder and Fallback (Website)

**Goal**: Expand typing placeholder and fallback to world-view framing.

**Tasks**:

1. **Update `use-typing-placeholder.ts` DEFAULT_SUGGESTIONS**
   - Replace fungal-only with world-view examples:
     - "Search species, compounds, weather..."
     - "Planes over Pacific, ships in port..."
     - "Earth2 climate, CREP live data..."
     - "What's happening on Earth right now?"
     - "Flights, vessels, satellites..."
     - "Species, environment, machines..."
     - (Keep 2–3 fungal examples for continuity)

2. **Update hero-search fallback placeholder**
   - Change "Search fungi, compounds..." → "Search nature, environment, live data..."

**Files**: `hooks/use-typing-placeholder.ts`, `components/home/hero-search.tsx`

---

### Phase 3: Search Integration Verification (Website)

**Goal**: Confirm homepage search → `/search?q=` → FluidSearchCanvas works for all suggestion types.

**Tasks**:

1. **Verify fluid widgets handle diverse queries**
   - CREP widget: aviation, maritime, satellite queries
   - Earth2 widget: weather, climate queries
   - Species/Chemistry/Genetics: biodiversity queries
   - Ensure no fungal-only routing; all widgets receive query and can show empty/loading states

2. **MycaSuggestionsWidget tip**
   - Change "try searching a species name" → "try species, weather, flights, or environment"

**Files**: `components/search/fluid/widgets/MycaSuggestionsWidget.tsx`, FluidSearchCanvas (audit)

---

### Phase 4: MINDEX Expansion (MINDEX Repo — Larger Scope)

**Goal**: Ingest data from all available points for holistic world view.

**Tasks** (high-level; detailed in separate MINDEX plan):

1. **CREP integration**
   - Aviation (flights), maritime (vessels), satellite data
   - ETL or API bridge from CREP collectors to MINDEX

2. **Earth2 / weather**
   - Climate simulation, weather forecasts, anomalies

3. **Human/machine activity**
   - Ports, dams, rivers, freeways (where data sources exist)
   - NatureOS device telemetry (already partial)

4. **Schema and API**
   - Extend MINDEX schema for non-biodiversity entities
   - Unified search endpoint that spans all domains

**Dependencies**: CREP collectors, Earth2 API, external data sources (e.g. AIS, ADS-B, OpenStreetMap)

---

### Phase 5: MYCA Intention API and Suggestive Search (MAS Repo)

**Goal**: MYCA suggestions (widgets, queries) reflect world-view, not fungi-only.

**Tasks**:

1. **Audit MAS intention/suggestion endpoints**
   - Identify where suggested queries and widgets are generated

2. **Expand suggestion prompts and logic**
   - Include CREP, Earth2, environment, human/machine in suggestion generation

3. **Agent/bot framing**
   - Ensure API responses explain why agents would use each suggestion

---

### Phase 6: NATUREOS Cohesion (NatureOS Repo)

**Goal**: NatureOS device/sensor data flows into MINDEX and is searchable.

**Tasks**:

1. **Confirm NatureOS → MINDEX pipeline**
   - Telemetry, sensor readings, device events

2. **Search suggestions**
   - "Device telemetry", "Sensor readings", "MycoBrain data"

---

## Implementation Order

| Phase | Scope | Effort | Dependency |
|-------|-------|--------|------------|
| **1** | Rotating Try: suggestions | 1–2 hours | None |
| **2** | Typing placeholder + fallback | ~30 min | None |
| **3** | Search integration verification | ~1 hour | None |
| **4** | MINDEX expansion | Days–weeks | CREP, Earth2, data sources |
| **5** | MYCA suggestion expansion | 2–4 hours | Phase 1–2 done |
| **6** | NATUREOS cohesion | 2–4 hours | MINDEX schema/API |

**Recommended first implementation**: Phases 1, 2, 3 (all Website repo, no backend changes).

---

## Suggestion Categories for Try: Buttons (Draft)

| Category | Example Terms |
|----------|---------------|
| Fungi | Amanita, Psilocybin, Mycelium, Reishi |
| Flora | Oak, Fern, Lichen |
| Fauna | Butterfly, Bird migration |
| Weather | Pacific storm, Temperature anomaly |
| CREP Aviation | Flights over Pacific |
| CREP Maritime | Ships in port |
| CREP Satellite | Satellite passes |
| Earth2 | Climate forecast, Hurricane track |
| Environment | River levels, Dam status |
| Human/Machine | Freeway congestion, Port activity |
| Agent use | What planes are over LA? |
| Agent use | Weather along shipping lane |

---

## Acceptance Criteria

- [ ] Try: buttons show rotating world-view suggestions (not just fungal)
- [ ] Typing placeholder cycles through nature, environment, CREP, Earth2, agent-use examples
- [ ] Fallback placeholder is "Search nature, environment, live data..." (or equivalent)
- [ ] Clicking any Try: suggestion routes to `/search?q=` and FluidSearchCanvas handles it
- [ ] MycaSuggestionsWidget tip reflects world-view
- [ ] Clear path documented for Phases 4–6 (MINDEX, MYCA, NATUREOS)

---

## Related Documents

- [CREP Integration Test Plan](../WEBSITE/website/docs/CREP_INTEGRATION_TEST_PLAN_MAR10_2026.md)
- [CREP Fungal Route Reliability](../WEBSITE/website/docs/CREP_FUNGAL_ROUTE_RELIABILITY_MAR11_2026.md)
- [Request Flow Architecture](./REQUEST_FLOW_ARCHITECTURE_MAR05_2026.md)
- [VM Layout and Dev Remote Services](./VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md)
