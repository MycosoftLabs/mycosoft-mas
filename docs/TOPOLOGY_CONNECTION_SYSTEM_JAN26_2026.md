# MAS Topology Connection System - January 26, 2026

## Overview

This document summarizes the major enhancements made to the MAS Topology Visualization system, specifically focusing on real connection management, visual drag-to-connect functionality, and backend integration.

## Key Features Implemented

### 1. Real Connection Persistence (Supabase/Memory)

**File: `website/app/api/mas/connections/route.ts`**

The connections API now persists connections to Supabase when available, with an in-memory fallback for development:

- **GET** - Retrieve all connections or filter by sourceId/targetId
- **POST** - Create a single connection with validation
- **DELETE** - Remove a connection
- **PATCH** - Bulk create connections (used by auto-fix)

Key functions:
- `persistConnection()` - Saves connection to Supabase or memory
- `getConnections()` - Retrieves connections with optional filters
- `deleteConnection()` - Removes connection from storage
- `notifyOrchestrator()` - Notifies MAS backend about connection changes

### 2. Topology API Enhancement

**File: `website/app/api/mas/topology/route.ts`**

The topology API now merges persisted connections with default connections:

- `fetchPersistedConnections()` - Retrieves connections from Supabase
- `generateConnections()` - Now accepts persisted connections and merges them
- Stats now include `persistedConnections` count
- Response includes `persistence` field indicating storage type

### 3. Visual Drag-to-Connect Mode

**Files:**
- `website/components/mas/topology/advanced-topology-3d.tsx`
- `website/components/mas/topology/topology-node.tsx`

Users can now visually create connections:

1. Click the "Connect" button in the bottom control bar
2. Click a source node (it gets highlighted)
3. Click a target node (visual ring indicator appears)
4. Connection Widget opens with AI analysis and options

Visual indicators:
- Connection mode source node is highlighted in purple
- Target nodes show cyan ring that pulses on hover
- Cursor changes to crosshair for connection targets
- Status bar at top shows connection mode instructions

### 4. Connection Widget with AI Analysis

**File: `website/components/mas/topology/topology-tools.tsx`**

The ConnectionWidget provides:

- **Config Tab**: Connection type selection, bidirectional toggle, priority
- **Insights Tab**: AI-generated compatibility score, quick insights, risk assessment
- **Implementation Tab**: Code changes needed, integrations required, testing notes

Features:
- Cascade connection detection (auto-suggest related connections)
- LLM-powered implementation plan on demand
- Risk level assessment with mitigations

### 5. Connection Proposer Service

**File: `website/lib/services/connection-proposer.ts`**

AI-powered connection analysis:

- Category compatibility matrix (14x14 categories)
- `generateConnectionProposal()` - Quick NLQ analysis
- `getLLMImplementationPlan()` - Detailed AI-generated plan
- `detectCascadeConnections()` - Find related connections to create
- `assessRisks()` - Identify potential issues

### 6. Auto-Fix Connection System

The auto-fix button in the Connection Health panel now:

1. Analyzes all disconnected agents
2. Generates required connections using `generateAllAutoConnections()`
3. Sends bulk PATCH request to `/api/mas/connections`
4. Shows progress indicator with status updates
5. Persists connections to database
6. Notifies MAS orchestrator (async)
7. Refreshes topology data to show new connections

## Database Schema

If using Supabase, create this table:

```sql
CREATE TABLE mas_connections (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  target_id TEXT NOT NULL,
  connection_type TEXT NOT NULL DEFAULT 'message',
  bidirectional BOOLEAN NOT NULL DEFAULT true,
  priority INTEGER NOT NULL DEFAULT 5,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by TEXT NOT NULL DEFAULT 'manual',
  status TEXT NOT NULL DEFAULT 'active',
  metadata JSONB
);

CREATE INDEX idx_mas_connections_source ON mas_connections(source_id);
CREATE INDEX idx_mas_connections_target ON mas_connections(target_id);
CREATE INDEX idx_mas_connections_status ON mas_connections(status);
```

## Environment Variables

Required for Supabase persistence:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
MAS_API_URL=http://192.168.0.188:8001
```

## Usage

### Creating a Connection Visually

1. Navigate to `/natureos/mas/topology`
2. Click the "Connect" button (bottom control bar)
3. Click a source node
4. Click a target node
5. Review the connection analysis in the widget
6. Configure connection type and options
7. Click "Create Connection"

### Using Auto-Fix

1. Click the "Health" button (bottom control bar)
2. Review disconnected agents
3. Click "Auto-Fix X Connections"
4. Wait for progress indicator to complete
5. New connections appear in the topology

## Architecture

```
User Interaction
      ↓
TopologyNode3D (click handler)
      ↓
handleNodeClickForConnection()
      ↓
ConnectionWidget (UI)
      ↓
onCreateConnection()
      ↓
POST /api/mas/connections
      ↓
persistConnection() → Supabase/Memory
      ↓
notifyOrchestrator() → MAS Backend
      ↓
fetchData() → Refresh topology
      ↓
generateConnections(nodes, persistedConnections)
      ↓
Merged connections displayed in 3D
```

## Testing

1. Open the topology page at `http://localhost:3010/natureos/mas/topology`
2. Use the Connect button to create new connections
3. Verify connections appear in the 3D visualization
4. Check the Connection Health panel for connectivity scores
5. Test auto-fix with disconnected agents
6. Verify persistence by refreshing the page

## Known Limitations

- Supabase table must be created manually
- MAS orchestrator endpoint may not exist (graceful fallback)
- Connection visuals update on next data fetch (not instant)

## Future Improvements

- Real-time WebSocket updates for connection changes
- Drag-and-drop line drawing between nodes
- Connection analytics and traffic monitoring
- Historical connection data and playback
