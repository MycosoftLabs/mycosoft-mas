# Quick Start - Document Sync

Quick reference for syncing all Mycosoft MAS documents to Notion and NAS.

## One-Command Sync (Recommended)

### Windows (PowerShell)
```powershell
.\scripts\sync_all_documents.ps1
```

### Linux/Mac
```bash
python scripts/sync_all_documents.py
```

## Step-by-Step

### 1. Generate Inventory

```bash
python scripts/document_inventory.py
```

This creates:
- `docs/document_inventory.json` - Complete inventory
- `DOCUMENT_INDEX.md` - Human-readable index

### 2. Sync to Notion (Optional)

**Prerequisites:**
1. Create Notion database with properties:
   - Name (Title)
   - Path (Rich Text)
   - Category (Select)
   - Size (Number)
   - Modified (Date)
   - GitHub (URL)
   - Local Path (Rich Text)
   - Hash (Rich Text)

2. Get API credentials:
   - Create integration at https://www.notion.so/my-integrations
   - Copy API key
   - Get database ID from database URL

3. Set environment variables:
```powershell
# Windows
$env:NOTION_API_KEY = "secret_..."
$env:NOTION_DATABASE_ID = "..."

# Linux/Mac
export NOTION_API_KEY="secret_..."
export NOTION_DATABASE_ID="..."
```

4. Run sync:
```bash
python scripts/sync_to_notion.py
```

### 3. Sync to NAS (Optional)

**Prerequisites:**
1. Mount NAS (if not already):
   - Windows: Map network drive `\\M-Y-C-A-L\docs`
   - Linux: Mount NFS/SMB share

2. Set environment variable:
```powershell
# Windows
$env:NAS_DOCS_PATH = "\\M-Y-C-A-L\docs"

# Linux/Mac
export NAS_DOCS_PATH="/mnt/mycosoft-nas/docs"
```

3. Run sync:
```bash
python scripts/sync_to_nas.py
```

## Current Status

**Total Documents:** 271
- Tracked in Git: 245
- Local Only: 26
- Modified: 10

**Categories:**
- Root: 16
- README: 83
- Guides: 36
- Reports: 36
- Integration: 12
- Deployment: 6
- Other: 82

## Access Documents

### For Agents (Python)
```python
from mycosoft_mas.services.document_service import get_document_service

service = get_document_service()
docs = service.get_all_documents()
content = service.read_document("docs/SYSTEM_INTEGRATIONS.md")
```

### For Humans
- **Local:** See `DOCUMENT_INDEX.md`
- **Notion:** Check your Notion database
- **NAS:** `$NAS_DOCS_PATH/mycosoft-mas-docs/`

## Troubleshooting

**Inventory not found?**
```bash
python scripts/document_inventory.py
```

**Notion sync fails?**
- Check API key and database ID
- Verify database schema
- Check API rate limits

**NAS sync fails?**
- Verify NAS is mounted
- Check write permissions
- Ensure NAS_DOCS_PATH is set

## Automation

### Windows Task Scheduler
Create task to run daily:
```
Action: Start a program
Program: python
Arguments: C:\path\to\repo\scripts\sync_all_documents.py
```

### Linux Cron
```bash
# Daily at 2 AM
0 2 * * * cd /path/to/repo && python scripts/sync_all_documents.py
```

## Files Generated

- `docs/document_inventory.json` - Complete inventory (JSON)
- `DOCUMENT_INDEX.md` - Human-readable index
- `docs/DOCUMENT_MANAGEMENT_SYSTEM.md` - Full documentation

## Next Steps

1. Review `DOCUMENT_INDEX.md` for all documents
2. Configure Notion sync (optional)
3. Configure NAS sync (optional)
4. Set up automated sync schedule
5. Integrate Document Service into agents

