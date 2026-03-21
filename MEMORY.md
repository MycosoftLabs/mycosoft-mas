# MYCA Memory Architecture

MYCA's memory is how she persists across sessions, learns from experience, shares knowledge between agents, and maintains continuity of self. This document is the complete reference for all memory systems.

## 6-Layer Memory Model

MYCA's memory mirrors biological memory — from fleeting thoughts to permanent knowledge:

```
                    ┌─────────────────────────────────────┐
                    │          SYSTEM (permanent)          │  Config, behaviors, global state
                    ├─────────────────────────────────────┤
                    │         EPISODIC (permanent)         │  Event history, task logs
                    ├─────────────────────────────────────┤
                    │         SEMANTIC (permanent)         │  Facts, knowledge, learned patterns
                    ├─────────────────────────────────────┤
                    │          WORKING (7 days)            │  Active task state, findings
                    ├─────────────────────────────────────┤
                    │          SESSION (24 hours)          │  Current conversation context
                    ├─────────────────────────────────────┤
                    │         EPHEMERAL (30 min)           │  Scratch space, transient data
                    └─────────────────────────────────────┘
```

| Layer | TTL | Backend | Use Cases |
|-------|-----|---------|-----------|
| **Ephemeral** | 30 min | In-memory | Reasoning scratch, temp calculations |
| **Session** | 24 hours | Redis | Conversation turns, dialog state |
| **Working** | 7 days | Redis | Active task state, temp findings |
| **Semantic** | Permanent | PostgreSQL + Qdrant | Long-term facts, learned patterns |
| **Episodic** | Permanent | PostgreSQL | Events, task completions, errors |
| **System** | Permanent | PostgreSQL | Configuration, learned behaviors |
| **Procedural** | Permanent | PostgreSQL | Learned procedures, playbooks |

**Implementation:** `mycosoft_mas/memory/myca_memory.py`

## Storage Backends

All data lives on **MINDEX VM (192.168.0.189)**:

### PostgreSQL (189:5432)
- **Persistent storage** for semantic, episodic, system, procedural layers
- Tables: `mindex.memory_entries`, `mindex.episodic_events`, `mindex.knowledge_nodes`, `mindex.knowledge_edges`, `mindex.semantic_facts`
- Indexed by scope, namespace, timestamp, TTL

### Redis (189:6379)
- **Short-term state** for ephemeral, session, working layers
- **Pub/sub** for agent-to-agent memory sharing
- Key patterns:
  - `mas:memory:conversation:*` — conversation context
  - `mas:memory:agent:*` — agent working memory
  - `mas:memory:ephemeral:*` — scratch space
  - `mas:memory:broadcast` — A2A shared memories
  - `mas:memory:sync` — sync events

### Qdrant (189:6333)
- **Vector embeddings** for semantic search
- Collections: `mycosoft_memory`, `semantic_facts`, `myca_semantic_memory`
- 1536 dimensions (OpenAI) or 768 dimensions (Gemini)
- Cosine distance similarity

## Scope Routing

When memory is written, the scope determines which backend handles it:

| Scope | Backend | TTL | Use |
|-------|---------|-----|-----|
| `CONVERSATION` | Redis | 3600s | Dialog turns |
| `USER` | Postgres + Qdrant | Permanent | User profiles |
| `AGENT` | Redis | 86400s | Agent state |
| `SYSTEM` | PostgreSQL | Permanent | Global config |
| `EPHEMERAL` | Redis | 60s | Transient |
| `DEVICE` | PostgreSQL | Permanent | Hardware state |
| `EXPERIMENT` | Postgres + Qdrant | Permanent | Scientific data |
| `WORKFLOW` | Redis + Postgres | 604800s | n8n execution |

**Implementation:** `mycosoft_mas/memory/service.py`

## Agent Memory Integration

Every agent inherits `AgentMemoryMixin` (`mycosoft_mas/agents/memory_mixin.py`):

