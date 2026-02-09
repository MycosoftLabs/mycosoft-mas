# CREP Phase 3: LLM Agent Memory Graph - February 6, 2026

## Executive Summary

Phase 3 implements a comprehensive knowledge graph and memory system for the CREP platform, enabling LLM agents to maintain context across sessions, store facts, and perform semantic search.

---

## Components Created

### Backend (MAS) - 15 Files

#### 1. Database Schema
**File:** `migrations/023_mindex_knowledge_graph.sql`

- `knowledge_nodes` - Graph nodes with JSONB properties and pgvector embeddings
- `knowledge_edges` - Relationships with weighted connections
- `user_contexts` - Cross-session user preferences
- `session_memory` - Per-session state and conversation history
- Includes indexes, triggers, and helper functions

#### 2. Graph Schema Types
**File:** `mycosoft_mas/memory/graph_schema.py`

```python
class NodeType(str, Enum):
    SPECIES, DEVICE, LOCATION, EVENT, USER, SESSION, CONCEPT, PREDICTION, OBSERVATION, ENTITY, FACT

class EdgeType(str, Enum):
    RELATED_TO, CONTAINS, LOCATED_AT, OBSERVED_BY, BELONGS_TO, DERIVED_FROM, SIMILAR_TO, PRECEDED_BY, FOLLOWED_BY, CAUSED_BY, PART_OF
```

Includes dataclasses: `KnowledgeNode`, `KnowledgeEdge`, `GraphSearchResult`, `GraphTraversalResult`, `SemanticSearchResult`

#### 3. Knowledge Graph Implementation
**File:** `mycosoft_mas/memory/mindex_graph.py`

- `MindexGraph` class with async PostgreSQL operations
- Node CRUD: `create_node()`, `get_node()`, `find_nodes()`, `update_node()`, `delete_node()`
- Edge operations: `create_edge()`, `get_edges()`
- Graph traversal: `get_neighbors()` with configurable depth
- Semantic search: `semantic_search()` using pgvector

#### 4. Embedding Providers
**File:** `mycosoft_mas/memory/embeddings.py`

- `OpenAIEmbedder` - text-embedding-ada-002 (1536 dimensions)
- `GeminiEmbedder` - Google embedding-001 (768 dimensions)
- `LocalEmbedder` - sentence-transformers (384 dimensions)
- Factory function `get_embedder(provider)`

#### 5. Vector Memory
**File:** `mycosoft_mas/memory/vector_memory.py`

- `VectorMemory` class for semantic search with pgvector
- Embedding caching for performance
- `semantic_search()`, `embed_and_store()`, `find_similar_nodes()`

#### 6. User Context Manager
**File:** `mycosoft_mas/memory/user_context.py`

- `UserContext` dataclass with preferences and history
- `UserContextManager` for CRUD operations
- Tracks recent entities, queries, saved views
- `get_context_for_llm()` for prompt injection

#### 7. Session Memory Manager
**File:** `mycosoft_mas/memory/session_memory.py`

- `SessionMemory` dataclass with conversation state
- `SessionMemoryManager` for session operations
- Working memory for short-term facts
- Pending actions for confirmation gating

### LangGraph Tools - 4 Files

#### 8. Graph Lookup Tool
**File:** `mycosoft_mas/llm/tools/graph_lookup_tool.py`

```python
class GraphLookupTool:
    name = "graph_lookup"
    description = "Look up an entity in the knowledge graph and find related entities."
```

#### 9. Timeline Search Tool
**File:** `mycosoft_mas/llm/tools/timeline_search_tool.py`

```python
class TimelineSearchTool:
    name = "timeline_search"
    description = "Search the MINDEX timeline database for events and entity tracks."
```

#### 10. Memory Store Tool
**File:** `mycosoft_mas/llm/tools/memory_store_tool.py`

```python
class MemoryStoreTool:
    name = "memory_store"
    description = "Store a fact or observation in long-term memory."

class SemanticRecallTool:
    name = "memory_recall"
    description = "Recall facts from long-term memory using semantic search."
```

### API Endpoints - 1 File

#### 11. Knowledge Graph API
**File:** `mycosoft_mas/core/routers/knowledge_graph_api.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph/node/{id}` | GET | Get node by ID |
| `/api/graph/search` | GET | Search nodes |
| `/api/graph/traverse` | GET | Traverse graph |
| `/api/graph/node` | POST | Create node |
| `/api/graph/edge` | POST | Create edge |
| `/api/graph/memory/search` | POST | Semantic search |
| `/api/graph/memory/store` | POST | Store fact |
| `/api/graph/context/user/{id}` | GET/PUT | User context |
| `/api/graph/context/session/{id}` | GET | Session context |

---

### Frontend (Website) - 4 Files

#### 12. Agent Memory Hook
**File:** `hooks/useAgentMemory.ts`

