# Earth2 + PersonaPlex Unified Integration - February 5, 2026

## Status: FULLY OPERATIONAL

All components tested and verified working on RTX 5090 (32GB VRAM).

## Services Running

| Service | Port | Status | Description |
|---------|------|--------|-------------|
| PersonaPlex/Moshi | 8998 | RUNNING | Voice AI (STT/TTS) |
| PersonaPlex Bridge | 8999 | RUNNING | Voice routing |
| Earth2Studio API | 8220 | RUNNING | Weather model inference |
| GPU Gateway | 8300 | RUNNING | Unified API entry point |

## Test Results

```
Voice-Earth2-Map Pipeline E2E Tests
===================================
Total Tests: 56
Passed: 56
Failed: 0
Success Rate: 100.0%
```

## Components Created

### Backend (Python - MAS)

1. **`scripts/earth2_voice_handler.py`**
   - Parses voice commands for weather forecasts, nowcasts, model loading
   - Intents: FORECAST, NOWCAST, LOAD_MODEL, SHOW_LAYER, HIDE_LAYER, EXPLAIN, GPU_STATUS
   - Generates frontend commands and spoken responses

2. **`scripts/map_voice_handler.py`**
   - Parses voice commands for map navigation
   - Intents: NAVIGATE, ZOOM, PAN, LAYER, RESET, CREP_FILTER, CREP_ENTITY, WHAT_HERE
   - Includes known location database (Tokyo, NYC, London, etc.)

3. **`scripts/voice_command_router.py`**
   - Unified router for all voice commands
   - Domain detection: earth2, map, crep, system, general
   - Routes to appropriate handler

4. **`scripts/context_injector.py`**
   - Injects map and Earth2 context into voice commands
   - Maintains state for map viewport, CREP layers, Earth2 models
   - Builds LLM context strings

5. **`scripts/vram_manager.py`**
   - Smart VRAM management for shared GPU
   - Model priority system
   - Memory pressure handling
   - Estimated VRAM budgets per model

6. **`scripts/local_gpu_services.py`** (Updated)
   - Added `/voice/route` endpoint
   - Added `/context/update` endpoint
   - Added `/context` and `/context/llm` endpoints

### Frontend (TypeScript - Website)

1. **`hooks/use-voice-map-bridge.ts`**
   - React hook for WebSocket voice bridge
   - Executes map commands on MapLibre GL
   - Handles Earth2 commands
   - Context management

2. **`scripts/start-with-gpu.js`**
   - Auto-starts GPU services with dev server
   - Health check polling
   - Graceful shutdown

3. **`package.json`** (Updated)
   - `npm run dev` now auto-starts GPU services
   - Added `dev:next-only` for Next.js only
   - Added `gpu:start` for manual GPU service start

## API Endpoints

### Gateway (http://localhost:8300)

```
GET  /              - Service status and discovery
GET  /health        - Health check all services
GET  /gpu/status    - GPU memory and details
POST /voice/route   - Route voice command
POST /context/update - Update map/Earth2 context
GET  /context       - Get current context
GET  /context/llm   - Get LLM-formatted context
```

### Voice Routing Example

```json
POST /voice/route
{
  "text": "show me a 24 hour weather forecast",
  "context": {
    "map": {"center": [0, 0], "zoom": 2},
    "earth2": {"activeModel": null}
  }
}

Response:
{
  "domain": "earth2",
  "success": true,
  "action": "forecast",
  "speak": "I'm running a 24 hour forecast using the FCN model.",
  "frontend_command": {
    "type": "show_forecast",
    "forecast_id": "fcn_20260205095100"
  }
}
```

## Quick Start

### Start All Services

```bash
# Option 1: Auto-start with dev server
cd website
npm run dev

# Option 2: Manual start
cd mycosoft-mas
python scripts/local_gpu_services.py
```

### Verify Services

```bash
curl http://localhost:8300/health
```

## GPU Memory Usage

| Component | VRAM Usage |
|-----------|-----------|
| PersonaPlex/Moshi | ~23 GB |
| Earth2 FCN model | ~2 GB |
| Earth2 Pangu model | ~3.5 GB |
| System overhead | ~1 GB |
| **Available for Earth2** | **~6 GB** |

## Voice Commands Supported

### Earth2 Commands
- "Show me a 24 hour forecast"
- "Run a nowcast"
- "Load the Pangu model"
- "Show wind layer"
- "Hide precipitation overlay"
- "What's the GPU status?"

### Map Commands
- "Go to Tokyo"
- "Zoom in"
- "Pan left"
- "Show satellite layer"
- "Reset the view"
- "Show only seismic events"
- "What's happening here?"

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CREP Dashboard (localhost:3010)               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Voice Controls  │  │    MapLibre     │  │  Earth2 Layers  │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │           │
│           └──────────────┬─────┴────────────────────┘           │
│                          │                                      │
│              useVoiceMapBridge Hook                             │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                  GPU Gateway (localhost:8300)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Voice Command Router                         │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐          │   │
│  │  │  Earth2    │  │    Map     │  │   CREP     │          │   │
│  │  │  Handler   │  │  Handler   │  │  Handler   │          │   │
│  │  └──────┬─────┘  └─────┬──────┘  └──────┬─────┘          │   │
│  │         │              │               │                  │   │
│  └─────────┴──────────────┴───────────────┴──────────────────┘   │
│                           │                                      │
│              Context Injector + VRAM Manager                     │
└──────────────────────────┬───────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Moshi     │    │   Bridge    │    │  Earth2     │
│  :8998      │    │   :8999     │    │  :8220      │
│  (Voice AI) │    │ (Routing)   │    │ (Weather)   │
└─────────────┘    └─────────────┘    └─────────────┘
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
                    ┌──────┴──────┐
                    │  RTX 5090   │
                    │  32GB VRAM  │
                    └─────────────┘
```

## Files Modified/Created

### New Files
- `scripts/earth2_voice_handler.py`
- `scripts/map_voice_handler.py`
- `scripts/voice_command_router.py`
- `scripts/context_injector.py`
- `scripts/vram_manager.py`
- `scripts/start_gateway_only.py`
- `tests/test_voice_earth2_map_pipeline_feb05_2026.py`
- `hooks/use-voice-map-bridge.ts` (website)
- `scripts/start-with-gpu.js` (website)

### Modified Files
- `scripts/local_gpu_services.py` (added voice routing)
- `hooks/index.ts` (website - exports)
- `package.json` (website - dev script)
- `.env.local` (website - GPU URLs)
