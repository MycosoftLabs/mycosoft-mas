# MYCOSOFT MAS Agent Registry

**Version**: 2.1.0  
**Date**: 2026-01-24  
**Total Agents**: 223+  

---

## Overview

The Mycosoft Multi-Agent System (MAS) consists of 215+ specialized AI agents organized into functional categories. MYCA (Mycosoft Autonomous Cognitive Agent) serves as the central orchestrator, coordinating all agent activities 24/7. This is the LARGEST fungal intelligence network in existence.

---

## Agent Categories Summary

| Category | Count | Description |
|----------|-------|-------------|
| Core | 10 | Orchestration, memory, routing |
| Financial | 12 | Banking, payments, treasury |
| Mycology | 25 | Species, taxonomy, traits |
| Research | 15 | Publications, synthesis, analysis |
| DAO | 40 | Governance, voting, treasury |
| Communication | 10 | Voice, email, social |
| Data | 30 | ETL, scrapers, enrichment |
| Infrastructure | 15 | Devices, network, storage |
| Simulation | 12 | Growth, compounds, genetics |
| Security | 8 | Auth, watchdog, compliance |
| Integration | 20 | APIs, webhooks, services |
| Device | 18 | MycoBrain, sensors, drones |
| Chemistry | 8 | ChemSpider, compounds, SAR |
| NLM | 20 | Training, inference, feedback |

---

## Core Agents (10)

### 1. MYCA Orchestrator
- **ID**: `myca-orchestrator`
- **Status**: Active
- **Port**: 8001
- **Description**: Central cognitive agent coordinating all other agents
- **Capabilities**: Agent lifecycle, task routing, memory management, voice interaction
- **Integration**: n8n, Qdrant, Redis, GPT-4, Grok

### 2. Memory Manager
- **ID**: `memory-manager`
- **Status**: Active
- **Description**: Short-term and long-term memory management
- **Storage**: Qdrant vectors, Redis cache, PostgreSQL

### 3. Task Router
- **ID**: `task-router`
- **Status**: Active
- **Description**: Routes incoming tasks to appropriate agents

### 4. Priority Queue
- **ID**: `priority-queue`
- **Status**: Active
- **Description**: Manages task prioritization and scheduling

### 5. Health Monitor
- **ID**: `health-monitor`
- **Status**: Active
- **Interval**: 60 seconds
- **Description**: Monitors all agent health and system status

### 6. Scheduler
- **ID**: `scheduler`
- **Status**: Active
- **Description**: Cron-like scheduling for recurring tasks

### 7. Dashboard
- **ID**: `dashboard`
- **Status**: Active
- **Description**: UniFi-style dashboard state management

### 8. Logger
- **ID**: `logger`
- **Status**: Active
- **Description**: Centralized logging across all agents

### 9. Config Manager
- **ID**: `config-manager`
- **Status**: Active
- **Description**: Dynamic configuration management

### 10. Heartbeat
- **ID**: `heartbeat`
- **Status**: Active
- **Description**: Agent liveness detection

---

## Financial Agents (12)

### 11-22. Financial Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 11 | `financial` | Active | Master financial orchestrator |
| 12 | `mercury` | Active | Mercury bank API integration |
| 13 | `stripe` | Active | Stripe payment processing |
| 14 | `accounting` | Active | QuickBooks/Xero integration |
| 15 | `invoice` | Active | Automated invoice generation |
| 16 | `budget` | Active | Budget tracking and forecasting |
| 17 | `payroll` | Active | Payroll automation |
| 18 | `tax` | Planned | Tax calculation and filing |
| 19 | `expense` | Active | Expense tracking |
| 20 | `treasury` | Active | Cash flow management |
| 21 | `investment` | Planned | Investment tracking |
| 22 | `audit-financial` | Active | Financial audit trails |

---

## Mycology Agents (25)

