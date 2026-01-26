# MAS Topology Dashboard - Technical Architecture
## Date: January 26, 2026

---

## System Overview

The MAS Topology Dashboard is a real-time 3D visualization and control interface for the Mycosoft Multi-Agent System (MAS). It consists of a Next.js frontend and a FastAPI backend orchestrator.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Next.js Frontend (Port 3010)                  │  │
│  │  - React 19 + TypeScript                                   │  │
│  │  - Three.js + React Three Fiber (3D Rendering)             │  │
│  │  - TailwindCSS + Shadcn UI                                 │  │
│  └────────────────────────┬───────────────────────────────────┘  │
└───────────────────────────┼──────────────────────────────────────┘
                            │ HTTP/WebSocket
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    NEXT.JS API ROUTES                             │
│  /api/mas/topology      - GET/POST topology data                 │
│  /api/mas/connections   - CRUD for agent connections             │
│  /api/mas/orchestrator/action - Orchestrator commands            │
│  /api/mas/agents        - Agent registry                         │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP/WebSocket Proxy
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│              MAS ORCHESTRATOR (192.168.0.188:8001)                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              FastAPI + Python 3.11                         │  │
│  │  - Agent Pool (Docker container management)                │  │
│  │  - Gap Detector (capability analysis)                      │  │
│  │  - Agent Factory (dynamic agent creation)                  │  │
│  │  - Memory Manager (vector DB + SQL)                        │  │
│  └────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                    DATA LAYER                                     │
│  - PostgreSQL (agent_logs, agent_run_log, agent_metrics)         │
│  - Redis (pub/sub, task queue, cache)                            │
│  - Qdrant (vector embeddings for semantic memory)                │
│  - TimescaleDB (time-series metrics)                             │
│  - Supabase (connection persistence, user state)                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## Frontend Components

### File Structure
```
website/
├── app/natureos/mas/topology/
│   └── page.tsx                    # Main page route
├── components/mas/topology/
│   ├── advanced-topology-3d.tsx    # Main 3D visualization (~2000 lines)
│   ├── topology-node.tsx           # 3D node rendering
│   ├── topology-connection.tsx     # Connection line rendering
│   ├── topology-tools.tsx          # Path tracer, spawn, command panels
│   ├── agent-registry.ts           # 247 agent definitions
│   └── use-topology-websocket.ts   # WebSocket/SSE hooks
└── app/api/mas/
    ├── topology/route.ts           # Topology data API
    ├── connections/route.ts        # Connections CRUD API
    ├── orchestrator/action/route.ts # Orchestrator commands
    └── agents/route.ts             # Agent registry API
```

### Key Components

#### `advanced-topology-3d.tsx`
- Main visualization component
- Uses `@react-three/fiber` for React/Three.js integration
- Uses `@react-three/drei` for camera controls, effects
- Implements force-directed layout with category clustering
- Handles node selection, connection creation, real-time updates

#### `topology-tools.tsx`
- Path Tracer panel: Source/target selection, path visualization
- Spawn Agent panel: Gap detection, orchestrator terminal
- Command Center: Health check, restart, sync, clear queue
- Connection Health: Connectivity score, auto-fix

#### `use-topology-websocket.ts`
- WebSocket connection to MAS orchestrator
- Auto-reconnect with exponential backoff
- Falls back to polling if WebSocket unavailable
- Message types: agent_update, metric_update, connection_update, incident

---

## API Endpoints

### GET /api/mas/topology
Returns full topology data for 3D visualization.

**Response:**
```typescript
{
  nodes: Array<{
    id: string
    name: string
    category: string
    status: 'active' | 'busy' | 'idle' | 'offline' | 'error'
    metrics: { cpu: number, memory: number, tasks: number }
  }>
  connections: Array<{
    source: string
    target: string
    type: 'data' | 'command' | 'event'
    active: boolean
  }>
  packets: Array<{ id, source, target, progress, type }>
  stats: {
    totalNodes: number
    activeNodes: number
    totalConnections: number
    activeConnections: number
    systemLoad: number
  }
}
```

### POST /api/mas/topology
Execute agent actions.

**Request:**
```typescript
{
  action: 'start' | 'stop' | 'restart' | 'spawn' | 'configure'
  nodeId: string
  data?: object
}
```

### GET/POST/DELETE/PATCH /api/mas/connections
CRUD operations for agent connections.

**GET Response:**
```typescript
{
  connections: Array<{
    id: string
    source: string
    target: string
    type: string
    created_at: string
  }>
  total: number
}
```

### POST /api/mas/orchestrator/action
Execute orchestrator commands.

**Request:**
```typescript
{
  action: 'health' | 'restart-all' | 'sync-memory' | 'clear-queue' | 'spawn' | 'diagnostics'
  data?: object
}
```

---

## Database Schema

### Supabase Tables

#### `mas_connections`
```sql
CREATE TABLE mas_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id VARCHAR NOT NULL,
  target_id VARCHAR NOT NULL,
  connection_type VARCHAR DEFAULT 'data',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(source_id, target_id)
);
```

#### `user_app_state`
```sql
CREATE TABLE user_app_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  tool_states JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id)
);
```

---

## WebSocket Protocol

### Connection
```
URL: ws://192.168.0.188:8001/api/dashboard/ws
Fallback: Polling every 30 seconds
```

### Message Types

```typescript
// Agent status update
{
  type: 'agent_update'
  data: { id: string, status: string, metrics: object }
}

// Metric update
{
  type: 'metric_update'
  data: { cpu: number, memory: number, throughput: number }
}

// Connection change
{
  type: 'connection_update'
  data: { source: string, target: string, action: 'added' | 'removed' }
}

// Security incident
{
  type: 'incident_created' | 'incident_updated' | 'incident_resolved'
  data: { id: string, severity: string, message: string }
}
```

---

## Environment Variables

### Frontend (.env.local)
```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx

# MAS Orchestrator
MAS_API_URL=http://192.168.0.188:8001
NEXT_PUBLIC_MAS_WS_ENABLED=true
NEXT_PUBLIC_MAS_WS_URL=ws://192.168.0.188:8001/api/dashboard/ws
```

### Backend (MAS)
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/mas
REDIS_URL=redis://localhost:6379

# Vector DB
QDRANT_URL=http://localhost:6333

# LLM APIs
OPENAI_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
```

---

## Deployment

### Development
```bash
cd website
npm run dev -- --port 3010
```

### Production (Sandbox VM)
```bash
# SSH to VM
ssh mycosoft@192.168.0.187

# Pull latest
cd /opt/mycosoft/website
git reset --hard origin/main

# Rebuild Docker
docker build -t website-website:latest --no-cache .

# Restart container
cd /opt/mycosoft
docker compose -p mycosoft-production up -d --force-recreate mycosoft-website

# Purge Cloudflare cache
# Via dashboard: dash.cloudflare.com → mycosoft.com → Caching → Purge Everything
```

---

## Performance Considerations

### 3D Rendering
- 247 nodes rendered with instancing where possible
- LOD (Level of Detail) for distant nodes
- Connection lines batched for efficiency
- Target: 60fps at 1080p

### Data Updates
- WebSocket preferred for real-time (<100ms latency)
- Polling fallback every 30 seconds
- Optimistic UI updates for actions

### Memory
- Agent registry: ~50KB
- Connection data: ~20KB
- 3D scene: ~100MB GPU memory

---

*Technical documentation for development team*
*Version: 1.0*
*Last Updated: January 26, 2026*
