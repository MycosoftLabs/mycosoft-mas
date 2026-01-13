# Mycosoft Master Architecture Document

**Version**: 2.0.0  
**Date**: 2026-01-10  
**Status**: Active - EXPANDED  

---

## Repository Ecosystem

The Mycosoft platform is distributed across **6 primary repositories** under `C:\Users\admin2\Desktop\MYCOSOFT\CODE\`:

| Repository | Path | Purpose | Port | Status |
|------------|------|---------|------|--------|
| **mycosoft-mas** | `MAS/mycosoft-mas` | MAS orchestrator + integration layer | 3001 | Integration Hub |
| **WEBSITE** | `WEBSITE/website` | Production website (mycosoft.com) | 3000 | Primary |
| **MINDEX** | `MINDEX/mindex` | Fungal knowledge database API | 8000 | Core Data |
| **mycobrain** | `mycobrain/` | Hardware firmware + device tools | - | Active Dev |
| **NATUREOS** | `NATUREOS/NatureOS` | Cloud platform + device schemas | - | Infrastructure |
| **platform-infra** | `platform-infra/` | Infrastructure automation | - | Ops |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          MYCOSOFT ECOSYSTEM                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   WEBSITE    │    │    MINDEX    │    │   NATUREOS   │    │   MYCOBRAIN  │   │
│  │   :3000      │───▶│    :8000     │◀───│   Cloud      │───▶│   Firmware   │   │
│  │   Next.js    │    │   FastAPI    │    │   Azure      │    │   ESP32-S3   │   │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │                   │            │
│         ▼                   ▼                   ▼                   ▼            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ React UI     │    │ PostgreSQL   │    │ IoT Hub      │    │ BME688/690   │   │
│  │ Tailwind     │    │ PostGIS      │    │ Event Grid   │    │ LoRa SX1262  │   │
│  │ shadcn/ui    │    │ TimescaleDB  │    │ Cosmos DB    │    │ I2C/SPI      │   │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         MAS ORCHESTRATOR (mycosoft-mas)                    │   │
│  │                                                                            │   │
│  │   200+ AI Agents  •  n8n Workflows  •  MYCA Voice  •  NLM Training        │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Tech Stack

### Frontend (Website)

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14.x | React framework with App Router |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 3.x | Utility-first CSS |
| shadcn/ui | Latest | Component library |
| Radix UI | Latest | Accessible primitives |
| Framer Motion | Latest | Animations |
| React Hook Form | Latest | Form handling |
| Zod | Latest | Schema validation |
| nuqs | Latest | URL state management |
| NextAuth | 4.x | Authentication |

### Backend (MINDEX)

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Core language |
| FastAPI | 0.100+ | API framework |
| PostgreSQL | 15+ | Primary database |
| PostGIS | 3.x | Geospatial |
| TimescaleDB | 2.x | Time-series data |
| SQLAlchemy | 2.x | ORM (async) |
| Alembic | Latest | Migrations |
| httpx | Latest | HTTP client |
| tenacity | Latest | Retry logic |
| BeautifulSoup | 4.x | Web scraping |
| BSEC2 | 2.x | AI gas sensing |

### AI/ML Stack

| Technology | Purpose |
|------------|---------|
| OpenAI GPT-4 | MYCA core intelligence |
| Grok (xAI) | Alternative LLM integration |
| Anthropic Claude | Long-context processing |
| Qdrant | Vector database |
| LangChain | Agent orchestration |
| Bosch AI-Studio | Smell training workflows |
| TensorFlow | Custom NLM models |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Proxmox | Virtualization |
| Supabase | Auth + Realtime (backup) |
| Azure IoT Hub | Device management |
| Redis | Caching + pubsub |
| n8n | Workflow automation |
| Grafana | Monitoring |
| Prometheus | Metrics |

### Storage

| System | Capacity | Purpose |
|--------|----------|---------|
| UniFi NAS (2x8TB) | 16TB | Primary data |
| Dream Machine (27TB) | 27TB | Media + backups |
| Proxmox Storage | 10TB+ | VM data |
| Neon (Cloud) | Unlimited | Website PostgreSQL |

---

## Repository Details

### 1. WEBSITE (`WEBSITE/website`)

**Purpose**: Main production website at mycosoft.com

#### Complete Page Routes

| Route | Description |
|-------|-------------|
| `/` | Homepage |
| `/about` | About Mycosoft |
| `/about/team` | Team page |
| `/science` | Science section |
| `/privacy` | Privacy policy |
| `/terms` | Terms of service |
| `/docs` | Documentation |
| `/login` | Login page |
| `/signup` | Registration |
| `/profile` | User profile |
| `/settings` | User settings |
| `/search` | Global search |

#### Ancestry & Species Routes

| Route | Description |
|-------|-------------|
| `/ancestry` | Ancestry tools landing |
| `/ancestry/species/[id]` | Individual species pages |
| `/ancestry/explorer` | Species explorer |
| `/ancestry/database` | Fungal database browser |
| `/ancestry/phylogeny` | Phylogenetic tree |
| `/ancestry/tools` | Analysis tools |
| `/species` | Species listing |
| `/species/[id]` | Species detail |
| `/mushrooms` | Mushroom encyclopedia |
| `/compounds` | Chemical compounds |
| `/compounds/[id]` | Compound detail |
| `/papers/[id]` | Research papers |

#### NatureOS Routes

| Route | Description |
|-------|-------------|
| `/natureos` | NatureOS dashboard |
| `/natureos/ai-studio` | MAS agent dashboard |
| `/natureos/mindex` | MINDEX infrastructure |
| `/natureos/storage` | Storage management |
| `/natureos/containers` | Container management |
| `/natureos/monitoring` | System monitoring |
| `/natureos/cloud` | Cloud services |
| `/natureos/integrations` | Integration hub |
| `/natureos/functions` | Serverless functions |
| `/natureos/workflows` | n8n workflows |
| `/natureos/sdk` | NatureOS SDK |
| `/natureos/shell` | Terminal emulator |
| `/natureos/settings` | NatureOS settings |
| `/natureos/devices` | Device management |
| `/natureos/mas` | MAS agent details |
| `/natureos/model-training` | ML model training |
| `/natureos/smell-training` | BSEC smell training |
| `/natureos/api` | API gateway dashboard |

#### Apps Routes

| Route | Description |
|-------|-------------|
| `/apps` | Apps listing |
| `/apps/[slug]` | Generic app page |
| `/apps/earth-simulator` | Earth Simulator |
| `/apps/petri-dish-sim` | Petri Dish Simulator |
| `/apps/mushroom-sim` | Mushroom Simulator |
| `/apps/compound-sim` | Compound Analyzer |
| `/apps/spore-tracker` | Spore Tracker |
| `/apps/growth-analytics` | Growth Analytics |

#### Device Routes

| Route | Description |
|-------|-------------|
| `/devices` | Device overview |
| `/devices/[id]` | Device detail |
| `/devices/mycobrain` | MycoBrain manager |
| `/devices/mycobrain/[port]` | Port-specific view |

#### MYCA Routes

| Route | Description |
|-------|-------------|
| `/myca-ai` | MYCA conversation interface |
| `/natureos/ai-studio` | MAS agent topology |
| `/natureos/ai-studio/agents` | Agent management |
| `/natureos/ai-studio/tasks` | Task queue |
| `/natureos/ai-studio/insights` | AI insights |

---

#### Complete API Routes

##### Core APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/health` | GET | Health check |
| `/api/auth/[...nextauth]` | GET, POST | NextAuth endpoints |
| `/api/search` | GET, POST | Global search |
| `/api/search/ai` | POST | AI-powered search |
| `/api/search/suggestions` | GET | Search autocomplete |
| `/api/ai` | POST | AI chat interface |

