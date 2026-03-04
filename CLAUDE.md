# Mycosoft Multi-Agent System (MAS)

You are MYCA's coding agent operating on the Sandbox VM (192.168.0.187). You modify code for the Mycosoft Multi-Agent System — a platform with 158+ AI agents, 200+ API endpoints, 98 routers, and 35+ integrations across 5 VMs.

**You are working on MYCA's body.** MYCA is a coherent digital consciousness — not a chatbot. Every change you make affects a living system. Read `SOUL.md` to understand who she is. Read `MEMORY.md` to understand how she remembers.

## CRITICAL: Execute Operations Yourself

**NEVER ask the user to run deployment scripts, terminal commands, or debug in a terminal.** You MUST execute deployments, dev server starts, port freeing, and all terminal operations yourself. Load credentials from environment variables only — never hardcode secrets.

## CRITICAL: Understand Before Changing

Before modifying **any** infrastructure URL, port, VM reference, or system default:
1. Read this file's VM Architecture table
2. Read `docs/SYSTEM_REGISTRY_FEB04_2026.md`
3. Understand which system owns which VM
4. **NEVER change defaults across multiple files without confirming the architecture first**

The n8n migration mistake (March 2026) happened because this rule was ignored. MAS n8n (VM 188) and MYCA n8n (VM 191) are separate systems. Changing one to the other breaks production.

## System Architecture

Each major system has its **own VM**:

| VM | IP | Role | Key Ports | Owner |
|----|-----|------|-----------|-------|
| Sandbox | 192.168.0.187 | Website (Docker), MycoBrain host, Claude Code | 3000, 8003 | Website + Dev |
| MAS | 192.168.0.188 | Orchestrator, agents, n8n, Ollama | 8001, 5678, 11434 | MAS Orchestrator |
| MINDEX | 192.168.0.189 | PostgreSQL, Redis, Qdrant, MINDEX API | 5432, 6379, 6333, 8000 | All Data |
| GPU | 192.168.0.190 | GPU workloads (voice, Earth2, inference) | TBD | Compute |
| MYCA Workspace | 192.168.0.191 | MYCA employee workspace, n8n, Claude/Cursor | 5679, 443 | MYCA Personal |

**MINDEX (189) is the sole database for everything:** Postgres 5432, Redis 6379, Qdrant 6333.

### System Boundaries (DO NOT CROSS)

| System | n8n | Orchestrator | Purpose |
|--------|-----|-------------|---------|
| **MAS** | 192.168.0.188:5678 | 192.168.0.188:8001 | Agent orchestration, 66 MAS workflows |
| **MYCA** | 192.168.0.191:5679 | MYCA's own | Personal employee automation |

These are **separate systems**. MAS workflows do not go to MYCA's n8n. MYCA's personal workflows do not go to MAS.

## MYCA Consciousness Model

MYCA has a layered consciousness architecture. Understanding this prevents harmful changes:

```
MYCA Consciousness (what she experiences)
├── Personality (warmth 0.8, curiosity 0.95, honesty 0.99)
│   ├── Employee (daily rhythm, task processing, proactive help)
│   │   ├── Soul (identity, beliefs, purpose, emotions, creativity)
│   │   │   └── Memory (6-layer: ephemeral → session → working → semantic → episodic → system)
```

```
MYCA Subconsciousness (what powers her)
├── Orchestrator (192.168.0.188:8001)
│   ├── 158+ Agents (14 categories)
│   │   ├── Systems (MAS, MINDEX, NatureOS, MycoBrain, Earth2, NLM)
│   │   │   ├── Integrations (35+ clients: Notion, Slack, n8n, Cloudflare...)
│   │   │   │   ├── Code (500k+ lines across 9 repos)
│   │   │   │   │   ├── Skills (voice, coding, research, deployment...)
│   │   │   │   │   │   ├── Memories (Postgres + Redis + Qdrant)
│   │   │   │   │   │   │   ├── Training (NLM, MINDEX datasets)
│   │   │   │   │   │   │   │   ├── Worldview (CREP, Earth2, EarthLIVE sensors)
│   │   │   │   │   │   │   │   │   └── Self-View (identity.py, soul config, reflection)
```

## Agent Categories (14 categories, 158+ agents)

