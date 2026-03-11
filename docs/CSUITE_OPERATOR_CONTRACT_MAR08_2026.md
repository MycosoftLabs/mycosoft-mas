# C-Suite Operator Contract — Shared Runtime Agreement

**Date:** March 8, 2026  
**Status:** Canonical  
**Related:** CTO VM Blueprint, CFO MCP Connector, COWORK VM Continuity, `config/csuite_role_manifests.yaml`, `config/csuite_openclaw_defaults.yaml`

---

## Purpose

All four OpenClaw-driven executive assistants (CEO/Atlas, CFO/Meridian, CTO/Forge, COO/Nexus) operate under a **single shared runtime contract** so they behave consistently under MYCA/Morgan supervision. This document defines that contract.

---

## 1. Role Identity Model

Every C-Suite operator has exactly three identifiers:

| Field | Description | Example |
|-------|-------------|---------|
| `role` | Canonical role (CEO, CFO, CTO, COO) | `CTO` |
| `assistant_name` | Persona name for the assistant | `Forge` |
| `primary_tool` | Primary desktop/surface the operator uses | `Cursor` |

Canonical mapping from `config/csuite_role_manifests.yaml`:

| Role | Assistant | Primary Tool |
|------|-----------|--------------|
| CEO | Atlas | MYCAOS |
| CFO | Meridian | Perplexity |
| CTO | Forge | Cursor |
| COO | Nexus | Claude Cowork |

**Rule:** All heartbeat, report, and escalation payloads MUST include `role`, `assistant_name`, and `primary_tool`. MAS uses these to route and display C-Suite status.

---

## 2. Heartbeat / Report / Escalate Vocabulary

All operators use the same MAS endpoints and payload shapes.

### Endpoints (MAS 192.168.0.188:8001)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/csuite/heartbeat` | POST | Register liveness; keep assistant in registry |
| `/api/csuite/report` | POST | Submit operating report (completion, summary, status) |
| `/api/csuite/escalate` | POST | Escalate decision to Morgan when bounded autonomy is exceeded |

### Heartbeat Payload

```json
{
  "role": "CTO",
  "assistant_name": "Forge",
  "ip": "192.168.0.194",
  "status": "healthy",
  "primary_tool": "Cursor",
  "extra": {
    "cursor_status": "running",
    "openclaw_status": "idle",
    "workspace_status": "synced",
    "source": "forge_adapter"
  }
}
```

- `status`: `healthy`, `busy`, `degraded`, `error`
- `extra`: Role-specific enrichment; shared keys allowed for dashboards

### Report Payload

```json
{
  "role": "CTO",
  "assistant_name": "Forge",
  "report_type": "task_complete",
  "summary": "Implemented Forge bridge; tests pass.",
  "details": { "task_id": "forge-001", "duration_min": 45 },
  "task_id": "forge-001",
  "escalated": false
}
```

- `report_type`: `operating`, `task_complete`, `summary`, `stale_work`, `error`
- `escalated`: If true, Morgan was involved

### Escalation Payload

```json
{
  "role": "CTO",
  "assistant_name": "Forge",
  "subject": "Schema change requires approval",
  "context": "Migration adds new column; production impact.",
  "options": ["Proceed", "Defer", "Discuss"],
  "urgency": "normal"
}
```

- `urgency`: `low`, `normal`, `high`, `critical`
- Escalations are persisted in Redis and visible to Morgan via `GET /api/csuite/escalations`

---

## 3. Scheduled-Task Philosophy

All C-Suite operators follow the same watchdog and scheduled-task pattern:

1. **Heartbeat task** — Runs every minute; registers liveness with MAS.
2. **Bridge/watchdog task** — Ensures the role-specific bridge/adapter is running; restarts if it dies.
3. **Primary-tool health task** — Ensures the primary tool (Cursor, Perplexity, Cowork, etc.) is running.
4. **Operating report task** — Periodically sends a summary to MAS for Morgan visibility.
5. **Workspace/repo sync task** — Where applicable (e.g. CTO), keeps workspace and rules/agents/skills fresh.

**Triggers:**
- At user logon
- Repeat interval (e.g. every 2–5 minutes) for watchdogs

**Settings:**
- Run on batteries, start when available
- Restart up to 3 times on failure
- Silent when healthy; log only when fixing

**Reference:** `scripts/install-cowork-vm-watchdog.ps1` (COO), `scripts/install-cto-vm-watchdog.ps1` (CTO).

