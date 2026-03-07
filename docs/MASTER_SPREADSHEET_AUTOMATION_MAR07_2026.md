# Master Spreadsheet Automation

**Date**: March 7, 2026  
**Status**: Complete (inventory + hardware; other tabs scaffolded)  
**Related**: `config/master_spreadsheet_automation.yaml`, `scripts/sync_master_spreadsheet.py`, `n8n/workflows/myca-master-spreadsheet-sync.json`

## Overview

The master spreadsheet is the canonical source of truth for Mycosoft inventory, hardware, apps & services, vendors, commitments, liabilities, recruitment, production, and Singlogs. It is continuously propagated by:

1. **Scheduled sync** – n8n runs every 30 minutes
2. **On-demand sync** – Zapier or other tools call the n8n webhook
3. **MAS API** – Agents and integrations call `POST /api/spreadsheet/sync` directly

## Architecture

```
Sources (Supabase, MAS API, CSV)
    ↓
sync_master_spreadsheet.py (fetch → CSV → push)
    ↑
POST /api/spreadsheet/sync (MAS)
    ↑
n8n workflow (Schedule 30min + Webhook)
    ↑
Zapier / MYCA / manual trigger
```

## Spreadsheet

- **ID**: `1rhuGmyxZakCVet1zMK3_C2f3SCOzH_dr6HH6EKWGRmc`
- **Tabs** (from config):

| Tab | Source | Status |
|-----|--------|--------|
| inventory | Supabase `components` | ✅ Enabled |
| hardware | MAS `/api/devices/network` | ✅ Enabled |
| apps_and_services | manual/CSV | 🔲 GID + source needed |
| customer_vendors | manual | 🔲 GID + source needed |
| commitments | manual | 🔲 GID + source needed |
| liabilities | manual | 🔲 GID + source needed |
| recruitment | manual | 🔲 GID + source needed |
| production | manual | 🔲 GID + source needed |
| singlogs | manual | 🔲 GID + source needed |

## Config

`config/master_spreadsheet_automation.yaml`:

- `spreadsheet_id`: Google Sheet ID
- `tabs.<name>.gid`: Worksheet GID (required for push)
- `tabs.<name>.source`: `supabase` | `mas_api` | `csv` | `manual` | `zapier_webhook`
- `tabs.<name>.enabled`: Include in sync

## Sync Script

```bash
# CSV only (no push)
python scripts/sync_master_spreadsheet.py

# Push to Google Sheets
python scripts/sync_master_spreadsheet.py --push

# Specific tabs
python scripts/sync_master_spreadsheet.py --push --tabs inventory,hardware
```

**Env vars**:

- `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` – Supabase
- `MAS_API_URL` (default `http://192.168.0.188:8001`) – MAS
- `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_SHEETS_CREDENTIALS_JSON` – Google Sheets

## MAS API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/spreadsheet/sync` | POST | Trigger sync. Query: `?tabs=inventory,hardware` |
| `/api/spreadsheet/status` | GET | Last sync status |

## n8n Workflow

**File**: `n8n/workflows/myca-master-spreadsheet-sync.json`

- **Schedule**: Every 30 min
- **Webhook**: `POST /webhook/master-spreadsheet-sync` (for Zapier, on-demand)

Webhook URL (n8n on MAS 188):  
`http://192.168.0.188:5678/webhook/master-spreadsheet-sync`

### Deploying / Syncing the Workflow to n8n

After creating or editing the workflow JSON in `n8n/workflows/`, push it to both local and cloud n8n:

```powershell
# Sync workflow to n8n (requires empty JSON body)
Invoke-RestMethod -Uri "http://192.168.0.188:8001/api/workflows/sync-both" -Method POST -ContentType "application/json" -Body "{}"
```

Or run the n8n sync script if available. The `sync-both` endpoint requires `Content-Type: application/json` and a body (use `{}`).

## Zapier Integration

1. **Trigger sync after events**  
   Use Zapier Webhooks to POST to the n8n webhook above when inventory changes, new vendors, etc.

2. **Zapier → n8n webhook**  
   - Zapier Trigger: e.g. new row in Airtable, form submit, schedule  
   - Zapier Action: Webhooks by Zapier → POST to  
     `http://192.168.0.188:5678/webhook/master-spreadsheet-sync`

3. **Optional post-sync Zap**  
   After sync, MAS could call `ZAPIER_WEBHOOK_URL` (config) to notify Zapier for downstream flows.

## MYCA Integration

- **Agents** call `POST http://192.168.0.188:8001/api/spreadsheet/sync` to trigger sync
- **Context** – Spreadsheet data can be read from Google Sheets API or the generated CSVs in `data/master_sheet/`
- **Skills** – Add a "sync master spreadsheet" skill that calls the API

## Enabling Additional Tabs

1. Create the tab in the Google Sheet and note its GID (from URL: `gid=XXXXXXXX`)
2. Set `tabs.<name>.gid` and `enabled: true` in config
3. Choose source:
   - **Supabase**: Set `source: supabase`, `supabase_table`, `columns`
   - **MAS API**: Set `source: mas_api`, `mas_endpoint`, `columns`
   - **CSV**: Create `data/master_sheet/<tab>.csv` with header row; set `source: csv`, `csv_path`
   - **Zapier**: Zapier writes to the sheet; we don’t overwrite that tab

## Related Documents

- [INVENTORY_GOOGLE_SHEETS_SYNC_MAR07_2026.md](./INVENTORY_GOOGLE_SHEETS_SYNC_MAR07_2026.md) – Original components sync
- [MYCA_N8N_TRIGGER_PATTERN_MAR07_2026.md](./MYCA_N8N_TRIGGER_PATTERN_MAR07_2026.md) – MYCA→n8n pattern
