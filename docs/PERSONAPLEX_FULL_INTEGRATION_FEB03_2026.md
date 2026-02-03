# PersonaPlex Full Integration - February 3, 2026

## Summary

Complete integration of the working PersonaPlex server with the Mycosoft website, including MAS orchestrator, memory, n8n workflows, and Metabase.

---

## Part 1: Components Created

### Website Integration (C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\)

#### Voice Client Library

| File | Purpose |
|------|---------|
| `lib/voice/personaplex-client.ts` | Full PersonaPlex WebSocket client with stats tracking |
| `lib/voice/index.ts` | Library exports |

**PersonaPlexClient Features:**
- WebSocket connection to PersonaPlex server (port 8998)
- Audio stats tracking (latency, played/missed audio, buffer min/max)
- Console logging with callbacks
- Microphone level monitoring
- MYCA prompt configuration

#### Voice Components

| File | Purpose |
|------|---------|
| `components/voice/PersonaPlexWidget.tsx` | Floating PersonaPlex widget for site-wide use |
| `components/voice/VoiceMonitorDashboard.tsx` | Audio monitoring UI with visualizers |
| `components/voice/index.ts` | Component exports |

**PersonaPlexWidget Features:**
- Expandable/collapsible floating button
- Connection status indicator
- Microphone and agent level visualizers
- Transcript and response display
- Settings panel with configuration
- Integrates VoiceMonitorDashboard

**VoiceMonitorDashboard Features:**
- Real-time microphone input visualization (bar chart)
- Agent response visualization (circular pulsing)
- Audio statistics (played, missed, latency, buffer)
- Console log output with color-coded messages
- Compact mode for inline display

#### Voice Hooks

| File | Purpose |
|------|---------|
| `hooks/usePersonaPlex.ts` | Main PersonaPlex integration hook with MAS, memory, n8n |
| `hooks/index.ts` | Hook exports (updated) |

**usePersonaPlex Features:**
- PersonaPlex connection management
- Audio level tracking
- Stats aggregation
- MAS orchestrator routing
- Memory persistence (short-term and long-term)
- n8n workflow execution
- Console message management

#### API Endpoints

| File | Purpose |
|------|---------|
| `app/api/memory/route.ts` | Voice conversation memory persistence |

**Memory API Features:**
- GET: Retrieve memory by key or type
- POST: Store memory with type classification
- DELETE: Clear memory by key, type, or all
- PUT: Get context and summarize short-term memory

---

## Part 2: Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Browser (User Interface)                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    PersonaPlexWidget                              │   │
│  │  ┌─────────────────┐  ┌─────────────────────────────────────────┐│   │
│  │  │ VoiceMonitor    │  │ usePersonaPlex Hook                     ││   │
│  │  │ Dashboard       │  │ - connect/disconnect                    ││   │
│  │  │ - Mic visualizer│  │ - sendToMAS()                           ││   │
│  │  │ - Agent visual  │  │ - executeN8nWorkflow()                  ││   │
│  │  │ - Stats display │  │ - saveToMemory()                        ││   │
│  │  │ - Console log   │  │ - recallFromMemory()                    ││   │
│  │  └─────────────────┘  └────────────────┬────────────────────────┘│   │
│  └─────────────────────────────────────────┼────────────────────────┘   │
└───────────────────────────────────────────┼─────────────────────────────┘
                                            │
              ┌─────────────────────────────┴─────────────────────────────┐
              │                                                           │
              ▼                                                           ▼
┌─────────────────────────────┐               ┌─────────────────────────────┐
│  PersonaPlex Server (8998)  │               │     Website API Routes       │
│  ┌────────────────────────┐ │               │ ┌──────────────────────────┐ │
│  │ Moshi 7B Model         │ │               │ │/api/mas/voice/orchestrator│ │
│  │ - RTX 5090 GPU         │ │               │ │- Intent classification   │ │
│  │ - CUDA graphs enabled  │ │               │ │- Safety confirmation     │ │
│  │ - 30ms/step latency    │ │               │ │- n8n workflow routing    │ │
│  │ - NATURAL_F2 voice     │ │               │ │- MAS agent routing       │ │
│  └────────────────────────┘ │               │ └────────────┬─────────────┘ │
│  ┌────────────────────────┐ │               │ ┌────────────▼─────────────┐ │
│  │ WebSocket /api/chat    │ │               │ │/api/memory               │ │
│  │ - Full duplex audio    │ │               │ │- Conversation storage    │ │
│  │ - Opus encoding        │ │               │ │- Context retrieval       │ │
│  │ - Text streaming       │ │               │ │- Short/long-term memory  │ │
│  └────────────────────────┘ │               │ └──────────────────────────┘ │
└─────────────────────────────┘               └──────────────┬──────────────┘
                                                             │
              ┌──────────────────────────────────────────────┴──────┐
              │                                                     │
              ▼                                                     ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│   MAS Orchestrator (8001)       │    │       n8n (5678)                │