```python
# Store a memory
await self.remember(
    content="User prefers dark mode",
    importance=0.7,
    layer="semantic",
    tags=["preference", "ui"]
)

# Recall memories
memories = await self.recall(
    query="user preferences",
    tags=["preference"],
    layer="semantic",
    limit=10
)

# Learn a permanent fact
await self.learn_fact({"subject": "Amanita muscaria", "predicate": "contains", "object": "ibotenic acid"})

# Record a task completion (episodic)
await self.record_task_completion(task_id, result, success=True)

# Share knowledge with other agents
await self.share_with_agents(
    content="New species identified in MINDEX",
    target_agents=["mycology_agent", "search_agent"]
)

# Save state for next session
await self.save_agent_state()
```

## Memory Coordinator

Central hub that routes all memory operations (`mycosoft_mas/memory/coordinator.py`):

```
MemoryCoordinator (singleton)
├── MYCAMemory — 6-layer system
├── ConversationMemory — turn tracking (max 100 turns, auto-summarize at 20)
├── EpisodicMemory — PostgreSQL event logs
├── CrossSessionMemory — user profiles across sessions
├── ProceduralMemory — learned workflows and procedures
├── PersonaPlexMemory — voice session persistence
├── N8NMemory — workflow execution history
└── A2AMemory — agent-to-agent knowledge sharing
```

## Agent-to-Agent Memory (A2A)

Agents share knowledge via Redis pub/sub:

| Channel | Purpose |
|---------|---------|
| `mas:memory:broadcast` | Share new memories with all/specific agents |
| `mas:memory:query` | Request memories from other agents |
| `mas:memory:response` | Respond to memory queries |
| `mas:memory:sync` | Sync events |

**Implementation:** `mycosoft_mas/memory/a2a_memory.py`

## Knowledge Graph

Structured relationships between concepts:

- **Node types:** Species, Device, Location, Event, User, Session, Concept, Prediction, Observation, Entity, Fact
- **Edge types:** related_to, contains, located_at, observed_by, belongs_to, derived_from, similar_to, preceded_by, caused_by, part_of
- **Backend:** PostgreSQL with vector embeddings
- **Implementation:** `mycosoft_mas/memory/graph_memory.py`, `mycosoft_mas/memory/mindex_graph.py`

## Event Ledger (Audit Trail)

Append-only JSONL log of all tool calls and actions (`mycosoft_mas/myca/event_ledger/`):

```json
{
  "ts": 1708200000,
  "session_id": "abc-123",
  "agent": "dev_agent",
  "tool": "file_editor",
  "args_hash": "sha256:abc123...",
  "result_status": "success",
  "elapsed_ms": 150,
  "risk_flags": [],
  "artifacts": ["path/to/file.py"]
}
```

- **Never logs full arguments** (privacy) — only SHA256 hashes
- **Risk flags:** injection_attempt, secret_attempt, path_denied, network_denied, sandbox_violation, timeout, high_risk_approved
- **Retention:** 7 days detailed, 30 days aggregated, then cold storage

## Memory Lifecycle

```
Agent Start
  └→ init_memory() → load MemoryCoordinator (singleton)
       └→ _load_agent_context() → restore from PostgreSQL (semantic layer)

Runtime
  └→ remember() / recall() / learn_fact() → route by scope/layer
       └→ Redis (transient) or Postgres+Qdrant (permanent)

Consolidation (every 5 min)
  └→ ephemeral memories decay → promote important ones to session → episodic

Agent Shutdown
  └→ save_agent_state() → persist final state to semantic layer
```

## Memory API

