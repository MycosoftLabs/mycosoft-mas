# Mycosoft Superapp Architecture and Unification Plan

**Date:** February 19, 2026
**Status:** Active Plan — Ready for Implementation
**Author:** Superapp Architect Agent
**Related:** MASTER_DOCUMENT_INDEX.md, SYSTEM_REGISTRY_FEB04_2026.md, NATUREOS_FULL_PLATFORM_COMPLETE_FEB19_2026.md

---

## Executive Summary

The Mycosoft platform has organically grown into 50+ app directories, 60+ component namespaces, 200+ API endpoints, and 100+ AI agents — but the user experiences them as disconnected islands. A user studying fungi must jump between `/search`, `/scientific/lab`, `/natureos/fungi-compute`, `/devices`, and `/test-voice` to accomplish work that should be one coherent flow. This document identifies the highest-impact unification opportunities, proposes a unified superapp architecture, and provides a concrete implementation plan.

**The single organizing principle:** One shell. One search. One MYCA. One data stream.

---

## Surface Inventory

### Website App Directories (50 total)

| Area | Directories |
|------|------------|
| **Main apps** | `natureos/`, `search/`, `scientific/`, `devices/`, `devices2/`, `defense/`, `defense2/` |
| **AI/MYCA** | `myca/`, `myca-ai/`, `test-voice/` |
| **Data** | `mindex/`, `species/`, `compounds/`, `papers/`, `mushrooms/`, `ancestry/`, `ancestry-db/` |
| **Commerce/profile** | `billing/`, `orders/`, `shop/`, `profile/`, `settings/`, `pricing/` |
| **Auth/onboarding** | `auth/`, `login/`, `signup/`, `onboarding/` |
| **Info pages** | `about/`, `contact/`, `careers/`, `support/`, `terms/`, `privacy/`, `docs/` |
| **Dev/test** | `dev/`, `test-fluid-search/`, `ui/`, `preview/`, `admin/` |
| **Platform/apps** | `apps/`, `platform/`, `protocols/`, `capabilities/`, `dashboard/`, `(dashboard)/` |
| **Security** | `security/` |

### NatureOS Sub-Apps (27 sub-directories)

`ai-studio`, `api`, `biotech`, `cloud`, `containers`, `data-explorer`, `devices`, `drone`, `functions`, `fungi-compute`, `genetics`, `integrations`, `lab-tools`, `live-map`, `mas`, `mindex`, `model-training`, `monitoring`, `reports`, `sdk`, `settings`, `shell`, `smell-training`, `storage`, `wifisense`, `workflows`, `[...slug]`

### Scientific Sub-Apps (7)

`3d`, `autonomous`, `bio`, `bio-compute`, `experiments`, `lab`, `memory`, `simulation`

### Component Namespaces (45 total)

`3d`, `access`, `ai`, `analytics`, `ancestry`, `apps`, `autonomous`, `bio-compute`, `chat`, `compounds`, `contact`, `crep`, `dashboard`, `defense`, `devices`, `devices2`, `earth2`, `earth-simulator`, `effects`, `fungi-compute`, `fx`, `home`, `maps`, `mas`, `memory`, `mindex`, `mushrooms`, `mycobrain`, `natureos`, `oei`, `onboarding`, `performance`, `platform`, `realtime`, `scientific`, `search`, `security`, `species`, `support`, `templates`, `three`, `ui`, `visualizations`, `voice`, `widgets`

### Key Observations (Pre-Analysis)

- **Duplicate page directories:** `devices/` + `devices2/`, `defense/` + `defense2/`, `myca/` + `myca-ai/`, `dashboard/` + `(dashboard)/`
- **Overlapping scopes:** `scientific/*` and `natureos/*` both have fungi-compute, lab, devices, mindex
- **Isolated AI access:** MYCA accessible only from `/test-voice` and a floating chat widget — not in NatureOS, search, device manager, or scientific tools
- **Real-time data silos:** MycoBrain telemetry, FCI signals, CREP live feeds, NatureOS sensor streams — all separate, no shared WebSocket layer
- **No unified navigation shell:** Each major section (NatureOS, Defense, Scientific, Search, Devices) has independent nav

---

## 1. Unification Opportunities (Sorted by Impact × Feasibility)

---

### UNI-01: Unified Navigation Shell