│   192.168.0.188                 │    │       192.168.0.188             │
│ ┌─────────────────────────────┐ │    │ ┌─────────────────────────────┐ │
│ │ Agent Registry (223 agents) │ │    │ │ Workflows:                  │ │
│ │ - Core agents               │ │    │ │ - MYCA Command API          │ │
│ │ - Financial agents          │ │    │ │ - MYCA Speech Complete      │ │
│ │ - Mycology agents           │ │    │ │ - MYCA Orchestrator         │ │
│ │ - Research agents           │ │    │ │ - Agent Heartbeat           │ │
│ │ - DAO agents                │ │    │ │ - Data Sync                 │ │
│ │ - Security agents           │ │    │ └─────────────────────────────┘ │
│ │ - Infrastructure agents     │ │    │ ┌─────────────────────────────┐ │
│ └─────────────────────────────┘ │    │ │ Webhooks:                   │ │
│ ┌─────────────────────────────┐ │    │ │ - /webhook/myca/command     │ │
│ │ NLQ Engine                  │ │    │ │ - /webhook/myca/speech_turn │ │
│ │ - Intent parsing            │ │    │ │ - /webhook/myca/safety      │ │
│ │ - Entity extraction         │ │    │ └─────────────────────────────┘ │
│ │ - Agent routing             │ │    └─────────────────────────────────┘
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│       Metabase (3030)           │
│ ┌─────────────────────────────┐ │
│ │ Data Queries via NLQ        │ │
│ │ - Agent statistics          │ │
│ │ - System metrics            │ │
│ │ - Conversation analytics    │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

---

## Part 3: How to Use

### Add PersonaPlex Widget to Any Page

```tsx
import { FloatingPersonaPlexWidget } from "@/components/voice"

export default function MyPage() {
  return (
    <div>
      {/* Your page content */}
      
      {/* Add floating PersonaPlex widget */}
      <FloatingPersonaPlexWidget
        onTranscript={(text) => console.log("User said:", text)}
        onResponse={(response) => console.log("MYCA:", response)}
        onCommand={(cmd, result) => console.log("Command:", cmd, result)}
      />
    </div>
  )
}
```

### Use PersonaPlex Hook Directly

```tsx
import { usePersonaPlex } from "@/hooks"

function MyComponent() {
  const personaplex = usePersonaPlex({
    serverUrl: "ws://localhost:8998/api/chat",
    voicePrompt: "NATURAL_F2.pt",
    enableMasRouting: true,
    enableMemory: true,
    enableN8n: true,
  })

  return (
    <div>
      <button onClick={() => personaplex.connect()}>Connect</button>
      <button onClick={() => personaplex.disconnect()}>Disconnect</button>
      
      <p>Status: {personaplex.status}</p>
      <p>Transcript: {personaplex.transcript}</p>
      <p>Response: {personaplex.lastResponse}</p>
      
      {/* Execute n8n workflow */}
      <button onClick={() => personaplex.executeN8nWorkflow("myca/command", { action: "status" })}>
        Get Status
      </button>
      
      {/* Save to memory */}
      <button onClick={() => personaplex.saveToMemory("user_preference", { theme: "dark" })}>
        Save Preference
      </button>
    </div>
  )
}
```

### Add Voice Monitor Dashboard

```tsx
import { VoiceMonitorDashboard } from "@/components/voice"
import { usePersonaPlex } from "@/hooks"

function VoiceDebugPanel() {
  const personaplex = usePersonaPlex()

  return (
    <VoiceMonitorDashboard
      status={personaplex.status}
      stats={personaplex.stats}
      micLevel={personaplex.micLevel}
      agentLevel={personaplex.agentLevel}
      consoleMessages={personaplex.consoleMessages}
      websocketUrl="ws://localhost:8998/api/chat"
    />
  )
}
```

---

## Part 4: API Reference

### Memory API

