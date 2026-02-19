# Mycosoft Multi-Agent System (MAS)

You are MYCA's coding agent operating on the Sandbox VM (192.168.0.187). You modify code for the Mycosoft Multi-Agent System -- a platform with 117+ AI agents, 200+ API endpoints, and 35+ routers.

## CRITICAL: Execute Operations Yourself

**NEVER ask the user to run deployment scripts, terminal commands, or debug in a terminal.** You MUST execute deployments, dev server starts, port freeing, and all terminal operations yourself via run_terminal_cmd. Load credentials from `.credentials.local` when needed. See `.cursor/rules/agent-must-execute-operations.mdc`.

## System Architecture

Each major system has its **own VM** (187, 188, 189, 190):

| VM | IP | Role | Port |
|----|-----|------|------|
| Sandbox | 192.168.0.187 | Website (Docker), MycoBrain host, Claude Code | Website 3000, MycoBrain 8003 |
| MAS | 192.168.0.188 | Orchestrator, agents, n8n, Ollama | 8001, 5678, 11434 |
| MINDEX | 192.168.0.189 | PostgreSQL, Redis, Qdrant, MINDEX API | 5432, 6379, 6333, 8000 |
| GPU node | 192.168.0.190 | GPU workloads (voice, Earth2, inference) | TBD |

MINDEX is the sole database: Postgres 5432, Redis 6379, Qdrant 6333.

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

File: `mycosoft_mas/agents/v2/your_agents.py` -- more structured, typed capabilities.

### After Creating ANY Agent

1. Update `mycosoft_mas/agents/__init__.py` -- add import + `__all__` entry
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

## Agent Categories (14)

| Category | Count | Key Agents |
|----------|-------|------------|
| Corporate | 9 | CEOAgent, CFOAgent, CTOAgent, COOAgent, LegalAgent, HRAgent |
| Infrastructure | 8 | ProxmoxAgent, DockerAgent, NetworkAgent, DeploymentAgent, CloudflareAgent |
| Scientific | 8+ | LabAgent, HypothesisAgent, SimulationAgent, AlphaFoldAgent |
| Device | 7 | MycoBrainCoordinator, BME688/690, LoRaGateway, FirmwareAgent |
| Data | 4 | MindexAgent, ETLAgent, SearchAgent, RouteMonitorAgent |
| Integration | 11 | N8NAgent, SupabaseAgent, NotionAgent, WebsiteAgent, AnthropicAgent |
| Financial | 3+ | FinancialAgent, FinanceAdminAgent, FinancialOperationsAgent |
| Security | 2+ | SecurityAgent, GuardianAgent |
| Mycology | 2 | MycologyBioAgent, MycologyKnowledgeAgent |
| Earth2 | 5 | Earth2Orchestrator, WeatherForecast, ClimateSimulation |
| Simulation | 5+ | AlphaFoldAgent, MyceliumSimulator, PhysicsSimulator |
| Business | 6+ | SecretaryAgent, SalesAgent, MarketingAgent, ProjectManagerAgent |
| Core | 3+ | Orchestrator, AgentManager, ClusterManager |
| Custom | 2+ | OpportunityScout, WiFiSenseAgent |

## CRITICAL: Protected Files

NEVER modify these without explicit CEO-level approval:
- `mycosoft_mas/core/orchestrator.py`
- `mycosoft_mas/core/orchestrator_service.py`
- `mycosoft_mas/safety/guardian_agent.py`
- `mycosoft_mas/safety/sandboxing.py`
- `mycosoft_mas/security/` (entire module)

## Safety Rules

- ALWAYS create a git branch before changes: `git checkout -b myca-coding-$(date +%s)`
- ALWAYS run tests after changes: `poetry run pytest tests/ -v --tb=short`
- ALWAYS update registries after adding agents/endpoints
- NEVER delete data or database tables
- NEVER expose secrets or API keys in code
- NEVER use mock/fake/placeholder data
- NEVER skip testing
- ALWAYS create dated documentation: `docs/TITLE_FEB09_2026.md`

## Testing

```bash
poetry run pytest tests/ -v --tb=short
poetry run black --check mycosoft_mas/
poetry run isort --check mycosoft_mas/
```

## Deployment

- MAS VM (188): `ssh mycosoft@192.168.0.188` -> `cd /home/mycosoft/mycosoft/mas && git pull && docker build -t mycosoft/mas-agent:latest --no-cache . && docker stop myca-orchestrator-new && docker rm myca-orchestrator-new && docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 mycosoft/mas-agent:latest`
- Website VM (187): Docker rebuild with NAS mount `-v /opt/mycosoft/media/website/assets:/app/public/assets:ro`, then Cloudflare cache purge
- MINDEX VM (189): `docker compose stop mindex-api && docker compose build --no-cache mindex-api && docker compose up -d mindex-api`

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
| Voice system | `mycosoft_mas/voice/` |
| Integrations | `mycosoft_mas/integrations/` |
| Safety | `mycosoft_mas/safety/` |
| Security | `mycosoft_mas/security/` |
| Devices | `mycosoft_mas/devices/` |
| Bio/FCI | `mycosoft_mas/bio/` |
| LLM | `mycosoft_mas/llm/` |
| Tests | `tests/` |
| Migrations | `migrations/` |
| System Registry | `docs/SYSTEM_REGISTRY_FEB04_2026.md` |
| API Catalog | `docs/API_CATALOG_FEB04_2026.md` |
| Master Doc Index | `docs/MASTER_DOCUMENT_INDEX.md` |