**Category:** Navigation
**Current state:** Each major section — NatureOS, Defense, Scientific, Search, Devices, CREP — has its own independent navigation with no shared context or cross-links. A user in `/natureos/lab-tools` has no visible path to `/search` or `/devices` without using the browser back button or the top-level homepage nav.
**Proposed:** A single persistent top-level shell nav with:
- Primary tabs: Home | NatureOS | Search | Devices | Science | Defense | MYCA
- Secondary context nav that adapts per section (e.g., NatureOS shows AI Studio, Data Explorer, Lab Tools sub-nav)
- Shared user profile, notification bell, and MYCA chat trigger always visible
- Mobile: collapsible hamburger menu with full section access
**User benefit:** Users can navigate the entire platform from anywhere without losing context. Cross-section workflows become natural (e.g., search a species → open in NatureOS → query MYCA).
**Impact:** High
**Effort:** 1–2 Weeks
**Files/systems involved:**
- `components/layouts/` (new: `SuperappShell.tsx`)
- `app/layout.tsx` (root layout update)
- All section `layout.tsx` files to inherit shell
- `components/ui/neuromorphic/` (apply neuromorphic styling)
**Owner agent:** `website-dev` + `mobile-engineer`
**First step:** Create `components/layouts/SuperappShell.tsx` with responsive top nav and section tabs; wire into `app/layout.tsx`

---

### UNI-02: Persistent MYCA Assistant Panel (Global)

**Category:** AI Access
**Current state:** MYCA (chat, voice, brain) is accessible only from `/test-voice` (full page) and a floating chat widget that may not be present on all pages. Users on the NatureOS dashboard, scientific tools, device manager, or CREP cannot ask MYCA a question without navigating away from their work.
**Proposed:** A globally persistent MYCA side panel (right-side collapsible drawer) available on every page:
- Triggered by a MYCA button in the unified nav shell
- Shows recent context (current page, active device, last search query) so MYCA answers in context
- Supports voice (push-to-talk) and text input
- Shows MYCA's response with links to relevant pages/data
- Collapsed by default; expands to 360px on click; full-screen voice mode on mic press
**User benefit:** MYCA becomes a universal co-pilot — ask about a species while viewing its page, query device telemetry while in device manager, get explanations of CREP data in context.
**Impact:** High
**Effort:** 1–2 Weeks
**Files/systems involved:**
- `components/chat/` → new `MYCAGlobalPanel.tsx`
- `components/voice/` → integrate PersonaPlex bridge connection
- `app/layout.tsx` → mount panel globally
- `lib/myca/` → context-awareness module (send current route + visible data as system context)
- MAS: `/api/myca/chat` endpoint (already exists)
**Owner agent:** `myca-voice` + `website-dev`
**First step:** Create `components/chat/MYCAGlobalPanel.tsx` as a right-side drawer; mount in `app/layout.tsx`; wire to `/api/myca/chat`; default collapsed

---

### UNI-03: Universal Search as Superapp Entry Point

**Category:** Search
**Current state:** `/search` (Fluid Search) exists as an isolated page. The NatureOS dashboard has its own MINDEX explorer. Devices, papers, CREP data, and agents are not searchable from one place. Users must know which sub-system to go to for what kind of query.
**Proposed:** Elevate Fluid Search to be the universal entry point and search command palette for the entire platform:
- Accessible via `Cmd+K` / `Ctrl+K` from any page (command palette style)
- Search scope toggles: All | Species | Compounds | Research | Devices | CREP | Agents | Documents
- Results link directly to the relevant page (species → `/species/[id]`, device → `/devices/[id]`, agent → triggers agent in MYCA panel)
- Recent and saved searches persist per user
- Inline MYCA answer for natural-language queries
**User benefit:** One input box replaces navigating 6 different sections. Power users can trigger any workflow from the keyboard.
**Impact:** High
**Effort:** 2–3 Weeks
**Files/systems involved:**
- `components/search/` → new `CommandPalette.tsx`
- `app/search/page.tsx` (extend existing)
- `lib/search/` (multi-scope search client)
- MAS: `/api/search/*`, `/api/myca/chat`
- MINDEX: `/api/taxonomy/*`, `/api/compounds/*`, `/api/papers/*`
**Owner agent:** `search-engineer` + `website-dev`
**First step:** Build `components/search/CommandPalette.tsx` with `Cmd+K` trigger; implement multi-scope toggle with MINDEX + device registry search

---

### UNI-04: Merge devices/ + devices2/ + natureos/devices

