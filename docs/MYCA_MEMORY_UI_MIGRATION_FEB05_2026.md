# MYCA Memory System UI Migration - February 5, 2026

## Overview

This document describes the migration of memory system UI components from the deprecated `unifi-dashboard` directory to the main website repository at `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\`.

## Migration Summary

### Background

The memory system UI components were initially built in the `mycosoft-mas/unifi-dashboard` directory, which was deprecated. All user-facing components needed to be migrated to the main website repository to ensure they are included in website deployments.

### Components Migrated

| Component | Source | Destination | Purpose |
|-----------|--------|-------------|---------|
| `BrainStatusWidget.tsx` | `unifi-dashboard/src/components/widgets/memory/` | `website/components/memory/` | Displays MYCA Brain operational status |
| `UserProfileWidget.tsx` | `unifi-dashboard/src/components/widgets/memory/` | `website/components/memory/` | User preferences and learned facts viewer/editor |
| `EpisodicMemoryViewer.tsx` | `unifi-dashboard/src/components/widgets/memory/` | `website/components/memory/` | Timeline of significant events |
| `KnowledgeGraphViewer.tsx` | `unifi-dashboard/src/components/widgets/memory/` | `website/components/memory/` | Visual knowledge graph with SVG rendering |
| `MemoryHealthWidget.tsx` | `unifi-dashboard/src/components/widgets/memory/` | `website/components/memory/` | Compact dashboard health indicator |
| `index.ts` | `unifi-dashboard/src/components/widgets/memory/` | `website/components/memory/` | Component barrel export |

### API Routes Migrated

| Route | Purpose | MAS Backend Endpoint |
|-------|---------|---------------------|
| `/api/brain/route.ts` | Brain status and chat proxy | `POST/GET /voice/brain/*` |
| `/api/brain/context/[userId]/route.ts` | User-specific brain context | `GET /voice/brain/context/{userId}` |
| `/api/memory/user/[userId]/route.ts` | User profile CRUD | `GET/POST /api/memory/user/{userId}/*` |
| `/api/memory/episodes/route.ts` | Episodic memory retrieval | `POST /api/memory/recall` |
| `/api/memory/stats/route.ts` | Memory system statistics | `GET /api/memory/stats` |

### Hooks Migrated

| Hook | Purpose | Methods |
|------|---------|---------|
| `use-memory.ts` | Memory system operations | `getStats`, `getUserProfile`, `updateUserProfile`, `getEpisodes`, `getBrainStatus`, `getBrainContext`, `exportMemory`, `cleanupMemory` |
| `use-brain.ts` | Brain API operations | `getStatus`, `getContext`, `chat`, `recordEvent` |

---

## New File Locations

### Website Repository Structure

```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\
├── app/
│   ├── api/
│   │   ├── brain/
│   │   │   ├── route.ts                 # Brain status/chat proxy
│   │   │   └── context/
│   │   │       └── [userId]/
│   │   │           └── route.ts         # User context proxy
│   │   └── memory/
│   │       ├── user/
│   │       │   └── [userId]/
│   │       │       └── route.ts         # User profile operations
│   │       ├── episodes/
│   │       │   └── route.ts             # Episodic memory retrieval
│   │       └── stats/
│   │           └── route.ts             # Memory statistics
│   ├── dashboard/
│   │   └── page.tsx                     # Updated with MemoryHealthWidget
│   └── scientific/
│       └── memory/
│           └── page.tsx                 # Updated with real data + widgets
├── components/
│   └── memory/
│       ├── index.ts                     # Barrel export
│       ├── BrainStatusWidget.tsx        # Brain status display
│       ├── UserProfileWidget.tsx        # User preferences
│       ├── EpisodicMemoryViewer.tsx     # Event timeline
│       ├── KnowledgeGraphViewer.tsx     # Graph visualization
│       └── MemoryHealthWidget.tsx       # Health indicator
└── hooks/
    ├── use-memory.ts                    # Memory operations hook
    └── use-brain.ts                     # Brain API hook
```

---

## Updated Pages

### Scientific Memory Page (`/scientific/memory`)

The page now includes:

1. **Real-time Statistics**
   - Active Sessions (from `/api/memory/stats`)
   - Facts Stored
   - Knowledge Nodes
   - Embeddings count

2. **Memory Layers Breakdown**
   - Visual badges showing count per layer
   - Importance percentages

3. **Tabbed Widget Interface**
   - **Brain Status**: `BrainStatusWidget` showing LLM provider health
   - **User Profile**: `UserProfileWidget` for preferences and facts
   - **Episodes**: `EpisodicMemoryViewer` timeline
   - **Knowledge Graph**: `KnowledgeGraphViewer` visualization

4. **Auto-refresh** every 30 seconds

### Main Dashboard (`/dashboard`)

Added `MemoryHealthWidget` between Quick Stats and Quick Actions sections, showing:
- Overall brain status
- Memory coordinator health
- Active sessions count
- Facts stored count

---

## Component Details

### BrainStatusWidget

Displays MYCA Brain operational status:

```tsx
<BrainStatusWidget />
```

Features:
- Overall status indicator (healthy/degraded/error)
- LLM provider health (Gemini, Claude, GPT-4)
- Memory coordinator status
- Active session/conversation count
- Refresh button with loading state

### UserProfileWidget

User preferences and learned facts:

```tsx
<UserProfileWidget userId="morgan" />
```

Features:
- Preference editing (communication style, topics, language)
- Save functionality with API persistence
- Learned facts display with categories
- Last updated timestamp

### EpisodicMemoryViewer

Timeline of significant events:

```tsx
<EpisodicMemoryViewer agentId="myca_brain" limit={20} />
```

Features:
- Event type badges (task_complete, conversation, insight, error)
- Timestamp and agent information
- Context expansion
- Filterable by event type

### KnowledgeGraphViewer

SVG-based knowledge graph visualization:

```tsx
<KnowledgeGraphViewer />
```

Features:
- Node/edge rendering
- Zoom controls
- Search and filter
- Node type filtering (concept, fact, entity, relation)
- Interactive node selection

### MemoryHealthWidget

Compact dashboard indicator:

```tsx
<MemoryHealthWidget />
```

Features:
- Status badge (healthy/degraded/warning)
- Core component indicators
- Link to full Memory System page

---

## API Route Details

### Brain Routes

**GET /api/brain?endpoint=status**
```json
{
  "success": true,
  "data": {
    "brain_initialized": true,
    "memory_coordinator_active": true,
    "providers": {
      "gemini": { "available": true, "healthy": true },
      "claude": { "available": true, "healthy": true },
      "openai": { "available": false }
    },
    "stats": {
      "active_sessions": 3,
      "total_memories": 2847
    }
  }
}
```

**POST /api/brain (chat)**
```json
{
  "endpoint": "chat",
  "message": "Hello MYCA",
  "user_id": "morgan",
  "session_id": "optional"
}
```

### Memory Routes

**GET /api/memory/stats**
```json
{
  "success": true,
  "data": {
    "active_conversations": 3,
    "total_memories": 2847,
    "vector_count": 45000,
    "myca_memory": {
      "layers": {
        "ephemeral": { "count": 45, "avg_importance": 0.3 },
        "session": { "count": 156, "avg_importance": 0.5 },
        "working": { "count": 234, "avg_importance": 0.6 },
        "semantic": { "count": 1245, "avg_importance": 0.7 },
        "episodic": { "count": 892, "avg_importance": 0.8 },
        "system": { "count": 275, "avg_importance": 0.9 }
      }
    }
  }
}
```

**GET /api/memory/user/[userId]**
```json
{
  "success": true,
  "profile": {
    "user_id": "morgan",
    "preferences": {
      "communication_style": "technical",
      "topics_of_interest": ["mycology", "AI", "bioinformatics"]
    },
    "facts": [
      { "key": "role", "value": "Founder of Mycosoft" }
    ]
  }
}
```

---

## Fallback Demo Data

All API routes include fallback demo data when the MAS backend is unavailable:

```typescript
// Example from /api/memory/stats/route.ts
const demoData = {
  active_conversations: 3,
  total_memories: 2847,
  vector_count: 45000,
  coordinator: { active_conversations: 3 },
  myca_memory: {
    total_memories: 2847,
    layers: {
      ephemeral: { count: 45, avg_importance: 0.3 },
      session: { count: 156, avg_importance: 0.5 },
      // ...
    }
  }
};
```

---

## Environment Configuration

The website uses `MAS_ORCHESTRATOR_URL` environment variable:

```bash
# .env.local
MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001
```

Fallback: `http://localhost:8001`

---

## Files Removed from Deprecated Directory

The following were cleaned up from `unifi-dashboard`:

- `src/components/widgets/memory/` (entire directory)
- `src/app/api/brain/` (entire directory)
- `src/app/api/memory/user/` (entire directory)
- `src/app/api/memory/episodes/` (entire directory)
- `src/hooks/useBrain.ts`

Note: `MemoryManagementPanel.tsx` was retained in `unifi-dashboard` as it's an internal MAS-only admin tool, not a user-facing component.

---

## Integration with MAS Backend

### Backend Endpoints Used

| Website Route | MAS Backend Endpoint |
|--------------|---------------------|
| `/api/brain?endpoint=status` | `GET /voice/brain/status` |
| `/api/brain` (POST chat) | `POST /voice/brain/chat` |
| `/api/brain/context/[userId]` | `GET /voice/brain/context/{userId}` |
| `/api/memory/user/[userId]` | `GET /api/memory/user/{userId}/profile` |
| `/api/memory/user/[userId]` (POST) | `POST /api/memory/write` |
| `/api/memory/episodes` | `POST /api/memory/recall` |
| `/api/memory/stats` | `GET /api/memory/stats` |

---

## Deployment Notes

### After Website Changes

1. **Local Testing**: `npm run dev` on port 3010
2. **Commit & Push**: To GitHub
3. **SSH to VM**: `ssh mycosoft@192.168.0.187`
4. **Pull Code**: `git reset --hard origin/main`
5. **Rebuild Docker**: `docker build -t website-website:latest --no-cache .`
6. **Restart Container**: With NAS mount for media assets
7. **Clear Cloudflare Cache**: PURGE EVERYTHING
8. **Verify**: Compare localhost vs sandbox.mycosoft.com

---

## Related Documents

- `MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md` - Backend integration
- `MYCA_MEMORY_INTEGRATION_PLAN_FEB05_2026.md` - Full integration plan
- `MEMORY_AWARENESS_PROTOCOL_FEB05_2026.md` - Awareness system
- `MYCA_MEMORY_ARCHITECTURE_FEB05_2026.md` - 6-layer architecture

---

## Version Information

- Website Memory Components: 1.0.0
- API Routes: 1.0.0
- Hooks: 1.0.0
- Memory Page: 2.0.0 (with real data)
- Dashboard Integration: 1.0.0

---

*MYCA Memory UI Migration - February 5, 2026*
*Mycosoft Multi-Agent System*