- `useSemanticSearch()` - Search memory semantically
- `useMemoryStore()` - Store facts
- `useGraphLookup()` - Look up nodes
- `useGraphTraversal()` - Traverse graph
- `useUserContext()` - User preferences
- `useAgentMemory()` - Combined hook

#### 13. Memory Panel Component
**File:** `components/crep/memory/memory-panel.tsx`

Tabbed interface with:
- Context view (recent activity, saved views, preferences)
- Search view (semantic search with results)
- History view (query history)

#### 14. Context Indicator
**File:** `components/crep/memory/context-indicator.tsx`

Visual indicator showing:
- Brain icon with animation when active
- Sparkles for active context
- Badge with context count

#### 15. Index Export
**File:** `components/crep/memory/index.ts`

---

## Architecture Diagram

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                       CREP Dashboard                            â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”          â”‚
â”‚  â”‚ Memory Panel â”‚  â”‚   Timeline   â”‚  â”‚    Maps      â”‚          â”‚
â”‚  â”‚  Context Ind â”‚  â”‚              â”‚  â”‚              â”‚          â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜          â”‚
â”‚           â”‚                                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”       â”‚
â”‚  â”‚              useAgentMemory Hook                     â”‚       â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜       â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚ REST API
                           â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                        MAS Backend                              â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”          â”‚
â”‚  â”‚ Knowledge    â”‚  â”‚  LangGraph   â”‚  â”‚  Vector      â”‚          â”‚
â”‚  â”‚ Graph API    â”‚  â”‚  Tools       â”‚  â”‚  Memory      â”‚          â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜          â”‚
â”‚         â”‚                 â”‚                 â”‚                   â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”          â”‚
â”‚  â”‚                  MindexGraph                      â”‚          â”‚
â”‚  â”‚            User/Session Context                   â”‚          â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜          â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚
                           â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                      PostgreSQL + pgvector                      â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”          â”‚
â”‚  â”‚ knowledge_   â”‚  â”‚ user_        â”‚  â”‚ session_     â”‚          â”‚
â”‚  â”‚ nodes/edges  â”‚  â”‚ contexts     â”‚  â”‚ memory       â”‚          â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜          â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Usage Examples

### Store a Fact
```typescript
const { storeFact } = useAgentMemory();
await storeFact("The Amanita muscaria was observed near coordinates 45.5, -122.6", {
  importance: 0.8
});
```

### Semantic Search
```typescript
const { search, searchResults } = useAgentMemory();
await search("fungi observations near Portland");
// searchResults contains nodes with similarity scores
```

### Get User Context
```typescript
const { context } = useAgentMemory("user-123");
console.log(context.recent_entities);
console.log(context.preferred_layers);
```

### LLM Agent Tool Usage
```python
tools = get_all_tools()
# GraphLookupTool, TimelineSearchTool, MemoryStoreTool, SemanticRecallTool
```

---

## Configuration

### Environment Variables
```bash
DATABASE_URL=postgresql://mycosoft:mycosoft@localhost:5432/mindex
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
EMBEDDER_PROVIDER=openai  # or gemini, local
```

### Apply Migration
```bash
psql $DATABASE_URL -f migrations/023_mindex_knowledge_graph.sql
```

---

## Total Files Created: 15

| Category | Count | Files |
|----------|-------|-------|
| Migration | 1 | 023_mindex_knowledge_graph.sql |
| Memory Module | 6 | graph_schema.py, mindex_graph.py, embeddings.py, vector_memory.py, user_context.py, session_memory.py |
| LLM Tools | 4 | graph_lookup_tool.py, timeline_search_tool.py, memory_store_tool.py, __init__.py |
| API Router | 1 | knowledge_graph_api.py |
| Frontend Hooks | 1 | useAgentMemory.ts |
| Frontend Components | 3 | memory-panel.tsx, context-indicator.tsx, index.ts |

---

## Next Steps

Phase 3 is complete. The knowledge graph and memory system is ready for:
- Integration with existing LLM agents
- Connection to timeline data for contextual queries
- Deployment to production

CREP phases status:
- **Phase 4: Frontend Timeline Visualization** — Complete. LOD, trails, rendering libs + map layers (TrailLayer, EventMarkerLayer, AggregatedLayer, useLOD). See [CREP_PHASES_3_6_IMPLEMENTATION_FEB06_2026.md](CREP_PHASES_3_6_IMPLEMENTATION_FEB06_2026.md).
- **Phase 5: Data Pipeline Collectors** — Complete. OpenSky, USGS, NORAD, orchestrator, circuit breaker, audit log. AIS and NOAA collectors: see [CREP_PHASE5_ADDITIONAL_COLLECTORS_FEB06_2026.md](CREP_PHASE5_ADDITIONAL_COLLECTORS_FEB06_2026.md).
- **Phase 6: Performance & Scalability** — Complete. WebSocket pub/sub (realtime/pubsub.py), health checks, Prometheus-style metrics.