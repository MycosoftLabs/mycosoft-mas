# PersonaPlex Full-Duplex Voice + MAS Tool Integration
## February 3, 2026 - Implementation Complete

---

## Executive Summary

Successfully implemented **full-duplex voice conversation** through PersonaPlex/Moshi with **MAS (Multi-Agent System) tool call integration**. The system now:

1. **Full-Duplex Voice**: Moshi handles all voice I/O (STT + LLM + TTS)
2. **MAS Tool Calls**: Bridge detects tool intents, executes via MAS, injects results
3. **Text Cloning**: All conversation text is cloned to MAS for memory building
4. **Event Stream**: MAS events (agent updates, tool results) are injected into conversation

---

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                         USER (Browser)                                       â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚ Microphone     â”‚ â”€â”€Opus Audioâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶  â”‚ WebSocket to Bridge    â”‚ â”‚
â”‚  â”‚ (opus-rec)     â”‚                              â”‚ (localhost:8999)       â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                              â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                                          â”‚              â”‚
â”‚  â”‚ Speaker        â”‚ â—€â”€â”€Opus Audioâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤              â”‚
â”‚  â”‚ (decoder)      â”‚                                          â”‚              â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                                          â–¼              â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                                               â”‚
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚               PERSONAPLEX BRIDGE (localhost:8999) v6.0.0     â”‚              â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”             â”‚
â”‚  â”‚  Audio Forward â—€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ Moshi       â”‚
â”‚  â”‚                                                                          â”‚
â”‚  â”‚  Text Extract â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ MAS Clone   â”‚
â”‚  â”‚                                                                          â”‚
â”‚  â”‚  Tool Intent â”€â”€â”€â”€â”€â–¶ MAS Execute â”€â”€â”€â”€â”€â–¶ Result Inject â”€â”€â”€â”€â”€â–¶ Moshi       â”‚
â”‚  â”‚                                                                          â”‚
â”‚  â”‚  Event Poll â—€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ MAS       â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                     â”‚                                         â”‚
                     â–¼                                         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   MOSHI SERVER (localhost:8998)â”‚   â”‚   MAS ORCHESTRATOR (192.168.0.188:8001)â”‚
â”‚   - NVIDIA PersonaPlex 7B      â”‚   â”‚   - Voice Orchestrator API              â”‚
â”‚   - RTX 5090 + CUDA Graphs     â”‚   â”‚   - Voice Tools API                     â”‚
â”‚   - MYCA Persona loaded        â”‚   â”‚   - Event Stream                        â”‚
â”‚   - Text injection (kind=2)    â”‚   â”‚   - Memory Cloning                      â”‚
â”‚   - ~30ms/step latency         â”‚   â”‚   - Tool Execution                      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Files Modified/Created

### Moshi Server (Modified)
**File:** `personaplex-repo/moshi/moshi/server.py`

Changes:
- Added MAS text injection support (kind=2 messages)
- Added `mas_context_queue` for storing injected events
- Added kind=3 for control/acknowledgment messages
- Added `/health` endpoint with MAS injection flag

### PersonaPlex Bridge (v6.0.0)
**File:** `services/personaplex-local/personaplex_bridge_nvidia.py`

Features:
- Full-duplex audio forwarding to Moshi
- Tool intent detection with pattern matching
- Async tool execution via MAS
- Text cloning to MAS memory
- Event stream polling and injection
- Session management with transcript history

### Voice Tools API (New)
**File:** `mycosoft_mas/core/routers/voice_tools_api.py`

Endpoints:
- `POST /api/voice/tools/execute` - Execute a tool call
- `GET /api/voice/tools/devices/{name}/status` - Get device status

Supported Tools:
- `device_status` - NatureOS device status (Mushroom1, SporeBase, etc.)
- `agent_list` - MAS agent registry summary
- `query_mindex` - MINDEX fungal knowledge search
- `system_status` - Overall system health

### MYCA Prompts
**File:** `config/myca_personaplex_prompt_1000.txt`

Short prompt optimized for Moshi's URL parameter limits, includes:
- MYCA identity and personality
- Real-time integration instructions (handling [SYSTEM], [TOOL], [MEMORY] prefixes)
- Capability overview

---

## Tool Call Flow

1. **User speaks**: "What's the status of Mushroom 1?"
2. **Moshi transcribes**: Audio â†’ Text
3. **Bridge extracts text**: Clones to MAS + checks for tool intent
4. **Tool detected**: `device_status` pattern matches
5. **MAS executes**: `GET /api/voice/tools/devices/mushroom1/status`
6. **Result injected**: `[TOOL RESULT] Mushroom1 is online, temp 22.5C`
7. **Moshi incorporates**: Speaks the result naturally
8. **User hears**: "Mushroom One is online at 22.5 degrees Celsius"

---

## Event Types

| Type | Description | Example |
|------|-------------|---------|
| `agent_update` | Agent status change | "Opportunity Scout found 3 leads" |
| `tool_result` | Tool execution result | "MINDEX query returned 5 species" |
| `memory_insight` | Memory recall | "You mentioned Cordyceps earlier" |
| `notification` | System notification | "Backup completed" |
| `knowledge` | Knowledge discovery | "Optimal temp for Lion's Mane is 18C" |

---

## Configuration

### Environment Variables

`ash
# Moshi Server
MOSHI_HOST=localhost
MOSHI_PORT=8998

# MAS Orchestrator
MAS_ORCHESTRATOR_URL=http://192.168.0.188:8001
MAS_TIMEOUT=10
MAS_EVENT_POLL_INTERVAL=2.0
`

### Startup Commands

`powershell
# 1. Start Moshi Server (RTX 5090)
python c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\start_personaplex.py

# 2. Start PersonaPlex Bridge
python c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\services\personaplex-local\personaplex_bridge_nvidia.py

# 3. Test integration
python c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\scripts\test_personaplex_mas.py
`

---

## Testing

### Integration Test

`ash
python scripts/test_personaplex_mas.py
`

Tests:
- Moshi server health
- Bridge health and features
- MAS orchestrator health
- Voice tools endpoints
- Voice orchestrator chat (MYCA identity)
- Event stream
- Session creation

### Manual Voice Test

1. Open `http://localhost:3010/test-voice` (or native Moshi at 8998)
2. Grant microphone permission
3. Speak naturally: "Hello MYCA, what's your name?"
4. MYCA should respond with identity
5. Try: "Check the status of Mushroom 1"
6. MYCA should query device and respond with status

---

## Key Improvements from Previous Version

| Before (v5.x) | After (v6.0.0) |
|---------------|----------------|
| Text injection ignored by Moshi | Text injection acknowledged (kind=3) |
| No tool execution | Full tool call pipeline |
| Passive event polling | Active event injection |
| Basic memory cloning | Comprehensive transcript history |
| Single endpoint attempts | Multi-endpoint fallback |

---

## Next Steps

1. **Deploy to MAS VM**: Push code and restart services
2. **Test with real NatureOS devices**: Connect Mushroom1, etc.
3. **Add more tool patterns**: Weather, calendar, document search
4. **Implement voice activity detection**: Better turn-taking
5. **Add memory recall**: Use vector search for context

---

*Document Created: February 3, 2026*
*Status: Implementation Complete - Ready for Testing*