### 23-47. Mycology Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 23 | `mycology-bio` | Active | Core mycology research |
| 24 | `species-classifier` | Active | AI species identification |
| 25 | `taxonomy-manager` | Active | Taxonomic hierarchy management |
| 26 | `trait-extractor` | Active | Trait extraction from text |
| 27 | `edibility-classifier` | Active | Edibility determination |
| 28 | `toxicity-analyzer` | Active | Toxin identification |
| 29 | `habitat-mapper` | Active | Habitat preference mapping |
| 30 | `distribution-tracker` | Active | Geographic distribution |
| 31 | `morphology-analyzer` | Active | Physical characteristic analysis |
| 32 | `phylogeny-builder` | Active | Evolutionary tree construction |
| 33 | `synonym-resolver` | Active | Taxonomic synonym resolution |
| 34 | `image-classifier` | Active | Mushroom image classification |
| 35 | `spore-tracker` | Active | Spore collection management |
| 36 | `growth-analyzer` | Active | Growth pattern analysis |
| 37 | `compound-analyzer` | Active | Chemical compound analysis |
| 38 | `genome-manager` | Active | Genetic sequence management |
| 39 | `smell-trainer` | Active | BME688 smell training |
| 40 | `cultivation-advisor` | Active | Cultivation recommendations |
| 41 | `bioactive-scanner` | Active | Bioactive compound detection |
| 42 | `medicinal-assessor` | Active | Medicinal property assessment |
| 43 | `ecosystem-modeler` | Active | Ecological relationship modeling |
| 44 | `climate-correlator` | Active | Climate impact analysis |
| 45 | `substrate-recommender` | Active | Substrate optimization |
| 46 | `contamination-detector` | Active | Contamination identification |
| 47 | `harvest-timer` | Active | Optimal harvest timing |

---

## Research Agents (15)

### 48-62. Research Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 48 | `research-coordinator` | Active | Research project coordination |
| 49 | `pubmed-scraper` | Active | PubMed publication scraping |
| 50 | `scholar-scraper` | Active | Google Scholar integration |
| 51 | `mycobank-sync` | Active | MycoBank data synchronization |
| 52 | `inaturalist-sync` | Active | iNaturalist observations |
| 53 | `gbif-sync` | Active | GBIF occurrence data |
| 54 | `literature-summarizer` | Active | Paper summarization |
| 55 | `citation-manager` | Active | Citation tracking |
| 56 | `hypothesis-generator` | Active | Research hypothesis generation |
| 57 | `methodology-advisor` | Active | Research methodology suggestions |
| 58 | `data-validator` | Active | Research data validation |
| 59 | `peer-review-assistant` | Active | Peer review assistance |
| 60 | `grant-tracker` | Active | Grant application tracking |
| 61 | `collaboration-finder` | Active | Research collaboration matching |
| 62 | `trend-analyzer` | Active | Research trend analysis |

---

## DAO Agents (40)

### 63-102. MycoDAO Autonomous Operations

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 63 | `dao-orchestrator` | Active | Central DAO coordination |
| 64 | `governance` | Active | Proposal management |
| 65 | `voting` | Active | Vote processing |
| 66 | `treasury-dao` | Active | DAO treasury management |
| 67 | `token-manager` | Active | Token distribution |
| 68 | `staking` | Active | Staking mechanics |
| 69 | `rewards` | Active | Reward distribution |
| 70 | `proposal-creator` | Active | Proposal generation |
| 71 | `quorum-tracker` | Active | Quorum monitoring |
| 72 | `delegate-manager` | Active | Delegation management |
| 73 | `ip-tokenization` | Active | IP asset tokenization |
| 74 | `nft-minter` | Active | NFT creation |
| 75 | `royalty-distributor` | Active | Royalty payments |
| 76 | `contributor-tracker` | Active | Contribution tracking |
| 77 | `reputation-scorer` | Active | Reputation scoring |
| 78 | `dispute-resolver` | Active | Dispute resolution |
| 79 | `multisig-coordinator` | Active | Multi-signature coordination |
| 80 | `timelock-manager` | Active | Timelock operations |
| 81 | `snapshot-taker` | Active | Governance snapshots |
| 82 | `forum-moderator` | Active | Forum moderation |
| 83-102 | `dao-worker-{1-20}` | Active | Generic DAO worker agents |

---

## Communication Agents (10)

