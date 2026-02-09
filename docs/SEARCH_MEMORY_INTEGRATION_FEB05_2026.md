# Search Memory Integration - February 5, 2026

## Overview

This document describes the Search Memory Integration system, which connects the homepage search feature with MYCA's memory architecture. The system tracks user search behavior, interests, and AI conversations to provide personalized search experiences and enrich the MINDEX database with user interest data.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Homepage Search Experience                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  User Search Query  ──►  Unified Search  ──►  Results Display               │
│         │                      │                    │                        │
│         ▼                      ▼                    ▼                        │
│  [Search Memory]        [Query Record]       [Click Tracking]                │
│         │                      │                    │                        │
└─────────┴──────────────────────┴────────────────────┴────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Search Memory Manager                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  SearchSession                                                               │
│    ├── queries: List[SearchQuery]                                            │
│    ├── focused_species: List[str]                                            │
│    ├── explored_topics: List[SearchTopic]                                    │
│    ├── ai_conversation: List[AIMessage]                                      │
│    └── widget_interactions: List[WidgetInteraction]                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Session Lifecycle                                                           │
│    start_session() ──► add_query() ──► record_focus() ──► end_session()     │
│                             │                │                               │
│                             ▼                ▼                               │
│                    [MINDEX Analytics]  [User Interests]                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Integration Points                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  MINDEX Database                                                             │
│    ├── mindex.search_sessions    (completed session data)                    │
│    ├── mindex.user_interests     (user interest scores per taxon)            │
│    └── mindex.search_analytics   (query-level analytics)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  MYCA 6-Layer Memory                                                         │
│    ├── Semantic: High-interest species (score >= 0.7)                        │
│    └── Episodic: AI breakthroughs and discoveries                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Memory Brain                                                                │
│    └── Search context injected into LLM prompts                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Voice Integration                                                           │
│    └── VoiceSearchBridge links voice sessions to search sessions             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### Backend (MAS)

#### 1. SearchMemoryManager (`mycosoft_mas/memory/search_memory.py`)

Core class managing search sessions:

```python
from mycosoft_mas.memory import get_search_memory

# Start a session
search_memory = await get_search_memory()
session = await search_memory.start_session(user_id="user_123")

# Record a query
query = await search_memory.add_query(
    session_id=session.id,
    query="psilocybe cubensis",
    result_count=15,
    result_types={"species": 10, "compounds": 5}
)

# Record focusing on a species
await search_memory.record_focus(
    session_id=session.id,
    species_id="42",
    topic="chemistry"
)

# End and consolidate
summary = await search_memory.end_session(session.id)
```

#### 2. Search Memory API (`mycosoft_mas/core/routers/search_memory_api.py`)

REST API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search/memory/start` | POST | Start new search session |
| `/api/search/memory/query` | POST | Record a search query |
| `/api/search/memory/focus` | POST | Record species/topic focus |
| `/api/search/memory/click` | POST | Record result click |
| `/api/search/memory/ai` | POST | Record AI conversation turn |
| `/api/search/memory/context/{session_id}` | GET | Get session context |
| `/api/search/memory/end/{session_id}` | POST | End session, get summary |
| `/api/search/memory/history` | GET | Get user's search history |
| `/api/search/memory/enrich` | POST | Enrich MINDEX with search data |
| `/api/search/memory/stats` | GET | Get system statistics |

#### 3. Voice-Search Bridge (`mycosoft_mas/memory/voice_search_memory.py`)

Links voice sessions with search sessions:

```python
from mycosoft_mas.memory import get_voice_search_bridge

bridge = await get_voice_search_bridge()

# Link sessions
link = await bridge.create_link(
    user_id="user_123",
    voice_session_id=voice_uuid,
    search_session_id=search_uuid
)

# Record voice query (propagates to search memory)
await bridge.record_voice_query(
    voice_session_id=voice_uuid,
    query="Tell me about cubensis",
    species_mentioned=["42"]
)

# Get search context for voice response
context = await bridge.get_search_context_for_voice(voice_uuid)
```

#### 4. Memory Brain Integration (`mycosoft_mas/llm/memory_brain.py`)

Search context is automatically injected into LLM prompts:

```
=== ACTIVE SEARCH SESSION ===
Recent searches: psilocybe cubensis, lion's mane
Currently viewing: Psilocybe cubensis
Species explored: 42, 87, 156
Topics explored: chemistry, genetics
Recent AI exchanges:
  user: What compounds are in this...
  assistant: Psilocybe cubensis contains...
```

### Database (PostgreSQL)

#### Migration: `018_search_memory.sql`

Creates tables:

1. **mindex.search_sessions** - Completed session data
2. **mindex.user_interests** - User interest scores per taxon
3. **mindex.search_analytics** - Query-level analytics

Views:

1. **mindex.popular_searches** - Popular queries in last 30 days
2. **mindex.user_interest_summary** - User interests with taxa names
3. **mindex.session_stats** - Daily session statistics

### Frontend (Website)

#### 1. API Routes

| Route | File | Description |
|-------|------|-------------|
| `/api/search/memory` | `app/api/search/memory/route.ts` | Main memory operations |
| `/api/search/memory/session/[sessionId]` | `app/api/search/memory/session/[sessionId]/route.ts` | Session-specific operations |
| `/api/search/mindex-enrich` | `app/api/search/mindex-enrich/route.ts` | MINDEX enrichment |
| `/api/search/history` | `app/api/search/history/route.ts` | User search history |

#### 2. Hooks

**useSearchMemory** - Direct memory operations:

```typescript
import { useSearchMemory } from '@/hooks/use-search-memory';

