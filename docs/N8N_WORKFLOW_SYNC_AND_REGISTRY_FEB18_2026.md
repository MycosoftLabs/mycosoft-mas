# n8n Workflow Sync and MYCA Registry – February 18, 2026

**Status:** Complete  
**Purpose:** Local and cloud n8n forever synced; MYCA full view and full access to workflows; all agents and rules for workflow creation and modification in place.

---

## Summary

- **Sync:** Repo `n8n/workflows/*.json` is source of truth. `POST /api/workflows/sync-both` pushes to both **local** (N8N_LOCAL_URL) and **cloud** (N8N_URL) so production and local dev stay in sync.
- **Registry:** `GET /api/workflows/registry` gives MYCA a full list of all workflows (id, name, active, category, webhook_base).
- **MYCA access:** Full CRUD, activate/deactivate, clone, export, sync via `/api/workflows/*`. Mounted in `myca_main.py` under `/api/workflows/`.
- **Rules:** `.cursor/rules/n8n-management.mdc` – when to create workflows, when to sync, which sub-agents to use.
- **Sub-agents:** **n8n-workflow** (create/design), **n8n-ops** (health, sync), **n8n-workflow-sync** (sync-both, parity).

---

## API Endpoints (MAS)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/workflows/registry` | GET | Full registry for MYCA |
| `/api/workflows/sync-both` | POST | Sync repo → local + cloud |
| `/api/workflows/list` | GET | List workflows |
| `/api/workflows/health` | GET | n8n health |
| `/api/workflows/stats` | GET | Workflow stats |
| `/api/workflows/{id}` | GET/PUT/DELETE | Get, update, delete |
| `/api/workflows/{id}/activate` | POST | Activate |
| `/api/workflows/{id}/deactivate` | POST | Deactivate |
| `/api/workflows/create` | POST | Create |
| `/api/workflows/sync` | POST | Sync to primary n8n |
| `/api/workflows/export-all` | POST | Export all to repo |

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `N8N_URL` | `http://192.168.0.188:5678` | Production n8n (VM 188) |
| `N8N_LOCAL_URL` | `http://localhost:5678` | Local n8n |
| `N8N_API_KEY` | (none) | API key for production |
| `N8N_LOCAL_API_KEY` | (none) | API key for local |

---

## Files Touched

- `mycosoft_mas/core/myca_main.py` – Mount n8n_workflows_router under `/api`.
- `mycosoft_mas/core/routers/n8n_workflows_api.py` – Added `/registry`, `/sync-both`.
- `.cursor/rules/n8n-management.mdc` – New rule for all agents.
- `.cursor/agents/n8n-ops.md` – Updated for sync-both and registry.
- `.cursor/agents/n8n-workflow.md` – Updated for “anything that needs a workflow gets one” and sync-both.
- `.cursor/agents/n8n-workflow-sync.md` – New agent for sync and parity.
- `docs/SUBAGENT_ROLES_AND_COMMANDS_FEB12_2026.md` – n8n-workflow-sync and n8n row.
- `.cursor/rules/agent-must-invoke-subagents-and-docs.mdc` – n8n task row.

---

## Verification

1. **Registry:** `curl http://192.168.0.188:8001/api/workflows/registry`
2. **Sync-both:** `curl -X POST http://192.168.0.188:8001/api/workflows/sync-both -H "Content-Type: application/json" -d '{"activate_core": true}'`
3. **Health:** `curl http://192.168.0.188:8001/api/workflows/health`

---

## Related

- Rule: `.cursor/rules/n8n-management.mdc`
- Agents: `n8n-ops`, `n8n-workflow`, `n8n-workflow-sync`
- Engine: `mycosoft_mas/core/n8n_workflow_engine.py`
- Repo workflows: `n8n/workflows/*.json`