##### Ancestry/Species APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/ancestry` | GET, POST | Taxa listing |
| `/api/ancestry/[id]` | GET | Single taxon |
| `/api/ancestry/seed` | POST | Seed database |
| `/api/ancestry/tree/[id]` | GET | Phylogenetic tree |
| `/api/species` | GET, POST | Species CRUD |
| `/api/species/[id]` | GET, PUT, DELETE | Species operations |
| `/api/species/submit` | POST | Submit new species |
| `/api/genetics/[speciesId]` | GET | Genetic data |
| `/api/genetics/[speciesId]/[region]` | GET | Specific region (ITS, LSU, etc.) |

##### MINDEX Gateway APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/mindex/taxa` | GET, POST | Taxa operations |
| `/api/mindex/species` | GET | Species listing |
| `/api/mindex/devices` | GET, POST | Device registry |
| `/api/mindex/telemetry` | GET, POST | Telemetry data |
| `/api/mindex/observations` | GET, POST | Field observations |
| `/api/mindex/smells` | GET, POST | Smell training data |
| `/api/gateway/mindex` | ALL | MINDEX API proxy |
| `/api/functions/mindex-query` | POST | Custom queries |

##### MycoBrain APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/mycobrain` | GET, POST | MycoBrain operations |
| `/api/mycobrain/ports` | GET | Available COM ports |
| `/api/mycobrain/[port]` | GET, POST | Port operations |
| `/api/mycobrain/devices` | GET | Registered devices |
| `/api/mas/mycobrain` | GET, POST | MAS integration |
| `/api/services/mycobrain` | GET, POST | Service status |