REST endpoints for external access (`mycosoft_mas/core/routers/memory_api.py`):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/memory/write` | POST | Store memory value |
| `/api/memory/read` | POST | Retrieve memory (with semantic search) |
| `/api/memory/delete` | POST | Remove memory (requires scope+namespace+key) |
| `/api/memory/summarize` | POST | Summarize conversation (with archive option) |
| `/api/memory/health` | GET | Backend health status |
| `/api/memory/audit` | GET | Operation audit trail |

## MCP Memory Server

Tools for Claude/Cursor MCP clients (`mycosoft_mas/memory/mcp_memory_server.py`):

- `memory_write` — store with category, importance, tags
- `memory_read` — read by ID
- `memory_search` — semantic search across all memory
- `memory_list` — list with filters
- `memory_update` — modify existing
- `memory_delete` — remove

## Specialized Memory Systems

| System | File | Purpose |
|--------|------|---------|
| Voice sessions | `memory/personaplex_memory.py` | Voice conversation persistence, emotion tracking |
| n8n workflows | `memory/n8n_memory.py` | Workflow execution history, status tracking |
| Search memory | `memory/search_memory.py` | Full-text search across all memory |
| Vector memory | `memory/vector_memory.py` | pgvector integration, embedding cache |
| Earth2 memory | `routers/earth2_memory_api.py` | Climate simulation memories |

## Embeddings

Vector embeddings for semantic search (`mycosoft_mas/memory/embeddings.py`):

| Provider | Model | Dimensions |
|----------|-------|------------|
| OpenAI | text-embedding-ada-002 | 1536 |
| Gemini | embedding-001 | 768 |

## Key Implementation Files

| File | Purpose |
|------|---------|
| `memory/myca_memory.py` | Core 6-layer memory |
| `memory/service.py` | Unified memory service (scope routing) |
| `memory/coordinator.py` | Central coordinator hub |
| `memory/memory_modules.py` | ConversationMemory, CrossSessionMemory |
| `memory/episodic_memory.py` | Event-based memories |
| `memory/semantic_memory.py` | Factual knowledge (Qdrant) |
| `memory/procedural_memory.py` | Learned procedures |
| `memory/session_memory.py` | Per-session state |
| `memory/graph_memory.py` | Knowledge graph |
| `memory/vector_memory.py` | pgvector integration |
| `memory/a2a_memory.py` | Agent-to-agent sharing |
| `memory/personaplex_memory.py` | Voice session memory |
| `memory/n8n_memory.py` | Workflow execution memory |
| `memory/embeddings.py` | Vector embedding providers |
| `memory/mcp_memory_server.py` | MCP tool interface |
| `agents/memory_mixin.py` | Agent memory methods |
| `myca/event_ledger/ledger_writer.py` | Audit trail |

| `memory/persistent_graph.py` | Persistent knowledge graph |
| `memory/analytics.py` | Memory analytics |
| `memory/user_context.py` | User context memory |
| `memory/autobiographical.py` | Autobiographical memory |
| `memory/cleanup.py` | Memory cleanup tasks |
| `memory/earth2_memory.py` | Earth2 specific memory |
| `memory/export.py` | Memory export tools |
| `memory/fungal_memory_bridge.py` | Fungal network memory bridge |
| `memory/gpu_memory.py` | GPU memory integration |
| `memory/graph_indexer.py` | Graph memory indexer |
| `memory/graph_schema.py` | Graph memory schema |
| `memory/langgraph_checkpointer.py` | LangGraph checkpointer |
| `memory/long_term.py` | Long term memory |
| `memory/mem0_adapter.py` | Mem0 adapter |
| `memory/openviking_bridge.py` | OpenViking bridge |
| `memory/openviking_sync.py` | OpenViking sync |
| `memory/short_term.py` | Short term memory |
| `memory/temporal_patterns.py` | Temporal memory patterns |
| `memory/voice_search_memory.py` | Voice search memory |

### Memory API Routers
| `core/routers/memory_api.py` | Memory API routing |
| `core/routers/memory_integration_api.py` | Integration API |
| `core/routers/conversation_memory_api.py` | Conversation Memory API |
| `core/routers/earth2_memory_api.py` | Earth2 Memory API |
| `core/routers/search_memory_api.py` | Search Memory API |
| `core/routers/memory_updates_ws.py` | Memory Updates WebSocket |
