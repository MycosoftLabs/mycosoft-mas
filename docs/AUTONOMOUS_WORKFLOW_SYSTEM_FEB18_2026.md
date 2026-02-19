# Autonomous n8n Workflow Management System

**Date:** February 18, 2026  
**Status:** Complete  
**Related plan:** `.cursor/plans/autonomous_n8n_workflow_system_77a7ade3.plan.md`

## Overview

The Autonomous n8n Workflow Management System implements 24/7 health monitoring, drift detection, auto-sync, voice/LLM execution, NLM-to-workflow triggers, and workflow outcome tracking. Source of truth remains `n8n/workflows/*.json`; sync targets both local and cloud n8n.

## Delivered Components

### Phase 1: Stub implementations fixed

| Component | File | Description |
|-----------|------|-------------|
| **N8NWorkflowAgent** | `mycosoft_mas/agents/workflow/n8n_workflow_agent.py` | Real implementation using N8NWorkflowEngine (list/get/activate/deactivate/sync) and N8NClient for execute_workflow. Task types: execute_workflow, trigger_workflow, list_workflows, get_workflow, activate, deactivate, sync_all. |
| **WorkflowGeneratorAgent** | `mycosoft_mas/agents/workflow_generator_agent.py` | Registered in agent registry; voice skill `system.workflow.create`; `generate_save_and_sync_workflow(description, name, tags)` saves to repo and runs sync-both. |

### Phase 2: Autonomous health and sync

| Component | File | Description |
|-----------|------|-------------|
| **WorkflowAutoMonitor** | `mycosoft_mas/services/workflow_auto_monitor.py` | Health loop every 60s (local + cloud n8n); drift loop every 15 min (repo vs instance checksums); auto-sync on drift; optional on_failure callback. Singleton: `get_workflow_auto_monitor()`. |
| **Startup/shutdown** | `mycosoft_mas/core/myca_main.py` | `startup_event`: starts WorkflowAutoMonitor; `shutdown_event`: stops it. |

### Phase 3: Voice and LLM integration

| Component | File | Description |
|-----------|------|-------------|
| **Voice run_workflow** | `mycosoft_mas/core/routers/voice_tools_api.py` | `run_workflow` tool: parses workflow name from query, calls N8NWorkflowAgent.process_task(execute_workflow). |
| **API execute** | `mycosoft_mas/core/routers/n8n_workflows_api.py` | `POST /workflows/execute` (WorkflowExecuteRequest: workflow_name, data) for voice and LLM. |
| **LLM tools** | `mycosoft_mas/llm/tool_pipeline.py` | `execute_workflow`: in-process call to N8NWorkflowAgent. `generate_workflow`: in-process call to WorkflowGeneratorAgent.generate_save_and_sync_workflow. Both registered in ToolRegistry. |

### Phase 4: NLM integration

| Component | File | Description |
|-----------|------|-------------|
| **NLM workflow bridge** | `mycosoft_mas/nlm/workflow_bridge.py` | `get_workflow_for_prediction(query_type, labels, metadata)`; `trigger_workflow_from_nlm(workflow_name, input_data)`; `maybe_trigger_workflow_from_prediction(...)` with confidence threshold. Map: anomaly→security_alert, spore_forecast→earth2_spore_alert, model_drift→nlm_model_hub, species_id→mindex_species_scraper. Exported from `mycosoft_mas.nlm`. |

### Phase 5: Learning and optimization

| Component | File | Description |
|-----------|------|-------------|
| **Workflow outcome tracking** | `mycosoft_mas/services/learning_feedback.py` | `record_workflow_execution(workflow_name, success, duration_seconds, error_message)`; `get_workflow_performance()` returns per-workflow stats (total, success_count, failed_count, success_rate, avg_duration_seconds). |
| **Execute endpoint** | `mycosoft_mas/core/routers/n8n_workflows_api.py` | POST /execute records start/duration and calls learning service on success/failure. |
| **Performance API** | `mycosoft_mas/core/routers/n8n_workflows_api.py` | `GET /workflows/performance` returns learning feedback workflow stats. |

### Phase 6: Cursor sub-agent enhancements

| Agent | File | Additions |
|-------|------|-----------|
| **n8n-autonomous** | `.cursor/agents/n8n-autonomous.md` | New agent: auto-monitor status, force drift/sync, view performance, restart monitor, configure intervals. |
| **n8n-ops** | `.cursor/agents/n8n-ops.md` | Auto-monitor and learning section; GET /workflows/performance, POST /workflows/execute. |
| **n8n-workflow** | `.cursor/agents/n8n-workflow.md` | Generate workflow from description (LLM/voice); execution history; GET /workflows/performance. |

## API Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/workflows/registry` | Full workflow registry |
| POST | `/api/workflows/sync-both` | Sync repo → local + cloud |
| POST | `/api/workflows/execute` | Execute workflow by name (voice/LLM) |
| GET | `/api/workflows/performance` | Per-workflow execution stats |
| GET | `/api/workflows/health` | n8n connection health |
| GET | `/api/workflows/list` | List workflows |

## Verification

1. **Registry:** `GET http://192.168.0.188:8001/api/workflows/registry` shows workflows.
2. **Sync:** `POST http://192.168.0.188:8001/api/workflows/sync-both` with `{"activate_core": true}` syncs to both.
3. **Voice:** "Run the backup workflow" → run_workflow tool → execute by name.
4. **LLM:** execute_workflow and generate_workflow tools in tool pipeline (in-process).
5. **Auto-monitor:** MAS startup logs show WorkflowAutoMonitor started.
6. **Drift:** Change in repo vs instance triggers auto-sync (monitor loop).
7. **NLM:** Use `maybe_trigger_workflow_from_prediction()` from NLM inference with confidence threshold.
8. **Performance:** `GET http://192.168.0.188:8001/api/workflows/performance` returns stats after executions.

## Related docs

- `docs/N8N_WORKFLOW_SYNC_AND_REGISTRY_FEB18_2026.md` — n8n sync and registry
- `.cursor/rules/n8n-management.mdc` — n8n management rule
- `.cursor/agents/n8n-ops.md`, `n8n-workflow.md`, `n8n-autonomous.md` — sub-agents