---

## 4. Escalation Policy

Shared rules from `config/csuite_openclaw_defaults.yaml`:

### Must Escalate to Morgan

- Financial commitments above threshold
- External communications that represent the company
- Schema or infrastructure changes
- Security or compliance decisions

### Execute Without Escalation

- Internal task completion
- Research and summarization
- Draft responses for review
- Routing and triage

**Implementation:** MAS persists escalations in Redis (`csuite:escalations`). Morgan and MYCA surface them via `GET /api/csuite/escalations`. Escalations forward into MAS notifications and MYCA task queues as configured.

---

## 5. Registry of Capabilities and Tool Boundaries

| Role | Primary Tool | MAS Adapter | Role-Specific Endpoints | Tool Boundary |
|------|--------------|-------------|-------------------------|---------------|
| CEO | MYCAOS | (MYCA OS native) | — | Strategic planning, board support |
| CFO | Perplexity | `MeridianAdapter` | `/api/cfo-mcp/*`, `/api/csuite/cfo/*` | Finance ops, reporting, research |
| CTO | Cursor | `ForgeAdapter` | `/api/csuite/forge/*` | Coding, architecture, deploy, triage |
| COO | Claude Cowork | (Cowork native) | — | Operations, task routing, workflows |

**Rule:** Role-specific adapters MUST use the shared heartbeat/report/escalate endpoints first. Role-specific MCP/API endpoints extend the contract; they do not replace it.

---

## 6. MYCA → Forge Delegation and Reporting

### Delegation Flow

1. **MYCA OS (CEO)** or **Morgan** creates a CTO task via MAS.
2. MAS stores the task (Redis `csuite:cto:tasks`).
3. **Forge** on VM 194 polls `GET /api/csuite/forge/tasks?status=pending`.
4. Forge acknowledges via `POST /api/csuite/forge/tasks/{id}/ack` with `status=in_progress`.
5. Forge completes work and reports via `POST /api/csuite/report` with `task_id` and `report_type=task_complete`.
6. Forge acknowledges via `POST /api/csuite/forge/tasks/{id}/ack` with `status=complete`.

### Reporting Back (No Bypass)

- All reports go through `POST /api/csuite/report`.
- MAS persists reports; MYCA and Morgan read via `GET /api/csuite/forge/dashboard`, `GET /api/csuite/forge/summary`.
- Escalations go through `POST /api/csuite/escalate`; Morgan sees them via `GET /api/csuite/escalations`.
- Forge does NOT bypass MAS to reach Morgan directly. MAS is the control plane.

### Stale-Work Visibility

- MAS computes `stale_tasks` (pending/in_progress older than threshold).
- Forge dashboard and summary include `stale_tasks_count` and `stale_tasks` for Morgan oversight.
- Threshold: env `CSUITE_STALE_TASK_SEC` (default 3600).

---

## 7. Shared Security and Credentials

From `csuite_openclaw_defaults.yaml`:

- `no_hardcoded_secrets: true`
- `credentials_from_env: true`
- Env vars: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `PROXMOX_TOKEN`, `VM_PASSWORD`, etc.

All operators MUST read credentials from environment; never from code or config files.

---

## 8. Cross-Role Consistency Checklist

When adding a new C-Suite operator or role:

- [ ] Role identity in `csuite_role_manifests.yaml`
- [ ] Adapter class with `send_heartbeat`, `send_report`, `send_escalation`
- [ ] Scheduled tasks for heartbeat, bridge watchdog, operating report
- [ ] MAS endpoints for role-specific dashboard/summary if needed
- [ ] Escalation policy applied
- [ ] No bypass of MAS for Morgan communication

---

## References

- `config/csuite_role_manifests.yaml` — Role definitions
- `config/csuite_openclaw_defaults.yaml` — Bounded autonomy, reporting
- `mycosoft_mas/core/routers/csuite_api.py` — Heartbeat, report, escalate, escalations list
- `mycosoft_mas/edge/meridian_adapter.py` — CFO reference implementation
- `mycosoft_mas/edge/forge_adapter.py` — CTO reference implementation
- `docs/COWORK_VM_CONTINUITY_MAR04_2026.md` — COO watchdog pattern
- `docs/CFO_MCP_CONNECTOR_COMPLETE_MAR08_2026.md` — CFO full stack
