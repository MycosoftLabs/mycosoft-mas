# CREP Voice Control Implementation - February 6, 2026

## Overview

This document describes the end-to-end voice control implementation for the CREP (Common Relevant Environmental Picture) dashboard. Voice commands spoken to PersonaPlex are routed through the MAS VoiceCommandRouter, which generates `frontend_command` objects that are broadcast to the CREP map via WebSocket.

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   User Voice    │────▶│  PersonaPlex Bridge  │────▶│  MAS Voice Command  │
│   (Mic Input)   │     │    (ws://8999)       │     │    API (/voice)     │
└─────────────────┘     └──────────────────────┘     └─────────────────────┘
                                   │                          │
                                   │                          ▼
                                   │                 ┌─────────────────────┐
                                   │                 │  VoiceCommandRouter │
                                   │                 │   - Earth2Handler   │
                                   │                 │   - MapVoiceHandler │
                                   │                 └─────────────────────┘
                                   │                          │
                                   ▼                          │
                        ┌──────────────────────┐              │
                        │   CREP WebSocket     │◀─────────────┘
                        │   Subscribers        │   frontend_command
                        └──────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │    CREP Map UI       │
                        │  (Voice Controls)    │
                        └──────────────────────┘
```

## Components

### MAS Backend

#### 1. Voice Command API (`mycosoft_mas/core/routers/voice_command_api.py`)

New FastAPI router that exposes the VoiceCommandRouter as an HTTP API.

**Endpoints:**
- `POST /api/voice/command` - Route a voice command and return frontend_command
- `POST /api/voice/command/batch` - Route multiple commands
- `GET /api/voice/command/domains` - Get available command domains
- `GET /api/voice/command/help` - Get help text
- `GET /api/voice/health` - Health check

**Request:**
```json
{
  "text": "show satellites",
  "session_id": "abc123",
  "user_id": "morgan",
  "source": "personaplex"
}
```

**Response:**
```json
{
  "success": true,
  "domain": "crep",
  "action": "show_layer",
  "speak": "Showing satellites layer.",
  "frontend_command": {
    "type": "showLayer",
    "layer": "satellites"
  },
  "needs_llm_response": false,
  "raw_text": "show satellites"
}
```

#### 2. PersonaPlex Bridge (`services/personaplex-local/personaplex_bridge_nvidia.py`)

Updated to v8.1.0 with CREP voice control integration:

- Calls MAS `/api/voice/command` when user text is transcribed
- Maintains WebSocket subscribers for CREP map clients
- Broadcasts `frontend_command` to all connected map clients
- New endpoint: `/ws/crep/commands` for map clients to connect

**New Features:**
- `route_voice_command()` - Calls MAS API for command routing
- `broadcast_frontend_command()` - Sends commands to map clients
- `/ws/crep/commands` - WebSocket endpoint for CREP clients

### Website Frontend

#### 3. Voice Command Proxy (`app/api/voice/command/route.ts`)

Next.js API route that proxies requests to MAS backend.

**Usage:**
```typescript
const response = await fetch('/api/voice/command', {
  method: 'POST',
  body: JSON.stringify({ text: 'go to Tokyo' })
})
const { frontend_command, speak } = await response.json()
```

#### 4. Map WebSocket Client (`lib/voice/map-websocket-client.ts`)

WebSocket client for connecting to PersonaPlex Bridge's CREP command channel.

```typescript
const client = new MapWebSocketClient({
  url: 'ws://localhost:8999/ws/crep/commands',
  onCommand: (command, speak) => {
    // Execute command on map
  }
})
client.connect()
```

#### 5. useMapWebSocket Hook (`hooks/useMapWebSocket.ts`)

React hook for CREP voice command integration.

```typescript
const { isConnected, lastCommand, sendCommand } = useMapWebSocket({
  onFlyTo: (lng, lat, zoom) => map.flyTo([lng, lat], zoom),
  onShowLayer: (layer) => setLayerVisible(layer, true),
  onHideLayer: (layer) => setLayerVisible(layer, false),
  // ... other handlers
})
```

**Handlers:**
- `onFlyTo(lng, lat, zoom?, duration?)`
- `onZoomBy(delta, duration?)`
- `onSetZoom(zoom, duration?)`
- `onPanBy(offset, duration?)`
- `onResetView()`
- `onShowLayer(layer)`
- `onHideLayer(layer)`
- `onToggleLayer(layer)`
- `onApplyFilter(type, value)`
- `onClearFilters()`
- `onRunForecast(model, leadTime)`
- `onRunNowcast()`
- `onLoadModel(model)`
- `onGetEntityDetails(entity)`
- `onGeocodeAndFlyTo(query, zoom?)`
- `onSpeak(text)`

#### 6. useMapVoiceControl Hook (`hooks/useMapVoiceControl.ts`)

Enhanced with MAS backend support.

```typescript
const { processVoiceCommand } = useMapVoiceControl({
  useMASBackend: true, // NEW: Use MAS for command routing
  onFlyTo: (lng, lat, zoom) => { ... },
  geocodeLocation: async (query) => { ... },
})
```

#### 7. VoiceMapControls Component (`components/crep/voice-map-controls.tsx`)

UI component for voice control on CREP map.

**Features:**
- WebSocket connection status indicator
- PersonaPlex voice status
- Command logging
- Quick action buttons
- Typed command input
- Last spoken response display

**Props:**
```typescript
interface VoiceMapControlsProps extends MapCommandHandlers {
  className?: string
  collapsed?: boolean
  enableWebSocket?: boolean  // Connect to PersonaPlex Bridge
  useMASBackend?: boolean    // Use MAS for command routing
}
```

#### 8. CREP Dashboard Page (`app/dashboard/crep/page.tsx`)

Wired VoiceMapControls to the map with all handlers.

## Voice Command Examples

### Navigation
| Command | frontend_command |
|---------|------------------|
| "Go to Tokyo" | `{ type: "geocodeAndFlyTo", query: "Tokyo", zoom: 10 }` |
| "Zoom in" | `{ type: "zoomBy", delta: 2 }` |
| "Zoom to level 5" | `{ type: "setZoom", zoom: 5 }` |
| "Pan left" | `{ type: "panBy", offset: [-200, 0] }` |
| "Reset view" | `{ type: "flyTo", center: [0, 20], zoom: 2 }` |

### Layers
| Command | frontend_command |
|---------|------------------|
| "Show satellites" | `{ type: "showLayer", layer: "satellites" }` |
| "Hide aircraft" | `{ type: "hideLayer", layer: "aircraft" }` |
| "Toggle vessels" | `{ type: "toggleLayer", layer: "vessels" }` |

### Filters
| Command | frontend_command |
|---------|------------------|
| "Filter by severity high" | `{ type: "applyFilter", filterType: "severity", filterValue: "high" }` |
| "Clear filters" | `{ type: "clearFilters" }` |

### Earth2 Weather
| Command | frontend_command |
|---------|------------------|
| "Show 24 hour forecast" | `{ type: "run_forecast", model: "fcn", lead_time: 24 }` |
| "Load pangu model" | `{ type: "load_model", model: "pangu" }` |
| "Show wind layer" | `{ type: "earth2_show_layer", layer: "wind" }` |

## Data Flow

1. **User speaks** → PersonaPlex captures audio via WebSocket
2. **STT transcription** → Moshi 7B converts audio to text
3. **Command routing** → PersonaPlex Bridge calls MAS `/api/voice/command`
4. **Domain detection** → VoiceCommandRouter detects domain (map, earth2, crep, system)
5. **Handler execution** → MapVoiceHandler or Earth2VoiceHandler processes command
6. **Response generation** → Returns `frontend_command` and `speak` text
7. **WebSocket broadcast** → PersonaPlex Bridge broadcasts to CREP clients
8. **Map execution** → CREP map receives and executes `frontend_command`
9. **Voice response** → PersonaPlex speaks the response to user

## Configuration

### Environment Variables

```bash
# MAS Backend
MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001

# PersonaPlex Bridge
MOSHI_HOST=localhost
MOSHI_PORT=8998
MAS_TIMEOUT=10
```

### WebSocket URLs

| Service | URL |
|---------|-----|
| PersonaPlex Voice | `ws://localhost:8999/ws/{session_id}` |
| CREP Commands | `ws://localhost:8999/ws/crep/commands` |
| Moshi STT/TTS | `ws://localhost:8998/api/chat` |

## Testing

### Manual Testing

1. Start PersonaPlex Bridge: `python personaplex_bridge_nvidia.py`
2. Start MAS: `uvicorn mycosoft_mas.main:app --port 8001`
3. Start Website: `npm run dev` (port 3010)
4. Open CREP: `http://localhost:3010/dashboard/crep`
5. Connect PersonaPlex voice
6. Say: "Show satellites" → Should show satellite layer on map
7. Say: "Go to Tokyo" → Should fly to Tokyo
8. Say: "Zoom in" → Should zoom in

### API Testing

```bash
# Test voice command API
curl -X POST http://localhost:8001/api/voice/command \
  -H "Content-Type: application/json" \
  -d '{"text": "show satellites"}'

# Expected response
{
  "success": true,
  "domain": "crep",
  "action": "show_layer",
  "frontend_command": {"type": "showLayer", "layer": "satellites"},
  "speak": "Showing satellites layer."
}
```

### WebSocket Testing

```javascript
// Connect to CREP command channel
const ws = new WebSocket('ws://localhost:8999/ws/crep/commands')
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'frontend_command') {
    console.log('Received command:', data.command)
  }
}
```

## Files Modified/Created

### MAS Backend
- `mycosoft_mas/core/routers/voice_command_api.py` (NEW)
- `mycosoft_mas/core/routers/__init__.py` (MODIFIED)
- `services/personaplex-local/personaplex_bridge_nvidia.py` (MODIFIED - v8.1.0)

### Website Frontend
- `app/api/voice/command/route.ts` (NEW)
- `lib/voice/map-websocket-client.ts` (MODIFIED)
- `hooks/useMapWebSocket.ts` (NEW)
- `hooks/useMapVoiceControl.ts` (MODIFIED)
- `components/crep/voice-map-controls.tsx` (MODIFIED)
- `app/dashboard/crep/page.tsx` (MODIFIED)

## Future Enhancements

1. **Speech synthesis integration** - Have MYCA speak responses through browser TTS
2. **Command confirmation** - "Are you sure you want to clear all filters?"
3. **Context awareness** - Use current map viewport in command interpretation
4. **Multi-step commands** - "Zoom in to Tokyo and show earthquakes"
5. **Custom command learning** - Remember user's preferred command phrases
6. **Voice feedback loop** - Record command success/failure for ML training

## Troubleshooting

### Voice not connecting
- Check PersonaPlex Bridge is running on port 8999
- Verify Moshi is running on port 8998
- Check browser microphone permissions

### Commands not executing
- Check WebSocket connection in VoiceMapControls UI
- Verify MAS is running on port 8001
- Check browser console for errors

### Map not responding
- Verify mapRef is initialized
- Check handler functions are connected
- Look for TypeScript errors in browser console

---

*Document created: February 6, 2026*
*Version: 1.0.0*
*Author: MYCA Agent System*
