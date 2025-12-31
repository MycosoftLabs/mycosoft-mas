# Notion Knowledge Base Sync Setup

This guide explains how to set up automatic synchronization of documentation to Notion.

## Prerequisites

1. **Notion Account** with admin access to a workspace
2. **Notion Integration** created at https://www.notion.so/my-integrations
3. **Notion Database** for storing documentation

## Step 1: Create Notion Integration

1. Go to https://www.notion.so/my-integrations
2. Click **"New integration"**
3. Name it: `Mycosoft Docs Sync`
4. Select your workspace
5. Set capabilities:
   - ✅ Read content
   - ✅ Update content
   - ✅ Insert content
6. Click **Submit**
7. Copy the **Internal Integration Token** (starts with `secret_`)

## Step 2: Create Documentation Database

1. In Notion, create a new **Database** (full page)
2. Name it: `Mycosoft Documentation`
3. Add these properties:
   | Property Name | Type |
   |---------------|------|
   | Name | Title |
   | Path | Text |
   | Category | Select |
   | Size | Number |
   | Modified | Date |
   | GitHub | URL |
   | Local Path | Text |
   | Hash | Text |

4. Click **Share** → **Invite** → Select your integration
5. Copy the **Database ID** from the URL:
   - URL: `https://notion.so/workspace/abc123def456...`
   - Database ID: `abc123def456` (the 32-character ID)

## Step 3: Configure Environment Variables

### Windows (PowerShell)

```powershell
# Set for current session
$env:NOTION_API_KEY = "secret_your_api_key_here"
$env:NOTION_DATABASE_ID = "your_database_id_here"

# Set permanently (User level)
[Environment]::SetEnvironmentVariable("NOTION_API_KEY", "secret_your_api_key_here", "User")
[Environment]::SetEnvironmentVariable("NOTION_DATABASE_ID", "your_database_id_here", "User")
```

### Windows (CMD)

```cmd
set NOTION_API_KEY=secret_your_api_key_here
set NOTION_DATABASE_ID=your_database_id_here
```

### Linux/macOS

```bash
export NOTION_API_KEY="secret_your_api_key_here"
export NOTION_DATABASE_ID="your_database_id_here"

# Add to ~/.bashrc or ~/.zshrc for persistence
```

### .env File (Recommended)

Create a `.env` file in the project root:

```env
NOTION_API_KEY=secret_your_api_key_here
NOTION_DATABASE_ID=your_database_id_here
```

**Note:** The `.env` file is gitignored and should never be committed.

## Step 4: Run Document Sync

```bash
# First, update the document inventory
python scripts/document_inventory.py

# Then sync to Notion
python scripts/sync_to_notion.py
```

## Automated Sync

### Option 1: Scheduled Task (Windows)

```powershell
# Create scheduled task to run daily
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-File C:\path\to\mycosoft-mas\scripts\sync_all_documents.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "MycoSoft-NotionSync"
```

### Option 2: Git Hook

Add to `.git/hooks/post-commit`:

```bash
#!/bin/bash
python scripts/document_inventory.py
python scripts/sync_to_notion.py
```

### Option 3: CI/CD (GitHub Actions)

```yaml
# .github/workflows/sync-docs.yml
name: Sync Documentation
on:
  push:
    paths:
      - 'docs/**'
      - '*.md'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install requests
      - run: python scripts/sync_to_notion.py
        env:
          NOTION_API_KEY: ${{ secrets.NOTION_API_KEY }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
```

## Troubleshooting

### "NOTION_API_KEY not set"

Ensure environment variable is set in your current shell:

```powershell
echo $env:NOTION_API_KEY
```

### "404 Not Found"

The database ID is incorrect or the integration doesn't have access:
1. Verify database ID from URL
2. Ensure integration is shared with the database

### "401 Unauthorized"

The API key is invalid:
1. Regenerate the token in Notion integrations
2. Update environment variable

### Rate Limiting

If syncing many documents, you may hit rate limits. The script handles this with retries.

## What Gets Synced

| Document Type | Location | Category |
|--------------|----------|----------|
| MycoBoard Technical Reference | `docs/MYCOBOARD_TECHNICAL_REFERENCE.md` | Hardware |
| System Integration Guide | `docs/SYSTEM_INTEGRATION_GUIDE.md` | Integration |
| MycoBoard Roadmap | `docs/MYCOBOARD_ROADMAP.md` | Planning |
| MycoBrain README | `services/mycobrain/README.md` | Service |
| Notion Complete Guide | `docs/notion/MYCOBOARD_COMPLETE_GUIDE.md` | Knowledge Base |

Plus 400+ other documentation files.

## Related Scripts

- `scripts/document_inventory.py` - Scan and index all documents
- `scripts/sync_to_notion.py` - Sync to Notion knowledge base
- `scripts/sync_to_nas.py` - Sync to NAS storage
- `scripts/sync_all_documents.py` - Run all sync operations

---

*Last Updated: December 2024*