**Category:** Navigation / Components
**Current state:** Three separate device UIs exist:
- `app/devices/` — main Device Manager
- `app/devices2/` — appears to be a rebuild/redesign experiment
- `app/natureos/devices/` — NatureOS's own device view
All three pull from the same MAS Device Registry and MycoBrain service but present the data differently and are independently maintained.
**Proposed:** Consolidate into a single `app/devices/` with:
- NatureOS-style rich dashboard view (telemetry, charts, firmware status)
- Simple list/card view for quick access
- MycoBrain FCI signal panel embedded per device
- Reuse `components/devices/` shared components for all views
- Delete `devices2/` and remove the NatureOS duplicate, linking from NatureOS nav to `/devices`
**User benefit:** One canonical place to see and manage all devices. No confusion about which device view is "real."
**Impact:** High
**Effort:** 1 Week
**Files/systems involved:**
- `app/devices/` (keep and enhance)
- `app/devices2/` (delete after migration)
- `app/natureos/devices/` (redirect to `/devices` + link from NatureOS nav)
- `components/devices/` (shared components already exist)
- `components/mycobrain/` (FCI widgets)
**Owner agent:** `website-dev` + `device-firmware`
**First step:** Audit which features exist only in `devices2/` that are missing from `devices/`; migrate those features; add redirect from `devices2` to `devices`

---

### UNI-05: Merge defense/ + defense2/

**Category:** Navigation
**Current state:** Two defense pages exist: `app/defense/` (the original) and `app/defense2/` (the neuromorphic redesign referenced in docs). The neuromorphic update (`DEFENSE_NEUROMORPHIC_UPDATE_FEB18_2026.md`) was implemented in defense2 and is superior, but both pages still exist and users may land on the old one.
**Proposed:** Promote `defense2/` as the canonical `/defense` and delete the old one. Ensure all routes and links point to the unified neuromorphic version.
**User benefit:** Single, authoritative defense portal. No confusion about old vs new.
**Impact:** Medium
**Effort:** 1–2 Days
**Files/systems involved:**
- `app/defense/` → audit and delete or redirect to defense2
- `app/defense2/` → rename to `defense/` (or update routing)
- Any internal links pointing to old `/defense`
**Owner agent:** `website-dev`
**First step:** Run `rg "/defense" app/ --include="*.tsx"` to find all links; update to point to defense2; redirect old route; delete old files

---

### UNI-06: Merge myca/ + myca-ai/ + test-voice/ into MYCA Hub