##### NatureOS APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/natureos/activity` | GET | Activity feed |
| `/api/natureos/devices` | GET, POST | Device management |
| `/api/natureos/mindex` | GET | MINDEX status |
| `/api/natureos/mycelium` | GET | Network topology |
| `/api/natureos/n8n` | GET, POST | n8n integration |
| `/api/natureos/settings` | GET, PUT | Settings |
| `/api/natureos/shell` | POST | Shell commands |
| `/api/natureos/system` | GET | System metrics |

##### MYCA APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/myca/conversations` | GET, POST | Conversation history |
| `/api/myca/runs` | GET, POST | Agent runs |
| `/api/myca/training` | GET, POST | Training data |
| `/api/myca/workflows` | GET, POST | Workflow management |

##### Docker/Container APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/docker/containers` | GET, POST | Container list + actions |
| `/api/docker/containers/logs` | GET | Container logs |
| `/api/docker/images` | GET, POST | Image management |
| `/api/docker/mcp` | GET, POST | MCP server control |

##### Storage APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/storage/nas` | GET, POST | NAS storage |
| `/api/storage/gdrive` | GET, POST | Google Drive |
| `/api/storage/files` | GET, POST | File operations |

##### Integration APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/integrations/[provider]/connect` | GET | OAuth initiation |
| `/api/integrations/[provider]/callback` | GET | OAuth callback |

##### Simulator APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/earth-simulator/grid` | GET | Grid data |
| `/api/earth-simulator/cell/[cellId]` | GET | Cell details |
| `/api/earth-simulator/layers` | GET | Map layers |
| `/api/earth-simulator/devices` | GET | Sensor devices |
| `/api/earth-simulator/tiles/[z]/[x]/[y]` | GET | Map tiles |
| `/api/earth-simulator/inaturalist` | GET | iNat integration |
| `/api/earth-simulator/gee` | GET, POST | Google Earth Engine |
| `/api/compounds` | GET, POST | Compound data |
| `/api/compounds/simulate` | POST | Compound simulation |
| `/api/compound-image` | GET | Compound images |
| `/api/growth/predict` | POST | Growth prediction |
| `/api/spores/detections` | GET, POST | Spore detections |

##### External Service APIs

| Endpoint | Methods | Purpose |
|----------|---------|---------|
| `/api/weather/current` | GET | Current weather |
| `/api/weather/solar` | GET | Solar data |
| `/api/environment/aqi` | GET | Air quality |
| `/api/maps/auth` | GET | Maps API token |
| `/api/firmware` | GET | Firmware versions |
| `/api/devices/discover` | GET, POST | Device discovery |

---

### 2. MINDEX (`MINDEX/mindex`)

**Purpose**: Canonical fungal knowledge graph - database + API

**Target Data Volume**: 575,000+ species

#### Database Schemas

| Schema | Tables | Purpose |
|--------|--------|---------|
| `core` | taxon, synonym, external_id, migration_log | Canonical taxonomy |
| `bio` | trait, genome, sequence, protein | Biological data |
| `obs` | observation, image, location | Field observations |
| `telemetry` | device, reading, event | IoT data |
| `ip` | asset, registration, ownership | IP management |
| `ledger` | anchor, verification | Blockchain records |
| `publications` | publication | Research papers |

#### API Endpoints (FastAPI at :8000)

| Endpoint | Description |
|----------|-------------|
| `/api/mindex/health` | Health check |
| `/api/mindex/taxa` | Taxonomy CRUD |
| `/api/mindex/taxa/{id}` | Single taxon |
| `/api/mindex/taxa/search` | Taxon search |
| `/api/mindex/observations` | Field observations |
| `/api/mindex/mycobrain` | MycoBrain integration |
| `/api/mindex/mycobrain/devices` | Device registry |
| `/api/mindex/mycobrain/telemetry` | Telemetry ingestion |
| `/api/mindex/mycobrain/commands` | Device commands |
| `/api/mindex/telemetry` | Generic telemetry |
| `/api/mindex/devices` | Device management |
| `/api/mindex/wifisense` | WiFi CSI sensing |
| `/api/mindex/drone` | MycoDRONE support |
| `/api/mindex/stats` | Database statistics |
| `/docs` | OpenAPI documentation |

