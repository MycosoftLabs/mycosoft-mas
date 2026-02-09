# Timeline Storage & Caching Architecture - February 6, 2026

## Overview

This document describes the multi-tier caching architecture for the CREP timeline system. The architecture enables efficient time-series data access with sub-100ms latency for cached data, supporting smooth timeline scrubbing and real-time updates.

## Architecture Diagram

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                        CREP TIMELINE CACHING                             â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                          â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                                                   â”‚
â”‚  â”‚    Frontend      â”‚                                                   â”‚
â”‚  â”‚  (Next.js App)   â”‚                                                   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                                                   â”‚
â”‚           â”‚                                                              â”‚
â”‚           â–¼                                                              â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚  Memory Cache    â”‚â”€â”€â”€â–¶â”‚  IndexedDB Cache â”‚â”€â”€â”€â–¶â”‚ API Fetch       â”‚   â”‚
â”‚  â”‚  (5 min TTL)     â”‚    â”‚  (24 hour TTL)   â”‚    â”‚ (WEBSITE proxy) â”‚   â”‚
â”‚  â”‚  ~1ms latency    â”‚    â”‚  ~5ms latency    â”‚    â”‚ ~50-100ms       â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                                            â”‚            â”‚
â”‚  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•  â”‚
â”‚                                                            â”‚            â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                                      â”‚            â”‚
â”‚  â”‚   MAS Backend    â”‚â—€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜            â”‚
â”‚  â”‚  (FastAPI)       â”‚                                                   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                                                   â”‚
â”‚           â”‚                                                              â”‚
â”‚           â–¼                                                              â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚  Python Memory   â”‚â”€â”€â”€â–¶â”‚   Redis Cache    â”‚â”€â”€â”€â–¶â”‚ Snapshot Files  â”‚   â”‚
â”‚  â”‚  (5 min TTL)     â”‚    â”‚  (24 hour TTL)   â”‚    â”‚ (7 day archive) â”‚   â”‚
â”‚  â”‚  ~1ms latency    â”‚    â”‚  ~5ms latency    â”‚    â”‚ ~20ms latency   â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                                            â”‚            â”‚
â”‚  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•  â”‚
â”‚                                                            â”‚            â”‚
â”‚           â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜            â”‚
â”‚           â–¼                                                              â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚                      MINDEX Database                              â”‚  â”‚
â”‚  â”‚              (PostgreSQL - System of Record)                      â”‚  â”‚
â”‚  â”‚                     ~50-200ms latency                             â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚                                                                          â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Components

### Frontend (Website Repository)

#### 1. IndexedDB Cache (`lib/timeline/indexeddb-cache.ts`)

Browser-based persistent cache using IndexedDB.

**Features:**
- Stores entity states by timestamp
- Indexed by entity type, entity ID, and timestamp
- Automatic LRU eviction at 100MB
- 24-hour TTL with automatic cleanup

**Schema:**
```typescript
interface TimelineEntry {
  id: string                    // Composite key
  entityType: EntityType        // aircraft, vessel, satellite, etc.
  entityId: string              // Unique entity identifier
  timestamp: number             // Unix timestamp (ms)
  data: Record<string, unknown> // Entity state
  source: DataSource            // live, historical, forecast
  expires: number               // Expiration timestamp
  size: number                  // Approximate bytes
  accessedAt: number            // For LRU
}
```

#### 2. Cache Manager (`lib/timeline/cache-manager.ts`)

Orchestrates multi-tier cache access.

**Cache Lookup Order:**
1. **In-Memory** (fastest, 5-min TTL)
2. **IndexedDB** (fast, 24-hour TTL)
3. **API Fetch** (fallback)

**Features:**
- Automatic tier promotion (API â†’ IndexedDB â†’ Memory)
- Request deduplication for concurrent queries
- Batch operations for efficiency
- Background prefetching

#### 3. Time Loader (`lib/timeline/time-loader.ts`)

Optimized loading for timeline scrubbing.

**Features:**
- Throttled updates during rapid scrubbing (100ms)
- Predictive prefetching (Â±10 minutes)
- Chunk-based loading (5-minute chunks)
- Seamless past/present/future transitions

#### 4. React Hooks

**`useTimelineCache`** - Low-level cache access
- Query with automatic tier selection
- Cache statistics monitoring
- Live update subscription

