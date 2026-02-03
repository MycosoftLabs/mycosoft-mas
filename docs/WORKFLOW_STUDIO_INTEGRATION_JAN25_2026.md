# N8N Workflow Studio Integration - January 25, 2026

## Overview

This document describes the comprehensive n8n Workflow Studio integration into the MYCA MAS dashboard. This system enables full visualization, monitoring, and control of n8n workflows directly from the MYCA AI Studio interface.

## Architecture

### Backend Components (Python)

1. **N8NWorkflowEngine** (`mycosoft_mas/core/n8n_workflow_engine.py`)
   - Full CRUD operations on workflows
   - Activation/deactivation control
   - Archiving with versioning
   - Execution monitoring
   - 24/7/365 scheduler for auto-sync

2. **MYCAWorkflowOrchestrator** (`mycosoft_mas/core/myca_workflow_orchestrator.py`)
   - High-level orchestration layer
   - Dynamic workflow rewiring
   - Event-based notifications

3. **Workflow API Router** (`mycosoft_mas/core/routers/n8n_workflows_api.py`)
   - FastAPI endpoints for workflow management

### Frontend Components (Next.js/React)

1. **WorkflowStudioView** (`unifi-dashboard/src/components/views/WorkflowStudioView.tsx`)
   - Main workflow management interface
   - Category-based workflow organization
   - Real-time execution monitoring
   - Activate/deactivate controls
   - Search and filtering
   - Sync functionality

2. **API Routes** (`unifi-dashboard/src/app/api/n8n/`)
   - `/api/n8n/workflows` - List and manage workflows
   - `/api/n8n/executions` - View execution history
   - `/api/n8n/sync` - Sync local workflows to n8n

## Accessing Workflow Studio

1. Open the MYCA Dashboard at http://localhost:3000
2. Click the **Zap icon** in the left navigation (labeled "Workflow Studio")
3. The Workflow Studio displays all n8n workflows organized by category

## Features

### Workflow Categories
- **Core MYCA** - Main MYCA command and orchestration workflows
- **Speech/Voice** - Voice interaction and TTS workflows
- **Native Integrations** - AI, comms, and data integrations
- **Operations** - Proxmox, UniFi, NAS management
- **MINDEX** - Mushroom index scraping workflows
- **Custom** - User-created workflows

### Workflow Controls
- **Activate/Deactivate** - Toggle workflow active state
- **Open in n8n** - Direct link to edit workflow in n8n UI
- **Sync** - Sync local workflow files to n8n instance
- **Refresh** - Reload workflow data

### Monitoring
- Real-time workflow statistics
- Execution success/failure counts
- Recent activity feed
- Auto-refresh every 30 seconds

## Configuration

### Environment Variables

```env
# n8n Connection
N8N_URL=http://192.168.0.188:5678
N8N_API_KEY=<your-api-key>

# Cloud n8n (optional)
N8N_CLOUD_URL=https://mycosoft.app.n8n.cloud
N8N_CLOUD_API_KEY=<your-cloud-api-key>

# MAS API
MAS_API_URL=http://localhost:8000
```

## Current State

| Metric | Value |
|--------|-------|
| Total Workflows | 48 |
| Active Workflows | 12 |
| Categories | 6 |
| Auto-sync Interval | 15 min |

## Files Created/Modified

### Created
- `unifi-dashboard/src/components/views/WorkflowStudioView.tsx`
- `unifi-dashboard/src/app/api/n8n/workflows/route.ts`
- `unifi-dashboard/src/app/api/n8n/executions/route.ts`
- `unifi-dashboard/src/app/api/n8n/sync/route.ts`
- `mycosoft_mas/core/n8n_workflow_engine.py` (extended)
- `mycosoft_mas/core/myca_workflow_orchestrator.py`
- `mycosoft_mas/core/routers/n8n_workflows_api.py`
- `scripts/deploy_n8n_workflows.py`

### Modified
- `unifi-dashboard/src/components/Dashboard.tsx` - Added workflows case
- `unifi-dashboard/src/components/Navigation.tsx` - Added Workflow Studio nav item

## Scaling Considerations

The system is designed to scale to hundreds of workflows:

1. **Category-based organization** - Workflows grouped by function
2. **Lazy loading** - Only visible workflows rendered
3. **Efficient API** - Pagination-ready endpoints
4. **Background sync** - Non-blocking workflow synchronization
5. **Caching** - API responses cached appropriately

## Next Steps

1. Add workflow dependency visualization
2. Implement workflow templates for quick creation
3. Add execution logs viewer
4. Create workflow comparison tool
5. Integrate with agent topology view

---

*Document created: January 25, 2026*
*Author: MYCA Workflow Automation System*