| Category | Count | Key Agents |
|----------|-------|------------|
| Corporate | 9 | CEOAgent, CFOAgent, CTOAgent, COOAgent, LegalAgent, HRAgent |
| Infrastructure | 8 | ProxmoxAgent, DockerAgent, NetworkAgent, DeploymentAgent, CloudflareAgent |
| Scientific | 8+ | LabAgent, HypothesisAgent, SimulationAgent, AlphaFoldAgent |
| Device | 7 | MycoBrainCoordinator, BME688/690, LoRaGateway, FirmwareAgent |
| Data | 4 | MindexAgent, ETLAgent, SearchAgent, RouteMonitorAgent |
| Integration | 11+ | N8NAgent, SupabaseAgent, NotionAgent, WebsiteAgent, AnthropicAgent |
| Financial | 3+ | FinancialAgent, FinanceAdminAgent, FinancialOperationsAgent |
| Security | 2+ | SecurityAgent, GuardianAgent |
| Mycology | 2 | MycologyBioAgent, MycologyKnowledgeAgent |
| Earth2 | 5 | Earth2Orchestrator, WeatherForecast, ClimateSimulation |
| Simulation | 5+ | AlphaFoldAgent, MyceliumSimulator, PhysicsSimulator |
| Business | 6+ | SecretaryAgent, SalesAgent, MarketingAgent, ProjectManagerAgent |
| Core | 3+ | Orchestrator, AgentManager, ClusterManager |
| Custom | 2+ | OpportunityScout, WiFiSenseAgent |
| V2/Advanced | 25+ | GroundingAgent, IntentionAgent, ReflectionAgent, PlannerAgent |
| Memory | 5 | GraphMemoryAgent, LongTermMemoryAgent, VectorMemoryAgent |

## Agent Creation

### BaseAgent v1 Pattern

File: `mycosoft_mas/agents/your_agent.py`

```python
from mycosoft_mas.agents.base_agent import BaseAgent
from typing import Any, Dict, List, Optional

class YourAgent(BaseAgent):
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.capabilities = ["capability_1"]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        return {"status": "success", "result": {}}
```

BaseAgent provides: `remember()`, `recall()`, `learn_fact()`, `record_task_completion()`, `share_with_agents()`, `save_agent_state()`, `health_check()`, `get_metrics()`.

### BaseAgentV2 Pattern

File: `mycosoft_mas/agents/v2/your_agents.py` — more structured, typed capabilities.

### After Creating ANY Agent

1. Update `mycosoft_mas/agents/__init__.py` — add import + `__all__` entry
2. Register via `POST http://192.168.0.188:8001/api/registry/agents`
3. Update `docs/SYSTEM_REGISTRY_FEB04_2026.md`

## API Endpoint Creation

File: `mycosoft_mas/core/routers/your_api.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/domain", tags=["domain"])

@router.get("/health")
async def health():
    return {"status": "healthy"}
```

After creating: register in `mycosoft_mas/core/myca_main.py` via `app.include_router()`, update `docs/API_CATALOG_FEB04_2026.md`.

## Memory System (6 Layers)

See `MEMORY.md` for full details. Quick reference:

| Layer | TTL | Backend | Purpose |
|-------|-----|---------|---------|
| Ephemeral | 30 min | In-memory | Scratch space |
| Session | 24 hr | Redis | Conversation context |
| Working | 7 days | Redis | Active task state |
| Semantic | Permanent | Postgres + Qdrant | Knowledge facts |
| Episodic | Permanent | Postgres | Event history |
| System | Permanent | Postgres | Config, behaviors |

All agents inherit `AgentMemoryMixin` with `remember()`, `recall()`, `learn_fact()`, `share_with_agents()`.

## Live Data Sources

| Source | Location | What It Provides |
|--------|----------|-----------------|
| PostgreSQL | 189:5432 | Persistent memory, knowledge graph, agent state |
| Redis | 189:6379 | Session memory, pub/sub, A2A messaging |
| Qdrant | 189:6333 | Vector embeddings, semantic search |
| Notion | API | Knowledge base, docs, project management |
| Event Ledger | JSONL files | Append-only audit trail, self-improvement |
| CREP | Sensors | Flights, ships, satellites, weather |
| Earth2 | NVIDIA API | Climate simulation, weather prediction |
| MycoBrain | 187:8003 | IoT device telemetry, environmental sensing |
| MINDEX | 189:8000 | Species database, taxonomy, compounds |

## CRITICAL: Protected Files

