# Supabase Credentials Setup

**Date**: March 7, 2026  
**Related**: `docs/SUPABASE_OPERATIONAL_BACKBONE_COMPLETE_MAR07_2026.md`

## Overview

Store all Supabase, Google Sheets, and external-integration credentials in `.env` (gitignored). Never hardcode or commit secrets.

## Setup Steps

### 1. Copy the example

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
copy .env.example .env
```

### 2. Fill in `.env` with your values

Use the variable names below. Get values from Supabase dashboard, Google Cloud Console, etc.

| Variable | Where to get it |
|----------|-----------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase Project Settings → API → Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Project Settings → API → service_role secret |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` | Supabase Project Settings → API → publishable key |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to your Sheets service account JSON file |
| `ASANA_API_KEY` | Asana → My Settings → Apps → Personal access token |
| `ASANA_WORKSPACE_ID` | Asana workspace URL or API |
| `NOTION_API_KEY` | Notion → Integrations → Create integration |
| `NOTION_DATABASE_*` | Notion database IDs (from database URL) |
| `GITHUB_TOKEN` | GitHub → Settings → Developer settings → Personal access tokens |
| `GITHUB_OWNER` | Your GitHub org or username |
| `GITHUB_REPO` | Repo name or owner/repo |

### 3. Google Sheets service account

1. Ensure the service account JSON exists (e.g. `client_secret_*.json`).
2. Set `GOOGLE_APPLICATION_CREDENTIALS` to the full path, e.g.:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=C:\Users\admin2\Desktop\MYCOSOFT\cred\client_secret_537091752800-....json
   ```
3. Share the master Google Sheet with the service account email (e.g. `myca-sheets@gen-lang-client-0314241488.iam.gserviceaccount.com`).

### 4. MAS VM (188) deployment

For the MAS container on VM 188 to run ingest and spreadsheet sync, pass these env vars when starting the container:

- `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GOOGLE_APPLICATION_CREDENTIALS` (path inside container, or mount the JSON file)

Or load from a `.env` file on the VM before `docker run`.

### 5. Website `.env.local`

For frontend Supabase access, add to `WEBSITE/website/.env.local`:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY`

## Verification

```powershell
# Ingest
curl -X POST "http://192.168.0.188:8001/api/ingest/external"

# Spreadsheet sync
curl -X POST "http://192.168.0.188:8001/api/spreadsheet/sync"

# LLM ledger (after chat): check llm_usage_ledger in Supabase
```

## Related

- `.env.example` — Variable names and placeholders
- `docs/SUPABASE_OPERATIONAL_BACKBONE_COMPLETE_MAR07_2026.md` — Architecture
- `no-hardcoded-secrets.mdc` — Security rule
