# PersonaPlex Full-Duplex Architecture - February 3, 2026

## Overview

PersonaPlex v5.0.0 implements a **full-duplex voice architecture** where:

1. **Moshi handles all voice processing** (STT + LLM + TTS)
2. **MAS receives async text clones** for memory and knowledge building
3. **No interruption** of real-time conversation flow

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

## Benefits

1. **Lower Latency**: No waiting for MAS response
2. **Natural Flow**: Moshi's full-duplex model works uninterrupted
3. **Memory Building**: MAS still receives all transcripts for context
4. **Simpler Browser**: No Web Speech API complexity
5. **Clean Architecture**: Clear separation of concerns
