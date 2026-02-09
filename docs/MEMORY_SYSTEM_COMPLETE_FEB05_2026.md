# MYCA Memory System Complete - February 5, 2026

## Executive Summary

The MYCA Memory System is now fully integrated across backend, frontend, and API layers. This document provides a complete reference for the memory system as of February 5, 2026.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WEBSITE (mycosoft.com)                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        Memory UI Components                            │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │  │
│  │  │ BrainStatus  │ │ UserProfile  │ │ Episodic     │ │ Knowledge    │  │  │
│  │  │ Widget       │ │ Widget       │ │ Viewer       │ │ Graph Viewer │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │  │
│  │                      ┌──────────────────┐                              │  │
│  │                      │ MemoryHealth     │                              │  │
│  │                      │ Widget (Dashboard)│                              │  │
│  │                      └──────────────────┘                              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        API Proxy Routes                                │  │
│  │  /api/brain/      /api/memory/stats    /api/memory/user/[userId]      │  │
│  │  /api/brain/context/[userId]           /api/memory/episodes            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        React Hooks                                     │  │
│  │           use-memory.ts              use-brain.ts                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MAS ORCHESTRATOR (192.168.0.188:8001)                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Brain API Router                               │  │
│  │  POST /voice/brain/chat     GET /voice/brain/status                   │  │
│  │  POST /voice/brain/stream   GET /voice/brain/context/{user_id}        │  │
│  │  POST /voice/brain/event                                               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        MYCAMemoryBrain                                 │  │
│  │  - Memory-aware LLM wrapper                                           │  │
│  │  - Pre-response context loading                                       │  │
│  │  - Post-response memory storage                                       │  │
│  │  - Automatic fact learning                                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Memory Coordinator                                │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │  │
│  │  │ MYCAMemory │ │ Cross      │ │ Episodic   │ │ Conversation       │  │  │
│  │  │ (6-Layer)  │ │ Session    │ │ Memory     │ │ Memory             │  │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STORAGE BACKENDS                                    │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐                 │
│  │  Redis    │  │PostgreSQL │  │  Qdrant   │  │ In-Memory │                 │
│  │ (Session) │  │ (MINDEX)  │  │ (Vector)  │  │(Ephemeral)│                 │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Six-Layer Memory Architecture

| Layer | Retention | Storage | Purpose | Use Cases |
|-------|-----------|---------|---------|-----------|
| **Ephemeral** | 30 min | In-memory | Transient processing data | Temp variables, scratch space |
| **Session** | 24 hrs | Redis | Conversation context | Dialog history, session prefs |
| **Working** | 7 days | Redis + PostgreSQL | Active task state | Multi-step tasks, pending ops |
| **Semantic** | Permanent | PostgreSQL + Qdrant | Long-term knowledge | Facts, preferences, learnings |
| **Episodic** | Permanent | PostgreSQL | Event-based memories | Significant interactions |
| **System** | Permanent | PostgreSQL + Files | Configuration | System settings, patterns |

---

## Backend Components

### Core Memory Modules

| Module | Location | Purpose |
|--------|----------|---------|
| `myca_memory.py` | `mycosoft_mas/memory/` | 6-layer memory management |
| `memory_brain.py` | `mycosoft_mas/llm/` | Memory-aware LLM wrapper |
| `coordinator.py` | `mycosoft_mas/memory/` | Central memory orchestration |
| `personaplex_memory.py` | `mycosoft_mas/memory/` | Voice session persistence |
| `n8n_memory.py` | `mycosoft_mas/memory/` | Workflow execution history |
| `mem0_adapter.py` | `mycosoft_mas/memory/` | Mem0-compatible API |
| `mcp_memory_server.py` | `mycosoft_mas/memory/` | MCP server for Claude |

### API Routers

| Router | Location | Endpoints |
|--------|----------|-----------|
| `brain_api.py` | `mycosoft_mas/core/routers/` | `/voice/brain/*` |
| `memory_api.py` | `mycosoft_mas/core/routers/` | `/api/memory/*` |
| `voice_orchestrator_api.py` | `mycosoft_mas/core/routers/` | `/voice/*` |

---

## Frontend Components (Website)

### Memory UI Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `BrainStatusWidget.tsx` | `website/components/memory/` | Brain operational status |
| `UserProfileWidget.tsx` | `website/components/memory/` | User preferences editor |
| `EpisodicMemoryViewer.tsx` | `website/components/memory/` | Event timeline |
| `KnowledgeGraphViewer.tsx` | `website/components/memory/` | Graph visualization |
| `MemoryHealthWidget.tsx` | `website/components/memory/` | Dashboard health indicator |

### API Proxy Routes

| Route | Purpose |
|-------|---------|
| `/api/brain/route.ts` | Brain status and chat proxy |
| `/api/brain/context/[userId]/route.ts` | User context retrieval |
| `/api/memory/user/[userId]/route.ts` | User profile CRUD |
| `/api/memory/episodes/route.ts` | Episodic memory retrieval |
| `/api/memory/stats/route.ts` | Memory statistics |

### React Hooks

| Hook | Methods |
|------|---------|
| `use-memory.ts` | `getStats`, `getUserProfile`, `updateUserProfile`, `getEpisodes`, `getBrainStatus`, `getBrainContext`, `exportMemory`, `cleanupMemory` |
| `use-brain.ts` | `getStatus`, `getContext`, `chat`, `recordEvent` |