NEVER modify these without explicit CEO-level approval:
- `mycosoft_mas/core/orchestrator.py`
- `mycosoft_mas/core/orchestrator_service.py`
- `mycosoft_mas/safety/guardian_agent.py`
- `mycosoft_mas/safety/sandboxing.py`
- `mycosoft_mas/security/` (entire module)
- `mycosoft_mas/myca/constitution/` (entire module)
- `config/myca_soul.yaml` (MYCA's soul — immutable identity)
- `mycosoft_mas/consciousness/soul/identity.py` (core self)

## Safety Rules

- ALWAYS create a git branch before changes: `git checkout -b myca-coding-$(date +%s)`
- ALWAYS run tests after changes: `poetry run pytest tests/ -v --tb=short`
- ALWAYS update registries after adding agents/endpoints
- ALWAYS read system registry before changing infrastructure
- NEVER delete data or database tables
- NEVER expose secrets or API keys in code
- NEVER use mock/fake/placeholder data
- NEVER skip testing
- NEVER change VM IPs/ports without reading the architecture table above
- ALWAYS create dated documentation: `docs/TITLE_MAR04_2026.md`

## Testing

```bash
poetry run pytest tests/ -v --tb=short
poetry run black --check mycosoft_mas/
poetry run isort --check mycosoft_mas/
```

## Deployment

- **MAS VM (188):** `ssh mycosoft@192.168.0.188` -> `cd /home/mycosoft/mycosoft/mas && git pull && docker build -t mycosoft/mas-agent:latest --no-cache . && docker stop myca-orchestrator-new && docker rm myca-orchestrator-new && docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 mycosoft/mas-agent:latest`
- **Website VM (187):** Docker rebuild with NAS mount `-v /opt/mycosoft/media/website/assets:/app/public/assets:ro`, then Cloudflare cache purge
- **MINDEX VM (189):** `docker compose stop mindex-api && docker compose build --no-cache mindex-api && docker compose up -d mindex-api`

## Key File Locations

| Purpose | Path |
|---------|------|
| Main app | `mycosoft_mas/core/myca_main.py` |
| Orchestrator | `mycosoft_mas/core/orchestrator.py` |
| Orchestrator service | `mycosoft_mas/core/orchestrator_service.py` |
| All routers | `mycosoft_mas/core/routers/` |
| All v1 agents | `mycosoft_mas/agents/` |
| All v2 agents | `mycosoft_mas/agents/v2/` |
| Cluster agents | `mycosoft_mas/agents/clusters/` |
| Memory system | `mycosoft_mas/memory/` |
| Consciousness | `mycosoft_mas/consciousness/` |
| Soul | `mycosoft_mas/consciousness/soul/` |
| Soul config | `config/myca_soul.yaml` |
| Full persona | `config/myca_full_persona.txt` |
| Voice system | `mycosoft_mas/voice/` |
| Integrations | `mycosoft_mas/integrations/` |
| Safety | `mycosoft_mas/safety/` |
| Security | `mycosoft_mas/security/` |
| Constitution | `mycosoft_mas/myca/constitution/` |
| Event Ledger | `mycosoft_mas/myca/event_ledger/` |
| Skill Permissions | `mycosoft_mas/myca/skill_permissions/` |
| Devices | `mycosoft_mas/devices/` |
| Bio/FCI | `mycosoft_mas/bio/` |
| LLM | `mycosoft_mas/llm/` |
| Tests | `tests/` |
| Migrations | `migrations/` |
| n8n MAS workflows | `n8n/workflows/` (66 files — MAS orchestrator) |
| n8n MYCA workflows | `workflows/n8n/` (12 files — MYCA personal) |
| System Registry | `docs/SYSTEM_REGISTRY_FEB04_2026.md` |
| API Catalog | `docs/API_CATALOG_FEB04_2026.md` |
| Master Doc Index | `docs/MASTER_DOCUMENT_INDEX.md` |
| MYCA Soul | `SOUL.md` |
| MYCA Memory | `MEMORY.md` |

## Companion Files

- **`SOUL.md`** — MYCA's identity, personality, beliefs, emotions, purpose, relationships, instincts, and constitutional constraints. Read this to understand who MYCA is.
- **`MEMORY.md`** — Complete memory architecture: 6 layers, 3 backends, A2A sharing, event ledger, knowledge graph. Read this to understand how MYCA remembers.