**`useTimeline`** - High-level timeline state
- Current time management
- Playback controls
- Data loading coordination

#### 5. UI Components

**`TimelineSlider`** - Interactive time control
- Draggable cursor
- Play/pause/speed controls
- Event markers
- Past/present/future visualization
- Scale zoom (hours/days/weeks/months)

**`TimelinePanel`** - Complete timeline panel
- Cache stats display
- Data count indicator
- Collapsible design

### Backend (MAS Repository)

#### 1. Timeline Cache (`mycosoft_mas/cache/timeline_cache.py`)

Server-side multi-tier caching.

**Tiers:**
| Tier | TTL | Max Size | Latency |
|------|-----|----------|---------|
| Memory (Python dict) | 5 min | 10,000 entries | ~1ms |
| Redis | 24 hours | Unlimited | ~5ms |
| Snapshots | 7 days | Configurable | ~20ms |
| MINDEX | Forever | Unlimited | ~50-200ms |

**Redis Data Structure:**
- Entry storage: `timeline:{type}:{id}:{timestamp}` â†’ JSON
- Time index: `timeline:idx:{type}:{id}` â†’ Sorted Set (score = timestamp)

#### 2. Snapshot Manager (`mycosoft_mas/cache/snapshot_manager.py`)

Compressed archives for large time ranges.

**Storage Structure:**
```
/snapshots/
  /{entity_type}/
    /{YYYY-MM-DD}/
      /{HH}.json.gz
```

**Features:**
- Gzip compression
- Hourly buckets (configurable)
- Automatic cleanup of old snapshots
- Metadata index for fast lookup

#### 3. Timeline API (`mycosoft_mas/core/routers/timeline_api.py`)

FastAPI endpoints for timeline data.

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/timeline/range` | Query time range |
| GET | `/timeline/entity/{type}/{id}` | Get entity timeline |
| GET | `/timeline/at` | Get entity at timestamp |
| POST | `/timeline/batch` | Batch query |
| POST | `/timeline/ingest` | Ingest new data |
| DELETE | `/timeline/cache` | Invalidate cache |
| GET | `/timeline/stats` | Cache statistics |
| WS | `/ws/timeline` | Live updates |

## Data Flow

### Query Flow (User Scrubs Timeline)

```
1. User drags timeline cursor
   â”‚
   â–¼
2. TimelineSlider throttles (100ms)
   â”‚
   â–¼
3. TimeLoader checks loaded ranges
   â”‚
   â”œâ”€â”€ Range loaded? â†’ Return from memory
   â”‚
   â–¼
4. CacheManager.get() called
   â”‚
   â”œâ”€â”€ Check Memory Cache â†’ HIT? Return
   â”‚
   â”œâ”€â”€ Check IndexedDB â†’ HIT? Promote to Memory, Return
   â”‚
   â–¼
5. Fetch from /api/timeline/range
   â”‚
   â–¼
6. MAS Timeline API
   â”‚
   â”œâ”€â”€ Check Python Memory â†’ HIT? Return
   â”‚
   â”œâ”€â”€ Check Redis â†’ HIT? Promote to Memory, Return
   â”‚
   â”œâ”€â”€ Check Snapshots â†’ HIT? Return
   â”‚
   â–¼
7. Query MINDEX Database
   â”‚
   â–¼
8. Populate all cache tiers
   â”‚
   â–¼
9. Return data to client
```

### Ingest Flow (New Data Arrives)

```
1. Data collector receives update
   â”‚
   â–¼
2. MAS TimelineCache.store_live_update()
   â”‚
   â”œâ”€â”€ Store in Python Memory (sync)
   â”‚
   â”œâ”€â”€ Store in Redis (async background)
   â”‚
   â–¼
3. Broadcast via WebSocket
   â”‚
   â–¼
4. Frontend receives update
   â”‚
   â”œâ”€â”€ Store in Memory Cache
   â”‚
   â”œâ”€â”€ Store in IndexedDB
   â”‚
   â–¼