### 103-112. Communication Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 103 | `voice` | Active | Voice via ElevenLabs/Whisper |
| 104 | `email` | Active | Email automation |
| 105 | `sms` | Active | SMS via Twilio |
| 106 | `slack` | Active | Slack integration |
| 107 | `discord` | Active | Discord bot |
| 108 | `telegram` | Active | Telegram bot |
| 109 | `notification-router` | Active | Multi-channel routing |
| 110 | `push` | Active | Push notifications |
| 111 | `social-media` | Active | Social media posting |
| 112 | `newsletter` | Active | Newsletter generation |

---

## Data Agents (30)

### 113-142. Data & ETL Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 113 | `mindex` | Active | MINDEX database agent |
| 114 | `etl-orchestrator` | Active | ETL job coordination |
| 115 | `search` | Active | Multi-source search |
| 116 | `analytics` | Active | Business intelligence |
| 117 | `knowledge-graph` | Active | Knowledge graph maintenance |
| 118 | `vector-store` | Active | Qdrant embeddings |
| 119 | `scraper-inat` | Active | iNaturalist scraper |
| 120 | `scraper-mycobank` | Active | MycoBank scraper |
| 121 | `scraper-gbif` | Active | GBIF scraper |
| 122 | `scraper-theyeasts` | Active | TheYeasts.org scraper |
| 123 | `scraper-fusarium` | Active | Fusarium.org scraper |
| 124 | `scraper-mushroom-world` | Active | Mushroom.World scraper |
| 125 | `scraper-fungidb` | Active | FungiDB scraper |
| 126 | `scraper-index-fungorum` | Active | Index Fungorum scraper |
| 127 | `scraper-wikipedia` | Active | Wikipedia trait extraction |
| 128 | `scraper-ncbi` | Active | NCBI GenBank scraper |
| 129 | `data-cleaner` | Active | Data quality cleanup |
| 130 | `deduplicator` | Active | Duplicate detection |
| 131 | `normalizer` | Active | Data normalization |
| 132 | `enricher` | Active | Data enrichment |
| 133 | `validator` | Active | Schema validation |
| 134 | `migrator` | Active | Data migration |
| 135 | `backup` | Active | Database backup |
| 136 | `archiver` | Active | Data archival |
| 137 | `indexer` | Active | Search indexing |
| 138 | `cache-manager` | Active | Redis cache management |
| 139 | `stream-processor` | Active | Real-time data streams |
| 140 | `aggregator` | Active | Data aggregation |
| 141 | `exporter` | Active | Data export (CSV, JSON) |
| 142 | `importer` | Active | Bulk data import |

---

## Infrastructure Agents (15)

### 143-157. Infrastructure Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 143 | `docker-manager` | Active | Container orchestration |
| 144 | `proxmox-manager` | Active | VM management |
| 145 | `network` | Active | UniFi network integration |
| 146 | `storage-nas` | Active | NAS management |
| 147 | `storage-cloud` | Active | Cloud storage (S3, GCS) |
| 148 | `dns` | Active | DNS management |
| 149 | `ssl` | Active | SSL certificate management |
| 150 | `load-balancer` | Active | Traffic distribution |
| 151 | `backup-infra` | Active | Infrastructure backup |
| 152 | `monitoring` | Active | Prometheus/Grafana |
| 153 | `alerting` | Active | Alert management |
| 154 | `scaling` | Active | Auto-scaling |
| 155 | `deployment` | Active | CI/CD deployment |
| 156 | `resource-optimizer` | Active | Resource optimization |
| 157 | `cost-tracker` | Active | Infrastructure costs |

---

## Simulation Agents (12)

### 158-169. Simulation Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 158 | `earth-simulator` | Active | NatureOS Earth simulation |
| 159 | `petri-dish` | Active | Petri dish simulation |
| 160 | `mushroom-growth` | Active | Mushroom growth sim |
| 161 | `compound-sim` | Active | Compound behavior sim |
| 162 | `genetic-sim` | Active | Genetic phenotype sim |
| 163 | `antiviral-sim` | Active | Antiviral efficacy sim |
| 164 | `antibacterial-sim` | Active | Antibacterial efficacy sim |
| 165 | `antifungal-sim` | Active | Antifungal efficacy sim |
| 166 | `protein-sim` | Active | Protein folding sim |
| 167 | `amino-acid-sim` | Active | Amino acid interaction |
| 168 | `climate-sim` | Active | Climate impact sim |
| 169 | `ecosystem-sim` | Active | Ecosystem dynamics sim |