function SearchComponent() {
  const {
    sessionId,
    isActive,
    startSession,
    recordQuery,
    recordFocus,
    recordClick,
    recordAITurn,
    endSession,
    enrichMindex,
  } = useSearchMemory({ userId: 'user_123' });

  // Record a search
  const handleSearch = async (query: string, results: SearchResult[]) => {
    await recordQuery(query, results.length, { species: results.length });
  };

  // Record clicking a result
  const handleClick = async (speciesId: string) => {
    await recordClick(speciesId);
    await recordFocus(speciesId, 'species');
  };
}
```

**useSearchContext** - Context provider and consumer:

```typescript
import { SearchContextProvider, useSearchContext } from '@/hooks/use-search-context';

// Provider (wrap your app)
function App() {
  return (
    <SearchContextProvider userId="user_123" autoStart>
      <SearchPage />
    </SearchContextProvider>
  );
}

// Consumer (any component)
function SearchResults() {
  const { 
    queries, 
    currentSpecies, 
    focusedSpecies,
    recordQuery,
    recordFocus,
  } = useSearchContext();

  return (
    <div>
      <p>Recent: {queries.join(', ')}</p>
      <p>Viewing: {currentSpecies}</p>
    </div>
  );
}
```

**useMemoryTrackedSearch** - Automatic memory tracking:

```typescript
import { useMemoryTrackedSearch } from '@/hooks/use-unified-search';

function SearchWithMemory() {
  const [query, setQuery] = useState('');
  const sessionId = useSearchSession();

  const { 
    species, 
    compounds, 
    totalCount,
    recordClick,  // Built-in click recording
  } = useMemoryTrackedSearch(query, 'user_123', sessionId);

  return (
    <div>
      {species.map(s => (
        <SpeciesCard 
          key={s.id} 
          species={s}
          onClick={() => recordClick(s.id, 'species')}
        />
      ))}
    </div>
  );
}
```

## Memory Consolidation

When a search session ends, the system consolidates data:

### High-Interest Species → Semantic Memory

Species with interest score >= 0.7 are stored in MYCA's semantic memory:

```python
{
    "type": "user_search_interest",
    "user_id": "user_123",
    "species_id": "42",
    "interest_score": 0.85,
    "explored_topics": ["chemistry", "genetics"]
}
```

### AI Breakthroughs → Episodic Memory

Sessions with significant AI discoveries (4+ messages, detailed responses):

```python
{
    "type": "search_ai_discovery",
    "user_id": "user_123",
    "session_id": "...",
    "summary": {
        "message_count": 8,
        "topics_discussed": ["chemistry"],
        "species_discussed": ["42"]
    }
}
```

## Interest Score Calculation

Interest scores (0.0 - 1.0) are calculated from:

| Factor | Weight | Description |
|--------|--------|-------------|
| Base | 0.5 | Initial interest from any interaction |
| Focus Time | 0.3 max | Time spent viewing (up to 5 minutes) |
| Topic Exploration | 0.2 max | Number of widget interactions |
| AI Conversation | 0.2 max | Number of AI exchanges |

## Data Flow

1. **User starts search** → Session created
2. **User types query** → Query recorded, results tracked
3. **User clicks result** → Click and focus recorded
4. **User explores widgets** → Widget interactions tracked
5. **User asks AI** → AI turns recorded with context
6. **Session ends** (timeout or explicit) →
   - Summary calculated
   - MINDEX enriched with interests
   - High-value data consolidated to long-term memory

## Configuration

### Environment Variables

```bash
# MAS Backend
MINDEX_DATABASE_URL=postgresql://mycosoft:...@192.168.0.189:5432/mindex

# Website Frontend
MAS_API_URL=http://192.168.0.187:8000
```

### Session Timeout

Default: 30 minutes of inactivity

```python
SearchMemoryManager.SESSION_TIMEOUT = timedelta(minutes=30)
```

## Files Created

### Backend (MAS)

- `mycosoft_mas/memory/search_memory.py` - Search memory manager
- `mycosoft_mas/memory/voice_search_memory.py` - Voice-search bridge
- `mycosoft_mas/core/routers/search_memory_api.py` - REST API
- `migrations/018_search_memory.sql` - Database migration

### Frontend (Website)

- `app/api/search/memory/route.ts` - Main API route
- `app/api/search/memory/session/[sessionId]/route.ts` - Session route
- `app/api/search/mindex-enrich/route.ts` - Enrichment route
- `app/api/search/history/route.ts` - History route
- `hooks/use-search-memory.ts` - Direct memory hook
- `hooks/use-search-context.ts` - Context provider hook

### Modified Files

- `mycosoft_mas/memory/__init__.py` - Added exports
- `mycosoft_mas/llm/memory_brain.py` - Search context injection
- `mycosoft_mas/integrations/mindex_client.py` - User interest methods
- `mycosoft_mas/core/routers/__init__.py` - Router registration
- `hooks/use-unified-search.ts` - Memory tracking integration
- `hooks/index.ts` - Hook exports

## Testing

### Backend

```bash
# Test search memory API
curl -X POST http://192.168.0.187:8000/api/search/memory/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'

# Get stats
curl http://192.168.0.187:8000/api/search/memory/stats
```

### Frontend

```typescript
// In browser console
const response = await fetch('/api/search/memory?user_id=test');
const data = await response.json();
console.log(data);
```

## Related Documentation

- [MYCA Memory Architecture](./MYCA_MEMORY_ARCHITECTURE_FEB04_2026.md)
- [PersonaPlex Voice Integration](./MYCA_VOICE_REAL_INTEGRATION_FEB03_2026.md)
- [MINDEX Database Schema](./MINDEX_SCHEMA.md)
- [Homepage Search Plan](../.cursor/plans/search_memory_integration_85f68bff.plan.md)