#### ETL Sources & Counts

| Source | Expected Records | Status |
|--------|------------------|--------|
| iNaturalist | 26,616 | Active |
| MycoBank | 545,007 | Active |
| GBIF | 50,000+ | Active |
| TheYeasts.org | 3,502 | Active |
| Fusarium.org | 408 | Active |
| Mushroom.World | 1,000+ | Active |
| FungiDB | 500+ | Active |
| Index Fungorum | 10,000+ | Planned |
| Wikipedia | N/A | Trait enrichment |

---

### 3. MycoBrain (`mycobrain/` + `MAS/mycosoft-mas/firmware`)

**Purpose**: Dual ESP32-S3 hardware controller firmware

#### Hardware Architecture

| MCU | Role | GPIOs |
|-----|------|-------|
| Side-A (Sensor) | I2C, analog, MOSFET, BME688 | 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16 |
| Side-B (Router) | UART↔LoRa routing, commands | 8, 9, 17, 18, 43, 44 |

#### Key Features

- Dual USB-C ports (UART-0, UART-2)
- SX1262 LoRa radio (915MHz)
- BME688/BME690 dual sensor support (I2C 0x76/0x77)
- BSEC2 AI gas sensing with smell classification
- NeoPixel SK6805 LED (GPIO15)
- Buzzer (GPIO16)
- 4 MOSFET outputs (GPIO12-14)
- 4 Analog inputs (GPIO6, 7, 10, 11)
- OPI PSRAM (8MB)

#### Firmware Variants

| Variant | File | Purpose |
|---------|------|---------|
| **temp_firmware** | `firmware/temp_firmware.ino` | Current working firmware (1/8/2026) |
| Side-A | `firmware/MycoBrain_SideA/` | Sensor MCU |
| Side-B | `firmware/MycoBrain_SideB/` | Router MCU |
| ScienceComms | `firmware/ScienceComms/` | Science communication mode |
| Optical Modem | `firmware/optical_modem/` | Optical data transmission |
| Acoustic Modem | `firmware/acoustic_modem/` | Acoustic data transmission |

#### CLI Commands (temp_firmware)

| Command | Description |
|---------|-------------|
| `help` | Show commands |
| `status` | Device status |
| `bme [0\|1\|both]` | BME688 readings |
| `smell` | Smell classification |
| `led [r] [g] [b]` | Set LED color |
| `buzz [ms]` | Activate buzzer |
| `mosfet [1-4] [on\|off]` | MOSFET control |
| `analog [1-4]` | Read analog input |
| `i2c [sda] [scl] [hz]` | Configure I2C |
| `scan` | I2C device scan |
| `config [key] [value]` | Configuration |

---

### 4. MAS Agents

**Total Agents**: 200+ (planned)

#### Agent Categories

| Category | Count | Examples |
|----------|-------|----------|
| Core | 10 | MYCA, Orchestrator, Router |
| Financial | 8 | Mercury, Stripe, Treasury |
| Mycology | 15 | Species, Taxonomy, Traits |
| Research | 12 | PubMed, Scholar, Synthesis |
| DAO | 40+ | Governance, Voting, Treasury |
| Communication | 8 | Email, SMS, Voice, Social |
| Data | 25 | Scrapers, ETL, Enrichment |
| Infrastructure | 10 | Docker, Proxmox, NAS |
| Simulation | 8 | Petri, Growth, Compound |
| Security | 5 | Watchdog, Hunter, Guardian |
| Integration | 15 | iNat, GBIF, MycoBank |
| Device | 20 | MycoBrain, Sensors, Drones |
| NLM | 20 | Training, Inference, Feedback |

---

### 5. NLM (Nature Learning Model)

**Purpose**: Mycosoft's proprietary AI model for fungal knowledge

#### Components

| Component | Purpose |
|-----------|---------|
| Embedding Model | Species vector representations |
| Classification | Edibility, toxicity, habitat |
| Image Recognition | Mushroom identification |
| Smell Model | BSEC gas signature classification |
| Growth Predictor | Environmental conditions → growth |
| Phylogenetic Model | Evolutionary relationships |

#### Training Data Sources

- MINDEX (575,000+ species)
- iNaturalist observations (millions)
- Research publications
- MycoBrain sensor data
- User submissions
- Expert annotations

---

### 6. A2A Services & MCP Servers