---

## Security Agents (8)

### 170-177. Security Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 170 | `auth` | Active | Authentication |
| 171 | `authorization` | Active | Access control |
| 172 | `watchdog` | Active | Threat monitoring |
| 173 | `hunter` | Active | Threat hunting |
| 174 | `guardian` | Active | System protection |
| 175 | `compliance` | Active | Regulatory compliance |
| 176 | `audit` | Active | Security audit logs |
| 177 | `incident-response` | Active | Incident handling |

---

## Integration Agents (20)

### 178-197. Integration Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 178 | `n8n` | Active | n8n workflow orchestration |
| 179 | `github` | Active | GitHub integration |
| 180 | `notion` | Active | Notion knowledge base |
| 181 | `google-drive` | Active | Google Drive |
| 182 | `aws` | Active | AWS services |
| 183 | `azure` | Active | Azure services |
| 184 | `gcp` | Active | Google Cloud |
| 185 | `openai` | Active | OpenAI API |
| 186 | `anthropic` | Active | Claude API |
| 187 | `grok` | Active | xAI Grok API |
| 188 | `elevenlabs` | Active | Voice synthesis |
| 189 | `whisper` | Active | Speech recognition |
| 190 | `mapbox` | Active | Mapping services |
| 191 | `weather-api` | Active | Weather data |
| 192 | `unifi` | Active | UniFi integration |
| 193 | `palantir` | Planned | Palantir Foundry |
| 194 | `snowflake` | Planned | Snowflake data |
| 195 | `databricks` | Planned | Databricks ML |
| 196 | `supabase` | Active | Supabase services |
| 197 | `webhook-handler` | Active | Generic webhooks |

---

## Device Agents (18)

### 198-215. Device Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 198 | `mycobrain` | Active | MycoBrain management |
| 199 | `mycobrain-side-a` | Active | Sensor MCU control |
| 200 | `mycobrain-side-b` | Active | Router MCU control |
| 201 | `device-discovery` | Active | Device discovery |
| 202 | `device-registry` | Active | Device registration |
| 203 | `firmware-manager` | Active | OTA firmware updates |
| 204 | `telemetry-collector` | Active | Sensor data collection |
| 205 | `command-dispatcher` | Active | Device commands |
| 206 | `sensor-bme688` | Active | BME688 sensor agent |
| 207 | `sensor-bme690` | Active | BME690 sensor agent |
| 208 | `lora-gateway` | Active | LoRa communication |
| 209 | `wifi-sense` | Active | WiFi CSI sensing |
| 210 | `optical-modem` | Active | Optical communication |
| 211 | `acoustic-modem` | Active | Acoustic communication |
| 212 | `myco-drone` | Planned | MycoDRONE control |
| 213 | `camera` | Active | Camera integration |
| 214 | `spectrometer` | Planned | Spectrometer control |
| 215 | `microscope` | Planned | Microscope automation |

---

## Chemistry Agents (8)

### 216-223. Chemistry Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 216 | `chemspider-sync` | Active | Syncs compound data from ChemSpider API |
| 217 | `compound-enricher` | Active | Enriches compounds with external data sources |
| 218 | `compound-analyzer` | Active | Analyzes compound properties and activities |
| 219 | `sar-analyzer` | Active | Structure-Activity Relationship analysis |
| 220 | `protein-folder` | Planned | Protein folding predictions (AlphaFold) |
| 221 | `peptide-analyzer` | Planned | Peptide sequence analysis |
| 222 | `chemical-sim` | Active | Chemical simulation engine |
| 223 | `bioactivity-predictor` | Active | Predicts biological activity from structure |

**ChemSpider Integration Details:**
- API Key: Environment variable `CHEMSPIDER_API_KEY`
- Base URL: `https://api.rsc.org/compounds/v1`
- Rate Limit: 100 requests/minute
- Data cached for 24 hours
- Syncs to MINDEX `bio.compound` tables

---

## NLM Agents (20)

### 224-243. Nature Learning Model Suite

