# MYCA Memory Architecture - February 5, 2026

## Overview

The MYCA Memory System provides a comprehensive, multi-layered memory architecture for the Mycosoft Multi-Agent System. It enables persistent context, learning, and awareness across all components of the ecosystem.

## Six-Layer Memory Architecture

### 1. Ephemeral Memory
- **Retention**: Minutes (30 min default)
- **Purpose**: Transient working data during active processing
- **Storage**: In-memory only
- **Use Cases**: Current calculation context, temporary variables

### 2. Session Memory
- **Retention**: Hours (24 hrs default)
- **Purpose**: Conversation context within a session
- **Storage**: In-memory with optional persistence
- **Use Cases**: Dialog history, user preferences during session

### 3. Working Memory
- **Retention**: Hours to Days (7 days default)
- **Purpose**: Active task state and ongoing work
- **Storage**: In-memory + PostgreSQL backup
- **Use Cases**: Multi-step task progress, pending operations

### 4. Semantic Memory
- **Retention**: Permanent
- **Purpose**: Long-term knowledge and facts
- **Storage**: PostgreSQL + Vector embeddings
- **Use Cases**: Learned facts, system knowledge, user preferences

### 5. Episodic Memory
- **Retention**: Permanent
- **Purpose**: Event-based memories
- **Storage**: PostgreSQL
- **Use Cases**: Significant interactions, decisions, errors

### 6. System Memory
- **Retention**: Permanent
- **Purpose**: Configuration and learned behaviors
- **Storage**: PostgreSQL + File backup
- **Use Cases**: System configurations, learned patterns, calibration data

## Key Components

### Core Memory Modules

| Module | Location | Purpose |
|--------|----------|---------|
| `myca_memory.py` | `mycosoft_mas/memory/` | 6-layer memory management |
| `personaplex_memory.py` | `mycosoft_mas/memory/` | Voice session persistence |
| `n8n_memory.py` | `mycosoft_mas/memory/` | Workflow execution history |
| `mem0_adapter.py` | `mycosoft_mas/memory/` | Mem0-compatible API |
| `mcp_memory_server.py` | `mycosoft_mas/memory/` | MCP server for Claude |
| `memory_modules.py` | `mycosoft_mas/memory/` | Additional memory utilities |

### Database Schemas

| Schema | Tables | Purpose |
|--------|--------|---------|
| `memory` | entries, consolidations | Unified memory storage |
| `mem0` | memories | Mem0-compatible storage |
| `mcp` | memories | MCP memory storage |
| `voice` | sessions, feedback | Voice session data |
| `workflow` | executions, patterns | Workflow history |
| `graph` | nodes, edges | Knowledge graph |
| `cross_session` | user_context | Cross-session data |

## Memory Operations

### Remember (Write)
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

### Recall (Read)
```python
from mycosoft_mas.memory.myca_memory import MemoryQuery

results = await memory.recall(
    query=MemoryQuery(
        layer=MemoryLayer.SEMANTIC,
        tags=["preference"],
        min_importance=0.5,
        limit=10
    )
)
```

### Forget (Delete)
```python
await memory.forget(entry_id, hard_delete=False)  # Archive
await memory.forget(entry_id, hard_delete=True)   # Permanent delete
```

## Memory Decay

The Adaptive Decay system manages memory lifecycle:

| Strategy | Description |
|----------|-------------|
| Linear | Constant decay over time |
| Exponential | Natural forgetting curve |
| Step | Discrete retention levels |
| Importance-weighted | Decay based on importance + access patterns |

## Integration Points

### TypeScript/JavaScript
```typescript
import { MYCAMemoryBridge } from './bridges/memory_bridge';

const memory = new MYCAMemoryBridge({ apiUrl: 'http://localhost:8000' });
await memory.remember({ key: 'value' }, 'session');
```

### C# / .NET
```csharp
var memory = new MYCAMemoryBridge("http://localhost:8000");
await memory.RememberAsync(content, MemoryLayer.Session);
```

### MCP (Model Context Protocol)
Tools available: `memory_write`, `memory_read`, `memory_update`, `memory_delete`, `memory_search`, `memory_list`

## Backup & Recovery

- **Proxmox Snapshots**: Daily at 2:00 AM
- **PostgreSQL Backups**: Daily at 4:00 AM via `snapshot-schedule.sh`
- **NAS Sync**: Continuous with integrity verification
- **Recovery**: Automatic with state restoration

## Monitoring

Use `SystemMonitor` to track memory system health:
```python
from mycosoft_mas.core.system_monitor import get_system_monitor

monitor = await get_system_monitor()
dashboard = await monitor.get_dashboard()
```

---

## Related Documents

- **[MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md](./MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md)** - Brain-memory integration
- **[MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md](./MYCA_MEMORY_UI_MIGRATION_FEB05_2026.md)** - UI component migration
- **[MYCA_MEMORY_INTEGRATION_PLAN_FEB05_2026.md](./MYCA_MEMORY_INTEGRATION_PLAN_FEB05_2026.md)** - Full integration plan
- **[MEMORY_SYSTEM_COMPLETE_FEB05_2026.md](./MEMORY_SYSTEM_COMPLETE_FEB05_2026.md)** - Complete system reference

---

*Updated: February 5, 2026*
