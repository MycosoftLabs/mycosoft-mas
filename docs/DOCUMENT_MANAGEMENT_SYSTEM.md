# Document Management System

Complete system for managing, indexing, and syncing all Mycosoft MAS documentation across local storage, GitHub, Notion, and NAS.

## Overview

This system provides:
- **Complete inventory** of all markdown and README files
- **Notion integration** for knowledge base sync
- **NAS sync** for shared access across the organization
- **Agent-accessible service** for MYCA and other agents
- **Automatic indexing** and categorization

## Components

### 1. Document Inventory Scanner (`scripts/document_inventory.py`)

Scans the entire codebase and creates a comprehensive inventory of all documents.

**Features:**
- Finds all `.md` and `README*` files
- Categorizes documents (root, docs, guides, reports, etc.)
- Tracks Git status (tracked, modified, on GitHub)
- Calculates file hashes for change detection
- Generates JSON inventory and markdown index

**Usage:**
```bash
python scripts/document_inventory.py
```

**Output:**
- `docs/document_inventory.json` - Complete inventory in JSON format
- `DOCUMENT_INDEX.md` - Human-readable markdown index

### 2. Notion Sync (`scripts/sync_to_notion.py`)

Syncs all documents to Notion knowledge base.

**Prerequisites:**
- Notion API key
- Notion database ID

**Environment Variables:**
```bash
export NOTION_API_KEY="your_api_key"
export NOTION_DATABASE_ID="your_database_id"
```

**Usage:**
```bash
python scripts/sync_to_notion.py
```

**Features:**
- Creates/updates Notion pages for each document
- Includes full document content
- Tracks metadata (path, category, size, hash)
- Links to GitHub when available

### 3. NAS Sync (`scripts/sync_to_nas.py`)

Syncs all documents to NAS shared drive for organization-wide access.

**Prerequisites:**
- NAS mounted and accessible
- Write permissions on NAS

**Environment Variables:**
```bash
# Windows
set NAS_DOCS_PATH=\\M-Y-C-A-L\docs

# Linux
export NAS_DOCS_PATH=/mnt/mycosoft-nas/docs
```

**Usage:**
```bash
python scripts/sync_to_nas.py
```

**Features:**
- Preserves directory structure
- Creates index files (JSON and Markdown)
- Verifies file integrity
- Fast access for agents and tools

### 4. Master Sync Script (`scripts/sync_all_documents.py`)

Orchestrates the complete workflow.

**Usage:**
```bash
python scripts/sync_all_documents.py
```

**Workflow:**
1. Scan and inventory all documents
2. Sync to Notion (if configured)
3. Sync to NAS (if configured)
4. Generate summary report

### 5. Document Service (`mycosoft_mas/services/document_service.py`)

Python service for agents to access documents programmatically.

**Usage:**
```python
from mycosoft_mas.services.document_service import get_document_service

service = get_document_service()

# Get all documents
docs = service.get_all_documents()

# Search documents
results = service.search_documents("deployment")

# Read document content
content = service.read_document("docs/SYSTEM_INTEGRATIONS.md")

# Get documents by category
guides = service.get_documents_by_category("guides")

# Get document summary
summary = service.get_document_summary()
```

## Document Categories

Documents are automatically categorized:

- **root** - Root-level documents
- **docs** - General documentation
- **readme** - README files
- **guides** - Setup/installation guides
- **reports** - Status reports and summaries
- **integration** - Integration documentation
- **deployment** - Deployment and Docker docs
- **agent** - Agent-specific documentation
- **module** - Module documentation
- **service** - Service documentation
- **other** - Uncategorized

## Inventory Structure

The inventory JSON contains:

```json
{
  "metadata": {
    "version": "1.0",
    "generated": "2024-01-01T00:00:00",
    "root_path": "/path/to/repo",
    "summary": {
      "total_documents": 120,
      "tracked_in_git": 100,
      "local_only": 20,
      "category_breakdown": {...}
    }
  },
  "documents": [
    {
      "id": "docs/SYSTEM_INTEGRATIONS.md",
      "name": "SYSTEM_INTEGRATIONS.md",
      "path": "docs/SYSTEM_INTEGRATIONS.md",
      "category": "integration",
      "size_bytes": 12345,
      "modified": "2024-01-01T00:00:00",
      "hash": "sha256...",
      "git": {
        "tracked": true,
        "modified": false,
        "on_github": true
      },
      "url_github": "https://github.com/...",
      "notion_ready": true,
      "nas_synced": false
    }
  ],
  "categories": {
    "integration": ["docs/SYSTEM_INTEGRATIONS.md", ...]
  }
}
```

## Setup

### 1. Initial Scan

Run the inventory scanner:

```bash
python scripts/document_inventory.py
```

### 2. Configure Notion (Optional)

1. Create a Notion database with these properties:
   - Name (Title)
   - Path (Rich Text)
   - Category (Select)
   - Size (Number)
   - Modified (Date)
   - GitHub (URL)
   - Local Path (Rich Text)
   - Hash (Rich Text)

2. Set environment variables:
```bash
export NOTION_API_KEY="secret_..."
export NOTION_DATABASE_ID="..."
```

3. Run sync:
```bash
python scripts/sync_to_notion.py
```

### 3. Configure NAS (Optional)

1. Mount NAS (if not already mounted):
   - Windows: Map network drive to `\\M-Y-C-A-L\docs`
   - Linux: Mount NFS/SMB share

2. Set environment variable:
```bash
export NAS_DOCS_PATH="/path/to/nas/docs"
```

3. Run sync:
```bash
python scripts/sync_to_nas.py
```

### 4. Run Complete Sync

```bash
python scripts/sync_all_documents.py
```

## Automation

### Scheduled Sync

Add to cron (Linux) or Task Scheduler (Windows):

```bash
# Daily sync at 2 AM
0 2 * * * cd /path/to/repo && python scripts/sync_all_documents.py
```

### CI/CD Integration

Add to GitHub Actions:

```yaml
- name: Sync Documents
  run: |
    python scripts/document_inventory.py
    python scripts/sync_to_notion.py
    python scripts/sync_to_nas.py
  env:
    NOTION_API_KEY: ${{ secrets.NOTION_API_KEY }}
    NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
    NAS_DOCS_PATH: ${{ secrets.NAS_DOCS_PATH }}
```

## Access for Agents

MYCA and other agents can access documents via the Document Service:

```python
from mycosoft_mas.services.document_service import get_document_service

service = get_document_service()

# Get system topology
docs = service.get_all_documents()
for doc in docs:
    content = service.read_document(doc["path"])
    # Process document...
```

## Troubleshooting

### Inventory Not Found

Ensure you've run the inventory scanner first:
```bash
python scripts/document_inventory.py
```

### Notion Sync Fails

- Verify API key and database ID
- Check database schema matches expected properties
- Review Notion API rate limits

### NAS Sync Fails

- Verify NAS is mounted and accessible
- Check write permissions
- Ensure NAS_DOCS_PATH is set correctly

### Agent Service Errors

- Ensure inventory file exists
- Check file paths are correct
- Verify NAS path if using NAS access

## Maintenance

### Regular Updates

Run sync weekly or after major documentation changes:

```bash
python scripts/sync_all_documents.py
```

### Cleanup

Remove old documents from NAS if needed:
```bash
# NAS documents are in: $NAS_DOCS_PATH/mycosoft-mas-docs/
```

## Related Documentation

- `DOCUMENT_INDEX.md` - Complete document index
- `docs/document_inventory.json` - Full inventory data
- `README.md` - Main repository README

