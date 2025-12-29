# Auto-Indexing Setup for New Documents

Automatic indexing system that detects and indexes new markdown/README files as they are created or modified.

## Overview

The system automatically:
- ✅ Detects new `.md` and `README*` files
- ✅ Indexes them in Qdrant for vector search
- ✅ Caches metadata in Redis
- ✅ Updates the document inventory
- ✅ Works via file system watcher or git hooks

## Components

### 1. Document Watcher Service

**File:** `mycosoft_mas/services/document_watcher.py`

Monitors the file system for new or modified documents and automatically indexes them.

**Features:**
- Periodic scanning (default: every 60 seconds)
- Hash-based change detection
- Automatic indexing in knowledge base
- Background operation

### 2. Auto-Index Script

**File:** `scripts/auto_index_new_documents.py`

Manual script to scan and index new documents immediately.

**Usage:**
```bash
python scripts/auto_index_new_documents.py
```

### 3. Git Hooks

**File:** `.git/hooks/post-commit`

Automatically indexes documents when markdown/README files are committed.

**Setup:**
```powershell
# Windows
.\scripts\setup_git_hooks.ps1

# Linux/Mac
chmod +x .git/hooks/post-commit
```

## Setup

### Option 1: Automatic Watcher (Recommended)

The document watcher starts automatically when the knowledge base is initialized:

```python
# In orchestrator or API startup
from mycosoft_mas.services.document_knowledge_base import get_knowledge_base

kb = await get_knowledge_base()  # Watcher starts automatically
```

**Configuration:**
- **Watch interval:** 60 seconds (default)
- **Root path:** Repository root
- **Auto-start:** Enabled by default

### Option 2: Manual Start via API

```bash
# Start watcher
curl -X POST "http://localhost:8000/documents/watch/start"

# Force scan
curl -X POST "http://localhost:8000/documents/watch/scan"
```

### Option 3: Git Hooks

Set up git hooks for automatic indexing on commit:

```powershell
# Windows
.\scripts\setup_git_hooks.ps1

# Linux/Mac
chmod +x .git/hooks/post-commit
```

The hook will automatically index any markdown/README files that are committed.

## How It Works

### File System Watcher

1. **Initial Scan:** On startup, scans all existing documents
2. **Periodic Scans:** Every 60 seconds, scans for new/modified files
3. **Change Detection:** Uses file hash to detect modifications
4. **Auto-Indexing:** Automatically indexes new/modified documents
5. **Background Operation:** Runs in background, non-blocking

### Git Hook

1. **Commit Detection:** Post-commit hook checks for markdown/README changes
2. **Background Indexing:** Runs indexing script in background
3. **Non-Blocking:** Doesn't slow down git operations

## Usage

### Automatic (Default)

The watcher starts automatically with the knowledge base. No action needed.

### Manual Scan

```bash
# Force immediate scan
python scripts/auto_index_new_documents.py

# Or via API
curl -X POST "http://localhost:8000/documents/watch/scan"
```

### Check Status

```bash
# Get statistics
curl "http://localhost:8000/documents/stats/summary"
```

## Configuration

### Watch Interval

Modify the watch interval in code:

```python
from mycosoft_mas.services.document_watcher import DocumentWatcher

watcher = DocumentWatcher(watch_interval=30)  # 30 seconds
```

### Root Path

Specify a different root path:

```python
watcher = DocumentWatcher(root_path="/path/to/docs")
```

## Integration

### With Orchestrator

The watcher is automatically started when the orchestrator initializes the knowledge base:

```python
# In orchestrator._initialize_document_knowledge_base()
self.document_knowledge_base = DocumentKnowledgeBase()
await self.document_knowledge_base.initialize()
# Watcher starts automatically
```

### With API

The watcher starts when the knowledge base is first accessed:

```python
# First API call to /documents/search
# Automatically initializes knowledge base and watcher
```

## Monitoring

### Logs

Watch for log messages:
```
INFO: Document watcher started
INFO: Found 3 new/modified documents
INFO: Auto-indexed document: docs/NEW_DOC.md
```

### Statistics

Check indexing statistics:
```bash
curl "http://localhost:8000/documents/stats/summary"
```

## Troubleshooting

### Watcher Not Starting

1. Check knowledge base initialization
2. Verify Qdrant and Redis are available
3. Check logs for errors

### Documents Not Indexing

1. Verify file is `.md` or `README*`
2. Check file is not in ignored directories (`.git`, `node_modules`, etc.)
3. Run manual scan to test

### Git Hook Not Working

1. Verify hook is executable: `chmod +x .git/hooks/post-commit`
2. Check hook file exists
3. Test hook manually: `bash .git/hooks/post-commit`

## Best Practices

1. **Let it run automatically** - The watcher handles everything
2. **Use git hooks** - For immediate indexing on commit
3. **Manual scan for bulk** - Use script for initial indexing
4. **Monitor logs** - Check for indexing errors

## Related Documentation

- `docs/DOCUMENT_KNOWLEDGE_BASE_INTEGRATION.md` - Knowledge base overview
- `docs/DOCUMENT_MANAGEMENT_SYSTEM.md` - Document management system
- `DOCUMENT_INDEX.md` - Complete document index

