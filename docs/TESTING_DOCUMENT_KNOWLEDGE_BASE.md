# Testing Document Knowledge Base

Complete guide for testing that the document knowledge base is working and accessible in Cursor and MYCA.

## Quick Test

Run the comprehensive test script:

```bash
python scripts/test_document_knowledge_base.py
```

This will test:
- ✅ Document service
- ✅ Knowledge base initialization
- ✅ Vector search
- ✅ Document indexing
- ✅ Search queries
- ✅ API endpoints

## Step-by-Step Testing

### 1. Test Document Service

```python
from mycosoft_mas.services.document_service import get_document_service

service = get_document_service()
docs = service.get_all_documents()
print(f"Found {len(docs)} documents")

# Search
results = service.search_documents("deployment")
print(f"Found {len(results)} deployment docs")
```

### 2. Test Knowledge Base

```python
from mycosoft_mas.services.document_knowledge_base import get_knowledge_base

kb = await get_knowledge_base()

# Search
results = await kb.search("deployment guide", limit=5)
for result in results:
    print(f"{result['name']}: {result['score']:.3f}")
```

### 3. Test API Endpoints

```bash
# Start API server
uvicorn mycosoft_mas.core.myca_main:app --reload

# In another terminal, test search
curl "http://localhost:8000/documents/search?q=deployment&limit=5"

# Test getting a document
curl "http://localhost:8000/documents/docs/SYSTEM_INTEGRATIONS.md"
```

## Testing in Cursor

### Method 1: Via Cursor's AI Chat

1. **Open Cursor**
2. **Open AI Chat** (Cmd/Ctrl + L)
3. **Ask questions about your documentation:**

```
"Search for deployment documentation"
"What integration guides do we have?"
"Show me the system architecture documentation"
```

The AI should be able to access documents via the knowledge base.

### Method 2: Via Code Context

1. **Open any Python file**
2. **Use @ to reference documents:**

```python
# In your code, you can reference:
from mycosoft_mas.services.document_knowledge_base import get_knowledge_base

# Ask Cursor: "How do I search for documents using the knowledge base?"
# Cursor should reference the documentation
```

### Method 3: Direct API Access

Create a test file in Cursor:

```python
# test_docs.py
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        # Search
        response = await client.get(
            "http://localhost:8000/documents/search",
            params={"q": "deployment", "limit": 5}
        )
        print(response.json())

asyncio.run(test())
```

## Testing with MYCA

### Method 1: Via Voice/UI

1. **Start MYCA** (if using voice interface)
2. **Ask questions:**

```
"MYCA, what deployment documentation do we have?"
"Search for integration guides"
"What's in the system architecture docs?"
```

### Method 2: Via API

```python
# In MYCA agent code
from mycosoft_mas.services.document_knowledge_base import get_knowledge_base

async def handle_query(query: str):
    kb = await get_knowledge_base()
    results = await kb.search(query, limit=3)
    
    if results:
        # Get top result content
        content = await kb.get_document_content(results[0]["path"])
        return content[:500]  # First 500 chars
    return "No documents found"
```

### Method 3: Via Orchestrator

```python
# In agent code
async def process_task(self, task):
    orchestrator = self.get_orchestrator()
    
    if orchestrator and orchestrator.document_knowledge_base:
        kb = orchestrator.document_knowledge_base
        
        # Search
        results = await kb.search(task.description, limit=5)
        
        # Use results...
```

## Verification Checklist

### ✅ Basic Functionality

- [ ] Document service loads all documents
- [ ] Knowledge base initializes successfully
- [ ] Qdrant connection works
- [ ] Redis connection works
- [ ] Embeddings generate correctly

### ✅ Search Functionality

- [ ] Vector search returns results
- [ ] Search scores are reasonable (> 0.5)
- [ ] Category filtering works
- [ ] Limit parameter works

### ✅ Indexing

- [ ] Documents can be indexed
- [ ] New documents are detected
- [ ] Modified documents are re-indexed
- [ ] Hash-based change detection works

### ✅ API Access

- [ ] Search endpoint works
- [ ] Get document endpoint works
- [ ] Related documents endpoint works
- [ ] Stats endpoint works

### ✅ Integration

- [ ] Orchestrator has knowledge base
- [ ] Agents can access via orchestrator
- [ ] Watcher starts automatically
- [ ] Auto-indexing works

## Common Issues and Solutions

### Issue: "Qdrant not available"

**Solution:**
```bash
# Start Qdrant
docker compose up -d qdrant

# Or check connection
curl http://localhost:6333/health
```

### Issue: "Redis not available"

**Solution:**
```bash
# Start Redis
docker compose up -d redis

# Or check connection
redis-cli ping
```

### Issue: "Embeddings not available"

**Solution:**
```bash
# Install sentence-transformers
pip install sentence-transformers
```

### Issue: "No search results"

**Solution:**
```bash
# Index documents first
python scripts/index_documents.py

# Or force scan
python scripts/auto_index_new_documents.py
```

### Issue: "API not accessible"

**Solution:**
```bash
# Start API server
uvicorn mycosoft_mas.core.myca_main:app --reload

# Check it's running
curl http://localhost:8000/health
```

## Test Scenarios

### Scenario 1: New Document Creation

1. Create a new file: `docs/TEST_DOC.md`
2. Add content: `# Test Document\n\nThis is a test.`
3. Wait 60 seconds (or run: `python scripts/auto_index_new_documents.py`)
4. Search: `curl "http://localhost:8000/documents/search?q=test"`
5. Verify: Should find the new document

### Scenario 2: Search from Cursor

1. Open Cursor
2. Ask: "What deployment documentation do we have?"
3. Cursor should reference docs from knowledge base
4. Verify: Results match actual deployment docs

### Scenario 3: MYCA Query

1. Start MYCA
2. Ask: "Search for integration guides"
3. MYCA should search knowledge base
4. Verify: Returns relevant integration docs

## Performance Testing

### Test Search Speed

```python
import time
import asyncio
from mycosoft_mas.services.document_knowledge_base import get_knowledge_base

async def test_speed():
    kb = await get_knowledge_base()
    
    queries = ["deployment", "integration", "API", "setup", "architecture"]
    
    for query in queries:
        start = time.time()
        results = await kb.search(query, limit=10)
        elapsed = time.time() - start
        print(f"{query}: {elapsed:.3f}s, {len(results)} results")

asyncio.run(test_speed())
```

**Expected:** < 0.5 seconds per query (with caching)

### Test Indexing Speed

```bash
time python scripts/index_documents.py
```

**Expected:** ~1-2 seconds per document

## Monitoring

### Check Statistics

```bash
curl "http://localhost:8000/documents/stats/summary"
```

### Check Logs

```bash
# Watch for indexing messages
tail -f logs/*.log | grep -i "index\|document"
```

### Check Qdrant

```bash
# Check collection
curl "http://localhost:6333/collections/mycosoft_documents"
```

## Success Criteria

✅ **All tests pass** in test script
✅ **Search returns results** for common queries
✅ **API endpoints respond** correctly
✅ **New documents auto-index** within 60 seconds
✅ **Cursor can access** documentation
✅ **MYCA can search** documentation

## Next Steps After Testing

1. ✅ Verify all tests pass
2. ✅ Test in Cursor
3. ✅ Test with MYCA
4. ✅ Monitor performance
5. ✅ Adjust configuration if needed

## Related Documentation

- `docs/DOCUMENT_KNOWLEDGE_BASE_INTEGRATION.md` - Integration guide
- `docs/AUTO_INDEXING_SETUP.md` - Auto-indexing setup
- `DOCUMENT_INDEX.md` - Complete document index


