# Supabase + Google Sheets Full Automation

**Date:** March 7, 2026  
**Status:** Complete

## Overview

The Supabase backbone and Google Sheets sync are fully automated. One manual step is required once: creating a Google Cloud service account for Sheets API access.

## One-Time Manual Step: Google Service Account

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**.
2. Select or create a project.
3. **Enable Google Sheets API**: APIs & Services → Enable APIs → search "Google Sheets API" → Enable.
4. **Create a service account**:
   - APIs & Services → Credentials → Create Credentials → Service Account.
   - Name it (e.g. `myca-sheets-sync`).
   - Skip optional steps, click Done.
5. **Create a key**:
   - Open the new service account → Keys → Add Key → Create new key → JSON.
   - Download the JSON file.
6. **Share the master spreadsheet** with the service account email (e.g. `myca-sheets-sync@your-project.iam.gserviceaccount.com`):
   - Open the sheet: `1rhuGmyxZakCVet1zMK3_C2f3SCOzH_dr6HH6EKWGRmc`
   - Share → add the service account email with **Editor** access.

## Credential Options

Choose one:

| Option | How |
|--------|-----|
| **Inline JSON** | Add to MAS `.env`: `GOOGLE_SHEETS_CREDENTIALS_JSON={"type":"service_account",...}` (minified, single line) |
| **Base64** | Base64-encode the JSON and set `GOOGLE_SHEETS_CREDENTIALS_JSON=eyJ0eXBlIjoic2VydmljZV9hY2NvdW50Ii4uLn0=` |
| **File path** | Save JSON as `cred/myca-sheets.json` and set `GOOGLE_APPLICATION_CREDENTIALS=path/to/myca-sheets.json` |

The setup script auto-discovers service account JSON in:
- `~/Desktop/MYCOSOFT/cred/`
- `~/MYCOSOFT/cred/`
- `MAS/cred/`

## Automation Flow

```
n8n (every 30 min + webhook)
  → POST /api/ingest/external or /api/spreadsheet/sync
  → sync_master_spreadsheet.py --push
  → Google Sheets
```

## Run Automation

**One-shot (setup + sync):**
```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/_automate_supabase_and_sheets.py
```

**Setup only (env, creds, MAS restart, n8n sync):**
```powershell
python scripts/_setup_supabase_vm188.py
```

**Trigger sync only (MAS must be running):**
```powershell
# Via MAS API
Invoke-RestMethod -Uri "http://192.168.0.188:8001/api/spreadsheet/sync" -Method POST -ContentType "application/json" -Body "{}"

# Or run sync script directly (needs env + creds)
python scripts/sync_master_spreadsheet.py --push
```

## Config: Tabs Without GID

Tabs in `config/master_spreadsheet_automation.yaml` with empty `gid` are now supported:
- The sync script looks up the worksheet by **tab name**.
- If the worksheet does not exist, it is **created automatically**.

## Related

- `scripts/_setup_supabase_vm188.py` – VM env, creds, n8n key
- `scripts/sync_master_spreadsheet.py` – Multi-tab sync to Sheets
- `scripts/_automate_supabase_and_sheets.py` – One-shot setup + sync
- `config/master_spreadsheet_automation.yaml` – Tab config
- `mycosoft_mas/core/routers/spreadsheet_sync_api.py` – API endpoint
