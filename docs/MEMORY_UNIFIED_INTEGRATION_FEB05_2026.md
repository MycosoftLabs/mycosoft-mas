# MYCA Memory System Unified Integration Guide
## February 5, 2026

This document provides a comprehensive guide to the unified memory system integration, covering Earth2 weather AI memory, GPU state memory, MINDEX consolidation, and enhanced context injection.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Memory Modules](#memory-modules)
3. [Database Schema](#database-schema)
4. [Context Injection](#context-injection)
5. [API Endpoints](#api-endpoints)
6. [Frontend Integration](#frontend-integration)
7. [Voice Command Memory](#voice-command-memory)
8. [Configuration](#configuration)
9. [Testing](#testing)

---

## Architecture Overview

The unified memory system consolidates all memory operations into MINDEX as the sole database backend, providing specialized memory modules for different domains:

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    MYCA Memory Brain                             â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚ Earth2 Memoryâ”‚  â”‚  GPU Memory  â”‚  â”‚  Search Memory       â”‚   â”‚
â”‚  â”‚              â”‚  â”‚              â”‚  â”‚                      â”‚   â”‚
â”‚  â”‚ - Forecasts  â”‚  â”‚ - VRAM State â”‚  â”‚ - Sessions           â”‚   â”‚
â”‚  â”‚ - User Prefs â”‚  â”‚ - Model Load â”‚  â”‚ - User Interests     â”‚   â”‚
â”‚  â”‚ - Model Statsâ”‚  â”‚ - Patterns   â”‚  â”‚ - Query History      â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚         â”‚                 â”‚                      â”‚               â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚                     MINDEX PostgreSQL                      â”‚  â”‚
â”‚  â”‚                   (Sole Database Backend)                  â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚                                                                  â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚              Context Injection (to LLM prompts)                  â”‚
â”‚  - User Profile        - GPU State                              â”‚
â”‚  - Recalled Memories   - Map Context                            â”‚
â”‚  - Recent Episodes     - Search Session                         â”‚
â”‚  - Voice History       - Earth2 Weather                         â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Memory Modules

### 1. Earth2 Memory (`mycosoft_mas/memory/earth2_memory.py`)

Specialized memory for weather AI forecasts:

**Features:**
- Forecast result storage with location, model, and timing
- User weather preference learning (favorite locations, models, variables)
- Model usage statistics tracking
- Inference result caching for quick recall

**Classes:**
- `Earth2Model` - Enum of supported models (FCN, Pangu, Graphcast, etc.)
- `WeatherVariable` - Enum of weather variables
- `ForecastResult` - Dataclass for forecast results
- `UserWeatherPreferences` - Learned user preferences
- `ModelUsageStats` - Model usage statistics
- `Earth2Memory` - Main memory manager

**Usage:**
```python
from mycosoft_mas.memory import get_earth2_memory

memory = await get_earth2_memory()

# Record a forecast
await memory.record_forecast(
    user_id="morgan",
    model="fcn",
    location={"lat": 37.7749, "lng": -122.4194},
    lead_time_hours=24,
    variables=["temperature", "wind_u", "wind_v"],
    inference_time_ms=1500,
    source="voice"
)

# Get user preferences
prefs = await memory.get_user_preferences("morgan")
print(f"Favorite locations: {prefs.favorite_locations}")

# Get model stats
stats = await memory.get_model_stats("fcn")
```

### 2. GPU Memory (`mycosoft_mas/memory/gpu_memory.py`)

Tracks GPU state and enables intelligent model preloading:

**Features:**
- Model load/unload event history
- VRAM usage tracking and snapshots
- Inference latency metrics
- Usage pattern learning for preload recommendations

**Classes:**
- `GPUModelType` - Enum of GPU model types
- `LoadState` - Model load states
- `ModelLoadEvent` - Load/unload event record
- `VRAMSnapshot` - Point-in-time VRAM state
- `ModelUsagePattern` - Learned usage patterns
- `GPUMemory` - Main memory manager

**Usage:**
```python
from mycosoft_mas.memory import get_gpu_memory

memory = await get_gpu_memory()

# Record model load
await memory.record_model_load(
    model_name="earth2_fcn",
    model_type="earth2_fcn",
    vram_mb=4096,
    load_time_ms=2500,
    triggered_by="voice"
)

# Get current state
state = await memory.get_current_state()
print(f"VRAM: {state['used_vram_mb']}MB / {state['total_vram_mb']}MB")

# Get preload recommendations
recommendations = await memory.get_preload_recommendations()
```

### 3. Search Memory (`mycosoft_mas/memory/search_memory.py`)

Manages homepage search sessions:

**Features:**
- Search session lifecycle management
- Query tracking with MINDEX enrichment
- Widget interaction recording
- AI conversation context
- Session consolidation to long-term memory

### 4. Voice-Search Bridge (`mycosoft_mas/memory/voice_search_memory.py`)

Links voice sessions to search sessions for seamless context.

---

## Database Schema

### Migration Files

1. **019_earth2_memory.sql** - Earth2 tables
   - `mindex.earth2_forecasts` - Forecast results
   - `mindex.earth2_user_preferences` - User preferences
   - `mindex.earth2_model_usage` - Model statistics

2. **019b_gpu_memory.sql** - GPU state tables
   - `mindex.gpu_model_events` - Load/unload events
   - `mindex.gpu_vram_snapshots` - VRAM snapshots
   - `mindex.gpu_model_patterns` - Usage patterns
   - `mindex.gpu_inference_metrics` - Inference timing

3. **020_mindex_unified_memory.sql** - Unified memory schema
   - `mindex.memory_entries` - Central memory storage
   - `mindex.conversation_memory` - Conversation turns
   - `mindex.episodic_memory` - Events and experiences
   - `mindex.working_memory` - Active session context
   - `mindex.system_memory` - Global facts
   - `mindex.user_profiles` - User information
   - `mindex.memory_relationships` - Knowledge graph edges
   - `mindex.memory_analytics` - Usage tracking

### Running Migrations

```bash
# Apply migrations to MINDEX database
psql -h 192.168.0.189 -U mycosoft -d mindex -f migrations/019_earth2_memory.sql
psql -h 192.168.0.189 -U mycosoft -d mindex -f migrations/019b_gpu_memory.sql
psql -h 192.168.0.189 -U mycosoft -d mindex -f migrations/020_mindex_unified_memory.sql
```

---

## Context Injection

The `MYCAMemoryBrain` (`mycosoft_mas/llm/memory_brain.py`) injects context from all memory sources into LLM prompts:

### Context Types

1. **User Profile** - Preferences and traits
2. **Recalled Memories** - Semantically relevant memories
3. **Recent Episodes** - Recent events
4. **Voice History** - Previous voice sessions
5. **Search Session** - Active search context
6. **Earth2 Weather** - Weather preferences and forecasts
7. **GPU State** - Model availability and VRAM
8. **Map Context** - Geographic context (when available)

### Example Injected Context

```
=== USER PREFERENCES ===
- preferred_language: English
- voice_style: conversational

=== RELEVANT MEMORIES ===
- User interested in mushroom cultivation
- Previous weather query for San Francisco

=== WEATHER AI CONTEXT ===
Favorite locations: San Francisco, Seattle
Preferred models: fcn, pangu
Recent forecasts: 2
  - San Francisco (fcn, 24h)

=== GPU STATE ===
VRAM: 8192MB / 32768MB (25%)
Loaded models: earth2_fcn, whisper
Active models: 2

=== ACTIVE SEARCH SESSION ===
Recent searches: psilocybe, cultivation, substrate
Species explored: Psilocybe cubensis, Psilocybe cyanescens
```

---

## API Endpoints

### Earth2 Memory API (`/api/earth2-memory`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/forecasts/{user_id}` | GET | Get user forecast history |
| `/preferences/{user_id}` | GET | Get user weather preferences |
| `/model-stats` | GET | Get model usage statistics |
| `/popular-locations` | GET | Get popular forecast locations |
| `/check-cache` | POST | Check for cached forecast |
| `/voice-context/{user_id}` | GET | Get context for voice |
| `/stats` | GET | Get memory statistics |

### Search Memory API (`/api/search-memory`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/session` | POST | Start new session |
| `/session/{session_id}/query` | POST | Record query |
| `/session/{session_id}/context` | GET | Get session context |
| `/session/{session_id}/end` | POST | End session |
| `/history/{user_id}` | GET | Get user history |

---

## Frontend Integration

### React Hooks

#### `useEarth2Memory`

```typescript
import { useEarth2Memory } from "@/hooks/use-earth2-memory"

function WeatherDashboard() {
  const {
    preferences,
    forecastHistory,
    modelStats,
    popularLocations,
    checkCachedForecast,
    getVoiceContext,
  } = useEarth2Memory("morgan")
  
  // Check for cached forecast before running new one
  const cached = await checkCachedForecast("fcn", 37.77, -122.42)
  if (cached) {
    // Use cached result
  }
}
```

### API Routes (Website)

```
app/api/memory/earth2/route.ts
app/api/memory/earth2/forecasts/[userId]/route.ts
app/api/memory/earth2/preferences/[userId]/route.ts
app/api/memory/earth2/model-stats/route.ts
```

---

## Voice Command Memory

The voice command router (`scripts/voice_command_router.py`) now includes pattern learning:

**Features:**
- Command history tracking
- Domain pattern learning
- Automatic preference learning
- Memory persistence

**Pattern Learning:**
```python
# Patterns are learned from successful commands
# Example: "show me weather for san francisco" -> earth2 domain

# Learned patterns improve routing over time
# High-frequency patterns get prioritized

# Get command statistics
stats = router.get_command_stats()
print(f"Total commands: {stats['total_commands']}")
print(f"Domains: {stats['domains']}")
```

---

## Configuration

### Environment Variables

```bash
# MINDEX Database
MINDEX_DATABASE_URL=postgresql://mycosoft:REDACTED_VM_SSH_PASSWORD@192.168.0.189:5432/mindex

# GPU Configuration
EARTH2_GPU_DEVICE=cuda:0
GPU_TOTAL_VRAM_MB=32768

# Cache Settings
EARTH2_CACHE_TTL_HOURS=6
GPU_MAX_HISTORY_SIZE=1000
```

### Memory Retention

| Layer | Default Retention |
|-------|-------------------|
| Ephemeral | 30 minutes |
| Session | 24 hours |
| Working | 7 days |
| Semantic | Permanent |
| Episodic | Permanent |
| System | Permanent |

---

## Testing

### Python Tests

```python
import asyncio
from mycosoft_mas.memory import get_earth2_memory, get_gpu_memory

async def test_memory():
    # Test Earth2 memory
    e2_mem = await get_earth2_memory()
    await e2_mem.record_forecast(
        user_id="test",
        model="fcn",
        location={"lat": 0, "lng": 0},
        lead_time_hours=24,
        variables=["temperature"],
        inference_time_ms=100,
        source="test"
    )
    
    forecasts = await e2_mem.get_user_forecasts("test")
    assert len(forecasts) > 0
    
    # Test GPU memory
    gpu_mem = await get_gpu_memory()
    await gpu_mem.record_model_load(
        model_name="test_model",
        model_type="custom",
        vram_mb=1024,
        load_time_ms=500
    )
    
    state = await gpu_mem.get_current_state()
    assert "test_model" in state["loaded_models"]
    
    print("All tests passed!")

asyncio.run(test_memory())
```

### API Tests

```bash
# Health check
curl http://localhost:8000/api/earth2-memory/health

# Get forecasts
curl http://localhost:8000/api/earth2-memory/forecasts/morgan

# Get model stats
curl http://localhost:8000/api/earth2-memory/model-stats
```

---

## Files Created/Modified

### New Files

| File | Description |
|------|-------------|
| `mycosoft_mas/memory/earth2_memory.py` | Earth2 weather memory manager |
| `mycosoft_mas/memory/gpu_memory.py` | GPU state memory manager |
| `mycosoft_mas/core/routers/earth2_memory_api.py` | Earth2 memory API router |
| `migrations/019_earth2_memory.sql` | Earth2 database tables |
| `migrations/019b_gpu_memory.sql` | GPU database tables |
| `migrations/020_mindex_unified_memory.sql` | Unified memory schema |
| `website/hooks/use-earth2-memory.ts` | React hook for Earth2 memory |
| `website/app/api/memory/earth2/*` | Next.js API routes |

### Modified Files

| File | Changes |
|------|---------|
| `mycosoft_mas/memory/__init__.py` | Added Earth2 and GPU exports |
| `mycosoft_mas/memory/myca_memory.py` | Updated to use MINDEX schema |
| `mycosoft_mas/llm/memory_brain.py` | Added Earth2, GPU, Map context injection |
| `mycosoft_mas/earth2/earth2_service.py` | Added memory recording |
| `scripts/voice_command_router.py` | Added pattern learning |
| `mycosoft_mas/core/routers/__init__.py` | Added earth2_memory router |

---

## Summary

This unified memory integration provides:

1. **Earth2 Memory** - Complete weather AI memory with forecasts, preferences, and caching
2. **GPU Memory** - VRAM tracking and intelligent preloading
3. **MINDEX Consolidation** - Single database backend for all memory
4. **Enhanced Context Injection** - Rich context for LLM prompts
5. **Voice Command Learning** - Pattern-based routing improvement
6. **Frontend Integration** - React hooks and API routes

All components are designed to work together, sharing context and enabling MYCA to provide more personalized, context-aware responses.