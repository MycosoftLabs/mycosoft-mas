# External Repo Integration — System Boundaries and Extension Seams

**Date**: March 10, 2026  
**Author**: MYCA  
**Status**: Complete

## Overview

This document captures the current Mycosoft system boundaries and extension seams across MAS, WEBSITE, MINDEX, MycoBrain, Mycorrhizae, and NatureOS. It serves as the architecture baseline for external repository integration decisions.

---

## 1. System Boundaries

### MAS (Multi-Agent System) — Orchestration Hub

| Property | Value |
|----------|-------|
| **Entry** | `mycosoft_mas/core/myca_main.py` |
| **VM** | 192.168.0.188 |
| **Port** | 8001 |
| **Role** | Central orchestration, API hub, agent routing, memory, integrations |

**Boundary**: MAS is the single orchestration plane. All agent coordination, task routing, memory access, and external API delegation flows through MAS. There is no second orchestration layer.

**Key routers (98+)** include: orchestrator, agent registry, gap API, coding, integrations, notifications, documents, scientific, mindex query, platform, bio, fusarium, redteam, ethics, network, memory, device registry, csuite, cfo_mcp, voice_v9, crep_stream, devices_stream, and others.

---

### MINDEX — Structured Data and Search Plane

| Property | Value |
|----------|-------|
| **Entry** | `mindex_api/main.py` |
| **VM** | 192.168.0.189 |
| **Port** | 8000 |
| **Role** | Species, compounds, taxonomy, telemetry, observations, vector search |

**Boundary**: MINDEX is the canonical structured data layer. Postgres 5432, Redis 6379, Qdrant 6333. All biodiversity, telemetry, and search data flows through MINDEX. iNaturalist/GBIF data is imported via ETL into MINDEX; external APIs are fallback only.

**Key routers**: health, taxon, telemetry, devices, mycobrain, observations, compounds, genetics, unified_search, grounding, a2a_agent, and more.

---

### WEBSITE — Route-Gated Shell with Provider-Based Features

| Property | Value |
|----------|-------|
| **Entry** | `app/layout.tsx`, `components/providers/AppShellProviders.tsx` |
| **VM** | 192.168.0.187 |
| **Port** | 3000 (prod), 3010 (dev) |
| **Role** | Public-facing Next.js app; route-based MYCA/voice/state activation |

**Boundary**: WEBSITE is a route-gated shell. Feature activation is provider-based and path-dependent. Light public routes (/, /about, /devices, etc.) do not load MYCA or voice. Routes like `/search`, `/myca`, `/natureos`, `/dashboard`, `/test-voice` activate MYCAProvider, UnifiedVoiceProvider, and AppStateProvider.

**Extension seams**:
- `app/api/*` — API routes (CREP, devices, mas proxy, etc.)
- `components/` — React components
- CREP data adapters — `app/api/crep/fungal/route.ts` and similar

---

### MycoBrain — Device Service

| Property | Value |
|----------|-------|
| **Entry** | `services/mycobrain/mycobrain_service_standalone.py` |
| **Location** | VM 187:8003 or local 8003 |
| **Role** | Serial comms with MycoBrain hardware; heartbeat to MAS; device visibility |

**Boundary**: MycoBrain is the device ingress. All ESP32/MycoBrain hardware communicates through this service. It sends heartbeats to MAS `/api/devices/heartbeat` every 30 seconds. Telemetry can be bridged to website ingest API and Supabase.

**Protocol**: MDP v1. Serial ports, USB VID detection, command mapping.

---

### Mycorrhizae — Protocol/Event Layer

| Property | Value |
|----------|-------|
| **Entry** | `api/main.py` (mycorrhizae-protocol) |
| **Port** | 8002 |
| **Role** | Keys, channels, event streaming; FCI (Fungal Computer Interface); broker |

**Boundary**: Mycorrhizae is the protocol and event layer, not the canonical database. It uses Postgres and Redis for its own state but does not replace MINDEX as the data plane. MAS and MINDEX remain canonical.

---

### NatureOS — Biological Computing Platform

| Property | Value |
|----------|-------|
| **Entry** | C# `.NET` — `src/core-api/Program.cs` |
| **Role** | Workflows, devices, lab tools; SignalR real-time; device fleet |

**Boundary**: NatureOS is a separate C# platform. WEBSITE exposes `/natureos` and `/natureos/ai-studio` as route prefixes. MAS references NatureOS device fleet and bridges. NatureOS is not the orchestration plane; MAS orchestrates.

---

## 2. VM Layout

| VM | IP | Role | Key Ports |
|----|-----|------|-----------|
| Sandbox | 192.168.0.187 | Website, MycoBrain host | 3000, 8003 |
| MAS | 192.168.0.188 | Orchestrator, n8n, Ollama | 8001, 5678, 11434 |
| MINDEX | 192.168.0.189 | Database, API | 8000, 5432, 6379, 6333 |
| GPU | 192.168.0.190 | GPU workloads | TBD |
| MYCA | 192.168.0.191 | MYCA workspace, n8n | 5679, 443, 8089 |

---

## 3. Extension Seams

### Where new capabilities can land

| System | Seam | Example |
|--------|------|---------|
| **MAS** | New router in `core/routers/` | Add `include_router()` in `myca_main.py` |
| **MINDEX** | New router in `mindex_api/routers/` | ETL jobs, scrapers, API routes |
| **WEBSITE** | `app/api/*`, CREP adapters | Turf/Leaflet in CREP routes, map components |
| **MycoBrain** | MDP protocol, serial commands | Firmware variants, new sensor handlers |
| **Mycorrhizae** | Channels, keys, FCI | Protocol extensions, new stream types |

### What must not be duplicated

- **Second orchestration plane** — MAS is the single orchestrator.
- **Second map stack** — Standardize on Leaflet + deck.gl; no parallel map engines.
- **Second chart/visualization stack** — Prefer existing stack; add only where gap is documented.
- **Adversarial scraping/security bypass** — No anti-bot, Cloudflare-bypass, or devtool-blocking tools.

---

## 4. Data and Request Flow

```
User Browser → Cloudflare → Sandbox (187:3000) → Website
Website → MAS (188:8001) | MINDEX (189:8000)
MycoBrain (187:8003) → MAS (188:8001) heartbeat
MAS → MINDEX (189:8000) for memory, species, vectors
Mycorrhizae (8002) → MAS, MINDEX (broker/channel layer)
```

MINDEX is primary for CREP observation data. iNaturalist/GBIF are fallbacks only. See `docs/CREP_INATURALIST_MINDEX_ETL_MAR09_2026.md` and `app/api/crep/fungal/route.ts`.

---

## 5. Related Documents

- [Request Flow Architecture](./REQUEST_FLOW_ARCHITECTURE_MAR05_2026.md)
- [CREP iNaturalist MINDEX ETL](./CREP_INATURALIST_MINDEX_ETL_MAR09_2026.md)
- [System Registry](./SYSTEM_REGISTRY_FEB04_2026.md)
- [Test Voice Local Fix](./TEST_VOICE_LOCAL_FIX_MAR10_2026.md)
- [CFO MCP Connector](./CFO_MCP_CONNECTOR_COMPLETE_MAR08_2026.md)