---

## Updated Pages

### Memory System Page (`/scientific/memory`)

Features:
- Real-time statistics with auto-refresh (30s)
- Memory layer breakdown with importance scores
- Tabbed interface: Brain Status, User Profile, Episodes, Knowledge Graph
- Client-side data fetching with error handling

### Main Dashboard (`/dashboard`)

Features:
- `MemoryHealthWidget` integration
- Quick link to Memory System page
- Status indicators for brain health

---

## Memory Operations

### Remember (Store)

```python
from mycosoft_mas.memory.myca_memory import get_myca_memory, MemoryLayer

memory = await get_myca_memory()
entry_id = await memory.remember(
    content={"fact": "User prefers dark mode"},
    layer=MemoryLayer.SEMANTIC,
    importance=0.8,
    tags=["preference", "ui"]
)
```

### Recall (Retrieve)

```python
results = await memory.recall(
    query=MemoryQuery(
        layer=MemoryLayer.SEMANTIC,
        tags=["preference"],
        min_importance=0.5,
        limit=10
    )
)
```

### Brain Chat (with Memory Context)

```python
from mycosoft_mas.llm.memory_brain import get_memory_brain

brain = await get_memory_brain()
response = await brain.get_response(
    message="Tell me about MINDEX",
    user_id="morgan",
    session_id="voice_001"
)
```

---

## API Reference

### Brain API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/voice/brain/chat` | POST | Non-streaming chat with memory |
| `/voice/brain/stream` | POST | SSE streaming chat |
| `/voice/brain/status` | GET | Brain health status |
| `/voice/brain/context/{user_id}` | GET | User memory context |
| `/voice/brain/event` | POST | Record significant event |

### Memory API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/memory/write` | POST | Store memory entry |
| `/api/memory/recall` | POST | Retrieve memories |
| `/api/memory/stats` | GET | System statistics |
| `/api/memory/user/{userId}/profile` | GET | User profile |
| `/api/memory/user/{userId}/preferences` | POST | Update preferences |

---

## Configuration

### Environment Variables

```bash
# MAS Backend
GEMINI_API_KEY=xxx           # Google Gemini (primary LLM)
ANTHROPIC_API_KEY=xxx        # Claude API
OPENAI_API_KEY=xxx           # OpenAI API
N8N_WEBHOOK_URL=xxx          # n8n webhook base

# Website
MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001
```

### Memory Settings

```python
# In MYCAMemoryBrain
max_recalled_memories = 5        # Semantic memories to load
max_recent_episodes = 3          # Recent episodes to include
memory_relevance_threshold = 0.5  # Minimum similarity score
```

---

## Data Flow

### Voice Interaction with Memory

```
User speaks → PersonaPlex/Moshi → Bridge → MAS Voice Orchestrator
                                                    │
                                                    ▼
                                        1. Try n8n workflow
                                                    │
                                        2. Try Memory Brain
                                           - Load user profile
                                           - Recall semantic memories
                                           - Get recent episodes
                                           - Inject context into prompt
                                           - Route to Gemini/Claude/GPT-4
                                           - Store conversation turn
                                           - Learn user facts
                                                    │
                                        3. Fallback to local responses
                                                    │
                                                    ▼
                                          Response → Bridge → Moshi TTS
```

---

## Monitoring

### System Monitor

```python
from mycosoft_mas.core.system_monitor import get_system_monitor

monitor = await get_system_monitor()
dashboard = await monitor.get_dashboard()
```

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/voice/brain/status` | Brain component health |
| `/api/memory/stats` | Memory system statistics |
| `/health` | Overall MAS health |

---

## Backup & Recovery

- **Proxmox Snapshots**: Daily at 2:00 AM
- **PostgreSQL Backups**: Daily at 4:00 AM
- **NAS Sync**: Continuous with integrity verification
- **Redis Persistence**: AOF + RDB snapshots
- **Recovery**: Automatic with state restoration

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md` | UI migration details |
| `MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md` | Backend brain integration |
| `MYCA_MEMORY_INTEGRATION_PLAN_FEB05_2026.md` | Full integration plan |
| `MYCA_MEMORY_ARCHITECTURE_FEB05_2026.md` | 6-layer architecture |
| `MEMORY_AWARENESS_PROTOCOL_FEB05_2026.md` | Awareness system |

---

## Version Information

| Component | Version |
|-----------|---------|
| Memory Brain | 1.0.0 |
| Brain API Router | 1.0.0 |
| Memory Coordinator | 1.0.0 |
| Website Memory UI | 1.0.0 |
| Website API Routes | 1.0.0 |
| React Hooks | 1.0.0 |
| Voice Orchestrator | 2.1.0-memory-brain |
| PersonaPlex Bridge | 8.0.0 |

---

## Next Steps

1. [ ] Add voice tone/emotion detection for context
2. [ ] Implement conversation summarization at session end
3. [ ] Add memory search UI with natural language queries
4. [ ] Integrate with n8n for memory-based workflow triggers
5. [ ] Add memory pruning for old/irrelevant content
6. [ ] Implement knowledge graph expansion
7. [ ] Add memory export/import for user data portability

---

*MYCA Memory System Complete - February 5, 2026*
*Mycosoft Multi-Agent System*