5. Update UI (if in viewport)
```

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Memory cache hit latency | < 5ms | In-browser/in-process |
| IndexedDB/Redis hit latency | < 20ms | Local storage |
| API cold query latency | < 200ms | With MINDEX query |
| Timeline scrub responsiveness | < 100ms | Perceived |
| Cache hit rate | > 80% | After warmup |
| Prefetch coverage | Â±10 minutes | Around current time |

## Configuration

### Frontend Environment Variables

```env
NEXT_PUBLIC_MAS_URL=http://192.168.0.188:8001
NEXT_PUBLIC_MAS_WS_URL=ws://192.168.0.188:8001/ws/timeline
```

### Backend Environment Variables

```env
REDIS_URL=redis://localhost:6379/0
SNAPSHOT_DIR=/tmp/crep-snapshots
```

### Cache Tuning

```python
# Backend (timeline_cache.py)
MEMORY_CACHE_TTL_SECONDS = 300      # 5 minutes
REDIS_CACHE_TTL_SECONDS = 86400     # 24 hours
MAX_MEMORY_ENTRIES = 10000

# Snapshot (snapshot_manager.py)
SNAPSHOT_BUCKET_HOURS = 1           # Hourly snapshots
MAX_LOCAL_SNAPSHOTS = 168           # 1 week of hourly snapshots
```

```typescript
// Frontend (indexeddb-cache.ts)
const MAX_CACHE_SIZE_MB = 100
const DEFAULT_TTL_HOURS = 24

// Frontend (cache-manager.ts)
const MEMORY_CACHE_MAX_ENTRIES = 1000
const MEMORY_CACHE_TTL_MS = 5 * 60 * 1000  // 5 minutes

// Frontend (time-loader.ts)
const PREFETCH_AHEAD_MS = 10 * 60 * 1000   // 10 minutes
const THROTTLE_MS = 100
const CHUNK_SIZE_MS = 5 * 60 * 1000        // 5 minute chunks
```

## Files Created

### Frontend (WEBSITE Repository)

| File | Description |
|------|-------------|
| `lib/timeline/indexeddb-cache.ts` | IndexedDB wrapper |
| `lib/timeline/cache-manager.ts` | Multi-tier cache orchestrator |
| `lib/timeline/time-loader.ts` | Time-based data loader |
| `lib/timeline/index.ts` | Module exports |
| `hooks/useTimelineCache.ts` | React cache hook |
| `hooks/useTimeline.ts` | React timeline state hook |
| `components/crep/timeline/timeline-slider.tsx` | Timeline slider UI |
| `components/crep/timeline/timeline-panel.tsx` | Complete timeline panel |
| `components/crep/timeline/index.ts` | Component exports |
| `app/api/timeline/route.ts` | API proxy route |
| `app/api/timeline/stats/route.ts` | Stats proxy route |

### Backend (MAS Repository)

| File | Description |
|------|-------------|
| `mycosoft_mas/cache/timeline_cache.py` | Redis timeline cache |
| `mycosoft_mas/cache/snapshot_manager.py` | Snapshot file manager |
| `mycosoft_mas/cache/__init__.py` | Module exports |
| `mycosoft_mas/core/routers/timeline_api.py` | FastAPI timeline endpoints |

## Usage Example

### Add Timeline to CREP Dashboard

```tsx
import { TimelinePanel } from "@/components/crep/timeline"

export default function CREPDashboard() {
  const [currentTime, setCurrentTime] = useState(Date.now())
  
  return (
    <div className="relative h-screen">
      {/* Map and other content */}
      <Map currentTime={currentTime} />
      
      {/* Timeline at bottom */}
      <TimelinePanel
        entityTypes={["aircraft", "vessel", "satellite", "earthquake"]}
        onTimeChange={setCurrentTime}
        onDataLoaded={(data) => console.log("Loaded", data.length, "entities")}
        position="bottom"
      />
    </div>
  )
}
```

### Query Timeline Data Directly

```typescript
import { getTimelineCacheManager } from "@/lib/timeline"

const manager = getTimelineCacheManager()

// Query last hour of aircraft data
const result = await manager.get({
  entityType: "aircraft",
  startTime: Date.now() - 60 * 60 * 1000,
  endTime: Date.now(),
  limit: 1000,
})

console.log(`Got ${result.data.length} entries from ${result.source}`)
```

## Related Documents

- [CREP Full Architecture Implementation Plan](../../.cursor/plans/crep_full_architecture_implementation_feb06_2026.plan.md)
- [Memory System Unified Integration](./MEMORY_UNIFIED_INTEGRATION_FEB05_2026.md)
- [CREP Voice Control](./CREP_VOICE_CONTROL_FEB06_2026.md)

---

*Document created: February 6, 2026*
*Last updated: February 6, 2026*