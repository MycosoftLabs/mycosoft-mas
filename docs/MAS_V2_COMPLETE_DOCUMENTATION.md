# MAS v2 Architecture Overhaul - Complete Documentation

**Date:** January 24, 2026  
**Version:** 2.0.0  
**Status:** Implementation Complete

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Architecture](#solution-architecture)
4. [Implementation Details](#implementation-details)
5. [File Inventory](#file-inventory)
6. [Agent Registry](#agent-registry)
7. [API Reference](#api-reference)
8. [Database Schema](#database-schema)
9. [Deployment Guide](#deployment-guide)
10. [Configuration Reference](#configuration-reference)
11. [Scripts Reference](#scripts-reference)
12. [Next Steps](#next-steps)

---

## Executive Summary

The MAS v2 Architecture Overhaul transforms the Multi-Agent System from a collection of documented class definitions into a fully operational, containerized agent runtime. This implementation delivers:

- **40 Agent Classes** across 5 categories (Corporate, Infrastructure, Device, Data, Integration)
- **Complete Runtime Engine** with Docker containerization
- **MYCA Orchestrator** with spawning, task distribution, and health monitoring
- **Real-Time Dashboard API** with WebSocket streaming
- **Memory Systems** (Redis short-term, MINDEX long-term, Qdrant vector)
- **Gap Detection** and automatic agent creation
- **Database Schema** for agent logging and snapshots

### Key Metrics

| Metric | Value |
|--------|-------|
| Files Created | 25 |
| Total Code Size | ~213 KB |
| Agent Classes | 40 |
| API Endpoints | 15+ |
| Database Tables | 5 |

---

## Problem Statement

### Before Implementation

The MAS existed only as:
- 55+ Python agent class files in `mycosoft_mas/agents/` - **definitions only, not running**
- MAS Orchestrator (FastAPI :8001) - basic routing, **no agent execution engine**
- AGENT_REGISTRY.md claiming 223+ agents - **0 actually running**

### Critical Gaps Identified

1. No Agent Runtime Engine - no process/container per agent
2. No Agent Isolation - no compartmentalized compute
3. No Agent Lifecycle Manager - no spawn, snapshot, archive
4. No Agent-to-Agent Protocol - documented but not implemented
5. No Real-time Agent Monitoring - dashboard used mock data
6. No Automatic Agent Creation - no gap detection system
7. No 24/7 Execution - agents didn't run as background workers
8. No MINDEX Logging - agent activities not stored in database

---

## Solution Architecture

### System Topology

```
                        INTERNET
                            |
                  Cloudflare Edge (CDN/WAF)
                            |
        +-------------------+-------------------+
        |                   |                   |
sandbox.mycosoft.com   api.mycosoft.com    brain.mycosoft.com
        |                   |                   |
+-------+-------------------+-------------------+-------+
|                   SANDBOX VM (192.168.0.187)          |
|                                                       |
|   +-------------+    +-------------+    +---------+   |
|   |   Website   |    |   MINDEX    |    |  Redis  |   |
|   |   :3000     |    |   :8000     |    |  :6379  |   |
|   +------+------+    +------+------+    +----+----+   |
+----------+------------------+----------------+--------+
           |                  |                |
+----------+------------------+----------------+--------+
|                   MAS VM (192.168.0.188)              |
|                                                       |
|   +-----------------------------------------------+   |
|   |            MYCA ORCHESTRATOR                  |   |
|   |            (Central Intelligence)             |   |
|   |            Port 8001                          |   |
|   +----------------------+------------------------+   |
|                          |                            |
|   +------+------+--------+--------+------+------+    |
|   |      |      |        |        |      |      |    |
|   v      v      v        v        v      v      v    |
|  +--+  +--+  +--+  +--+  +--+  +--+  +--+  +--+      |
|  |A1|  |A2|  |A3|  |A4|  |A5|  |..|  |An|  |..|      |
|  +--+  +--+  +--+  +--+  +--+  +--+  +--+  +--+      |
|                                                       |
|         Agent Containers (Docker Compose)             |
+-------------------------------------------------------+
```

### Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                     MYCA Orchestrator                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Agent   │  │   Task   │  │   Gap    │  │  Agent   │    │
│  │  Pool    │  │  Router  │  │ Detector │  │ Factory  │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌───────────────────────────────────────────────────────────┐
│                    Message Broker (Redis)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Pub/Sub   │  │   Streams   │  │   Cache     │        │
│  │  (Events)   │  │  (Tasks)    │  │  (State)    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└───────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│                     Agent Containers                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │Corporate│ │  Infra  │ │ Device  │ │  Data   │          │
│  │   (9)   │ │   (8)   │ │   (8)   │ │   (4)   │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ┌─────────────────────────────────────────────┐          │
│  │           Integration Agents (11)            │          │
│  └─────────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│                    Memory Systems                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    Redis    │  │   MINDEX    │  │   Qdrant    │        │
│  │ (Short-term)│  │ (Long-term) │  │  (Vectors)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└───────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Phase 1: Agent Container Runtime Engine

Created the foundational runtime system that allows agents to run in isolated Docker containers.

#### Models (`mycosoft_mas/runtime/models.py`)

Defined core data structures:

| Class | Purpose |
|-------|---------|
| `AgentStatus` | Lifecycle states (SPAWNING, ACTIVE, BUSY, IDLE, PAUSED, ERROR, SHUTDOWN, DEAD, ARCHIVED) |
| `MessageType` | Communication types (REQUEST, RESPONSE, EVENT, COMMAND, HEARTBEAT, BROADCAST, ACK) |
| `TaskPriority` | Priority levels (CRITICAL=10, HIGH=8, NORMAL=5, LOW=3, BACKGROUND=1) |
| `AgentCategory` | Agent categories (CORE, CORPORATE, FINANCIAL, MYCOLOGY, DATA, etc.) |
| `AgentConfig` | Agent configuration with resource limits, capabilities, settings |
| `AgentState` | Current runtime state of an agent |
| `AgentMessage` | Agent-to-Agent message format |
| `AgentTask` | Task to be executed by an agent |
| `AgentSnapshot` | State snapshot for persistence/recovery |
| `AgentMetrics` | Performance metrics for monitoring |

#### Agent Runtime (`mycosoft_mas/runtime/agent_runtime.py`)

Core execution engine that runs inside each agent container:

```python
class AgentRuntime:
    """
    Each agent runs an instance of this class which:
    - Listens for tasks from the orchestrator via Redis
    - Executes tasks using the agent's specific logic
    - Reports health and metrics
    - Handles graceful shutdown and snapshots
    """
```

Key features:
- Health check HTTP server on port 8080
- Task queue consumer
- Heartbeat loop
- Message handling
- MINDEX logging
- Graceful shutdown

#### Agent Pool (`mycosoft_mas/runtime/agent_pool.py`)

Manages the pool of running agent containers:

```python
class AgentPool:
    """
    Provides methods for:
    - Spawning new agent containers
    - Stopping agent containers
    - Monitoring container health
    - Scaling agents up/down
    - Resource management
    """
```

Key methods:
- `spawn_agent(config)` - Create and start container
- `stop_agent(agent_id, force)` - Stop container
- `restart_agent(agent_id)` - Restart container
- `get_agent_state(agent_id)` - Get current state
- `update_agent_health()` - Check all agent health

#### Message Broker (`mycosoft_mas/runtime/message_broker.py`)

Handles Agent-to-Agent communication via Redis:

```python
class MessageBroker:
    """
    Uses Redis for:
    - Pub/Sub for real-time events and broadcasts
    - Streams for persistent task queues
    """
```

Key methods:
- `publish(channel, message)` - Publish to channel
- `subscribe(channel, callback)` - Subscribe with callback
- `add_to_stream(stream, data)` - Add to Redis Stream
- `read_from_stream(...)` - Read from Stream as consumer

#### Snapshot Manager (`mycosoft_mas/runtime/snapshot_manager.py`)

Manages agent state snapshots:

```python
class SnapshotManager:
    """
    Provides methods for:
    - Creating snapshots of agent state
    - Restoring agents from snapshots
    - Listing available snapshots
    - Cleaning up old snapshots
    """
```

---

### Phase 2: MYCA Orchestrator Upgrade

#### Orchestrator Service (`mycosoft_mas/core/orchestrator_service.py`)

Central intelligence for managing all agents:

```python
class OrchestratorService:
    """
    Central intelligence that:
    - Manages agent lifecycle (spawn, stop, restart)
    - Distributes tasks to agents
    - Monitors agent health
    - Handles agent-to-agent communication
    - Detects gaps and auto-creates agents
    """
```

FastAPI endpoints provided:
- `GET /health` - Health check
- `GET /status` - Orchestrator status
- `GET /agents` - List all agents
- `GET /agents/{id}` - Agent details
- `POST /agents/spawn` - Spawn new agent
- `POST /agents/{id}/stop` - Stop agent
- `POST /agents/{id}/restart` - Restart agent
- `POST /agents/register` - Agent self-registration
- `POST /tasks` - Submit task
- `GET /tasks/{id}` - Task status
- `POST /messages` - Send agent message
- `GET /gaps` - Detect missing agents

#### Gap Detector (`mycosoft_mas/runtime/gap_detector.py`)

Detects missing agents that should exist:

```python
class GapDetector:
    """
    Gap Types:
    - Category: Missing agents in required categories
    - Route: API routes without monitoring agents
    - Integration: External services without agents
    - Device: MycoBrain devices without agents
    """
```

Required agents defined for each category:
- CORE: 3 agents (myca-core, task-router, event-processor)
- CORPORATE: 3 agents (ceo-agent, cfo-agent, cto-agent)
- INFRASTRUCTURE: 5 agents (proxmox, docker, network, storage, monitoring)
- SECURITY: 2 agents (soc-agent, audit-agent)
- DEVICE: 1 agent (mycobrain-coordinator)
- INTEGRATION: 3 agents (n8n, zapier, elevenlabs)
- DATA: 3 agents (mindex, etl, search)

#### Agent Factory (`mycosoft_mas/runtime/agent_factory.py`)

Creates new agents from templates:

```python
class AgentFactory:
    """
    Provides:
    - Template-based agent creation
    - Validation before creation
    - Approval workflow for certain agent types
    - Event logging
    """
```

Templates defined:
- `infrastructure` - Infrastructure management
- `data` - Data operations
- `security` - Security monitoring
- `device` - IoT device control
- `integration` - External integrations
- `route-monitor` - API route monitoring

---

### Phase 3: Priority Agents Implementation

Created 40 agent classes across 5 categories in `mycosoft_mas/agents/v2/`.

#### Base Agent (`base_agent_v2.py`)

Abstract base class all agents inherit from:

```python
class BaseAgentV2(ABC):
    """
    All agents should inherit and implement:
    - execute_task: Main task execution logic
    - get_capabilities: List of agent capabilities
    """
```

Standard capabilities:
- Health check handling
- Status reporting
- Capability listing
- Message sending
- Task execution
- MINDEX logging

#### Corporate Agents (`corporate_agents.py`)

| Agent | Type | Responsibilities |
|-------|------|-----------------|
| CEOAgent | ceo | Strategic decisions, major approvals |
| CFOAgent | cfo | Financial oversight, budget management |
| CTOAgent | cto | Technology decisions, architecture review |
| COOAgent | coo | Operations coordination, process optimization |
| LegalAgent | legal | Compliance, contracts, regulatory |
| HRAgent | hr | Team coordination, performance tracking |
| MarketingAgent | marketing | Brand, communications, campaigns |
| SalesAgent | sales | Revenue, customer relationships |
| ProcurementAgent | procurement | Vendor management, purchasing |

#### Infrastructure Agents (`infrastructure_agents.py`)

| Agent | Type | Responsibilities |
|-------|------|-----------------|
| ProxmoxAgent | proxmox | VM lifecycle, snapshots, resources |
| DockerAgent | docker | Container orchestration, images |
| NetworkAgent | network | UniFi integration, firewall, VLANs |
| StorageAgent | storage | NAS management, backups |
| MonitoringAgent | monitoring | Prometheus/Grafana, alerting |
| DeploymentAgent | deployment | CI/CD, deployments |
| CloudflareAgent | cloudflare | DNS, cache, tunnels |
| SecurityAgent | security | SOC integration, threat response |

#### Device Agents (`device_agents.py`)

| Agent | Type | Responsibilities |
|-------|------|-----------------|
| MycoBrainCoordinatorAgent | mycobrain-coordinator | Fleet management |
| MycoBrainDeviceAgent | mycobrain-device | Individual device control |
| BME688SensorAgent | sensor-bme688 | Air quality sensors |
| BME690SensorAgent | sensor-bme690 | Advanced sensors |
| LoRaGatewayAgent | lora-gateway | Radio communication |
| FirmwareAgent | firmware | OTA updates |
| MycoDroneAgent | mycodrone | Drone integration |
| SpectrometerAgent | spectrometer | Spectral analysis |

#### Data Agents (`data_agents.py`)

| Agent | Type | Responsibilities |
|-------|------|-----------------|
| MindexAgent | mindex | Database operations, ETL |
| ETLAgent | etl | Data pipeline management |
| SearchAgent | search | Search operations |
| RouteMonitorAgent | route-monitor | API route monitoring |

#### Integration Agents (`integration_agents.py`)

| Agent | Type | Responsibilities |
|-------|------|-----------------|
| N8NAgent | n8n | Workflow automation |
| ElevenLabsAgent | elevenlabs | Voice synthesis |
| ZapierAgent | zapier | 5000+ app integrations |
| IFTTTAgent | ifttt | Simple automation |
| OpenAIAgent | openai | GPT integration |
| AnthropicAgent | anthropic | Claude integration |
| GeminiAgent | gemini | Google AI |
| GrokAgent | grok | xAI real-time knowledge |
| SupabaseAgent | supabase | Auth/database |
| NotionAgent | notion | Documentation |
| WebsiteAgent | website | Website health |

---

### Phase 4: Dashboard and Memory Systems

#### Dashboard API (`mycosoft_mas/core/dashboard_api.py`)

Real-time monitoring endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/dashboard/agents` | GET | List all agents |
| `/api/dashboard/agents/{id}` | GET | Agent details |
| `/api/dashboard/agents/{id}/logs` | GET | Agent logs |
| `/api/dashboard/stats` | GET | Pool statistics |
| `/api/dashboard/topology` | GET | Graph data |
| `/api/dashboard/ws` | WebSocket | Real-time updates |
| `/api/dashboard/stream` | GET | SSE log stream |

WebSocket message types:
- `initial_state` - Full agent list on connect
- `agent_update` - Periodic status updates
- `heartbeat` - Keep-alive
- `ping/pong` - Client heartbeat

#### Memory Manager (`mycosoft_mas/runtime/memory_manager.py`)

Unified memory interface:

```python
class UnifiedMemoryManager:
    """
    Provides a single API for:
    - Short-term memory operations (Redis)
    - Long-term memory storage (MINDEX)
    - Semantic search (Qdrant)
    """
```

**ShortTermMemory (Redis):**
- Conversation context (last 10 messages)
- Current task state
- Agent configuration
- Temporary data with TTL

**LongTermMemory (MINDEX):**
- Agent activity logs
- Decision history
- Performance metrics
- Permanent knowledge

**VectorMemory (Qdrant):**
- Document embeddings
- Conversation embeddings
- Semantic search

---

### Phase 5: Database Schema

Created `migrations/003_agent_logging.sql` with:

#### Tables

**agent_logs**
```sql
- id SERIAL PRIMARY KEY
- agent_id VARCHAR(100)
- timestamp TIMESTAMPTZ
- action_type VARCHAR(100)
- input_summary TEXT
- output_summary TEXT
- success BOOLEAN
- duration_ms INTEGER
- resources_used JSONB
- related_agents TEXT[]
```

**agent_snapshots**
```sql
- id SERIAL PRIMARY KEY
- agent_id VARCHAR(100)
- snapshot_time TIMESTAMPTZ
- state JSONB
- config JSONB
- pending_tasks JSONB
- memory_state JSONB
- reason VARCHAR(255)
```

**agent_metrics**
```sql
- id SERIAL PRIMARY KEY
- agent_id VARCHAR(100)
- timestamp TIMESTAMPTZ
- cpu_percent FLOAT
- memory_mb INTEGER
- tasks_completed INTEGER
- tasks_failed INTEGER
- avg_task_duration_ms FLOAT
- messages_sent INTEGER
- messages_received INTEGER
- uptime_seconds INTEGER
- error_count INTEGER
```

**agent_messages**
```sql
- id SERIAL PRIMARY KEY
- message_id UUID
- from_agent VARCHAR(100)
- to_agent VARCHAR(100)
- message_type VARCHAR(50)
- payload JSONB
- priority INTEGER
- timestamp TIMESTAMPTZ
- correlation_id UUID
- acknowledged BOOLEAN
```

**agent_knowledge**
```sql
- id SERIAL PRIMARY KEY
- agent_id VARCHAR(100)
- key VARCHAR(255)
- value JSONB
- created_at TIMESTAMPTZ
- updated_at TIMESTAMPTZ
- expires_at TIMESTAMPTZ
```

#### Views

- `agent_activity_summary` - Aggregated activity per agent
- `recent_agent_errors` - Last 100 failed actions

#### Functions

- `cleanup_old_agent_logs(days)` - Remove old log entries
- `cleanup_old_agent_metrics(days)` - Remove old metrics

---

## File Inventory

### Runtime Engine Files

| File | Size | Purpose |
|------|------|---------|
| `mycosoft_mas/runtime/__init__.py` | 1.2 KB | Module initialization and exports |
| `mycosoft_mas/runtime/models.py` | 12.4 KB | Data models and enums |
| `mycosoft_mas/runtime/agent_runtime.py` | 16.4 KB | Core agent execution engine |
| `mycosoft_mas/runtime/agent_pool.py` | 11.4 KB | Container pool management |
| `mycosoft_mas/runtime/message_broker.py` | 7.0 KB | Redis Pub/Sub and Streams |
| `mycosoft_mas/runtime/snapshot_manager.py` | 5.2 KB | State persistence |
| `mycosoft_mas/runtime/memory_manager.py` | 12.7 KB | Unified memory interface |
| `mycosoft_mas/runtime/gap_detector.py` | 11.0 KB | Missing agent detection |
| `mycosoft_mas/runtime/agent_factory.py` | 10.2 KB | Agent template factory |

### Orchestrator Files

| File | Size | Purpose |
|------|------|---------|
| `mycosoft_mas/core/orchestrator_service.py` | 17.3 KB | Main orchestrator service |
| `mycosoft_mas/core/dashboard_api.py` | 6.6 KB | Dashboard API endpoints |

### Agent Files

| File | Size | Agent Classes |
|------|------|---------------|
| `mycosoft_mas/agents/v2/__init__.py` | 4.2 KB | Exports and registry |
| `mycosoft_mas/agents/v2/base_agent_v2.py` | 10.3 KB | Base agent class |
| `mycosoft_mas/agents/v2/corporate_agents.py` | 12.9 KB | 9 agents |
| `mycosoft_mas/agents/v2/infrastructure_agents.py` | 11.1 KB | 8 agents |
| `mycosoft_mas/agents/v2/device_agents.py` | 10.1 KB | 8 agents |
| `mycosoft_mas/agents/v2/data_agents.py` | 4.2 KB | 4 agents |
| `mycosoft_mas/agents/v2/integration_agents.py` | 17.6 KB | 11 agents |

### Docker Files

| File | Size | Purpose |
|------|------|---------|
| `docker/Dockerfile.agent` | 2.5 KB | Agent container image |
| `docker/docker-compose.agents.yml` | 7.0 KB | Full stack deployment |

### Database Files

| File | Size | Purpose |
|------|------|---------|
| `migrations/003_agent_logging.sql` | 5.5 KB | Schema additions |

### Documentation Files

| File | Size | Purpose |
|------|------|---------|
| `docs/MAS_V2_IMPLEMENTATION_SUMMARY.md` | 9.6 KB | Implementation summary |
| `docs/MAS_VM_PROVISIONING_GUIDE.md` | 7.0 KB | VM setup guide |
| `docs/DASHBOARD_COMPONENTS.md` | 2.3 KB | Dashboard component specs |
| `docs/MAS_V2_COMPLETE_DOCUMENTATION.md` | This file | Complete documentation |

### Script Files

| File | Purpose |
|------|---------|
| `scripts/create_runtime_files.py` | Creates runtime engine files |
| `scripts/create_orchestrator_upgrade.py` | Creates orchestrator files |
| `scripts/create_priority_agents.py` | Creates agent class files |
| `scripts/create_integration_agents.py` | Creates integration agent files |
| `scripts/create_dashboard_and_memory.py` | Creates dashboard and memory files |
| `scripts/provision_mas_vm.py` | Provisions MAS VM in Proxmox |
| `scripts/verify_implementation.py` | Verifies all files created |

---

## Agent Registry

### Complete Agent List (40 Agents)

```python
AGENT_REGISTRY = {
    # Corporate (9)
    "ceo-agent": CEOAgent,
    "cfo-agent": CFOAgent,
    "cto-agent": CTOAgent,
    "coo-agent": COOAgent,
    "legal-agent": LegalAgent,
    "hr-agent": HRAgent,
    "marketing-agent": MarketingAgent,
    "sales-agent": SalesAgent,
    "procurement-agent": ProcurementAgent,
    
    # Infrastructure (8)
    "proxmox-agent": ProxmoxAgent,
    "docker-agent": DockerAgent,
    "network-agent": NetworkAgent,
    "storage-agent": StorageAgent,
    "monitoring-agent": MonitoringAgent,
    "deployment-agent": DeploymentAgent,
    "cloudflare-agent": CloudflareAgent,
    "security-agent": SecurityAgent,
    
    # Device (7)
    "mycobrain-coordinator": MycoBrainCoordinatorAgent,
    "bme688-agent": BME688SensorAgent,
    "bme690-agent": BME690SensorAgent,
    "lora-gateway-agent": LoRaGatewayAgent,
    "firmware-agent": FirmwareAgent,
    "mycodrone-agent": MycoDroneAgent,
    "spectrometer-agent": SpectrometerAgent,
    
    # Data (3)
    "mindex-agent": MindexAgent,
    "etl-agent": ETLAgent,
    "search-agent": SearchAgent,
    
    # Integration (11)
    "n8n-agent": N8NAgent,
    "elevenlabs-agent": ElevenLabsAgent,
    "zapier-agent": ZapierAgent,
    "ifttt-agent": IFTTTAgent,
    "openai-agent": OpenAIAgent,
    "anthropic-agent": AnthropicAgent,
    "gemini-agent": GeminiAgent,
    "grok-agent": GrokAgent,
    "supabase-agent": SupabaseAgent,
    "notion-agent": NotionAgent,
    "website-agent": WebsiteAgent,
}
```

---

## API Reference

### Orchestrator API (Port 8001)

#### Health Check
```
GET /health
Response: { "status": "ok", "service": "myca-orchestrator" }
```

#### Orchestrator Status
```
GET /status
Response: {
    "status": "running",
    "started": true,
    "total_agents": 10,
    "pool_stats": {...},
    "pending_tasks": 5,
    "message_broker_connected": true
}
```

#### List Agents
```
GET /agents
Response: {
    "agents": [
        {
            "agent_id": "ceo-agent",
            "status": "active",
            "container_id": "abc123",
            "tasks_completed": 42,
            ...
        }
    ]
}
```

#### Spawn Agent
```
POST /agents/spawn
Body: {
    "agent_id": "custom-agent",
    "agent_type": "custom",
    "category": "core",
    "display_name": "Custom Agent",
    "cpu_limit": 1.0,
    "memory_limit": 512
}
Response: { "agent_id": "custom-agent", "status": "spawning", ... }
```

#### Submit Task
```
POST /tasks
Body: {
    "agent_id": "ceo-agent",
    "task_type": "approve_action",
    "payload": { "action": "deploy", "impact": "medium" },
    "priority": 8,
    "timeout": 300
}
Response: { "task_id": "uuid", "status": "submitted" }
```

#### Send Message
```
POST /messages
Body: {
    "from_agent": "ceo-agent",
    "to_agent": "cfo-agent",
    "message_type": "request",
    "payload": { "task_type": "budget_check" },
    "priority": 5
}
Response: { "message_id": "uuid", "status": "sent" }
```

### Dashboard API

#### WebSocket Connection
```
WS /api/dashboard/ws

Server Messages:
- { "type": "initial_state", "agents": [...] }
- { "type": "agent_update", "agents": [...], "timestamp": "..." }
- { "type": "heartbeat" }

Client Messages:
- { "type": "ping" }
- { "type": "subscribe", "agent_id": "ceo-agent" }
```

#### Server-Sent Events
```
GET /api/dashboard/stream
Response: text/event-stream

data: {"type": "agent_update", "agents": [...]}
```

---

## Database Schema

### Entity Relationship

```
┌─────────────────┐     ┌─────────────────┐
│   agent_logs    │     │ agent_snapshots │
├─────────────────┤     ├─────────────────┤
│ id              │     │ id              │
│ agent_id  ──────┼──┐  │ agent_id  ──────┼──┐
│ timestamp       │  │  │ snapshot_time   │  │
│ action_type     │  │  │ state           │  │
│ input_summary   │  │  │ config          │  │
│ output_summary  │  │  │ pending_tasks   │  │
│ success         │  │  │ memory_state    │  │
│ duration_ms     │  │  │ reason          │  │
└─────────────────┘  │  └─────────────────┘  │
                     │                       │
┌─────────────────┐  │  ┌─────────────────┐  │
│  agent_metrics  │  │  │ agent_messages  │  │
├─────────────────┤  │  ├─────────────────┤  │
│ id              │  │  │ id              │  │
│ agent_id  ──────┼──┤  │ message_id      │  │
│ timestamp       │  │  │ from_agent ─────┼──┤
│ cpu_percent     │  │  │ to_agent  ──────┼──┤
│ memory_mb       │  │  │ message_type    │  │
│ tasks_completed │  │  │ payload         │  │
│ tasks_failed    │  │  │ priority        │  │
│ ...             │  │  │ timestamp       │  │
└─────────────────┘  │  │ correlation_id  │  │
                     │  │ acknowledged    │  │
┌─────────────────┐  │  └─────────────────┘  │
│ agent_knowledge │  │                       │
├─────────────────┤  │  All agent_id fields  │
│ id              │  │  reference the same   │
│ agent_id  ──────┼──┘  agent identifier     │
│ key             │                          │
│ value           │                          │
│ created_at      │                          │
│ updated_at      │                          │
│ expires_at      │                          │
└─────────────────┘                          │
```

---

## Deployment Guide

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Redis server
- PostgreSQL (MINDEX)
- Qdrant (optional, for vector search)

### Quick Start

1. **Clone and setup:**
```bash
cd /opt/mycosoft
git clone https://github.com/mycosoft/mycosoft-mas.git
cd mycosoft-mas
```

2. **Build agent image:**
```bash
docker build -t mycosoft/mas-agent:latest -f docker/Dockerfile.agent .
```

3. **Run database migration:**
```bash
psql -U mas -d mindex -f migrations/003_agent_logging.sql
```

4. **Start MAS stack:**
```bash
docker compose -f docker/docker-compose.agents.yml up -d
```

5. **Verify health:**
```bash
curl http://localhost:8001/health
curl http://localhost:8001/agents
```

### Production Deployment

See `docs/MAS_VM_PROVISIONING_GUIDE.md` for full production setup including:
- Dedicated MAS VM (16 cores, 64 GB RAM)
- Redis cluster configuration
- Monitoring with Prometheus/Grafana
- Snapshot strategy
- Security hardening

---

## Configuration Reference

### Environment Variables

```bash
# MAS Configuration
REDIS_URL=redis://redis:6379/0
MINDEX_URL=http://mindex:8000
ORCHESTRATOR_URL=http://localhost:8001
QDRANT_URL=http://qdrant:6333

# Agent Settings
AGENT_ID=<auto-generated>
AGENT_TYPE=<from-template>
AGENT_CATEGORY=<category>
LOG_LEVEL=INFO
HEALTH_CHECK_INTERVAL=30
HEARTBEAT_INTERVAL=10
TASK_TIMEOUT=300
MAX_CONCURRENT_TASKS=5

# Resource Limits
CPU_LIMIT=1.0
MEMORY_LIMIT=512

# Integration Keys
PROXMOX_HOST=192.168.0.100
PROXMOX_TOKEN=<token>
UNIFI_HOST=192.168.1.1
UNIFI_USERNAME=<username>
UNIFI_PASSWORD=<password>
ELEVENLABS_API_KEY=<key>
OPENAI_API_KEY=<key>
ANTHROPIC_API_KEY=<key>
N8N_HOST=http://n8n:5678
```

### Docker Compose Services

```yaml
services:
  myca-orchestrator:     # Port 8001
  redis:                 # Port 6379
  myca-core:            # Core agent
  proxmox-agent:        # Proxmox management
  docker-agent:         # Container management
  soc-agent:            # Security
  n8n-agent:            # Workflow automation
  elevenlabs-agent:     # Voice synthesis
  mindex-agent:         # Database operations
  mycobrain-coordinator: # Device fleet
```

---

## Scripts Reference

| Script | Usage | Purpose |
|--------|-------|---------|
| `create_runtime_files.py` | `python scripts/create_runtime_files.py` | Creates all runtime engine files |
| `create_orchestrator_upgrade.py` | `python scripts/create_orchestrator_upgrade.py` | Creates orchestrator and gap detector |
| `create_priority_agents.py` | `python scripts/create_priority_agents.py` | Creates 30 priority agents |
| `create_integration_agents.py` | `python scripts/create_integration_agents.py` | Creates integration agents |
| `create_dashboard_and_memory.py` | `python scripts/create_dashboard_and_memory.py` | Creates dashboard API and memory manager |
| `provision_mas_vm.py` | `python scripts/provision_mas_vm.py` | Creates MAS VM in Proxmox |
| `verify_implementation.py` | `python scripts/verify_implementation.py` | Verifies all files exist |

---

## Next Steps

### Immediate (Deploy)

1. **Commit changes:**
   ```bash
   git add .
   git commit -m "Implement MAS v2 Architecture"
   git push origin main
   ```

2. **Deploy to Sandbox VM:**
   - SSH to 192.168.0.187
   - Pull latest code
   - Rebuild Docker images
   - Run migration
   - Start services

3. **Provision MAS VM:**
   - Run `provision_mas_vm.py`
   - Install Ubuntu 22.04
   - Configure network (192.168.0.188)
   - Deploy MAS stack

### Short-term (Dashboard UI)

1. Create React components:
   - `website/app/myca/dashboard/page.tsx`
   - `website/app/myca/agents/page.tsx`
   - `website/app/myca/agents/[id]/page.tsx`
   - `website/components/agents/AgentCard.tsx`
   - `website/components/agents/AgentTerminal.tsx`
   - `website/components/agents/AgentTopology.tsx`

2. Connect to WebSocket API

3. Implement real-time visualizations

### Medium-term (Operations)

1. Start priority agents in production
2. Configure integration credentials
3. Set up monitoring and alerting
4. Implement agent auto-scaling
5. Train NLM models with Qdrant embeddings

### Long-term (Optimization)

1. Analyze agent performance metrics
2. Optimize resource allocation
3. Implement advanced A2A protocols
4. Add more specialized agents
5. Enhance gap detection intelligence

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-01-24 | Initial MAS v2 implementation |

---

## Contributors

- MYCA Orchestrator (Implementation)
- Cursor AI Assistant (Architecture & Code Generation)

---

*This document was generated as part of the MAS v2 Architecture Overhaul implementation on January 24, 2026.*
