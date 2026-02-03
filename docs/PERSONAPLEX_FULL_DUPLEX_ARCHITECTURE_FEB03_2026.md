# PersonaPlex Full-Duplex Architecture - February 3, 2026

## Overview

PersonaPlex v5.1.0 implements a **full-duplex voice architecture** with **real-time event feedback**:

1. **Moshi handles all voice processing** (STT + LLM + TTS)
2. **MAS receives async text clones** for memory and knowledge building
3. **MAS Event Stream feeds back to Moshi** - agent updates, tool results, memory insights
4. **No interruption** of real-time conversation flow (events are injected naturally)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER                                         │
│                          │                                           │
│                          ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    BROWSER (localhost:3010)                  │    │
│  │  ┌──────────────┐                    ┌──────────────────┐   │    │
│  │  │ Mic Input    │ ──Opus Audio────▶  │ WebSocket        │   │    │
│  │  │ (opus-rec)   │                    │ to Bridge        │   │    │
│  │  └──────────────┘                    └────────┬─────────┘   │    │
│  │  ┌──────────────┐                             │              │    │
│  │  │ Speaker Out  │ ◀──Opus Audio───────────────┤              │    │
│  │  │ (decoder)    │                             │              │    │
│  │  └──────────────┘                             │              │    │
│  └───────────────────────────────────────────────┼──────────────┘    │
│                                                  │                   │
│                                                  ▼                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │               PERSONAPLEX BRIDGE (localhost:8999)            │    │
│  │                                                              │    │
│  │   Audio ◀──────────────────────────────────────────▶ Audio   │    │
│  │                         │                                    │    │
│  │                         │ Text (async clone)                 │    │
│  │                         ▼                                    │    │
│  │              ┌─────────────────────┐                         │    │
│  │              │ clone_to_mas_memory │ (fire-and-forget)       │    │
│  │              └──────────┬──────────┘                         │    │
│  └──────────────────────────┼───────────────────────────────────┘    │
│                             │                                        │
│          ┌──────────────────┼──────────────────────┐                │
│          │                  │                      │                │
│          ▼                  ▼                      ▼                │
│  ┌───────────────┐  ┌───────────────────┐  ┌──────────────────┐    │
│  │ MOSHI (8998)  │  │ MAS VM (188:8001) │  │ Memory Store     │    │
│  │               │  │                    │  │                  │    │
│  │ STT ─▶ LLM    │  │ /voice/memory/log │  │ Transcripts      │    │
│  │      ─▶ TTS   │  │ (async endpoint)  │  │ Context          │    │
│  │               │  │                    │  │ Knowledge        │    │
│  │ MYCA Persona  │  │ Intent Analysis   │  │                  │    │
│  │ loaded at     │  │ Agent Routing     │  │                  │    │
│  │ connect time  │  │ Memory Building   │  │                  │    │
│  └───────────────┘  └───────────────────┘  └──────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. PersonaPlex Bridge (localhost:8999)
- **Version**: 5.0.0-full-duplex
- **Role**: WebSocket proxy between browser and Moshi
- **Features**:
  - Forwards audio bidirectionally (no processing)
  - Extracts text from Moshi responses (kind=2)
  - Clones text to MAS asynchronously (fire-and-forget)
  - Does NOT wait for MAS response

### 2. Moshi Server (localhost:8998)
- **Role**: Full-duplex voice conversation
- **Features**:
  - Speech-to-Text (STT) via internal model
  - LLM reasoning with MYCA persona
  - Text-to-Speech (TTS) output
- **Persona**: Loaded from `config/myca_personaplex_prompt.txt`

### 3. MAS Orchestrator (192.168.0.188:8001)
- **Role**: Memory and knowledge building (background)
- **Endpoints**:
  - `POST /voice/memory/log` - Async transcript logging
  - `POST /voice/feedback` - Fallback endpoint
- **Features**:
  - Receives cloned transcripts (user + MYCA)
  - Builds conversation memory
  - NO response sent back to interrupt flow

