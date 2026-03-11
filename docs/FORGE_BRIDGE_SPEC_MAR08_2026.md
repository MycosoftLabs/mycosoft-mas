# Forge Bridge Spec — CTO VM 194

**Date:** March 8, 2026  
**Status:** Complete  
**Related Plan:** CTO VM 194 Blueprint (cto_vm_blueprint_bc9af924.plan.md)

## Overview

The Forge Bridge connects the CTO VM (192.168.0.194) to the MAS C-Suite API. Forge runs Cursor and OpenClaw as the primary engineering tool; the adapter sends enriched heartbeats, receives CTO task directives from MYCA/Morgan, reports completions, escalates engineering decisions, and maintains visibility of stale work.

## Delivered Components

### 1. ForgeAdapter

| File | Purpose |
|------|---------|
| `mycosoft_mas/edge/forge_adapter.py` | Thin adapter: heartbeat, report, escalation, task fetch/ack, dashboard |

**Usage (runs on CTO VM or any client):**

```python
from mycosoft_mas.edge import ForgeAdapter

adapter = ForgeAdapter(mas_api_url="http://192.168.0.188:8001", cto_vm_ip="192.168.0.194")

# Heartbeat with Cursor/OpenClaw/workspace status
await adapter.send_heartbeat(
    status="healthy",
    cursor_status="running",
    openclaw_status="ready",
    workspace_status="synced",
)

# Fetch pending CTO tasks from MYCA/Morgan
tasks = await adapter.fetch_pending_tasks(limit=10)

# Report completion
await adapter.send_report(
    report_type="task_complete",
    summary="Fixed auth bug in csuite_api",
    task_id="uuid-here",
)

# Escalate engineering decision
await adapter.send_escalation(
    subject="Security: rotate API key",
    context="Key may be exposed in logs",
    urgency="high",
)

# Mark task in progress or complete
await adapter.acknowledge_task(task_id="uuid", status="in_progress")
await adapter.acknowledge_task(task_id="uuid", status="complete", summary="Done")

# Dashboard (report history, tasks, assistant status)
dash = await adapter.get_forge_dashboard()
```

### 2. C-Suite API Forge Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/csuite/heartbeat` | POST | Register heartbeat (role=CTO, assistant=Forge) |
| `POST /api/csuite/report` | POST | Submit CTO report (role=CTO → CTO report history) |
| `POST /api/csuite/escalate` | POST | Escalate to Morgan |
| `POST /api/csuite/forge/task` | POST | Create CTO task (MYCA/Morgan delegation) |
| `GET /api/csuite/forge/tasks` | GET | List CTO tasks (filter: status, limit) |
| `POST /api/csuite/forge/tasks/{task_id}/ack` | POST | Acknowledge or complete task |
| `GET /api/csuite/forge/dashboard` | GET | CTO dashboard: report history, tasks, assistant status |

### 3. Redis Keys

| Key | Purpose |
|-----|---------|
| `csuite:cto:report_history` | CTO report history (list, max 100) |
| `csuite:cto:tasks` | CTO task hash (task_id → JSON) |

### 4. Task Model

```json
{
  "id": "uuid",
  "status": "pending | in_progress | complete | failed",
  "title": "string",
  "description": "string",
  "priority": "low | normal | high",
  "source": "myca | morgan | manual",
  "created_at": "ISO8601",
  "acked_at": "ISO8601 | null",
  "summary": "string | null",
  "details": {}
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAS_API_URL` | http://192.168.0.188:8001 | MAS API base URL |
| `CTO_VM_IP` | 192.168.0.194 | CTO VM IP for heartbeat identity |

## Integration with MYCA/Morgan

- **Task creation:** MYCA or Morgan delegates CTO work via `POST /api/csuite/forge/task`.
- **Forge polling:** Forge adapter calls `GET /api/csuite/forge/tasks?status=pending` to fetch work.
- **Report flow:** Forge sends reports via `POST /api/csuite/report`; CTO reports go to `csuite:cto:report_history`.
- **Escalation:** Forge calls `POST /api/csuite/escalate`; MAS forwards to MYCA/Morgan per csuite escalation policy.
- **Dashboard:** `GET /api/csuite/forge/dashboard` returns report history, pending tasks, and assistant status for MYCA control plane visibility.

## Verification Steps

1. **Heartbeat:** `curl -X POST http://192.168.0.188:8001/api/csuite/heartbeat -H "Content-Type: application/json" -d '{"role":"CTO","assistant_name":"Forge","ip":"192.168.0.194","status":"healthy","primary_tool":"Cursor","extra":{"cursor_status":"running"}}'`
2. **Create task:** `POST /api/csuite/forge/task` with `{"title":"...","description":"...","source":"manual"}`
3. **List tasks:** `GET /api/csuite/forge/tasks?status=pending`
4. **Dashboard:** `GET /api/csuite/forge/dashboard`

## Related Docs

- [CTO VM 194 Authoritative Spec](CTO_VM194_AUTHORITATIVE_SPEC_MAR08_2026.md)
- [CFO MCP Connector Complete](CFO_MCP_CONNECTOR_COMPLETE_MAR08_2026.md)
- [C-Suite OpenClaw VM Rollout Complete](CSUITE_OPENCLAW_VM_ROLLOUT_COMPLETE_MAR07_2026.md)