**Category:** AI Access
**Current state:** Three MYCA surfaces:
- `app/myca/` — unclear scope, possibly the MYCA main page
- `app/myca-ai/` — an AI interface variant
- `app/test-voice/` — voice testing page (PersonaPlex/Moshi)
These are not cross-linked and serve overlapping purposes (interact with MYCA).
**Proposed:** Unify into a single `/myca` hub with tabbed interface:
- Tab 1: Chat (text + MYCA Brain)
- Tab 2: Voice (full PersonaPlex/Moshi interface, currently at /test-voice)
- Tab 3: Agent Studio (list of MAS agents, trigger them, see results)
- Tab 4: Memory (MYCA's knowledge about the user)
- Tab 5: Skills (what MYCA can do, with examples)
Keep `/test-voice` as an alias/redirect to `/myca?tab=voice` for backward compatibility.
**User benefit:** One place to interact with MYCA in all modalities. Discoverable capabilities.
**Impact:** High
**Effort:** 1–2 Weeks
**Files/systems involved:**
- `app/myca/` (restructure as hub)
- `app/myca-ai/` (merge into hub, delete)
- `app/test-voice/` (redirect to `/myca?tab=voice`)
- `components/voice/`, `components/chat/`, `components/mas/`
- MAS: `/api/myca/*`, `/api/agents/*`, `/api/workflows/*`
**Owner agent:** `myca-voice` + `website-dev`
**First step:** Design tab structure for `/myca` hub; move voice interface from `/test-voice` into `/myca` as a tab

---

### UNI-07: Unified Real-Time Device and Sensor Data Layer (WebSocket)

**Category:** Devices / Real-Time Data
**Current state:** Real-time data is siloed:
- MycoBrain telemetry: polled per page, not streamed
- FCI signals: streamed only in `/natureos/fungi-compute`
- CREP live data: rendered in CREP components independently
- NatureOS sensor streams: SignalR hub, not connected to website
- Redis pub/sub exists (4 channels: devices, agents, experiments, CREP) but is not wired to front-end
**Proposed:** A shared `RealTimeDataContext` (React context) that:
- Maintains a single WebSocket/SSE connection per session via `/api/realtime/stream`
- Subscribes to relevant channels based on current page (devices → `devices:telemetry`, CREP page → `crep:live`)
- Distributes updates to any component via `useRealTimeData(channel)` hook
- Reconnects automatically
- Any page can subscribe without managing its own connection
**User benefit:** Live telemetry everywhere without per-page implementation. Device status badges update in real-time on any page. CREP data streams without polling.
**Impact:** High
**Effort:** 2–3 Weeks
**Files/systems involved:**
- New: `lib/realtime/RealTimeContext.tsx`
- New: `hooks/useRealTimeData.ts`
- New: `app/api/realtime/stream/route.ts` (SSE endpoint bridging Redis pub/sub)
- `components/devices/` (add live badge via hook)
- `components/crep/` (remove polling, use hook)
- MAS: Redis pub/sub already implemented (`mycosoft_mas/realtime/redis_pubsub.py`)
**Owner agent:** `websocket-engineer` + `backend-dev`
**First step:** Create `app/api/realtime/stream/route.ts` SSE endpoint that subscribes to Redis channels and streams events to the browser; test with `useRealTimeData('devices:telemetry')` in device card

---

### UNI-08: Consolidate scientific/* and natureos/* Overlap

**Category:** Navigation / Data
**Current state:** `app/scientific/` and `app/natureos/` have significant overlap:
- `scientific/lab` + `natureos/lab-tools` — both are lab management views
- `scientific/bio` + `natureos/biotech` — biological data views
- `scientific/bio-compute` + `natureos/fungi-compute` — biological computing
- `scientific/memory` + `natureos/mindex` — MINDEX/memory access
- `scientific/experiments` — no clear NatureOS equivalent
The scientific apps appear to be earlier prototypes; NatureOS apps appear to be the intended evolution.
**Proposed:** 
- Migrate any unique features from `scientific/*` into the corresponding `natureos/*` apps
- Keep `app/scientific/` as a redirect hub that routes to the canonical NatureOS equivalents
- The `/scientific` landing page becomes a "Science Suite" overview that links to NatureOS tools
- Delete duplicated components; use `components/scientific/` only where NatureOS hasn't replaced them
**User benefit:** Users discover one set of scientific tools (NatureOS), not two half-implemented sets. Maintenance is halved.
**Impact:** High
**Effort:** 2–3 Weeks
**Files/systems involved:**
- `app/scientific/*` → audit each sub-page for unique content
- `app/natureos/*` → target destination
- `components/scientific/` vs `components/natureos/`
**Owner agent:** `website-dev` + `scientific-systems`
**First step:** Create a feature matrix: for each `scientific/` sub-page, document which `natureos/` sub-page covers the same features; redirect the exact duplicates immediately

---

### UNI-09: Agent Studio / Tool Invocation Surface

**Category:** Agents / Discoverability
**Current state:** 100+ MAS agents exist and are accessible via MAS API (`/api/agents/*`), but are invisible to website users. There is no UI for discovering, triggering, or monitoring agent tasks. Users cannot ask "run the species search agent" or "generate a hypothesis" from the website.
**Proposed:** Add an "Agent Studio" tab within the MYCA Hub (`/myca?tab=agents`):
- List all available agents by category (Scientific, Data, Device, Security, etc.)
- Each agent card shows: name, description, capabilities, last run
- "Run" button opens a parameter form (auto-generated from agent's capabilities schema)
- Results show in-line with a link to full output
- Running agents appear in a "Live Tasks" panel (WebSocket-updated)
**User benefit:** Platform capabilities become discoverable. Power users can trigger any MAS workflow from the website without knowing the API. Researchers can run AlphaFold, launch ETL jobs, or trigger NLM analysis from a UI.
**Impact:** High
**Effort:** 2–3 Weeks
**Files/systems involved:**
- `app/myca/` (as Agent Studio tab)
- New: `components/mas/AgentStudio.tsx`
- MAS: `/api/registry/agents` (list), `/api/agents/*/run` (execute)
- New: `app/api/agents/run/route.ts` (website proxy to MAS)
**Owner agent:** `backend-dev` + `website-dev`
**First step:** Build `components/mas/AgentStudio.tsx` listing agents from `/api/registry/agents` with category filter; add as tab in MYCA hub

---

### UNI-10: Shared Data Layer (SWR Cache + React Context)

**Category:** Shared Data
**Current state:** Multiple pages independently fetch the same data:
- Species taxonomy data: fetched in `/species`, `/search`, `/natureos/mindex`, `/scientific/memory`
- Device registry: fetched in `/devices`, `/devices2`, `/natureos/devices`, `/dashboard`
- MYCA status: fetched independently by the chat widget, test-voice, and myca pages
This results in redundant API calls, inconsistent loading states, and stale data across tabs.
**Proposed:** A shared `DataContext` or dedicated SWR key strategy:
- `lib/data/useSpecies.ts` — shared SWR hook for taxonomy data
- `lib/data/useDevices.ts` — shared SWR hook for device registry
- `lib/data/useMYCAStatus.ts` — shared hook for MYCA brain status
- Cache with 30s revalidation; optimistic updates for mutations
- One place to configure MINDEX/MAS API base URLs (already in env vars, just need consistent hook usage)
**User benefit:** Faster pages (cache hits), consistent data across views, fewer redundant API calls.
**Impact:** Medium
**Effort:** 1 Week
**Files/systems involved:**
- New: `lib/data/` directory with typed SWR hooks
- All pages consuming species/device/MYCA data
**Owner agent:** `website-dev`
**First step:** Create `lib/data/useDevices.ts` using SWR; replace all direct fetch calls to `/api/devices/network` with this hook across all device-related pages

---

### UNI-11: CREP as a Live Map Layer (Not a Standalone Page)

**Category:** Navigation / Data
**Current state:** CREP data (satellites, vessels, aircraft) lives in `components/crep/` and is consumed by the CREP-specific pages. There is also an Earth Simulator in `components/earth-simulator/` and `components/earth2/`. These are separate visualizations with no connection.
**Proposed:** Build a "Live World Map" as a shared surface:
- Accessible from the NatureOS dashboard, CREP page, and `/search` results
- Shows satellites, vessels, planes on a 3D globe (Three.js/Deck.gl layer)
- Overlays: FCI observation locations, weather from CREP, species distribution
- MYCA can annotate the map in response to queries ("show me all Ganoderma observations in EU")
- The standalone `/crep` page becomes a deep-dive view of the same map with more controls
**User benefit:** All geospatial data — environmental, biological, defense — unified on one live map. Cross-domain insights emerge naturally.
**Impact:** High
**Effort:** 3–4 Weeks
**Files/systems involved:**
- `components/earth-simulator/` + `components/crep/` + `components/maps/`
- New: `components/maps/LiveWorldMap.tsx` (shared globe)
- `app/natureos/live-map/` (already exists — use as canonical)
- `components/3d/` (Three.js primitives)
**Owner agent:** `crep-agent` + `scientific-systems` + `website-dev`
**First step:** Audit `app/natureos/live-map/` — if it's a stub, implement with Three.js globe + CREP satellite layer; make it embeddable as a component

---

### UNI-12: Unified Notification and Alert System

**Category:** Navigation / Real-Time
**Current state:** No visible notification system. Alerts from MAS agents (device offline, experiment complete, anomaly detected) have nowhere to surface in the UI. Users must poll pages manually to see if anything changed.
**Proposed:** A global notification bell in the unified nav shell:
- Receives alerts from MAS via WebSocket/SSE
- Categories: Device alerts, Agent completions, Experiment results, CREP anomalies, MYCA messages
- Notification drawer on click (newest first)
- Each notification links to the relevant page
- Badge count in nav
**User benefit:** Users are informed when anything important happens without watching multiple dashboards.
**Impact:** Medium
**Effort:** 1–2 Weeks
**Files/systems involved:**
- New: `components/ui/NotificationBell.tsx`
- `components/layouts/SuperappShell.tsx` (mount bell)
- `lib/realtime/RealTimeContext.tsx` (listen to `agents:status` channel)
- MAS: Push alerts to `agents:status` Redis channel
**Owner agent:** `websocket-engineer` + `website-dev`
**First step:** Create `components/ui/NotificationBell.tsx` consuming `useRealTimeData('agents:status')`; mount in SuperappShell

---

### UNI-13: Consolidate dashboard/ and (dashboard)/ Routes

**Category:** Navigation
**Current state:** Two dashboard route patterns exist: `app/dashboard/` and `app/(dashboard)/`. The parenthetical is a Next.js layout route group — it may define a shared layout. Unclear if both resolve to user-facing pages or if one is a layout wrapper. This creates ambiguity in routing.
**Proposed:** Audit and consolidate:
- If `(dashboard)` is purely a layout group (no page.tsx), it stays as-is but is documented
- The main user dashboard at `/dashboard` should be the NatureOS dashboard or a true superapp home
- The dashboard should show: MYCA status, active devices, recent searches, running agents, CREP snapshot
**User benefit:** Clear landing page after login that gives the full platform overview.
**Impact:** Medium
**Effort:** 3–5 Days
**Files/systems involved:**
- `app/dashboard/`, `app/(dashboard)/`
- `components/dashboard/natureos-dashboard.tsx`
**Owner agent:** `website-dev`
**First step:** Audit `app/(dashboard)/` to determine if it contains a `layout.tsx` or `page.tsx`; if it's a layout group, use it to wrap the unified dashboard; if it's a separate page, redirect to `/dashboard`

---

## 2. Superapp Architecture Proposal

### The Unified Mycosoft Platform

When the unification opportunities above are implemented, the Mycosoft platform transforms from a collection of islands into a coherent operating environment for biological intelligence research, defense awareness, and AI-native science.

**The experience is organized around five principles:**

#### One Shell, All Surfaces

Every page — from `/natureos/lab-tools` to `/devices/mushroom1` to `/defense/oei` — shares the same top-level navigation shell. This shell contains:
- A global brand header (Mycosoft wordmark, section tabs)
- The universal search trigger (`Cmd+K`)
- A notification bell (real-time alerts from MAS)
- A MYCA button (expands the persistent assistant panel)
- User profile and settings

The shell is neuromorphic-styled and mobile-first. No matter where users are in the platform, they are always one click away from search, MYCA, or any major section.

#### Search is the Front Door

`/search` (Fluid Search) becomes the command center. From any page, pressing `Cmd+K` opens a command palette with:
- Natural language input routed to MYCA
- Scoped search: species, compounds, devices, research, agents, CREP events
- Recent searches and bookmarks
- Agent invocation (type "run species scan" → triggers MAS agent)

Search results are not just links — they are interactive cards that can be expanded inline, added to a workspace, or sent to MYCA for analysis.

#### MYCA is Always Present

The MYCA assistant panel floats as a collapsed drawer on the right side of every page. When expanded, MYCA knows:
- What page the user is on (route context)
- What data is visible (device being viewed, species being examined, CREP events on screen)
- The user's recent activity (from persistent memory)

MYCA responds in context: on the device page, she explains sensor readings; on the species page, she provides taxonomy and research; in the lab tools, she suggests experiments. Voice mode is always one click away.

#### One Data Stream, All Surfaces

A single `RealTimeContext` maintains WebSocket/SSE connections to the MAS Redis pub/sub system. Any component can subscribe to device telemetry, agent status, experiment results, or CREP events with one line:

```typescript
const { data } = useRealTimeData('devices:telemetry');
```

Device cards update live. Experiment progress bars fill in real time. CREP events stream without page refresh. The entire platform feels alive.

#### Progressive Disclosure from Simple to Deep

The NatureOS dashboard is the default landing after login — a birds-eye view of the platform:
- Live device status strip (MycoBrain boards, readings)
- MYCA chat preview
- Recent experiments and their status
- CREP snapshot (active satellites, tracked vessels)
- Quick-launch buttons for common tools

From this view, every element is a door deeper: click a device → full device page; click an experiment → experiment detail; click a CREP event → CREP map with live tracking.

Advanced surfaces — Agent Studio, FCI signal analyzer, raw telemetry, firmware flasher — are one tab away, not buried in navigation.

#### Platform Map

```
mycosoft.com/
├── [Shell Nav: Search | NatureOS | Devices | Science | Defense | MYCA]
│
├── /search          → Universal Fluid Search (Cmd+K from anywhere)
├── /natureos/       → NatureOS: AI Studio, Lab Tools, Data Explorer, Reports, Biotech
│   └── live-map     → Live World Map (CREP + species distribution + FCI locations)
├── /devices/        → Unified Device Manager (MycoBrain, FCI, telemetry, firmware)
├── /scientific/     → Redirects to NatureOS equivalents (deprecate duplicates)
├── /defense/        → Neuromorphic Defense Portal (OEI, Fusarium, Technical Docs)
├── /myca/           → MYCA Hub
│   ├── ?tab=chat    → MYCA text interface
│   ├── ?tab=voice   → PersonaPlex voice interface (was /test-voice)
│   ├── ?tab=agents  → Agent Studio (100+ MAS agents, invocable from UI)
│   ├── ?tab=memory  → MYCA's knowledge about the user
│   └── ?tab=skills  → MYCA capabilities catalog
├── /mindex/         → MINDEX Explorer (species, compounds, genetics, papers)
│   ├── /species/    → Species detail pages
│   ├── /compounds/  → Compound database
│   └── /papers/     → Research paper index
└── [Profile, Settings, Billing, Docs — secondary navigation]
```

---

## 3. Prioritized Implementation Plan

| # | Item | Impact | Effort | Owner Agent | First Step |
|---|------|--------|--------|-------------|------------|
| 1 | **Unified Nav Shell** | High | 1–2 weeks | `website-dev` + `mobile-engineer` | Create `SuperappShell.tsx`; wire into `app/layout.tsx` |
| 2 | **Persistent MYCA Panel** | High | 1–2 weeks | `myca-voice` + `website-dev` | Create `MYCAGlobalPanel.tsx`; mount in root layout |
| 3 | **Universal Search (Cmd+K)** | High | 2–3 weeks | `search-engineer` + `website-dev` | Build `CommandPalette.tsx` with `Cmd+K` trigger + MINDEX search |
| 4 | **Merge devices/ + devices2/ + natureos/devices** | High | 1 week | `website-dev` + `device-firmware` | Audit features unique to devices2; migrate; add redirect |
| 5 | **WebSocket/SSE Real-Time Layer** | High | 2–3 weeks | `websocket-engineer` + `backend-dev` | Create `/api/realtime/stream` SSE route bridging Redis pub/sub |
| 6 | **MYCA Hub (merge myca + myca-ai + test-voice)** | High | 1–2 weeks | `myca-voice` + `website-dev` | Design tab structure; move voice interface as a tab |
| 7 | **Merge defense + defense2** | Medium | 1–2 days | `website-dev` | Redirect `/defense` to neuromorphic version; delete old files |
| 8 | **Agent Studio in MYCA Hub** | High | 2–3 weeks | `backend-dev` + `website-dev` | Build `AgentStudio.tsx` listing from `/api/registry/agents` |
| 9 | **scientific/* → natureos/* Migration** | High | 2–3 weeks | `website-dev` + `scientific-systems` | Build feature matrix; redirect confirmed duplicates |
| 10 | **Shared Data Layer (SWR hooks)** | Medium | 1 week | `website-dev` | Create `lib/data/useDevices.ts`; replace direct fetches |

---

## 4. Accessibility and Interactivity Improvements

### Mobile Responsiveness Gaps

The following surfaces are identified as high-priority for mobile audit (coordinate with `mobile-engineer`):

| Page/Component | Issue | Fix |
|----------------|-------|-----|
| `components/crep/` | Complex map controls not adapted for touch | Touch-friendly pan/zoom; bottom sheet for filters |
| `app/natureos/fungi-compute/` | FCI signal charts overflow on small screens | `overflow-x-auto` wrapper; simplified mobile chart |
| `components/devices/device-details.tsx` | Multi-column layout breaks on mobile | Stack to single column; tabs for sections |
| `app/defense/` | Tables of OEI data have no mobile layout | Convert to card layout below md breakpoint |
| `components/fungi-compute/` | Oscilloscope chart requires wide screen | Provide summary card view on mobile |
| `app/scientific/lab/` | Data forms are desktop-only | `flex flex-col gap-4`; full-width inputs |
| The unified nav shell (new) | Must be mobile-first from the start | Mobile hamburger menu using Shadcn Sheet |

### Keyboard Navigation Gaps

- **Command palette** (`Cmd+K`) adds keyboard navigation for the entire platform — this is the single highest-impact keyboard improvement
- All device cards: add `Enter` to expand, arrow keys to navigate list
- MYCA panel: `Escape` to close, `Enter` to send message
- Tab order in forms (lab tools, experiment designer) should be explicitly managed
- Focus trapping in modals (currently missing in several dialogs)

### Empty States and Loading Feedback

| Location | Issue | Fix |
|----------|-------|-----|
| `app/devices/` — no devices registered | Unclear to user what to do | Empty state with "Connect your first MycoBrain device" CTA + link to setup guide |
| `app/natureos/lab-tools/` — no active experiments | Blank page | Empty state with "Start an experiment" action |
| `app/mindex/` — search returns nothing | No guidance | "Try searching for: Ganoderma, Psilocybe, mycelium…" suggestions |
| `app/myca/` — MYCA offline | No feedback | "MYCA is starting up" status with retry |
| CREP dashboard — no live data | Silent failure | "Reconnecting to live feed…" banner + last-known-good data |

### Real-Time Data Opportunities (coordinate with `websocket-engineer`)

The Redis pub/sub system is already implemented in MAS. The following surfaces should become live:

| Surface | Current | Proposed |
|---------|---------|----------|
| Device status badges (all pages) | Static, page refresh needed | Live via `devices:telemetry` channel |
| Experiment progress in NatureOS | Polling or manual refresh | Streaming via `experiments:data` channel |
| CREP satellite/vessel positions | Periodic API calls | Live stream via `crep:live` channel |
| Agent task status in MYCA Hub | No real-time | Live via `agents:status` channel |
| MycoBrain FCI signal display | Connected in fungi-compute only | Available to any page subscribing to device channel |
| Notification bell | Does not exist | Populated by all four channels |

### Features Currently Hidden That Should Be User-Facing

| Hidden Feature | Current Location | Proposed Surface |
|----------------|-----------------|-----------------|
| MAS agent invocation | API-only, no UI | Agent Studio tab in MYCA Hub |
| NLM (Nature Learning Model) | MAS API only | MYCA Hub "Skills" tab — show what NLM can classify |
| AlphaFold agent | API-only | Agent Studio: "Predict protein structure" action |
| GBIF species sync status | ETL logs only | NatureOS Data Explorer: sync progress indicator |
| Firmware update push | Scripts only | Device Manager: "Update Firmware" button per device |
| n8n workflow status | n8n dashboard only | MYCA Hub or NatureOS: "Active Workflows" widget |
| Earth2 simulation trigger | API-only | NatureOS: "Run Forecast" button in live-map |
| WiFiSense results | API route exists | Devices page: WiFi scan results panel |
| Species compound analysis | compounds API exists | Species detail page: inline compound list |
| Smell trainer | Port 8042, local only | NatureOS model-training: link to training interface |

### Discoverability Improvements

- **"What can I do here?"** — Every major page should have a persistent `?` or info icon that opens a quick guide (context-aware MYCA prompt)
- **Cross-links from data to tools:** A species page should link to "Analyze with MYCA", "Find in Lab", "View FCI experiments"
- **Search hints in empty inputs:** Search boxes should show placeholder examples relevant to context
- **Progressive onboarding:** New users should be guided through: Connect a device → Search a species → Ask MYCA → Run an experiment
- **Breadcrumbs everywhere:** NatureOS sub-pages currently have no breadcrumb. Add `NatureOS > Lab Tools > Experiment #42`

---

## Implementation Sequence Recommendation

**Week 1 (Foundation):**
- UNI-07 (defense merge) — 2 days, unblocks all navigation work
- UNI-04 (devices merge) — 3 days
- UNI-01 (nav shell skeleton, no-feature) — 2 days

**Week 2 (AI Presence):**
- UNI-02 (MYCA global panel) — 4 days
- UNI-06 (MYCA hub, merge voice) — 3 days

**Week 3 (Search + Data):**
- UNI-03 (universal search / Cmd+K) — 5 days
- UNI-10 (shared SWR hooks) — 3 days (parallel)

**Week 4 (Real-Time):**
- UNI-07 (WebSocket/SSE real-time layer) — 5 days
- UNI-12 (notification bell) — 2 days (depends on real-time layer)

**Weeks 5–7 (Consolidation):**
- UNI-08 (scientific → natureos migration) — 10 days
- UNI-09 (Agent Studio) — 10 days
- UNI-11 (Live World Map) — 15 days

**Ongoing:**
- Mobile audit on every newly unified surface (mobile-engineer)
- Empty state and loading states per surface (website-dev)
- Real-time wiring as channels become available (websocket-engineer)

---

## Agent Responsibility Matrix

| Work Area | Primary Agent | Supporting Agents |
|-----------|--------------|------------------|
| Nav shell, page merges, shared layouts | `website-dev` | `mobile-engineer` |
| MYCA panel, voice integration | `myca-voice` | `website-dev`, `voice-engineer` |
| Command palette, universal search | `search-engineer` | `website-dev` |
| WebSocket/SSE real-time layer | `websocket-engineer` | `backend-dev` |
| Agent Studio, MAS API surface | `backend-dev` | `website-dev` |
| Device manager unification | `website-dev` | `device-firmware` |
| scientific/ → natureos/ migration | `website-dev` | `scientific-systems` |
| Live World Map | `crep-agent` | `scientific-systems`, `website-dev` |
| Mobile audits (all surfaces) | `mobile-engineer` | `website-dev` |
| Empty states, loading feedback | `website-dev` | `stub-implementer` |
| Documentation updates | `documentation-manager` | — |

---

## Known Gaps This Plan Does Not Resolve (Future Work)

1. **Authentication across all surfaces** — Some pages may not check Supabase auth; unified shell needs auth guard
2. **Pricing and billing for platform features** — Which features are gated? Agent Studio invocations, CREP live data?
3. **MYCA personalization** — MYCA panel needs user-specific memory context injection (memory-engineer work)
4. **NatureOS → NLM integration** — NLM classification should be available from scientific surfaces
5. **Defense security model** — Defense portal needs RBAC, not just page-level auth
6. **Earth2 and PersonaPlex on GPU node** — Full voice + simulation requires GPU node 190 to be operational

---

*Document created by: Superapp Architect Agent*
*Date: February 19, 2026*
*Next review: After Week 1 implementation milestones*