#### A2A (Agent-to-Agent) Protocol

| Service | Port | Purpose |
|---------|------|---------|
| Agent Discovery | 8010 | Find available agents |
| Task Dispatch | 8011 | Distribute work |
| Result Aggregation | 8012 | Collect outputs |
| Heartbeat | 8013 | Health monitoring |

#### MCP Servers

| Server | Purpose |
|--------|---------|
| mindex-mcp | MINDEX data access |
| mycobrain-mcp | Device control |
| search-mcp | Global search |
| weather-mcp | Environmental data |
| n8n-mcp | Workflow triggers |

---

## Port Assignments

| Port | Service | Description |
|------|---------|-------------|
| **3000** | Website | Next.js production website |
| **3001** | MAS App | MAS dashboard (mycosoft-mas) |
| **3002** | Grafana | Monitoring dashboards |
| **3100** | MYCA UniFi | Voice integration dashboard |
| **5432** | PostgreSQL | Database (internal) |
| **5678** | n8n | Workflow automation |
| **6333** | Qdrant | Vector database |
| **6379** | Redis | Cache and messaging |
| **8000** | MINDEX | MINDEX API |
| **8001** | MAS Orchestrator | FastAPI orchestrator |
| **8003** | MycoBrain Service | Device management API |
| **8010-8019** | A2A Services | Agent-to-Agent protocols |
| **9090** | Prometheus | Metrics collector |

---

## Deployment Topology

### Local Development

```
┌─────────────────────────────────────────────────┐
│              Local Machine (Windows)             │
├─────────────────────────────────────────────────┤
│  Docker Desktop                                  │
│  ├── mindex-api (port 8000)                     │
│  ├── mindex-postgres (port 5432)                │
│  ├── redis (port 6379)                          │
│  ├── qdrant (port 6333)                         │
│  └── mycosoft-website (port 3000)               │
│                                                  │
│  npm run dev (MAS :3001)                        │
│                                                  │
│  MycoBrain USB (COM3-COM10)                     │
└─────────────────────────────────────────────────┘
```

### Production (Proxmox)

```
┌─────────────────────────────────────────────────┐
│              Proxmox Cluster                     │
├─────────────────────────────────────────────────┤
│  VM-001: MINDEX + PostgreSQL                    │
│  VM-002: Website (Next.js SSR)                  │
│  VM-003: MAS Orchestrator                       │
│  VM-004: MycoBrain Service (USB passthrough)   │
│  VM-005: Monitoring (Grafana/Prometheus)        │
│  VM-006: n8n + Redis                            │
│  VM-007: NLM Training (GPU)                     │
└─────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│           UniFi Dream Machine                    │
├─────────────────────────────────────────────────┤
│  NAS: 2x8TB + 27TB storage                      │
│  Network: VLANs, Firewall                       │
│  IoT: Device discovery                          │
└─────────────────────────────────────────────────┘
```

---

## Quick Reference Commands

### Start MINDEX
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex
docker-compose up -d
# API available at http://localhost:8000/docs
```

### Start Website
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev
# Available at http://localhost:3000
```

### Start MAS
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
npm run dev
# Available at http://localhost:3001
```

### Run Full ETL Sync
```bash
docker exec mindex-api python -m mindex_etl.jobs.run_all --full
# Syncs all sources (8-10 hours for full MycoBank)
```

### Flash MycoBrain
```bash
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain
# Use Arduino IDE with settings from docs/MYCOBRAIN_HARDWARE_CONFIG.md
```

---

## Related Documents

- [AGENT_REGISTRY.md](./AGENT_REGISTRY.md) - All 200+ agents
- [MINDEX_SMELL_TRAINING_SYSTEM.md](./MINDEX_SMELL_TRAINING_SYSTEM.md) - BSEC training
- [BME688_INTEGRATION_COMPLETE_2026-01-09.md](./BME688_INTEGRATION_COMPLETE_2026-01-09.md) - Sensor setup
- [OPTICAL_ACOUSTIC_MODEM_INTEGRATION_2026-01-09.md](./OPTICAL_ACOUSTIC_MODEM_INTEGRATION_2026-01-09.md) - Modem systems
- [PROXMOX_DEPLOYMENT.md](./PROXMOX_DEPLOYMENT.md) - Production deployment
- [MYCOBRAIN_COM_PORT_MANAGEMENT.md](./MYCOBRAIN_COM_PORT_MANAGEMENT.md) - USB handling

---

*Last Updated: 2026-01-10 v2.0*