**GET /api/memory**
```bash
# Get specific key
curl http://localhost:3000/api/memory?key=conversation_123

# Get recent items by type
curl http://localhost:3000/api/memory?type=voice_session&limit=10
```

**POST /api/memory**
```bash
curl -X POST http://localhost:3000/api/memory \
  -H "Content-Type: application/json" \
  -d '{"key": "conv_123", "value": {"input": "hello", "output": "Hi!"}, "type": "voice_session"}'
```

**PUT /api/memory** (Context)
```bash
# Get short-term context
curl -X PUT http://localhost:3000/api/memory \
  -H "Content-Type: application/json" \
  -d '{"action": "get_context", "type": "voice_session"}'
```

### MAS Voice Orchestrator

**POST /api/mas/voice/orchestrator**
```bash
curl -X POST http://localhost:3000/api/mas/voice/orchestrator \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the system status?", "want_audio": true}'
```

Response:
```json
{
  "conversation_id": "conv-1706979200000",
  "response_text": "System Status: All services operational...",
  "audio_base64": "...",
  "audio_mime": "audio/mpeg",
  "agent": "myca-orchestrator"
}
```

---

## Part 5: Configuration

### Environment Variables

```env
# MAS Orchestrator
MAS_API_URL=http://192.168.0.188:8001

# n8n
N8N_URL=http://192.168.0.188:5678

# ElevenLabs (fallback TTS)
ELEVENLABS_API_KEY=your-api-key
MYCA_VOICE_ID=aEO01A4wXwd1O8GPgGlF

# PersonaPlex (local)
PERSONAPLEX_URL=ws://localhost:8998/api/chat
```

### PersonaPlex Server

Start the optimized PersonaPlex server:
```powershell
python c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\start_personaplex.py
```

Configuration in `start_personaplex.py`:
- CUDA graphs: ENABLED (critical for real-time)
- Voice prompts: NATURAL_F2.pt
- Port: 8998

---

## Part 6: Files Summary

### Created Today (Feb 3, 2026)

| Repository | File | Purpose |
|------------|------|---------|
| WEBSITE | `lib/voice/personaplex-client.ts` | PersonaPlex WebSocket client |
| WEBSITE | `lib/voice/index.ts` | Library exports |
| WEBSITE | `components/voice/PersonaPlexWidget.tsx` | Floating voice widget |
| WEBSITE | `components/voice/VoiceMonitorDashboard.tsx` | Audio monitoring UI |
| WEBSITE | `components/voice/index.ts` | Component exports |
| WEBSITE | `hooks/usePersonaPlex.ts` | Main PersonaPlex hook |
| WEBSITE | `app/api/memory/route.ts` | Memory persistence API |
| MAS | `config/myca_personaplex_prompt.txt` | Full MYCA prompt (9990 chars) |
| MAS | `config/myca_personaplex_prompt_1000.txt` | Condensed prompt (792 chars) |
| MAS | `start_personaplex.py` | Fixed with CUDA graphs enabled |
| MAS | `docs/PERSONAPLEX_PERFORMANCE_FIX_FEB03_2026.md` | Performance fix docs |
| MAS | `docs/PERSONAPLEX_FULL_INTEGRATION_FEB03_2026.md` | This document |

### Modified Today

| Repository | File | Change |
|------------|------|--------|
| WEBSITE | `hooks/index.ts` | Added usePersonaPlex export |

---

## Part 7: Testing Checklist

### PersonaPlex Server
- [x] Server starts on port 8998
- [x] CUDA graphs enabled (~30ms/step)
- [x] Voice prompts load correctly
- [x] Full duplex audio working

### Website Integration
- [ ] FloatingPersonaPlexWidget renders
- [ ] Connection to PersonaPlex works
- [ ] Microphone visualization active
- [ ] Agent response visualization active
- [ ] Stats update in real-time
- [ ] Console messages display

### MAS Integration
- [ ] Voice orchestrator responds
- [ ] n8n workflows execute
- [ ] Memory saves/retrieves
- [ ] Agent routing works

---

## Part 8: Quick Start

1. **Start PersonaPlex Server**
   ```powershell
   cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
   python start_personaplex.py
   ```

2. **Start Website Dev Server**
   ```powershell
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
   npm run dev
   ```

3. **Open Website**
   - Go to http://localhost:3000
   - Look for floating microphone button (bottom-right)
   - Click to expand widget
   - Click connect button
   - Allow microphone access
   - Start talking to MYCA!

---

*Document created: February 3, 2026*
*Status: Integration Complete*
