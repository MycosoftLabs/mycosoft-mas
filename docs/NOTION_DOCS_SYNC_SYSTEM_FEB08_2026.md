# Mycosoft Documentation -> Notion Sync System (Feb 08, 2026)

## Overview

Comprehensive system that syncs **ALL documentation** (1,271+ .md files) across all Mycosoft repos to Notion. Includes auto-categorization, versioning, and a file watcher for real-time sync.

## Key Features

- **Multi-repo scanning**: MAS, WEBSITE, MINDEX, MycoBrain, NatureOS, Cursor Plans, MAS-NLM, MAS-TRN, Mycorrhizae
- **Auto-categorization**: 24 topic categories detected from filenames (Memory, Voice, Devices, API, etc.)
- **Versioning**: Changed documents create NEW Notion pages with date stamps - never replaces old versions
- **Real-time watcher**: Background process monitors all docs folders and auto-syncs new/changed files
- **Rate limiting**: Respects Notion API limits (3 req/sec) with automatic retry on 429
- **Content chunking**: Handles Notion's 2000-char block limit by intelligently splitting content
- **Sync state tracking**: SHA256 hashes track what's changed - only syncs what's needed

## Document Inventory

| Repo | Path | Count |
|------|------|-------|
| MAS | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\docs` | 379 |
| WEBSITE | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\docs` | 186 |
| Cursor Plans | `C:\Users\admin2\.cursor\plans` | 650 |
| MycoBrain | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\mycobrain\docs` | 23 |
| MINDEX | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex\docs` | 16 |
| NatureOS | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\NATUREOS\NatureOS\docs` | 11 |
| MAS-NLM | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\NLM\docs` | 3 |
| MAS-TRN | `C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\trn\docs` | 3 |
| **Total** | | **1,271** |

## Setup (First Time)

### Step 1: Create Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click **New integration**
3. Name: `Mycosoft Docs Sync`
4. Workspace: Select your Mycosoft workspace
5. Capabilities: Read, Update, Insert content
6. Click **Submit**
7. Copy the **Internal Integration Secret** (starts with `secret_`)

### Step 2: Create Notion Database

1. In Notion, create a new **full-page Database**
2. Name it: `Mycosoft Documentation`
3. **Share it** with the `Mycosoft Docs Sync` integration (click Share -> Invite)
4. Copy the **Database ID** from the URL:
   - URL format: `https://notion.so/workspace/<DATABASE_ID>?v=...`
   - The 32-character hex string is the Database ID

The sync script will automatically add these database properties:
- **Name** (title) - Document name
- **Repo** (select) - Source repo (MAS, WEBSITE, etc.)
- **Category** (select) - Auto-detected topic (Memory, Voice, API, etc.)
- **File Path** (text) - Relative path within repo
- **Source Type** (select) - Documentation or Plan
- **Sync Date** (date) - When this version was synced
- **File Modified** (date) - File's last modified time
- **Content Hash** (text) - For change detection
- **File Size** (number) - File size in bytes
- **Document Date** (text) - Date extracted from filename

### Step 3: Configure Credentials

**Option A: Interactive setup (recommended)**

```powershell
python scripts/notion_docs_sync.py --setup
```

**Option B: Manual**

```powershell
# Set permanently (User level)
[Environment]::SetEnvironmentVariable("NOTION_API_KEY", "secret_YOUR_KEY", "User")
[Environment]::SetEnvironmentVariable("NOTION_DATABASE_ID", "YOUR_DB_ID", "User")

# Also add to .env file
echo "NOTION_API_KEY=secret_YOUR_KEY" >> .env
echo "NOTION_DATABASE_ID=YOUR_DB_ID" >> .env
```

## Usage

### Full Sync (All Repos)

```powershell
python scripts/notion_docs_sync.py
# Or using PowerShell wrapper:
.\scripts\notion-sync.ps1 sync
```

### Sync Single Repo

```powershell
python scripts/notion_docs_sync.py --repo MAS
python scripts/notion_docs_sync.py --repo WEBSITE
python scripts/notion_docs_sync.py --repo "Cursor Plans"
```

### Dry Run (Preview)

```powershell
python scripts/notion_docs_sync.py --dry-run
.\scripts\notion-sync.ps1 dry-run
```

### Force Re-sync Everything

```powershell
python scripts/notion_docs_sync.py --force
.\scripts\notion-sync.ps1 force
```

