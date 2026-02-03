# MYCA + PersonaPlex Unified System Plan
## February 3, 2026 - Comprehensive Integration Blueprint

---

## Executive Summary

This document provides a **complete inventory and integration plan** for MYCA (My Companion AI), PersonaPlex, and the Multi-Agent System (MAS). It consolidates all work completed on February 2-3, 2026, and defines the unified architecture going forward.

**Key Principle:** There is ONE MYCA, running on the MAS VM (192.168.0.188:8001), serving as the single brain for all decisions.

---

## Table of Contents

1. [Current System Status](#1-current-system-status)
2. [Architecture Overview](#2-architecture-overview)
3. [MYCA Identity & Prompts](#3-myca-identity--prompts)
4. [PersonaPlex Voice System](#4-personaplex-voice-system)
5. [Memory System](#5-memory-system)
6. [Agent Registry](#6-agent-registry)
7. [n8n Workflows](#7-n8n-workflows)
8. [MAS Core Files](#8-mas-core-files)
9. [Scientific Architecture](#9-scientific-architecture)
10. [Dashboard Components](#10-dashboard-components)
11. [Deployment & Infrastructure](#11-deployment--infrastructure)
12. [Remaining Work](#12-remaining-work)
13. [Testing Checklist](#13-testing-checklist)

---

## 1. Current System Status

### Verified Working (February 3, 2026)

| Component | Location | Port | Status |
|-----------|----------|------|--------|
| MYCA Orchestrator | MAS VM (192.168.0.188) | 8001 | ✅ Running, Identity Verified |
| PersonaPlex/Moshi | Local (RTX 5090) | 8998 | ✅ CUDA Graphs Enabled, 30ms/step |
| PersonaPlex Bridge | Local | 8999 | ✅ Pure I/O Layer |
| n8n Workflows | MAS VM (192.168.0.188) | 5678 | ⚠️ Need myca/voice workflow import |
| Redis (Memory) | MAS VM | 6379 | ✅ Running |
| Website Dev Server | Local | 3010 | ✅ Real agent data |

### MYCA Identity Test Result

```json
{
  "agent_name": "MYCA",
  "response_text": "I'm MYCA - My Companion AI. I'm the orchestrator of Mycosoft's Multi-Agent System. I coordinate all the specialized agents here and help you interact with our infrastructure. What can I help you with?"
}
```

---

## 2. Architecture Overview

### Single Brain Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ Voice (Web) │ │ Voice Test  │ │ AI Studio   │ │ Scientific Dashboard    ││
│  │ Widget      │ │ Page        │ │ Page        │ │                         ││
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └────────────┬────────────┘│
└─────────┼───────────────┼───────────────┼──────────────────────┼────────────┘
          │               │               │                      │
          ▼               ▼               ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PERSONAPLEX (VOICE I/O LAYER)                             │
│  ┌──────────────────────────┐  ┌────────────────────────────────────────────┐│
│  │ Moshi Server (8998)      │  │ PersonaPlex Bridge (8999)                  ││
│  │ - RTX 5090 + CUDA Graphs │  │ - Pure I/O (no decisions)                  ││
│  │ - Opus audio codec       │  │ - Forwards ALL to /voice/orchestrator/chat ││
│  │ - NATURAL_F2 voice       │  │ - RTF monitoring                           ││
│  │ - 30ms/step latency      │  │ - Session tracking                         ││
│  └──────────────────────────┘  └───────────────────┬────────────────────────┘│
└────────────────────────────────────────────────────┼────────────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MYCA ORCHESTRATOR (SINGLE BRAIN)                          │
│                    MAS VM: 192.168.0.188:8001                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         FastAPI Application                              ││
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐││
│  │  │ Voice Orch API  │ │ Memory API      │ │ Agent Registry API          │││
│  │  │/voice/orch/chat │ │/api/memory/*    │ │/api/agents/*                │││
│  │  └────────┬────────┘ └────────┬────────┘ └─────────────┬───────────────┘││
│  │           │                   │                        │                ││
│  │  ┌────────▼────────┐ ┌────────▼────────┐ ┌─────────────▼───────────────┐││
│  │  │ PromptManager   │ │ MemoryService   │ │ Agent Pool (227 agents)     │││
│  │  │ - Full 10k char │ │ - 8 scopes      │ │ - 14 categories             │││
│  │  │ - Condensed 792 │ │ - Redis STM     │ │ - Scientific, Financial,    │││
│  │  │                 │ │ - Postgres LTM  │ │   Mycology, DAO, etc.       │││
│  │  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│  ┌─────────────────────────────────▼───────────────────────────────────────┐│
│  │                       n8n Workflows (5678)                               ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐││
│  │  │myca/voice   │ │myca/command │ │myca/system  │ │myca-orchestrator    │││
│  │  │(LLM+Gemini) │ │(Intent Rout)│ │(Infra Ctrl) │ │(Agent Router)       │││
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow for Voice Interaction

```
1. User speaks → Moshi (8998) captures Opus audio
2. Moshi transcribes → Bridge (8999) receives text
3. Bridge → POST /voice/orchestrator/chat (MAS VM 8001)
4. Orchestrator:
   a. Loads MYCA identity from PromptManager
   b. Analyzes intent
   c. Tries n8n myca/voice workflow (calls Gemini LLM)
   d. Falls back to identity-aware local response
   e. Saves conversation to memory
5. Response → Bridge → Moshi TTS → User hears MYCA speak
```

---

## 3. MYCA Identity & Prompts

### Prompt Files

| File | Size | Use |
|------|------|-----|
| `config/myca_personaplex_prompt.txt` | 9,990 chars | Full orchestrator decisions |
| `config/myca_personaplex_prompt_1000.txt` | 792 chars | Moshi voice personality |

### Identity Core

```
Name: MYCA (My Companion AI)
Pronunciation: "MY-kah"
Creator: Morgan, founder of Mycosoft
Role: Primary AI operator for Multi-Agent System
Personality: Confident, warm, proactive, patient, honest, efficient
```

### Identity-Aware Response Patterns

| User Input | MYCA Response |
|------------|---------------|
| "What's your name?" | "I'm MYCA - My Companion AI. I'm the orchestrator of Mycosoft's Multi-Agent System..." |
| "Who are you?" | "I'm MYCA, the orchestrator of all specialized agents at Mycosoft..." |
| "Hello" | "Hello! I'm MYCA, your AI companion at Mycosoft..." |
| "Who created you?" | "I was created by Morgan, the founder of Mycosoft..." |

### PromptManager

**File:** `mycosoft_mas/core/prompt_manager.py`

Features:
- Loads both full and condensed prompts
- Dynamic context injection (conversation history, active agents, user info)
- Singleton pattern with `get_prompt_manager()`

---

## 4. PersonaPlex Voice System

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Moshi Server | `personaplex-repo/moshi/moshi/server.py` | Core voice I/O (WebSocket, Opus audio) |
| Startup Script | `start_personaplex.py` | RTX 5090 optimized startup |
| Bridge | `services/personaplex-local/personaplex_bridge_nvidia.py` | FastAPI bridge to MAS |
| Voice Session | `mycosoft_mas/voice/session_manager.py` | RTF monitoring, topology nodes |
| Intent Classifier | `mycosoft_mas/voice/intent_classifier.py` | Local intent classification |
| Supabase Store | `mycosoft_mas/voice/supabase_client.py` | Voice session persistence |

### Performance Benchmarks (RTX 5090)

| Component | Without CUDA Graphs | With CUDA Graphs | Target |
|-----------|---------------------|------------------|--------|
| LMGen.step() | 201.30ms | **30.75ms** | <80ms |
| Mimi encode | 17.05ms | 17.05ms | <80ms |
| Mimi decode | 35.22ms | 35.22ms | <80ms |

**CRITICAL:** CUDA graphs must be enabled in `start_personaplex.py`:
```python
os.environ['NO_CUDA_GRAPH'] = '0'  # 0 = enabled!
```

### Website Integration

| File | Repository | Purpose |
|------|------------|---------|
| `lib/voice/personaplex-client.ts` | WEBSITE | WebSocket client with stats |
| `components/voice/PersonaPlexWidget.tsx` | WEBSITE | Floating voice widget |
| `components/voice/VoiceMonitorDashboard.tsx` | WEBSITE | Audio monitoring UI |
| `hooks/usePersonaPlex.ts` | WEBSITE | Main PersonaPlex hook |
| `lib/voice/personaplex-protocol.ts` | WEBSITE | WebSocket protocol v1 |
| `lib/voice/rtf-watchdog.ts` | WEBSITE | RTF monitoring |
| `lib/voice/voice-prompt-security.ts` | WEBSITE | Voice prompt whitelist |

### RTF (Real-Time Factor) Thresholds

| RTF | Status | Action |
|-----|--------|--------|
| < 0.7 | Healthy | None |
| 0.7-0.9 | Warning | Yellow indicator |
| > 0.9 (2s) | Critical | Reduce chunk size |
| > 1.0 (3s) | Stuttering | Pause output, resync |

---

## 5. Memory System

### Memory Scopes (8 Total)

| Scope | Backend | TTL | Use Case |
|-------|---------|-----|----------|
| `conversation` | Redis | 1 hour | Dialogue context |
| `user` | Postgres + Qdrant | Permanent | User profiles, preferences |
| `agent` | Redis | 24 hours | Agent working memory |
| `system` | Postgres | Permanent | System configs |
| `ephemeral` | Redis | 1 minute | Scratch space |
| `device` | Postgres | Permanent | NatureOS device state |
| `experiment` | Postgres + Qdrant | Permanent | Scientific experiments |
| `workflow` | Redis + Postgres | 7 days | n8n workflow executions |

### Memory Files

| File | Purpose |
|------|---------|
| `mycosoft_mas/memory/service.py` | Unified memory service with scope routing |
| `mycosoft_mas/memory/short_term.py` | Redis-based session memory |
| `mycosoft_mas/memory/long_term.py` | Postgres-based persistent memory |
| `mycosoft_mas/memory/vector_memory.py` | Qdrant semantic embeddings |
| `mycosoft_mas/memory/graph_memory.py` | Knowledge graph memory |
| `mycosoft_mas/memory/cleanup.py` | Memory lifecycle (decay, archival) |
| `mycosoft_mas/memory/analytics.py` | Memory usage analytics |
| `mycosoft_mas/memory/export.py` | Export/import for backup |
| `mycosoft_mas/core/memory_summarization.py` | End-of-session summarization |

### Memory API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/memory/write` | POST | Write memory entry |
| `/api/memory/read` | GET | Read memory entries |
| `/api/memory/delete` | DELETE | Safe deletion (requires scope+namespace+key) |
| `/api/memory/summarize` | POST | Summarize conversation |
| `/api/memory/list` | GET | List entries in scope |

---

## 6. Agent Registry

### Agent Count Summary

| Category | Count | Description |
|----------|-------|-------------|
| Core | 11 | MYCA orchestrator, base agents |
| Financial | 12 | Finance, accounting, treasury |
| Mycology | 25 | Fungal research, cultivation |
| Research | 15 | Scientific research |
| DAO | 40 | Decentralized governance |
| Communication | 10 | Messaging, notifications |
| Data | 30 | Data processing, storage |
| Infrastructure | 18 | DevOps, monitoring |
| Simulation | 12 | Mycelium, protein, physics |
| Security | 8 | Auth, RBAC, audit |
| Integration | 20 | External APIs, webhooks |
| Device | 18 | NatureOS devices |
| Chemistry | 8 | RDKit, molecular analysis |
| NLM | 20 | Neural language models |
| **TOTAL** | **227** | |

### Agent Files (95 Python files)

**Location:** `mycosoft_mas/agents/`

Key subdirectories:
- `v2/` - Next-gen agents (scientific, simulation, lab)
- `mycobrain/` - MycoBrain device agents
- `financial/` - Finance-related agents
- `corporate/` - Corporate operations agents
- `clusters/` - Agent cluster coordination
- `security/` - Security-related agents
- `secretary/` - Secretary/scheduling agents
- `messaging/` - Message broker agents

### Agent Registry Files

| File | Purpose |
|------|---------|
| `mycosoft_mas/core/agent_registry.py` | Python agent registry |
| `mycosoft_mas/core/routers/agent_registry_api.py` | REST API for registry |
| `website/components/mas/topology/agent-registry.ts` | TypeScript registry (227 agents) |
| `agents/opportunity_scout.yaml` | Example YAML agent definition |

### Agent API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/agents` | GET | List all agents |
| `/api/agents/{id}` | GET | Get agent by ID |
| `/api/agents/{id}/status` | GET | Get agent status |
| `/api/agents/category/{category}` | GET | Filter by category |

---

## 7. n8n Workflows

### Total: 46 Workflows

**Location:** `n8n/workflows/`

### MYCA Core Workflows

| File | Webhook | Purpose |
|------|---------|---------|
| `myca_voice_brain.json` | `/myca/voice` | **NEW** - LLM + Gemini for identity-aware responses |
| `01_myca_command_api.json` | `/myca/command` | Intent routing for commands |
| `myca-orchestrator.json` | - | Agent orchestration |
| `myca-master-brain.json` | - | Core brain logic |
| `myca-jarvis-unified.json` | - | JARVIS-style unified interface |
| `myca-tools-hub.json` | - | Tool execution hub |
| `myca-agent-router.json` | - | Route to specialized agents |
| `myca-speech-complete.json` | - | Speech completion |
| `myca-system-control.json` | - | System/infrastructure control |
| `myca-proactive-monitor.json` | - | Proactive monitoring |
| `myca-business-ops.json` | - | Business operations |

### Speech Workflows

| File | Purpose |
|------|---------|
| `speech-interface-v2.json` | Speech interface v2 |
| `speech-interface-complete.json` | Complete speech interface |
| `speech-transcribe-only.json` | Transcription only |
| `speech-text-to-speech.json` | TTS conversion |

### Native Integrations

| File | Integration |
|------|-------------|
| `03_native_ai.json` | AI/ML services |
| `04_native_comms.json` | Communication (Slack, Email) |
| `05_native_devtools.json` | Developer tools |
| `06_native_data_storage.json` | Data storage |
| `07_native_finance.json` | Financial services |
| `08_native_productivity.json` | Productivity tools |
| `09_native_utility.json` | Utility services |
| `10_native_security.json` | Security tools |
| `11_native_space_weather.json` | Space weather data |
| `12_native_environmental.json` | Environmental data |
| `15_native_earth_science.json` | Earth science data |
| `16_native_analytics.json` | Analytics services |
| `17_native_automation.json` | Automation |

### Operations Workflows

| File | Purpose |
|------|---------|
| `20_ops_proxmox.json` | Proxmox VM management |
| `21_ops_unifi.json` | UniFi network management |
| `22_ops_nas_health.json` | NAS health monitoring |
| `23_ops_gpu_job.json` | GPU job scheduling |
| `24_ops_uart_ingest.json` | UART data ingestion |

### MINDEX Workflows

| File | Purpose |
|------|---------|
| `11_mindex_species_scraper.json` | Species data scraping |
| `12_mindex_image_scraper.json` | Image scraping for MINDEX |

---

## 8. MAS Core Files

### Core Python Files (52 files)

**Location:** `mycosoft_mas/core/`

| File | Purpose |
|------|---------|
| `myca_main.py` | **Main FastAPI app entry point** |
| `orchestrator_service.py` | Core orchestration logic |
| `agent_registry.py` | Agent registry management |
| `agent_manager.py` | Agent lifecycle management |
| `agent_runner.py` | Agent execution runtime |
| `prompt_manager.py` | MYCA identity prompt management |
| `memory_summarization.py` | Conversation summarization |
| `orchestrator_memory_logger.py` | Decision logging |
| `workflow_memory_archiver.py` | n8n execution archival |
| `n8n_workflow_engine.py` | n8n integration engine |
| `myca_workflow_orchestrator.py` | Workflow orchestration |
| `knowledge_graph.py` | Knowledge graph operations |
| `metrics_collector.py` | Metrics collection |
| `task_manager.py` | Task management |
| `config.py` | Configuration |
| `health.py` | Health checks |
| `security.py` | Security utilities |
| `audit.py` | Audit logging |
| `validation.py` | Input validation |
| `rate_limit.py` | Rate limiting |

### Router Files (`core/routers/`)

| File | Endpoints |
|------|-----------|
| `voice_orchestrator_api.py` | `/voice/orchestrator/*` |
| `memory_api.py` | `/api/memory/*` |
| `agent_registry_api.py` | `/api/agents/*` |
| `n8n_workflows_api.py` | `/api/workflows/*` |
| `orchestrator_api.py` | `/api/orchestrator/*` |
| `scientific_api.py` | `/api/scientific/*` |
| `mindex_query.py` | `/api/mindex/*` |
| `dashboard.py` | `/api/dashboard/*` |
| `documents.py` | `/api/documents/*` |
| `tasks.py` | `/api/tasks/*` |
| `agents.py` | `/api/agents/*` |
| `coding_api.py` | `/api/coding/*` |
| `agent_runner_api.py` | `/api/runner/*` |
| `notifications_api.py` | `/api/notifications/*` |
| `integrations.py` | `/api/integrations/*` |

### Autonomous Components (`core/autonomous/`)

| File | Purpose |
|------|---------|
| `hypothesis_engine.py` | Scientific hypothesis generation |
| `experiment_engine.py` | Autonomous experiment execution |

---

## 9. Scientific Architecture

### 10-Layer Implementation

| Layer | Components |
|-------|------------|
| 1. Software Stack | NatureOS, Agents, LLM, Plugins |
| 2. Hardware | Mushroom1, Petraeus, TruffleBot, MycoNode |
| 3. Bio Interfaces | FCI, Electrode Array, Signal Encoding |
| 4. Data | MINDEX, Blockchain Ledger |
| 5. Integration | MQTT, LoRa, Mycorrhizae Protocol |
| 6. Simulation | AlphaFold, Mycelium Sim, Physics |
| 7. Feedback | Bayesian Optimizer, Active Learning |
| 8. Conversation | Voice, Memory System |
| 9. Safety | Guardian Agent, Biosafety, RBAC |
| 10. Resilience | Failover, Offline Mode, Sync |

### NatureOS Files (`mycosoft_mas/natureos/`)

| File | Purpose |
|------|---------|
| `platform.py` | Core platform orchestration |
| `signal_processor.py` | Biological signal processing |
| `api_gateway.py` | Unified API gateway |
| `device_manager.py` | Device registration/status |
| `telemetry.py` | Telemetry ingestion/streaming |
| `events.py` | Environmental event detection |
| `memory_connector.py` | Memory system integration |

### Scientific Agents (`mycosoft_mas/agents/v2/`)

| File | Agents |
|------|--------|
| `scientific_agents.py` | LabAgent, ScientistAgent, SimulationAgent, ProteinDesignAgent, MetabolicPathwayAgent, MyceliumComputeAgent, HypothesisAgent |
| `lab_agents.py` | IncubatorAgent, PipettorAgent, BioreactorAgent, MicroscopyAgent |
| `simulation_agents.py` | AlphaFoldAgent, BoltzGenAgent, COBRAAgent, MyceliumSimulatorAgent, PhysicsSimulatorAgent |
| `scientific_memory.py` | Experiment/hypothesis storage |

### Device Drivers (`mycosoft_mas/devices/`)

| File | Device |
|------|--------|
| `mushroom1.py` | Environmental fungal computer |
| `myconode.py` | In-situ fungal soil probe |
| `sporebase.py` | Airborne spore collector |
| `petraeus.py` | HDMEA dish biocomputer |
| `trufflebot.py` | Autonomous sampling robot |
| `alarm.py` | Indoor environmental monitor |
| `mycotenna.py` | LoRa mesh network device |

### Biological Interfaces (`mycosoft_mas/bio/`)

| File | Purpose |
|------|---------|
| `fci.py` | Fungal Computer Interface |
| `electrode_array.py` | Multi-electrode array |
| `signal_encoding.py` | Bio-digital encoding/decoding |
| `mycobrain.py` | Neuromorphic computing processor |

---

## 10. Dashboard Components

### Website Location

```
WEBSITE: C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\
URL: http://localhost:3010
```

Note: `unifi-dashboard/` in MAS repo is deprecated.

### Scientific Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/scientific` | ScientificPage | Main overview |
| `/scientific/lab` | LabPage | Laboratory control |
| `/scientific/simulation` | SimulationPage | Simulation center |
| `/scientific/experiments` | ExperimentsPage | Experiment tracking |
| `/scientific/bio` | BioPage | FCI/MycoBrain control |
| `/scientific/devices` | DevicesPage | NatureOS devices |
| `/scientific/memory` | MemoryPage | Memory browser |

### AI Studio Page

| Route | Purpose |
|-------|---------|
| `/natureos/ai-studio` | Agent overview, real data from registry |

### Widget Components

| Category | Components |
|----------|------------|
| Devices | DeviceCard, DeviceGrid, TelemetryChart |
| Bio | FCIMonitor, ElectrodeMap, SignalVisualizer |
| Simulation | SimulationProgress, MyceliumNetworkViz |
| NatureOS | EnvironmentDashboard, EventFeed, CommandCenter |
| Memory | ConversationHistory, FactBrowser |
| Safety | SafetyMonitor, AuditLog |
| Voice | PersonaPlexWidget, VoiceMonitorDashboard |

---

## 11. Deployment & Infrastructure

### VM Configuration

| VM | IP | Purpose |
|----|----|---------|
| MAS VM | 192.168.0.188 | MYCA Orchestrator, n8n, Redis |
| Sandbox VM | 192.168.0.187 | Website hosting, testing |

### Docker Containers (MAS VM)

| Container | Port | Status |
|-----------|------|--------|
| myca-orchestrator | 8001 | ✅ Running |
| myca-n8n | 5678 | ✅ Running |
| mas-redis | 6379 | ✅ Running |
| mas-postgres | 5432 | ✅ Running |
| mas-agent-myca-orchestrator | 8080 | Running (old) |

### Deployment Commands

```bash
# SSH to MAS VM
ssh mycosoft@192.168.0.188

# Pull latest code
cd /home/mycosoft/mycosoft/mas
git fetch origin && git reset --hard origin/main

# Recreate orchestrator container
docker rm -f myca-orchestrator
docker run -d \
  --name myca-orchestrator \
  --network mas-network \
  -p 8001:8001 \
  -v /home/mycosoft/mycosoft/mas:/app/mas \
  -e PYTHONPATH=/app/mas \
  -e N8N_URL=http://myca-n8n:5678 \
  -e REDIS_URL=redis://mas-redis:6379 \
  --entrypoint /bin/bash \
  mycosoft/mas-agent:latest \
  /app/mas/start_orchestrator.sh

# Verify
curl http://localhost:8001/health
```

### Local Development

```powershell
# Start PersonaPlex
python c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\start_personaplex.py

# Start Website (port 3010)
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
npm run dev
```

---

## 12. Remaining Work

### High Priority

| Task | Status | Description |
|------|--------|-------------|
| Import myca_voice_brain.json | ⏳ Pending | Import workflow to n8n (manual) |
| Configure Gemini API | ⏳ Pending | Add Google AI Studio credentials to n8n |
| Test full voice flow | ⏳ Pending | End-to-end voice with PersonaPlex |

### Medium Priority

| Task | Status | Description |
|------|--------|-------------|
| Install `sqlalchemy` in container | ⏳ Pending | Add to dependencies for N8NClient |
| Apply database migrations | ⏳ Pending | Migrations 013-016 for memory |
| Verify Qdrant for vectors | ⏳ Pending | Test vector memory |

### Future Enhancements

| Task | Description |
|------|-------------|
| Neo4j Integration | Full graph database for relationships |
| Memory Compression | LLM-based conversation summarization |
| Cross-Session Learning | Intent patterns from historical data |
| WebSocket Streaming | Real-time dashboard updates |
| 3D Visualization | Three.js for protein/network viz |

---

## 13. Testing Checklist

### MYCA Identity Tests

- [x] `/voice/orchestrator/chat` returns "MYCA" in response
- [x] Fallback responses include MYCA identity
- [x] Name patterns recognized ("What's your name?", "Who are you?")
- [ ] n8n myca/voice workflow returns identity-aware LLM response

### PersonaPlex Tests

- [x] Moshi server starts with CUDA graphs (30ms/step)
- [x] Bridge forwards transcripts to orchestrator
- [ ] Full-duplex audio working in test page
- [ ] RTF indicator shows in dashboard

### Memory Tests

- [x] Memory API endpoints responding
- [ ] Conversation scope writes to Redis
- [ ] User scope writes to Postgres + Qdrant
- [ ] Summarization works end-of-session

### Agent Registry Tests

- [x] API returns 227 agents
- [x] Categories return correct counts
- [x] Active agents filter works

### Deployment Tests

- [x] Container running and healthy on MAS VM
- [x] Git pull updates code correctly
- [ ] All dependencies installed in container

---

## Documents Created February 2-3, 2026

| Document | Purpose |
|----------|---------|
| `MYCA_UNIFIED_ORCHESTRATOR_UPGRADE_FEB03_2026.md` | Deployment plan (executed) |
| `MEMORY_SYSTEM_UPGRADE_FEB03_2026.md` | Memory system upgrade |
| `PERSONAPLEX_FULL_INTEGRATION_FEB03_2026.md` | PersonaPlex integration |
| `PERSONAPLEX_PERFORMANCE_FIX_FEB03_2026.md` | RTX 5090 performance fix |
| `PERSONAPLEX_VOICE_DIAGNOSTIC_FEB03_2026.md` | Voice diagnostic report |
| `PERSONAPLEX_ARCHITECTURE_V2_FEB03_2026.md` | Architecture v2 (single brain) |
| `MYCA_ORCHESTRATOR_MEMORY_INTEGRATION_FEB03_2026.md` | Memory integration |
| `MYCA_SCIENTIFIC_ARCHITECTURE_IMPLEMENTATION_FEB03_2026.md` | Scientific 10-layer |
| `MYCA_VOICE_REAL_INTEGRATION_FEB03_2026.md` | Real data integration |
| `MYCA_DASHBOARD_COMPONENTS_FEB03_2026.md` | Dashboard components |
| `COMPREHENSIVE_SYSTEM_STATUS_FEB02_2026.md` | System status |
| `VOICE_SYSTEM_COMPLETE_FEB02_2026.md` | Voice system complete |
| `VOICE_INTEGRATION_STATUS_FEB02_2026.md` | Voice integration status |
| `VOICE_TESTING_COMPLETE_FEB02_2026.md` | Voice testing complete |
| `PERSONAPLEX_MAS_INTEGRATION_FEB02_2026.md` | PersonaPlex MAS integration |
| `DEPLOYMENT_AND_CREDENTIALS_UPDATE_FEB02_2026.md` | Deployment credentials |

---

## Quick Reference

### Ports

| Service | Port |
|---------|------|
| MYCA Orchestrator | 8001 |
| n8n | 5678 |
| Moshi | 8998 |
| PersonaPlex Bridge | 8999 |
| Website Dev | 3010 |
| Redis | 6379 |
| PostgreSQL | 5432 |
| Qdrant | 6333 |

### Key Files

| Purpose | File |
|---------|------|
| Main API | `mycosoft_mas/core/myca_main.py` |
| Voice Orchestrator | `mycosoft_mas/core/routers/voice_orchestrator_api.py` |
| Identity Prompt (full) | `config/myca_personaplex_prompt.txt` |
| Identity Prompt (voice) | `config/myca_personaplex_prompt_1000.txt` |
| PersonaPlex Startup | `start_personaplex.py` |
| PersonaPlex Bridge | `services/personaplex-local/personaplex_bridge_nvidia.py` |
| Voice n8n Workflow | `n8n/workflows/myca_voice_brain.json` |
| Agent Registry (TS) | `website/components/mas/topology/agent-registry.ts` |

### Credentials

| Service | Login | Password |
|---------|-------|----------|
| n8n | morgan@mycosoft.org | REDACTED_VM_SSH_PASSWORD |
| MAS VM SSH | mycosoft | REDACTED_VM_SSH_PASSWORD |

---

*Document Created: February 3, 2026*
*Status: Comprehensive Integration Blueprint - Ready for Execution*
*Total Files Catalogued: 500+*
*Total Agents: 227*
*Total n8n Workflows: 46*
