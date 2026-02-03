# N8N AI Studio Integration - January 25, 2026

## Summary

Integrated n8n workflow management into the NatureOS AI Studio, replacing mock data with real n8n API integration. The Workflow Studio component provides a complete interface for viewing, managing, and interacting with n8n workflows directly from the MYCA Command Center.

## Changes Made

### Backend API Routes (Website)

| File | Purpose |
|------|---------|
| `app/api/n8n/workflows/route.ts` | Fetch workflows, activate/deactivate, with cloud fallback |
| `app/api/n8n/executions/route.ts` | Fetch execution history and stats |

### Frontend Components (Website)

| File | Purpose |
|------|---------|
| `components/mas/workflow-studio.tsx` | Main workflow management component |
| `components/mas/index.ts` | Updated exports to include WorkflowStudio |
| `app/natureos/ai-studio/page.tsx` | Updated to use WorkflowStudio in Workflows tab |

### Configuration Updates

| File | Changes |
|------|---------|
| `.env.local` | Added `N8N_API_KEY` for API authentication |

### Removed (Deprecated)

| Location | Files Removed |
|----------|---------------|
| `unifi-dashboard/src/app/api/n8n/` | All n8n API routes (deprecated dashboard) |
| `unifi-dashboard/src/components/views/` | WorkflowStudioView.tsx (deprecated) |

## Features

### Workflow Studio Component

1. **Connection Status Indicator**
   - Shows online/offline status
   - Displays warning banner when n8n is unreachable
   - Retry button for reconnection

2. **Statistics Dashboard**
   - Total workflows count
   - Active workflows count
   - 24h execution count
   - Failed execution count

3. **Workflow List**
   - Organized by category (Core MYCA, Speech/Voice, Native, Operations, MINDEX, Custom)
   - Expandable/collapsible category sections
   - Search functionality
   - Activation toggle per workflow
   - Direct link to open workflow in n8n

4. **Quick Access Panel**
   - Open n8n Editor button
   - Local n8n button (localhost:5678)
   - Summary stats

### API Features

1. **Dual n8n Support**
   - Primary: Local n8n on MAS VM (192.168.0.188:5678)
   - Fallback: n8n Cloud (mycosoft.app.n8n.cloud)

2. **Authentication**
   - API Key authentication (X-N8N-API-KEY header)
   - Fallback to Basic Auth (username/password)

3. **Workflow Categorization**
   - Automatic categorization based on workflow name
   - Categories: core, speech, native, ops, mindex, custom

## Environment Variables

```bash
# Local n8n
N8N_URL=http://192.168.0.188:5678
N8N_API_KEY=<jwt-token>
N8N_USERNAME=morgan@mycosoft.org
N8N_PASSWORD=Mushroom1!Mushroom1!

# n8n Cloud (fallback)
N8N_CLOUD_URL=https://mycosoft.app.n8n.cloud
N8N_CLOUD_API_KEY=<jwt-token>
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    NatureOS AI Studio                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Workflows Tab                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │            WorkflowStudio Component              │    │   │
│  │  │  - Stats Cards                                   │    │   │
│  │  │  - Connection Banner                             │    │   │
│  │  │  - Workflow List (by category)                   │    │   │
│  │  │  - Quick Access Panel                            │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js API Routes                            │
│  /api/n8n/workflows  ─────────────────────────────────────────  │
│  /api/n8n/executions ─────────────────────────────────────────  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────┐       ┌──────────────────────────┐
│  Local n8n (Primary) │       │  n8n Cloud (Fallback)    │
│  192.168.0.188:5678  │       │  mycosoft.app.n8n.cloud  │
└──────────────────────┘       └──────────────────────────┘
```

## Integration Points

### MAS Orchestrator
- n8n workflows triggered via webhooks from MYCA orchestrator
- Workflow status visible in AI Studio

### MINDEX
- MINDEX category workflows visible in Workflow Studio
- Direct access to MINDEX data pipelines

### Voice/Speech
- Speech category workflows for PersonaPlex integration
- Voice command routing through n8n

## Testing

### Manual Testing
1. Navigate to http://localhost:3010/natureos/ai-studio
2. Click "Workflows" tab
3. Verify:
   - Stats cards show data (when n8n is online)
   - Connection banner shows status
   - Workflow list loads and can be searched
   - Categories can be expanded/collapsed
   - Activation toggle works
   - Open n8n Editor button works

### Offline Handling
When n8n is unreachable:
- Yellow warning banner displayed
- Stats show 0
- Retry button available
- Quick Access panel still functional

## Known Issues

1. **n8n X-Frame-Options**: n8n cannot be embedded in iframes due to security headers. Resolved by providing "Open in new tab" buttons instead.

2. **MAS VM Connectivity**: When MAS VM (192.168.0.188) is offline, workflows show 0. The component handles this gracefully with offline indicators.

## Next Steps

1. Add workflow execution trigger from UI
2. Add workflow creation wizard
3. Add execution history timeline
4. Connect to real-time WebSocket for live updates
5. Add workflow templates library

---

*Document created: January 25, 2026*
*Author: Cursor AI Assistant*