### Sync Single File

```powershell
python scripts/notion_docs_sync.py --file "C:\...\docs\MY_DOC.md"
```

## Auto-Sync (File Watcher)

### Start Watcher (Foreground)

```powershell
python scripts/notion_docs_watcher.py
.\scripts\notion-sync.ps1 watch
```

### Start Watcher (Background)

```powershell
.\scripts\notion-sync.ps1 watch-bg
```

### Check Watcher Status

```powershell
.\scripts\notion-sync.ps1 status
```

### Stop Watcher

```powershell
.\scripts\notion-sync.ps1 stop
```

### Schedule Daily Sync (Windows Task Scheduler)

```powershell
.\scripts\notion-sync.ps1 schedule
# Creates "Mycosoft-NotionDocsSync" task running daily at 3 AM
```

## How Versioning Works

1. Every document gets a unique **sync key**: `{repo}:{relative_path}`
2. On first sync, a Notion page is created
3. On subsequent syncs, the file's **SHA256 hash** is compared to the stored hash
4. If content changed:
   - A **NEW** Notion page is created (the old version stays untouched)
   - The new page includes the sync date in its title
   - The sync state is updated to track the latest version
5. If content is unchanged, the document is skipped

This means you'll never lose old versions - they remain as separate pages in Notion, searchable by date.

## Auto-Categorization

Documents are automatically categorized by filename patterns:

| Category | Pattern Examples |
|----------|-----------------|
| Memory | MEMORY_*, *_MEMORY_* |
| Voice & AI | VOICE_*, PERSONAPLEX_*, MOSHI_* |
| Simulation | EARTH2_*, *_SIMULATION_* |
| Devices & Firmware | MYCOBRAIN_*, FIRMWARE_*, DEVICE_* |
| Deployment | DEPLOY_*, DOCKER_*, PIPELINE_* |
| Infrastructure | VM_*, PROXMOX_*, NAS_* |
| API | API_*, *_API_* |
| Security | SECURITY_*, AUDIT_* |
| Scientific | SCIENTIFIC_*, BIO_*, LAB_* |
| Testing | TEST_*, *_REPORT_* |
| Integration | INTEGRATION_*, *_SYNC_* |
| Architecture | ARCHITECTURE_*, SYSTEM_MAP_* |
| Planning | PLAN_*, ROADMAP_* |
| And 11 more... | See CATEGORY_PATTERNS in script |

## Files

| File | Purpose |
|------|---------|
| `scripts/notion_docs_sync.py` | Main sync script (discovery, categorization, upload) |
| `scripts/notion_docs_watcher.py` | File watcher for auto-sync |
| `scripts/notion-sync.ps1` | PowerShell convenience wrapper |
| `data/notion_sync_state.json` | Sync state tracking (hashes, page IDs) |
| `data/notion_watcher.log` | Watcher activity log |
| `data/notion_watcher.pid` | Background watcher PID file |

## Notion Database Schema

The database in Notion will be organized with these filterable/sortable properties:

- **Repo** - Filter by source repository
- **Category** - Filter by topic category
- **Source Type** - Documentation vs Plan
- **Sync Date** - Sort by when synced
- **File Modified** - Sort by file modification date
- **Document Date** - Date from filename (e.g., FEB08_2026)

### Recommended Notion Views

1. **All Docs** - Default table view sorted by Sync Date (newest first)
2. **By Repo** - Board view grouped by Repo property
3. **By Category** - Board view grouped by Category
4. **Recent Changes** - Table filtered to Sync Date = last 7 days
5. **Plans Only** - Table filtered to Source Type = Plan

## Troubleshooting

### "NOTION_API_KEY not set"
Run `python scripts/notion_docs_sync.py --setup` or set environment variables manually.

### "401 Unauthorized"
Regenerate API key at https://www.notion.so/my-integrations and update credentials.

### "404 Not Found"
The database ID is wrong or the integration hasn't been shared with the database. Go to the database in Notion, click Share, and add your integration.

### Rate Limiting
The script automatically handles 429 responses with retry-after delays. For 1,271 docs, initial sync takes about 15-20 minutes.

### Large Files
Files with more than 100 Notion blocks are truncated (Notion API limit). The most important content (headings, first sections) is preserved.

## Dependencies

- Python 3.11+
- `requests` (HTTP client for Notion API)
- `watchdog` (file system monitoring)

Install: `pip install requests watchdog`
