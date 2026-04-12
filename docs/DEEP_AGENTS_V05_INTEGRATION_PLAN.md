# Deep Agents v0.5 Integration Plan — Mycosoft MAS

**Date:** 2026-04-09  
**Author:** Morgan (CEO) + Computer  
**Scope:** Full codebase integration of LangChain Deep Agents v0.5 into `MycosoftLabs/mycosoft-mas`  
**Source:** [Deep Agents v0.5 Blog Post](https://blog.langchain.com/deep-agents-v0-5/) · [Async Subagents Docs](https://docs.langchain.com/oss/python/deepagents/async-subagents) · [Customization Docs](https://docs.langchain.com/oss/python/deepagents/customization)

---

## Executive Summary

Deep Agents v0.5 introduces **async (non-blocking) subagents**, **expanded multimodal filesystem support**, and a **middleware architecture** that map directly onto the Mycosoft MAS's existing orchestrator-centric design. The key win: replacing the current synchronous HTTP/Redis task delegation with non-blocking async subagents that let the MYCA orchestrator launch work across your VM fleet, continue responding to users, and collect results as they come in — without blocking.

This plan covers every layer of the codebase affected by the integration.

---

## Component-to-Feature Mapping

| Deep Agents v0.5 Feature | Current MAS Component | Impact |
|---|---|---|
| `AsyncSubAgent` + Agent Protocol server | `myca-orchestrator` (port 8001) + 60+ agent containers | **Critical** — Non-blocking delegation across VMs |
| `create_deep_agent()` orchestration | `mycosoft_mas/run_mas.py` + `mycosoft_mas/core/` | **Critical** — Replaces/wraps the orchestrator brain |
| Agent Protocol (threads + runs) | `a2a_register_script.py` (existing A2A v0.3) | **High** — Parallel protocol; keeps A2A for external, Agent Protocol for internal |
| Middleware (`wrap_tool_call`) | 3-tier permission model (Read/Write/Execute) | **High** — Formalizes permission enforcement |
| Virtual filesystem (StateBackend, FilesystemBackend) | 5-scope memory API (`memory_api.py`) | **Medium** — Skills/artifacts persistence |
| `TodoListMiddleware` | `agents/enums/task_status.py` (9 statuses) | **Medium** — Structured task tracking per agent |
| Multimodal file support (PDF, audio, video) | PersonaPlex voice (8999), MycoBrain sensors | **Medium** — Sensor data + voice transcripts in agent context |
| Skills system (`/skills/*.md`) | `.deepagents/skills/` (5 skills) + `.cursor/skills/` (22 skills) | **Low** — Already partially implemented |
| `SubAgent` (inline, sync) | Current synchronous HTTP agent calls | **Low** — Already how agents work today |
| `HumanInTheLoopMiddleware` | Escalation routing (Morgan/RJ/Garret) | **Low** — Formal approval gates |

---

## Phase 1: Foundation (Week 1-2)

### 1.1 Install Deep Agents & Dependencies

**Files affected:**
- `pyproject.toml` (Poetry)
- `Dockerfile.orchestrator`
- `requirements.txt` (if used by agent containers)

```bash
# Add to pyproject.toml [tool.poetry.dependencies]
poetry add deepagents>=0.5.0
poetry add langchain-anthropic langchain-openai
```

**Dockerfile.orchestrator changes:**
```dockerfile
# In builder stage, after poetry install
RUN pip install deepagents>=0.5.0
```

### 1.2 Create the Deep Agent Orchestrator Wrapper

**New file:** `mycosoft_mas/core/deep_agent_orchestrator.py`

This wraps the existing orchestrator brain (`run_mas.py`) inside `create_deep_agent()`, giving it planning, context management, and subagent delegation out of the box.

```python
from deepagents import AsyncSubAgent, create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.postgres import PostgresSaver

from mycosoft_mas.core.tools import (
    route_to_agent,
    query_mindex,
    send_notification,
    manage_task,
    memory_read,
    memory_write,
)

# Each domain agent becomes an AsyncSubAgent target
ASYNC_SUBAGENTS = [
    AsyncSubAgent(
        name="myca-secretary",
        description="Executive AI Secretary. Default handler for scheduling, "
                    "general queries, and unmatched requests.",
        graph_id="myca-secretary",
        # No url → ASGI transport for co-deployed agents
    ),
    AsyncSubAgent(
        name="myca-research",
        description="Deep research agent for biology, mycology, earth systems, "
                    "and MINDEX database queries. Use for multi-step research tasks.",
        graph_id="myca-research",
        url="http://192.168.0.188:8080",  # VM 188 — GPU node
    ),
    AsyncSubAgent(
        name="myca-devops",
        description="Infrastructure monitoring, Docker management, VM health, "
                    "and deployment operations.",
        graph_id="myca-devops",
        url="http://192.168.0.191:8080",  # VM 191 — MYCA's own PC
    ),
    AsyncSubAgent(
        name="myca-finance",
        description="Financial operations, budgeting, Mercury/Stripe integration, "
                    "and expense tracking.",
        graph_id="myca-finance",
        # Co-deployed via ASGI
    ),
    AsyncSubAgent(
        name="myca-hr",
        description="HR operations, team management, onboarding, and people ops.",
        graph_id="myca-hr",
        # Co-deployed via ASGI
    ),
]

def create_myca_orchestrator(db_url: str):
    """Create the MYCA Deep Agent orchestrator."""
    checkpointer = PostgresSaver.from_conn_string(db_url)

    agent = create_deep_agent(
        name="myca-orchestrator",
        model="anthropic:claude-sonnet-4-6",
        tools=[
            route_to_agent,
            query_mindex,
            send_notification,
            manage_task,
            memory_read,
            memory_write,
        ],
        system_prompt=MYCA_SYSTEM_PROMPT,  # From config/myca_full_persona.txt
        subagents=ASYNC_SUBAGENTS,
        backend=FilesystemBackend(root="/opt/mycosoft/mas/workspace"),
        skills=["/skills/"],
        checkpointer=checkpointer,
    )
    return agent
```

### 1.3 Implement Agent Protocol Server on Each Domain Agent

**Files affected (new):**
- `services/agent-protocol/server.py` — Shared Agent Protocol server template
- `agents/definitions/langgraph.json` — Co-deployed graph registry

**Files affected (modified):**
- `docker/Dockerfile.agent` — Add deepagents dependency
- Every agent container's entrypoint

Each of the 7 named agents (Secretary, HR, Finance, DevOps, Research, Router, Health) needs to expose the Agent Protocol. This means each agent container runs a LangGraph-compatible server.

**langgraph.json (for co-deployed agents):**
```json
{
  "graphs": {
    "myca-orchestrator": "./mycosoft_mas/core/deep_agent_orchestrator.py:agent",
    "myca-secretary": "./agents/secretary/graph.py:graph",
    "myca-finance": "./agents/finance/graph.py:graph",
    "myca-hr": "./agents/hr/graph.py:graph"
  }
}
```

**For remote agents (VM 188 Research, VM 191 DevOps):**
```json
{
  "graphs": {
    "myca-research": "./agents/research/graph.py:graph"
  }
}
```

Each remote VM runs its own `langgraph dev` or production server.

---

## Phase 2: Async Subagent Migration (Week 2-3)

### 2.1 Convert Synchronous Agent Dispatch to Async

**Current flow (blocking):**
```
User Request → Orchestrator → HTTP POST to agent container → WAIT → Response
```

**New flow (non-blocking):**
```
User Request → Deep Agent Orchestrator → start_async_task("myca-research", task) → Task ID
                                       → continues responding to user
                                       → check_async_task(task_id) when needed
                                       → result available
```

**Files affected:**
- `mycosoft_mas/core/routers/chat_api.py` — Replace synchronous agent dispatch with Deep Agent invocation
- `mycosoft_mas/core/routers/voice_orchestrator_api.py` — Same for voice pipeline
- `mycosoft_mas/core/prompt_manager.py` — Integrate with Deep Agent `system_prompt`

### 2.2 Map Task Status Enums

The existing `TaskStatus` enum maps to Deep Agent async task states:

| MAS TaskStatus | Deep Agent Async Status | Mapping |
|---|---|---|
| `TODO` | — | Pre-launch (no async task yet) |
| `SCHEDULED` | — | Pre-launch, time-gated |
| `IN_PROGRESS` | `running` | Active async task |
| `REVIEW` | `running` + `update_async_task` | Mid-task steering |
| `COMPLETED` | `success` | Task finished, result retrieved |
| `BLOCKED` | `running` (stalled) | Needs `update_async_task` to unblock |
| `CANCELLED` | `cancelled` | `cancel_async_task` called |
| `ON_HOLD` | — | Pause via middleware |
| `OVERDUE` | `running` (timeout exceeded) | Monitor via `list_async_tasks` |

**File affected:** `agents/enums/task_status.py` — Add `ASYNC_RUNNING`, `ASYNC_SUCCESS`, `ASYNC_ERROR` mappings

### 2.3 Redis Integration with Agent Protocol

The current Redis message bus (`redis://mas-redis:6379/0`) stays. Agent Protocol runs alongside it:

- **Redis:** Real-time pub/sub for health checks, heartbeats, and event streaming (existing)
- **Agent Protocol:** Thread-based task delegation for substantive work (new)

**New file:** `mycosoft_mas/core/async_task_bridge.py`

Bridges async task lifecycle events to Redis so the existing health monitor, heartbeat, and dashboard systems can track them:

```python
import redis
from deepagents.types import AsyncTaskStatus

class AsyncTaskBridge:
    """Publishes Deep Agent async task events to Redis for observability."""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    def on_task_started(self, task_id: str, agent_name: str, description: str):
        self.redis.publish("mas:async_tasks", json.dumps({
            "event": "started",
            "task_id": task_id,
            "agent": agent_name,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
        }))
    
    def on_task_completed(self, task_id: str, agent_name: str, result: str):
        self.redis.publish("mas:async_tasks", json.dumps({
            "event": "completed",
            "task_id": task_id,
            "agent": agent_name,
            "result_summary": result[:500],
            "timestamp": datetime.utcnow().isoformat(),
        }))
```

---

## Phase 3: Middleware & Permission System (Week 3-4)

### 3.1 Permission Enforcement Middleware

The existing 3-tier permission model maps perfectly to Deep Agents middleware:

**New file:** `mycosoft_mas/core/middleware/permission_middleware.py`

```python
from langchain.agents.middleware import wrap_tool_call

# Tier 1: Read — auto-approved
READ_TOOLS = {"memory_read", "query_mindex", "list_async_tasks", "check_async_task"}

# Tier 2: Write — requires approval
WRITE_TOOLS = {"memory_write", "manage_task", "update_async_task", "send_notification"}

# Tier 3: Execute — explicit yes
EXECUTE_TOOLS = {"start_async_task", "cancel_async_task", "deploy_service", "run_command"}

@wrap_tool_call
def permission_gate(request, handler):
    tool_name = request.name
    
    if tool_name in READ_TOOLS:
        return handler(request)  # Auto-approved
    
    elif tool_name in WRITE_TOOLS:
        # Log + require soft approval (auto-approve if from trusted agent)
        log_write_action(tool_name, request.args)
        return handler(request)
    
    elif tool_name in EXECUTE_TOOLS:
        # Hard gate — escalate to Morgan/RJ/Garret based on domain
        approval = request_human_approval(tool_name, request.args)
        if approval:
            return handler(request)
        raise PermissionDeniedError(f"Execute action {tool_name} denied")
    
    return handler(request)
```

### 3.2 Observability Middleware

**New file:** `mycosoft_mas/core/middleware/observability_middleware.py`

Feeds tool call metrics into the existing Prometheus/Grafana stack:

```python
@wrap_tool_call
def prometheus_metrics(request, handler):
    tool_name = request.name
    start = time.time()
    
    TOOL_CALLS_TOTAL.labels(tool=tool_name).inc()
    
    try:
        result = handler(request)
        TOOL_CALLS_SUCCESS.labels(tool=tool_name).inc()
        return result
    except Exception as e:
        TOOL_CALLS_ERRORS.labels(tool=tool_name, error=type(e).__name__).inc()
        raise
    finally:
        TOOL_CALL_DURATION.labels(tool=tool_name).observe(time.time() - start)
```

### 3.3 Integrate Middleware into Deep Agent

**File affected:** `mycosoft_mas/core/deep_agent_orchestrator.py`

```python
agent = create_deep_agent(
    # ...existing config...
    middleware=[
        permission_gate,
        prometheus_metrics,
        log_tool_calls,  # Existing logging
    ],
)
```

---

## Phase 4: Multimodal & Filesystem (Week 4-5)

### 4.1 MycoBrain Sensor Data as Multimodal Input

Deep Agents v0.5 can now read PDFs, audio, video, and images via the `read_file` tool with automatic MIME type detection.

**Integration point:** MycoBrain sensor data (BME688/690 environmental readings, camera feeds, spectral data) can be written to the agent's virtual filesystem and read by any subagent.

**Files affected:**
- `services/mycobrain/mas_integration.py` — Write sensor data to Deep Agent filesystem
- `services/mycobrain/mycobrain_service.py` — Pipe telemetry to filesystem

```python
# In mycobrain mas_integration.py
from deepagents.backends.utils import create_file_data

def push_sensor_reading_to_agent(agent, reading):
    """Push MycoBrain sensor data into the Deep Agent's virtual filesystem."""
    file_path = f"/sensors/{reading.device_id}/{reading.timestamp}.json"
    agent.update_state(
        {"files": {file_path: create_file_data(json.dumps(reading.to_dict()))}},
        config={"configurable": {"thread_id": "mycobrain-live"}},
    )
```

### 4.2 PersonaPlex Voice Transcripts

Voice conversations via the PersonaPlex bridge (port 8999) generate transcripts. These can be stored in the Deep Agent filesystem for cross-session context.

**Files affected:**
- `mycosoft_mas/core/routers/voice_orchestrator_api.py` — Write transcripts to filesystem
- `services/personaplex-local/bridge_api_v2.py` — Pipe audio metadata

### 4.3 Backend Selection Strategy

| Deployment | Backend | Reason |
|---|---|---|
| Production orchestrator (VM 187) | `FilesystemBackend(root="/opt/mycosoft/mas/workspace")` | Persistent disk, survives restarts |
| Co-deployed lightweight agents | `StateBackend()` (default) | Ephemeral, no disk needed |
| Remote GPU agents (VM 188) | `FilesystemBackend(root="/workspace")` | Persist research artifacts |
| MYCA's own PC (VM 191) | `LocalShellBackend()` | Full shell access for DevOps tasks |

---

## Phase 5: Docker & Deployment (Week 5-6)

### 5.1 New Docker Compose Structure

**New file:** `docker/docker-compose.deep-agents.yml`

This defines the Agent Protocol server topology:

```yaml
version: "3.8"

services:
  # === ORCHESTRATOR (Deep Agent Supervisor) ===
  myca-orchestrator:
    build:
      context: ..
      dockerfile: Dockerfile.orchestrator
    container_name: mas-deep-orchestrator
    ports:
      - "8001:8000"
    environment:
      AGENT_ROLE: supervisor
      DEEPAGENTS_MODE: "true"
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://mas-redis:6379/0
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LANGSMITH_API_KEY: ${LANGSMITH_API_KEY}  # For tracing (optional)
    volumes:
      - mas-workspace:/opt/mycosoft/mas/workspace
    depends_on:
      mas-redis: { condition: service_healthy }
      mas-postgres: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks: [mas-network]

  # === CO-DEPLOYED AGENTS (ASGI transport, same process) ===
  # Secretary, Finance, HR run inside orchestrator via langgraph.json
  # No separate containers needed for co-deployed agents

  # === REMOTE AGENTS (HTTP transport, separate containers) ===
  myca-research-server:
    build:
      context: ..
      dockerfile: docker/Dockerfile.agent-protocol
    container_name: mas-research-protocol
    ports:
      - "8080:8000"
    environment:
      AGENT_ID: myca-research
      GRAPH_ID: myca-research
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2048M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/ok"]
      interval: 30s
    restart: unless-stopped
    networks: [mas-network]

  myca-devops-server:
    build:
      context: ..
      dockerfile: docker/Dockerfile.agent-protocol
    container_name: mas-devops-protocol
    ports:
      - "8081:8000"
    environment:
      AGENT_ID: myca-devops
      GRAPH_ID: myca-devops
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
    restart: unless-stopped
    networks: [mas-network]

volumes:
  mas-workspace:

networks:
  mas-network:
    external: true
    name: myca-integration-network
```

### 5.2 New Dockerfile for Agent Protocol Servers

**New file:** `docker/Dockerfile.agent-protocol`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install deepagents and LangGraph server
RUN pip install --no-cache-dir \
    deepagents>=0.5.0 \
    langgraph-cli \
    langchain-anthropic \
    langchain-openai

COPY agents/ /app/agents/
COPY config/ /app/config/
COPY langgraph.json /app/langgraph.json

EXPOSE 8000

CMD ["langgraph", "up", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.3 Deployment Topology Change

**Before (current):**
```
                         ┌─────────────────────┐
                         │  myca-orchestrator   │
                         │  (FastAPI, port 8001)│
                         └──────────┬───────────┘
                                    │ HTTP + Redis (sync, blocking)
            ┌───────────┬───────────┼───────────┬───────────┐
            ▼           ▼           ▼           ▼           ▼
       [secretary] [finance]   [hr]      [devops]    [research]
       + 55 more agent containers (all blocking)
```

**After (with Deep Agents v0.5):**
```
                         ┌──────────────────────────────────┐
                         │     myca-orchestrator             │
                         │  (Deep Agent Supervisor)          │
                         │  create_deep_agent() + middleware │
                         │                                   │
                         │  Co-deployed (ASGI, zero latency):│
                         │  ├── myca-secretary graph         │
                         │  ├── myca-finance graph           │
                         │  └── myca-hr graph                │
                         └──────┬──────────────┬─────────────┘
                                │              │
                    Agent Protocol (HTTP)   Agent Protocol (HTTP)
                    (non-blocking)         (non-blocking)
                                │              │
                    ┌───────────▼──┐    ┌──────▼───────────┐
                    │ VM 188 (GPU) │    │ VM 191 (MYCA PC) │
                    │ myca-research│    │ myca-devops       │
                    │ + mindex     │    │ + shell access    │
                    │ + model train│    │ + Cursor IDE      │
                    └──────────────┘    └──────────────────┘
                    
                    Redis pub/sub stays for: heartbeats, health,
                    real-time events, dashboard updates
```

### 5.4 GitHub Actions CI/CD Updates

**Files affected:**
- `.github/workflows/ci.yml` — Add deepagents to test dependencies
- `.github/workflows/deploy-mas-production.yml` — Build new Dockerfile.agent-protocol
- `.github/workflows/deploy-to-vms.yml` — Deploy Agent Protocol servers to VMs

---

## Phase 6: Skills & Memory Migration (Week 6-7)

### 6.1 Migrate Existing Skills

The 5 existing `.deepagents/skills/` are already compatible. The 22 `.cursor/skills/` can be converted:

| Cursor Skill | Deep Agent Skill Migration |
|---|---|
| `create-mas-agent/SKILL.md` | Already at `.deepagents/skills/create_agent/` |
| `deploy-mas-service/SKILL.md` | Already at `.deepagents/skills/deploy/` |
| `docker-troubleshoot/SKILL.md` | → `.deepagents/skills/docker_troubleshoot/SKILL.md` |
| `security-audit/SKILL.md` | → `.deepagents/skills/security_audit/SKILL.md` |
| `vm-health-check/SKILL.md` | → `.deepagents/skills/vm_health_check/SKILL.md` |
| `workflow-orchestration/SKILL.md` | → `.deepagents/skills/workflow_orchestration/SKILL.md` |
| `run-system-tests/SKILL.md` | Already at `.deepagents/skills/run_evals/` |
| Remaining 15 skills | Convert as needed per agent domain |

### 6.2 Memory Architecture Bridge

**Current:** 5-scope namespaced memory API in `memory_api.py` (conversation, user, agent, system, ephemeral)

**New:** Deep Agents `memory` parameter + `MemoryMiddleware` using the filesystem

**Bridge strategy:** The existing Postgres/Qdrant memory stays as the persistent store. Deep Agents memory files (`/memory/*.md`) act as the hot-loaded context that agents read at startup.

**New file:** `mycosoft_mas/core/memory_sync.py`

```python
def sync_memory_to_filesystem(agent, memory_api, thread_id: str):
    """Pull relevant memories from Postgres/Qdrant into Deep Agent filesystem."""
    memories = memory_api.get_memories(scope="agent", limit=20)
    
    memory_content = "# Agent Memory\n\n"
    for m in memories:
        memory_content += f"- [{m.timestamp}] {m.content}\n"
    
    agent.update_state(
        {"files": {"/memory/agent_context.md": create_file_data(memory_content)}},
        config={"configurable": {"thread_id": thread_id}},
    )
```

---

## Phase 7: A2A + Agent Protocol Dual Protocol (Week 7-8)

### 7.1 Keep A2A for External, Agent Protocol for Internal

The existing `a2a_register_script.py` registers the MAS externally at `api.mycosoft.com/a2a/v1/message`. This stays — it's how external agents discover and pay for MINDEX queries.

Agent Protocol is added as the internal protocol for MYCA-to-MYCA communication.

**New file:** `mycosoft_mas/core/routers/agent_protocol_api.py`

```python
from fastapi import APIRouter

router = APIRouter(prefix="/agent-protocol/v1")

@router.post("/threads")
async def create_thread():
    """Agent Protocol: Create a new conversation thread."""
    ...

@router.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str):
    """Agent Protocol: Start a run on a thread."""
    ...

@router.get("/threads/{thread_id}/runs/{run_id}")
async def get_run(thread_id: str, run_id: str):
    """Agent Protocol: Check run status."""
    ...
```

### 7.2 Agent Card Update

Update the A2A Agent Card to advertise both protocols:

```json
{
  "name": "Myca MAS",
  "version": "5.0.0",
  "supportedInterfaces": [
    {
      "url": "https://api.mycosoft.com/a2a/v1/message",
      "protocolBinding": "HTTP+JSON",
      "protocolVersion": "0.3"
    },
    {
      "url": "https://api.mycosoft.com/agent-protocol/v1",
      "protocolBinding": "Agent Protocol",
      "protocolVersion": "1.0"
    }
  ]
}
```

---

## File Change Summary

### New Files (17)

| File | Purpose |
|---|---|
| `mycosoft_mas/core/deep_agent_orchestrator.py` | Main Deep Agent supervisor wrapper |
| `mycosoft_mas/core/async_task_bridge.py` | Async task events → Redis bridge |
| `mycosoft_mas/core/memory_sync.py` | Memory API → Deep Agent filesystem sync |
| `mycosoft_mas/core/middleware/permission_middleware.py` | 3-tier permission enforcement |
| `mycosoft_mas/core/middleware/observability_middleware.py` | Prometheus metrics for tool calls |
| `mycosoft_mas/core/routers/agent_protocol_api.py` | Agent Protocol HTTP endpoints |
| `agents/secretary/graph.py` | Secretary as LangGraph graph |
| `agents/finance/graph.py` | Finance as LangGraph graph |
| `agents/hr/graph.py` | HR as LangGraph graph |
| `agents/research/graph.py` | Research as LangGraph graph |
| `agents/devops/graph.py` | DevOps as LangGraph graph |
| `docker/Dockerfile.agent-protocol` | Agent Protocol server image |
| `docker/docker-compose.deep-agents.yml` | Deep Agent deployment topology |
| `langgraph.json` | Co-deployed graph registry |
| `.deepagents/skills/docker_troubleshoot/SKILL.md` | Migrated from Cursor |
| `.deepagents/skills/security_audit/SKILL.md` | Migrated from Cursor |
| `.deepagents/skills/vm_health_check/SKILL.md` | Migrated from Cursor |

### Modified Files (12)

| File | Change |
|---|---|
| `pyproject.toml` | Add `deepagents>=0.5.0` + LangChain deps |
| `Dockerfile.orchestrator` | Install deepagents, add langgraph.json |
| `docker/Dockerfile.agent` | Add deepagents dependency |
| `mycosoft_mas/run_mas.py` | Import and start Deep Agent orchestrator |
| `mycosoft_mas/core/routers/chat_api.py` | Route through Deep Agent instead of direct HTTP |
| `mycosoft_mas/core/routers/voice_orchestrator_api.py` | Route voice through Deep Agent |
| `mycosoft_mas/core/prompt_manager.py` | Feed prompts to `system_prompt` parameter |
| `agents/enums/task_status.py` | Add async task status mappings |
| `services/mycobrain/mas_integration.py` | Push sensor data to filesystem |
| `a2a_register_script.py` | Add Agent Protocol interface |
| `.github/workflows/ci.yml` | Add deepagents test deps |
| `.github/workflows/deploy-mas-production.yml` | Build agent-protocol images |

### Unchanged (preserved as-is)

- All 60+ existing agent container definitions in `docker-compose.all-agents.yml` — these continue running on Redis. Migration to Agent Protocol is per-agent and incremental.
- The entire `config/` directory (agent_config.json, mas_config.json, etc.)
- All `.cursor/` rules and agents (development tooling, unaffected)
- All `services/personaplex-local/` voice system files
- All `services/mycobrain/` device files (except `mas_integration.py`)
- All `scripts/` deployment and utility scripts

---

## Rollout Strategy

| Week | Phase | What Ships | Risk |
|---|---|---|---|
| 1-2 | Foundation | `deepagents` installed, `deep_agent_orchestrator.py` created, `langgraph.json` for co-deployed agents | Low — additive, no existing behavior changes |
| 2-3 | Async Migration | Secretary/Finance/HR run as co-deployed ASGI subagents. Orchestrator uses `start_async_task` for research/devops | Medium — changes task dispatch flow |
| 3-4 | Middleware | Permission gate + Prometheus metrics middleware active | Low — wraps existing logic |
| 4-5 | Multimodal | MycoBrain sensor data + voice transcripts in agent filesystem | Low — additive |
| 5-6 | Docker | `docker-compose.deep-agents.yml` deployed to VMs, Agent Protocol servers on 188/191 | Medium — infrastructure change |
| 6-7 | Skills/Memory | Cursor skills migrated, memory sync bridge active | Low — no behavior change |
| 7-8 | Dual Protocol | Agent Protocol endpoints live alongside A2A | Low — additive |

### Sandbox-First Deployment

1. Deploy all changes to sandbox VM first (existing pattern via `DEPLOY_TO_SANDBOX.ps1`)
2. Run `FULL_SYSTEM_TEST_FEB04_2026.py` (updated with async task tests)
3. 48-hour burn-in on sandbox
4. Blue-green swap to production (VM 187)

---

## Key Wins After Integration

1. **Non-blocking orchestration** — MYCA can launch deep research on VM 188's GPU while simultaneously answering a user on Slack. No more 30-second timeouts waiting for agent responses.

2. **Mid-task steering** — `update_async_task` lets Morgan or MYCA course-correct a running research task without canceling and restarting.

3. **Heterogeneous compute** — Research agent on GPU node (VM 188), DevOps agent with shell access on VM 191, lightweight agents co-deployed with orchestrator. Each runs on the right hardware.

4. **Formal permission enforcement** — The 3-tier model (Read/Write/Execute) moves from convention to middleware, enforced at every tool call.

5. **Observable tool calls** — Every agent action flows through Prometheus, visible in the existing Grafana dashboards.

6. **Reduced container sprawl** — Co-deploying Secretary, Finance, and HR via ASGI eliminates 3 container images. Scale down from 60+ to ~50 containers while adding capability.

7. **Skills portability** — The 22 Cursor skills become available to any Deep Agent, not just Cursor sessions.
