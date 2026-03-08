# CFO MCP Connector — Complete

**Date:** March 8, 2026  
**Status:** Complete  
**Related Plan:** CFO MCP Connector Plan (cfo_mcp_connector_69ee9307.plan.md)

## Overview

The CFO MCP Connector implements a hybrid Meridian/Perplexity runtime where:

- **Meridian** on the CFO VM (192.168.0.193) uses the Perplexity desktop app as the persona-facing surface
- A **MAS-hosted CFO MCP server** exposes finance discovery, delegation, workload visibility, and reporting
- A **thin Meridian adapter** on the CFO VM talks to the CFO MCP and relays reports back to MAS
- Finance actions are **first-class** in the MYCA federation loop (no generic fallback)
- New finance agents are **dynamically discoverable** from the registry without code changes

## Delivered Components

### 1. Finance Discovery Layer

| File | Purpose |
|------|---------|
| `mycosoft_mas/finance/discovery.py` | Canonical CFO-facing domain: `list_finance_agents`, `list_finance_services`, `list_finance_workloads`, `list_finance_tasks`, `delegate_finance_task`, `submit_finance_report`, `get_finance_status`, `get_finance_alerts` |

Pulls from `agent_registry` and C-Suite API; no hardcoded agent lists.

### 2. CFO MCP Server

| File | Purpose |
|------|---------|
| `mycosoft_mas/mcp/cfo_mcp_server.py` | Finance-specialized MCP server with 8 tools backed by discovery |
| `mycosoft_mas/core/routers/cfo_mcp_api.py` | REST API for Meridian: `GET /api/cfo-mcp/tools`, `POST /api/cfo-mcp/tools/call`, `GET /api/cfo-mcp/health` |

### 3. Meridian Adapter

| File | Purpose |
|------|---------|
| `mycosoft_mas/edge/meridian_adapter.py` | `MeridianAdapter` — connects to CFO MCP, packages Perplexity actions, relays reports to csuite |
| `scripts/run_meridian_adapter.py` | Runner: HTTP server on port 8995 |
| `infra/csuite/run_meridian_adapter.ps1` | CFO VM bootstrap script |

### 4. C-Suite Reporting Upgrades

| Endpoint | Purpose |
|----------|---------|
| `POST /api/csuite/finance-directive` | Persist CFO directives from Meridian |
| `POST /api/csuite/agent-report` | Agent/service reports back to CFO |
| `GET /api/csuite/cfo/dashboard` | CFO dashboard: directives, agent reports, summary |
| `GET /api/csuite/cfo/summary` | Compact summary for MYCA/Meridian |

Redis keys: `csuite:cfo:report_history`, `csuite:cfo:directives`, `csuite:cfo:agent_reports`.

### 5. MYCA Federation Integration

| File | Change |
|------|--------|
| `mycosoft_mas/myca/os/tool_orchestrator.py` | `run_finance_task()` — delegates to discovery |
| `mycosoft_mas/myca/os/core.py` | Route `task_type in ("finance","financial","cfo")` to `run_finance_task` |
| `mycosoft_mas/myca/os/gateway.py` | Webhook sources `csuite` and `finance` → `task_type=finance` |

### 6. Agent Registry Fixes

- Corrected `finance_admin` module path
- Resolved `financial` vs `financial_agent` naming mismatch
- Canonical CFO-facing finance registry entry

## Verification Steps

### Dynamic Discovery

1. Add a new finance agent to `agent_registry` with `AgentCategory.FINANCIAL`
2. Restart MAS
3. Call `GET http://192.168.0.188:8001/api/cfo-mcp/tools` and `POST /api/cfo-mcp/tools/call` with `name=list_finance_agents`
4. Confirm the new agent appears without changing MCP or discovery code

### End-to-End CFO Loop

1. **Meridian adapter** (on CFO VM or locally): `python scripts/run_meridian_adapter.py` — listens on 8995
2. **CFO MCP** (MAS): `http://192.168.0.188:8001/api/cfo-mcp/*`
3. **Flow:**
   - Meridian asks via Perplexity desktop
   - Adapter calls `POST /api/cfo-mcp/tools/call` with e.g. `list_finance_agents`
   - MCP delegates to discovery → agents
   - Adapter relays via `POST /api/csuite/report` or `/api/csuite/agent-report`
4. **MYCA visibility:** `GET /api/csuite/cfo/dashboard` and `GET /api/csuite/cfo/summary`

### Validation Script

`scripts/validate_cfo_mcp_connector.py` — Runs health, list_finance_agents, list_finance_services, cfo/dashboard, cfo/summary.

```bash
# Run validation (requires MAS on 188 with new CFO MCP code deployed)
python scripts/validate_cfo_mcp_connector.py
```

**Note:** Live validation requires deploying the CFO MCP and csuite changes to the MAS VM (192.168.0.188) via `deploy-mas-service` or equivalent. Until deployment, the script will return 404 for the new routes.

```bash
# Manual curl checks (after MAS deploy)
curl -s http://192.168.0.188:8001/api/cfo-mcp/health
curl -s http://192.168.0.188:8001/api/cfo-mcp/tools
curl -X POST http://192.168.0.188:8001/api/cfo-mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name":"list_finance_agents","arguments":{}}'
```

## Key Files

| Purpose | Path |
|---------|------|
| Finance discovery | `mycosoft_mas/finance/discovery.py` |
| CFO MCP server | `mycosoft_mas/mcp/cfo_mcp_server.py` |
| CFO MCP API | `mycosoft_mas/core/routers/cfo_mcp_api.py` |
| C-Suite API | `mycosoft_mas/core/routers/csuite_api.py` |
| Meridian adapter | `mycosoft_mas/edge/meridian_adapter.py` |
| Tool orchestrator | `mycosoft_mas/myca/os/tool_orchestrator.py` |
| Task routing | `mycosoft_mas/myca/os/core.py` |
| Webhook config | `mycosoft_mas/myca/os/gateway.py` |

## Known Gaps / Follow-Up

- Perplexity desktop automation boundaries may need adapter tweaks as the Perplexity app evolves
- Finance agent maturity varies; MCP sits on normalized discovery, but some agents may return placeholders
- Stale-task visibility for 24/7 oversight: `CSUITE_STALE_TASK_SEC` env (default 3600s) drives alerting

## Registries Updated

- `docs/SYSTEM_REGISTRY_FEB04_2026.md` — CFO MCP, finance discovery, Meridian adapter, csuite endpoints
- `docs/API_CATALOG_FEB04_2026.md` — CFO MCP API, csuite finance endpoints
- `docs/MASTER_DOCUMENT_INDEX.md` — This completion doc
