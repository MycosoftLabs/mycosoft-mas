# N8N Workflow Automation System for MYCA - January 25, 2026

## Overview

This document describes the comprehensive n8n workflow automation system built for MYCA (Mycosoft Autonomous Agent). This system enables MYCA to manage, rewire, archive, and automate n8n workflows 24/7/365.

## Architecture

### Core Components

1. **N8NWorkflowEngine** (`mycosoft_mas/core/n8n_workflow_engine.py`)
   - Full CRUD operations on workflows
   - Activation/deactivation
   - Archiving with versioning
   - Import/export from local files
   - Execution monitoring
   - Dynamic rewiring capabilities

2. **WorkflowScheduler** (same file)
   - 24/7/365 background scheduler
   - Automatic sync every 15 minutes
   - Health checks every 5 minutes
   - Daily archiving of all workflows
   - Event callbacks for integration

3. **MYCAWorkflowOrchestrator** (`mycosoft_mas/core/myca_workflow_orchestrator.py`)
   - High-level orchestration layer
   - Integration with main MYCA system
   - Event-based notifications
   - Dynamic workflow rewiring

4. **N8N Workflows API** (`mycosoft_mas/core/routers/n8n_workflows_api.py`)
   - REST API for workflow management
   - Scheduler control endpoints
   - Archive/restore operations

## Configuration

### Environment Variables

```bash
# Local n8n instance (MAS VM)
N8N_URL=http://192.168.0.188:5678
N8N_API_KEY=<your-api-key>

# Cloud n8n instance (optional)
N8N_CLOUD_URL=https://mycosoft.app.n8n.cloud
N8N_CLOUD_API_KEY=<your-cloud-api-key>
```

### Directory Structure

```
n8n/
â”œâ”€â”€ workflows/          # Local workflow JSON files
â”‚   â”œâ”€â”€ 01_myca_command_api.json
â”‚   â”œâ”€â”€ 02_router_integration_dispatch.json
â”‚   â”œâ”€â”€ myca-*.json
â”‚   â””â”€â”€ speech/
â”œâ”€â”€ archive/            # Versioned workflow backups
â”œâ”€â”€ backup/             # Export backups
â”œâ”€â”€ templates/          # Workflow templates
â””â”€â”€ registry/           # Version registry
```

## Usage

### Deploy Workflows to n8n

```bash
# Deploy all workflows (activate core workflows)
python scripts/deploy_n8n_workflows.py

# Deploy and activate ALL workflows
python scripts/deploy_n8n_workflows.py --activate-all

# Deploy to cloud instance
python scripts/deploy_n8n_workflows.py --cloud

# List current workflows
python scripts/deploy_n8n_workflows.py --list

# Backup workflows from n8n
python scripts/deploy_n8n_workflows.py --backup
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/workflows/health` | GET | Check n8n connection |
| `/workflows/stats` | GET | Get workflow statistics |
| `/workflows/list` | GET | List all workflows |
| `/workflows/{id}` | GET | Get specific workflow |
| `/workflows/create` | POST | Create new workflow |
| `/workflows/{id}` | PUT | Update workflow |
| `/workflows/{id}` | DELETE | Delete workflow |
| `/workflows/{id}/activate` | POST | Activate workflow |
| `/workflows/{id}/deactivate` | POST | Deactivate workflow |
| `/workflows/{id}/archive` | POST | Archive workflow version |
| `/workflows/{id}/versions` | GET | List archived versions |
| `/workflows/{id}/restore` | POST | Restore from archive |
| `/workflows/sync` | POST | Sync local to n8n |
| `/workflows/scheduler/start` | POST | Start 24/7 scheduler |
| `/workflows/scheduler/stop` | POST | Stop scheduler |

### Python API Usage

```python
from mycosoft_mas.core.n8n_workflow_engine import N8NWorkflowEngine, sync_workflows

# Quick sync
result = sync_workflows(activate_core=True)
print(f"Synced: {len(result.imported)} workflows")

# Full engine access
with N8NWorkflowEngine() as engine:
    # List workflows
    workflows = engine.list_workflows()
    
    # Activate a workflow
    engine.activate_workflow("workflow-id")
    
    # Archive with versioning
    engine.archive_workflow("workflow-id", reason="pre-update")
    
    # Clone a workflow
    engine.clone_workflow("workflow-id", "New Workflow Name")
    
    # Get execution stats
    stats = engine.get_execution_stats("workflow-id")
```

### MYCA Orchestrator Integration

```python
from mycosoft_mas.core.myca_workflow_orchestrator import (
    get_workflow_orchestrator,
    start_workflow_orchestrator
)

# Start the workflow orchestrator
orchestrator = await start_workflow_orchestrator(
    sync_interval=15,    # Sync every 15 minutes
    health_interval=5,   # Health check every 5 minutes
    archive_interval=24  # Archive daily
)

# Register event handlers
orchestrator.on_event("workflow_failed", handle_failure)
orchestrator.on_event("sync_complete", handle_sync)

# Get status
status = orchestrator.get_status()
print(f"Connected: {status.engine_connected}")
print(f"Workflows: {status.workflow_count}")

# Dynamic rewiring
orchestrator.rewire_workflow_connection(
    workflow_id="abc123",
    source_node="HTTP Request",
    target_node="Function"
)

# Disable/enable nodes
orchestrator.disable_node("abc123", "Slack Notification")
```

## Workflow Categories

| Category | Prefix | Description |
|----------|--------|-------------|
| CORE | `01_`, `02_`, `myca-` | MYCA core workflows |
| NATIVE | `native_` | Native integrations (AI, comms) |
| OPS | `ops_`, `20_` | Operations (Proxmox, UniFi) |
| SPEECH | `speech` | Voice/TTS workflows |
| TEMPLATE | `template` | Reusable templates |
| CUSTOM | - | User-created workflows |

## Scheduler Events

The 24/7 scheduler emits these events:

- `sync_complete`: After each sync cycle
- `workflow_failed`: When a workflow execution fails
- `health_check`: After each health check
- `health_degraded`: When failure count exceeds threshold

## Archiving & Versioning

Every workflow modification is automatically archived:
- Before updates
- Before deletions
- On scheduled archive cycles (daily)

Archives are stored in `n8n/archive/` with versioning:
```
{workflow_name}__v{version}__{timestamp}.json
```

Version registry stored in `n8n/registry/versions.json`.

## Security Notes

- API keys stored in environment variables
- Workflows archived before modification
- Deletion requires explicit `archive_first=False` to skip backup

## Troubleshooting

### Connection Issues
```python
engine = N8NWorkflowEngine()
health = engine.health_check()
if not health["connected"]:
    print(f"Error: {health['error']}")
```

### Sync Failures
Check the sync result for errors:
```python
result = engine.sync_all_local_workflows()
for error in result.errors:
    print(f"Failed: {error['file']} - {error['error']}")
```

---

*Document created: January 25, 2026*
*Author: MYCA Workflow Automation System*