## Data Flow

### Real-Time Conversation (Blocking)
```
User speaks → Browser Mic → Opus encode → Bridge → Moshi
Moshi STT → Moshi LLM → Moshi TTS → Bridge → Browser Speaker → User hears
```

### Memory Building (Non-Blocking, Async)
```
Moshi outputs text (kind=2) → Bridge extracts → asyncio.create_task() → MAS
                                                      ↓
                                              (fire-and-forget)
                                                      ↓
                                              MAS stores in memory
```

## Configuration

### Environment Variables
```bash
MOSHI_HOST=localhost
MOSHI_PORT=8998
MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001
MAS_TIMEOUT=5  # Short timeout for fire-and-forget
```

### MYCA Persona Location
```
config/myca_personaplex_prompt.txt
```

## API Endpoints

### Bridge (localhost:8999)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check + Moshi status |
| `/session` | POST | Create new voice session |
| `/ws/{session_id}` | WS | WebSocket for voice stream |
| `/session/{session_id}/history` | GET | Get conversation transcript |

### MAS (192.168.0.188:8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/voice/memory/log` | POST | Async transcript logging |
| `/health` | GET | Service health check |

## Testing

1. Start Moshi server (port 8998)
2. Start PersonaPlex Bridge:
   ```bash
   python services/personaplex-local/personaplex_bridge_nvidia.py
   ```
3. Open test page: `http://localhost:3010/test-voice`
4. Speak naturally - Moshi responds in real-time
5. Check MAS for memory: `http://192.168.0.188:8001/voice/feedback/recent`

## Changes from v4.x

| v4.x (Previous) | v5.0.0 (Current) |
|-----------------|------------------|
| Web Speech API for STT | Moshi handles all STT |
| MAS in request path (blocking) | MAS receives async clone (non-blocking) |
| Transcript batching to MAS | Fire-and-forget memory logging |
| Dual STT systems | Single STT (Moshi only) |

## MAS Event Stream

The bridge polls MAS every 2 seconds for events that should be injected into Moshi's conversation.

### Event Types

| Type | Description | Example |
|------|-------------|---------|
| `agent_update` | Agent status/result | "Opportunity Scout found 3 new leads" |
| `tool_result` | Tool execution result | "Database query returned 15 results" |
| `memory_insight` | Memory recall | "I recall you mentioned mushroom cultivation earlier" |
| `knowledge` | Knowledge discovery | "MINDEX shows Cordyceps grows best at 22°C" |
| `system_status` | System change | "VM backup completed successfully" |
| `notification` | General notification | "Meeting reminder in 10 minutes" |

### Publishing Events

Any MAS component (agents, tools, services) can publish events:

```python
from mycosoft_mas.core.myca_main import publish_event, notify_agent_update

# Generic event
publish_event("notification", "Something happened!", session_id="abc123")

# Agent update
notify_agent_update("OpportunityScout", "completed", "Found 3 new investor leads")

# Tool result
notify_tool_result("MINDEXQuery", "Retrieved 15 fungal species matching criteria")

# Memory insight
notify_memory_insight("User previously expressed interest in Cordyceps cultivation")
```

### Event Flow

```
Agent/Tool/Service → publish_event() → MASEventStore
                                            ↓
                                    Bridge polls /events/stream
                                            ↓
                                    format_event_for_moshi()
                                            ↓
                                    Inject into Moshi (0x02 text)
                                            ↓
                                    Moshi speaks: "One moment, I just got an update..."
```

## Benefits

1. **Lower Latency**: No waiting for MAS response
2. **Natural Flow**: Moshi's full-duplex model works uninterrupted
3. **Memory Building**: MAS still receives all transcripts for context
4. **Real-time Awareness**: Moshi can react to agent updates mid-conversation
5. **Simpler Browser**: No Web Speech API complexity
6. **Clean Architecture**: Clear separation of concerns
