# Document Knowledge Base Integration

Complete integration of document access for MYCA and all agents via orchestrator, with fast vector search using Qdrant, Redis caching, and PostgreSQL storage.

## Overview

The Document Knowledge Base provides:
- **Vector search** via Qdrant for semantic document search
- **Redis caching** for fast metadata and content access
- **PostgreSQL storage** for document metadata (optional)
- **API endpoints** for user and agent access
- **Orchestrator integration** for automatic agent access

## Architecture

```
┌─────────────────┐
│   MYCA / Agents │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│   Orchestrator          │
│  (document_knowledge_   │
│   _base instance)       │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Document Knowledge Base │
│  - Qdrant (vectors)     │
│  - Redis (cache)         │
│  - Document Service      │
└─────────────────────────┘
```

## Components

### 1. Document Knowledge Base Service

**File:** `mycosoft_mas/services/document_knowledge_base.py`

**Features:**
- Vector embeddings using sentence-transformers
- Qdrant integration for similarity search
- Redis caching for fast access
- Automatic document indexing
- Related document discovery

**Usage:**
```python
from mycosoft_mas.services.document_knowledge_base import get_knowledge_base

kb = await get_knowledge_base()

# Search documents
results = await kb.search("deployment guide", limit=10)

# Get document content
content = await kb.get_document_content("docs/SYSTEM_INTEGRATIONS.md")

# Find related documents
related = await kb.get_related_documents("docs/SYSTEM_INTEGRATIONS.md")
```

### 2. API Router

**File:** `mycosoft_mas/core/routers/documents.py`

**Endpoints:**
- `GET /documents/search?q=query` - Search documents
- `POST /documents/search` - Search with advanced options
- `GET /documents/{path}` - Get document content
- `GET /documents/{path}/related` - Get related documents
- `GET /documents/stats/summary` - Get statistics
- `POST /documents/index/{path}` - Index a document

**Example:**
```bash
# Search
curl "http://localhost:8000/documents/search?q=deployment&limit=5"

# Get document
curl "http://localhost:8000/documents/docs/SYSTEM_INTEGRATIONS.md"
```

### 3. Orchestrator Integration

**File:** `mycosoft_mas/orchestrator.py`

The orchestrator automatically initializes the document knowledge base and makes it available to all agents:

```python
# In orchestrator
self.document_knowledge_base: Optional[DocumentKnowledgeBase] = None

# Agents can access via orchestrator
kb = orchestrator.document_knowledge_base
if kb:
    results = await kb.search("query")
```

### 4. Agent Access

Agents can access documents through the orchestrator:

```python
class MyAgent(BaseAgent):
    async def process_task(self, task):
        # Get orchestrator reference
        orchestrator = self.get_orchestrator()  # Implement this
        
        if orchestrator and orchestrator.document_knowledge_base:
            kb = orchestrator.document_knowledge_base
            
            # Search for relevant documents
            docs = await kb.search(task.description, limit=5)
            
            # Read document content
            for doc in docs:
                content = await kb.get_document_content(doc["path"])
                # Process content...
```

## Setup

### 1. Install Dependencies

```bash
pip install qdrant-client sentence-transformers redis
```

### 2. Configure Environment

```bash
# Qdrant
export QDRANT_URL="http://localhost:6333"

# Redis
export REDIS_URL="redis://localhost:6379/0"

# PostgreSQL (optional)
export DATABASE_URL="postgresql://user:pass@localhost/mas"
```

### 3. Index Documents

```bash
python scripts/index_documents.py
```

This will:
- Load all documents from inventory
- Generate embeddings
- Index in Qdrant
- Cache metadata in Redis

### 4. Start Services

```bash
# Start Qdrant (via Docker)
docker compose up -d qdrant

# Start Redis (via Docker)
docker compose up -d redis

# Start MAS API
uvicorn mycosoft_mas.core.myca_main:app --reload
```

## Usage

### For Agents

```python
# Access via orchestrator
async def my_agent_task(self, task):
    kb = self.orchestrator.document_knowledge_base
    
    if kb:
        # Search
        results = await kb.search("deployment", limit=5)
        
        # Get content
        for doc in results:
            content = await kb.get_document_content(doc["path"])
            # Use content...
```

### For Users (API)

```bash
# Search
curl "http://localhost:8000/documents/search?q=deployment&limit=10"

# Get specific document
curl "http://localhost:8000/documents/docs/SYSTEM_INTEGRATIONS.md"

# Get related documents
curl "http://localhost:8000/documents/docs/SYSTEM_INTEGRATIONS.md/related"
```

### For MYCA (Voice/UI)

MYCA can access documents through the API or directly via the orchestrator:

```python
# In MYCA voice handler
async def handle_voice_query(query: str):
    kb = orchestrator.document_knowledge_base
    if kb:
        results = await kb.search(query, limit=3)
        # Return top result content
        if results:
            content = await kb.get_document_content(results[0]["path"])
            return content[:500]  # First 500 chars
```

## Performance

### Caching Strategy

- **Redis cache TTL:** 1 hour
- **Document metadata:** Cached in Redis
- **Search results:** Cached by query hash
- **Document content:** Cached in Redis

### Vector Search

- **Embedding model:** `all-MiniLM-L6-v2` (384 dimensions)
- **Search limit:** Configurable (default: 10)
- **Min score:** Configurable (default: 0.5)

### Indexing

- **Batch size:** 10 documents (configurable)
- **Parallel processing:** Yes
- **Incremental updates:** Yes (checks hash before re-indexing)

## Maintenance

### Re-index All Documents

```bash
python scripts/index_documents.py
```

### Index Single Document

```bash
curl -X POST "http://localhost:8000/documents/index/docs/SYSTEM_INTEGRATIONS.md?force=true"
```

### Check Statistics

```bash
curl "http://localhost:8000/documents/stats/summary"
```

## Troubleshooting

### Qdrant Not Available

If Qdrant is not available, the knowledge base will still work but without vector search:
- Document service still works
- Redis caching still works
- Search falls back to text matching

### Redis Not Available

If Redis is not available:
- Caching is disabled
- All requests go to Qdrant/Document Service
- Performance may be slower

### Embeddings Not Available

If sentence-transformers is not installed:
- Vector search is disabled
- Search falls back to text matching
- Related documents feature disabled

## Integration with Memory Systems

### Short-term Memory (Redis)

Document metadata and search results are cached in Redis for fast access.

### Long-term Memory (PostgreSQL)

Document metadata can be stored in PostgreSQL for persistence (optional).

### Knowledge Graph (Qdrant)

Document embeddings are stored in Qdrant for semantic search and relationship discovery.

## Next Steps

1. ✅ Knowledge base service created
2. ✅ API endpoints added
3. ✅ Orchestrator integration complete
4. ⏭️ Add agent helper methods
5. ⏭️ Add MYCA voice integration
6. ⏭️ Add UI search component

## Related Documentation

- `docs/DOCUMENT_MANAGEMENT_SYSTEM.md` - Document management overview
- `docs/QUICK_START_DOCUMENT_SYNC.md` - Quick start guide
- `DOCUMENT_INDEX.md` - Complete document index

