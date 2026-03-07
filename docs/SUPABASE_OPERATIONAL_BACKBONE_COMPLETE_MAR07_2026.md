# Supabase Operational Backbone — Complete

**Date**: March 7, 2026  
**Status**: Complete  
**Related Plan**: `.cursor/plans/supabase_operational_backbone_d160cd3a.plan.md`

## Overview

The Supabase Operational Backbone provides a canonical schema and data flow for operational domains (commitments, liabilities, customer/vendors, hardware, inventory) with external ingest (Asana, Notion, GitHub), LLM usage cost ledger, and master spreadsheet projection.

## Deliverables

### 1. Supabase Schema

- **Migration**: `WEBSITE/website/supabase/migrations/20260307120000_supabase_operational_backbone.sql`
- **Tables**: `components`, `hardware_network_devices`, `commitments`, `liabilities`, `customer_vendors`, `recruitment_roles`, `llm_usage_ledger`, `sync_runs`, `sheet_sync_status`, and related linkage tables

### 2. External Ingestors

- **Script**: `scripts/ingest_external_to_supabase.py`
- **Sources**: Asana → commitments; Notion → customer_vendors, commitments, liabilities, recruitment_roles; GitHub → commitments
- **Logic**: Upsert by `source_system` + `source_record_id`; normalized `customer_vendors.type` to `customer`|`vendor`|`partner`

### 3. LLM Usage Ledger

- **Module**: `mycosoft_mas/llm/llm_ledger.py` — posts to Supabase `llm_usage_ledger` (provider, model, tokens_in, tokens_out, estimated_cost)
- **Integration**: `mycosoft_mas/llm/router.py` — calls `persist_to_supabase_ledger()` after primary and fallback completion paths

### 4. Ingest API

- **Router**: `mycosoft_mas/core/routers/ingest_api.py`
- **Endpoint**: `POST /api/ingest/external?sources=asana,notion,github`
- **Purpose**: Triggers `ingest_external_to_supabase.py`; used by n8n before sheet sync

### 5. Master Spreadsheet Projection

- **Script**: `scripts/sync_master_spreadsheet.py` — reads from Supabase, falls back to MAS; writes `sheet_sync_status`, `sync_runs`
- **Config**: `config/master_spreadsheet_automation.yaml` — tab definitions
- **API**: `GET /api/spreadsheet/status`, `POST /api/spreadsheet/sync` in `spreadsheet_sync_api.py`

### 6. n8n Orchestration

- **Workflow**: `n8n/workflows/myca-master-spreadsheet-sync.json`
- **Flow**: Cron every 30 min + webhook → POST `/api/ingest/external` → POST `/api/spreadsheet/sync`
- **Purpose**: Ingest external data first, then project to master Google Sheet

## Environment Variables (Names Only)

Store values in `.env` or `.env.local`; never hardcode.

| Purpose | Env Var |
|---------|---------|
| Supabase URL | `NEXT_PUBLIC_SUPABASE_URL` |
| Supabase service role | `SUPABASE_SERVICE_ROLE_KEY` |
| Supabase publishable key | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` |
| Asana | `ASANA_API_KEY` or `ASANA_PAT` or `MYCA_ASANA_TOKEN`, `ASANA_WORKSPACE_ID` |
| Notion | `NOTION_API_KEY`, `NOTION_DATABASE_COMMITMENTS`, `NOTION_DATABASE_VENDORS`, `NOTION_DATABASE_LIABILITIES`, `NOTION_DATABASE_RECRUITMENT` |
| GitHub | `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO` |
| Google Sheets | `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON) |

## Verification

1. **Ingest**: `curl -X POST "http://192.168.0.188:8001/api/ingest/external"`
2. **Spreadsheet sync**: `curl -X POST "http://192.168.0.188:8001/api/spreadsheet/sync"`
3. **LLM ledger**: After any chat completion, check `llm_usage_ledger` in Supabase
4. **n8n**: Run workflow manually; confirm Ingest → Sync sequence

## Related Documents

- `docs/MASTER_SPREADSHEET_AUTOMATION_MAR07_2026.md` — Master spreadsheet automation
- `docs/SYSTEM_REGISTRY_FEB04_2026.md` — System registry
- `docs/API_CATALOG_FEB04_2026.md` — API catalog