| ID | Name | Status | Description |
|----|------|--------|-------------|
| 216 | `nlm-trainer` | Active | Model training orchestration |
| 217 | `nlm-embedder` | Active | Species embedding generation |
| 218 | `nlm-classifier` | Active | Classification inference |
| 219 | `nlm-image` | Active | Image recognition |
| 220 | `nlm-smell` | Active | Smell classification |
| 221 | `nlm-growth` | Active | Growth prediction |
| 222 | `nlm-phylogeny` | Active | Evolutionary inference |
| 223 | `nlm-feedback` | Active | User feedback processing |
| 224 | `nlm-validator` | Active | Model validation |
| 225 | `nlm-optimizer` | Active | Hyperparameter tuning |
| 226 | `nlm-deployer` | Active | Model deployment |
| 227 | `nlm-monitor` | Active | Model performance monitoring |
| 228 | `nlm-explainer` | Active | Model explainability |
| 229 | `nlm-data-curator` | Active | Training data curation |
| 230 | `nlm-augmenter` | Active | Data augmentation |
| 231 | `nlm-synthetic` | Active | Synthetic data generation |
| 232 | `nlm-transfer` | Active | Transfer learning |
| 233 | `nlm-ensemble` | Active | Model ensembling |
| 234 | `nlm-edge` | Active | Edge model optimization |
| 235 | `nlm-continual` | Active | Continual learning |

---

## Agent Topology

```
                              ┌───────────────────┐
                              │       MYCA        │
                              │   Orchestrator    │
                              │   (10 Core)       │
                              └─────────┬─────────┘
                                        │
    ┌───────────────┬───────────────┬───┴───┬───────────────┬───────────────┐
    │               │               │       │               │               │
┌───┴───┐       ┌───┴───┐       ┌───┴───┐ ┌─┴─┐       ┌─────┴─────┐   ┌─────┴─────┐
│Finance│       │Mycology│      │Research│ │DAO│       │   Data    │   │   NLM     │
│  (12) │       │  (25)  │      │  (15)  │ │(40)│      │   (30)    │   │   (20)    │
└───┬───┘       └───┬───┘       └───┬───┘ └─┬─┘       └─────┬─────┘   └─────┬─────┘
    │               │               │       │               │               │
┌───┴───┐       ┌───┴───┐       ┌───┴───┐ ┌─┴─┐       ┌─────┴─────┐   ┌─────┴─────┐
│Comms  │       │Device │       │SimSuite│ │Sec│       │Integration│   │   Infra   │
│  (10) │       │  (18) │       │  (12)  │ │(8)│       │   (20)    │   │   (15)    │
└───────┘       └───────┘       └───────┘ └───┘       └───────────┘   └───────────┘
```

---

## Agent Communication Protocols

### 1. Redis Pub/Sub
- Real-time event broadcasting
- Agent status updates
- Task completion notifications

### 2. Message Queue (Bull)
- Task distribution
- Job scheduling
- Retry handling

### 3. REST API
- Synchronous requests
- Health checks
- Direct agent calls

### 4. gRPC
- High-performance streaming
- Binary protocol efficiency

### 5. n8n Workflows
- Complex multi-agent orchestration
- Visual workflow design
- Conditional logic

### 6. A2A Protocol
- Agent-to-Agent direct communication
- Capability discovery
- Task negotiation

---

## Agent Lifecycle States

| State | Description |
|-------|-------------|
| `initializing` | Agent starting up |
| `active` | Agent ready and processing |
| `busy` | Agent processing a task |
| `idle` | Agent waiting for work |
| `paused` | Agent temporarily suspended |
| `error` | Agent in error state |
| `shutdown` | Agent shutting down |
| `dead` | Agent unresponsive |

---

## Adding New Agents

1. Define agent in `config/mas_config.json`
2. Implement agent class in `mycosoft_mas/agents/`
3. Create agent interface contract
4. Register with MYCA orchestrator
5. Add health check endpoint
6. Create n8n workflow if needed
7. Add to this registry
8. Deploy and test

---

## Related Documents

- [Master Architecture](./MASTER_ARCHITECTURE.md)
- [MAS Config](../config/mas_config.json)
- [n8n Workflows](../n8n/README.md)
- [A2A Protocol](./A2A_PROTOCOL.md)

---

*Last Updated: 2026-01-24 v2.1 - Added Chemistry Agents (ChemSpider Integration)*
