# MYCA Memory System Documentation Index - February 5, 2026

## Overview

This index provides a complete reference to all memory system documentation in the Mycosoft MAS project.

---

## Current Documentation (February 5, 2026)

### Primary References

| Document | Description | Status |
|----------|-------------|--------|
| **[MEMORY_SYSTEM_COMPLETE_FEB05_2026.md](./MEMORY_SYSTEM_COMPLETE_FEB05_2026.md)** | Complete system reference with architecture, components, and APIs | **CURRENT** |
| **[MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md](./MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md)** | UI component migration from unifi-dashboard to website | **CURRENT** |
| **[MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md](./MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md)** | Brain-memory integration for PersonaPlex voice | **CURRENT** |
| **[MYCA_MEMORY_ARCHITECTURE_FEB05_2026.md](./MYCA_MEMORY_ARCHITECTURE_FEB05_2026.md)** | 6-layer memory architecture specification | **CURRENT** |
| **[MYCA_MEMORY_INTEGRATION_PLAN_FEB05_2026.md](./MYCA_MEMORY_INTEGRATION_PLAN_FEB05_2026.md)** | Full integration plan with phases | **CURRENT** |
| **[MEMORY_AWARENESS_PROTOCOL_FEB05_2026.md](./MEMORY_AWARENESS_PROTOCOL_FEB05_2026.md)** | System awareness and monitoring protocol | **CURRENT** |

---

## Supporting Documentation

### February 4, 2026

| Document | Description | Status |
|----------|-------------|--------|
| **[MEMORY_INTEGRATION_GUIDE_FEB04_2026.md](./MEMORY_INTEGRATION_GUIDE_FEB04_2026.md)** | Integration guide for Python, TypeScript, C#, C++ | Valid |
| **[MEMORY_SYSTEM_FULL_TEST_REPORT_FEB04_2026.md](./MEMORY_SYSTEM_FULL_TEST_REPORT_FEB04_2026.md)** | Full test report with results | Valid |

### February 3, 2026 (Historical)

| Document | Description | Status |
|----------|-------------|--------|
| **[MEMORY_SYSTEM_COMPLETE_FEB03_2026.md](./MEMORY_SYSTEM_COMPLETE_FEB03_2026.md)** | Initial complete system report | Superseded |
| **[MEMORY_SYSTEM_UPGRADE_FEB03_2026.md](./MEMORY_SYSTEM_UPGRADE_FEB03_2026.md)** | Initial upgrade documentation | Superseded |
| **[MEMORY_SYSTEM_VERIFICATION_FEB03_2026.md](./MEMORY_SYSTEM_VERIFICATION_FEB03_2026.md)** | Initial verification report | Superseded |
| **[MEMORY_DASHBOARD_UI_FEB03_2026.md](./MEMORY_DASHBOARD_UI_FEB03_2026.md)** | Initial UI components (in unifi-dashboard) | Superseded |
| **[MYCA_ORCHESTRATOR_MEMORY_INTEGRATION_FEB03_2026.md](./MYCA_ORCHESTRATOR_MEMORY_INTEGRATION_FEB03_2026.md)** | Initial orchestrator integration | Superseded |
| **[MYCA_HYBRID_BRAIN_IMPLEMENTATION_FEB03_2026.md](./MYCA_HYBRID_BRAIN_IMPLEMENTATION_FEB03_2026.md)** | Hybrid brain architecture | Valid (extended) |

---

## Component Locations

### Backend (MAS Repository)

```
mycosoft-mas/
├── mycosoft_mas/
│   ├── memory/
│   │   ├── myca_memory.py          # 6-layer memory management
│   │   ├── coordinator.py          # Memory coordinator
│   │   ├── personaplex_memory.py   # Voice session persistence
│   │   ├── n8n_memory.py           # Workflow history
│   │   ├── mem0_adapter.py         # Mem0-compatible API
│   │   └── mcp_memory_server.py    # Claude MCP integration
│   ├── llm/
│   │   └── memory_brain.py         # Memory-aware LLM wrapper
│   └── core/
│       └── routers/
│           ├── brain_api.py        # Brain API endpoints
│           └── memory_api.py       # Memory API endpoints
```

### Frontend (Website Repository)

```
website/
├── app/
│   ├── api/
│   │   ├── brain/
│   │   │   ├── route.ts            # Brain status/chat proxy
│   │   │   └── context/[userId]/route.ts
│   │   └── memory/
│   │       ├── user/[userId]/route.ts
│   │       ├── episodes/route.ts
│   │       └── stats/route.ts
│   ├── dashboard/page.tsx          # With MemoryHealthWidget
│   └── scientific/memory/page.tsx  # Memory System page
├── components/
│   └── memory/
│       ├── BrainStatusWidget.tsx
│       ├── UserProfileWidget.tsx
│       ├── EpisodicMemoryViewer.tsx
│       ├── KnowledgeGraphViewer.tsx
│       ├── MemoryHealthWidget.tsx
│       └── index.ts
└── hooks/
    ├── use-memory.ts
    └── use-brain.ts
```

---

## Memory Layers Quick Reference

| Layer | Retention | Storage | Purpose |
|-------|-----------|---------|---------|
| **Ephemeral** | 30 min | In-memory | Transient processing |
| **Session** | 24 hrs | Redis | Conversation context |
| **Working** | 7 days | Redis + PostgreSQL | Active task state |
| **Semantic** | Permanent | PostgreSQL + Qdrant | Long-term knowledge |
| **Episodic** | Permanent | PostgreSQL | Significant events |
| **System** | Permanent | PostgreSQL + Files | Configuration |

---

## API Quick Reference

### Brain API (MAS)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/voice/brain/chat` | POST | Non-streaming chat |
| `/voice/brain/stream` | POST | SSE streaming |
| `/voice/brain/status` | GET | Health status |
| `/voice/brain/context/{user_id}` | GET | Memory context |

### Memory API (MAS)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/memory/write` | POST | Store memory |
| `/api/memory/recall` | POST | Retrieve memories |
| `/api/memory/stats` | GET | System statistics |

### Website Proxy Routes

| Route | Purpose |
|-------|---------|
| `/api/brain` | Brain status/chat proxy |
| `/api/brain/context/[userId]` | User context |
| `/api/memory/stats` | Memory statistics |
| `/api/memory/user/[userId]` | User profile |
| `/api/memory/episodes` | Episodic memory |

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| Feb 3, 2026 | 1.0.0 | Initial memory system with 8 scopes |
| Feb 4, 2026 | 1.1.0 | Integration guide, full test suite |
| Feb 5, 2026 | 2.0.0 | Brain integration, UI migration, 6-layer architecture |

---

## Next Steps

1. [ ] Voice tone/emotion detection for context
2. [ ] Conversation summarization at session end
3. [ ] Memory-based workflow triggers in n8n
4. [ ] Memory pruning for old content
5. [ ] Knowledge graph expansion
6. [ ] Memory export/import for data portability

---

*MYCA Memory Documentation Index - February 5, 2026*
*Mycosoft Multi-Agent System*
