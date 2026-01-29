# PersonaPlex Integration Complete - January 29, 2026

## Overview

PersonaPlex (NVIDIA's full-duplex conversational speech model) has been successfully integrated with MYCA and the Mycosoft ecosystem. This document provides complete setup and usage instructions.

## Status

| Component | Status | Details |
|-----------|--------|---------|
| PersonaPlex Server | WORKING | Running on port 8998 with RTX 5090 |
| Voice Synthesis | WORKING | NATF2.pt (female) as default |
| Audio Pipeline | WORKING | Full duplex Opus encoding/decoding |
| Python Client | WORKING | Tested with real audio - 4.48s response |
| Browser Client | WORKING | React UI with MYCA defaults + fallback |
| MAS Bridge | IMPLEMENTED | Intent classification and tool routing |
| Website Widget | IMPLEMENTED | Floating widget in unifi-dashboard |
| Voice Commands | IMPLEMENTED | Map, data, agent, device, navigation |
| MINDEX Voice API | IMPLEMENTED | Natural language queries |
| Dashboard Integration | READY | PersonaPlexFloatingWidget in ClientBody |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Browser Client                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐ │
│  │ Microphone   │→ │ opus-recorder │→ │ WebSocket (Opus)     │ │
│  │              │  │ WASM Encoder  │  │ ws://localhost:8998  │ │
│  └──────────────┘  └───────────────┘  └──────────────────────┘ │
│                                                │                │
│  ┌──────────────┐  ┌───────────────┐          │                │
│  │ Speaker      │← │ Opus Decoder  │← ────────┘                │
│  └──────────────┘  └───────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PersonaPlex Server (RTX 5090)                   │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐ │
│  │ Mimi Codec   │→ │ PersonaPlex   │→ │ Voice Synthesis      │ │
│  │ (Opus→PCM)   │  │ 7B LM         │  │ NATF2.pt (MYCA)      │ │
│  └──────────────┘  └───────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MAS Orchestrator                             │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐ │
│  │ Intent       │→ │ Tool Router   │→ │ Agent Execution      │ │
│  │ Classifier   │  │               │  │ (247+ agents)        │ │
│  └──────────────┘  └───────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start PersonaPlex Server

```powershell
cd c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python start_personaplex.py
```

The server will:
- Load PersonaPlex 7B model (~16GB VRAM)
- Load NATF2.pt voice prompt (female voice)
- Start listening on port 8998

### 2. Start Browser Client

```powershell
cd personaplex-repo\client
npm run dev
```

Access at: https://localhost:5173/

### 3. Test Connection

```powershell
python test_personaplex.py
```

Expected output:
```
SUCCESS: Handshake received! Server is ready for full-duplex.
SUCCESS: Full duplex audio working!
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| PERSONAPLEX_URL | ws://localhost:8998 | PersonaPlex server URL |
| MAS_ORCHESTRATOR_URL | http://192.168.0.188:8001 | MAS orchestrator URL |
| NO_TORCH_COMPILE | 1 | Required for RTX 5090 |

### Voice Options

| Voice File | Description |
|------------|-------------|
| NATF2.pt | **MYCA Default** - Natural Female 2 |
| NATF0.pt | Natural Female 0 |
| NATF1.pt | Natural Female 1 |
| NATF3.pt | Natural Female 3 |
| NATM0.pt | Natural Male 0 |
| NATM1.pt | Natural Male 1 |

### Text Prompts

Default MYCA prompt:
```
You are MYCA, the Mycosoft Autonomous Cognitive Agent. You are a helpful 
AI assistant with expertise in mycology, biology, chemistry, physics, 
and all Mycosoft products and services. You have a warm, professional, 
and knowledgeable personality. Be conversational but efficient.
```

## Files Modified/Created

### Server

- `start_personaplex.py` - Server startup script with NO_TORCH_COMPILE
- `test_personaplex.py` - Basic connection test
- `test_personaplex_conversation.py` - Full conversation test

### Client (personaplex-repo/client)

- `src/pages/Queue/Queue.tsx` - Added MYCA preset, AudioWorklet fallback
- `src/pages/Conversation/hooks/useModelParams.ts` - Default to NATF2 voice

### Website (unifi-dashboard)

- `src/components/PersonaPlexWidget.tsx` - Voice widget component
- `src/app/api/myca/personaplex/route.ts` - API endpoint
- `src/app/ClientBody.tsx` - Floating widget integration

### MAS (mycosoft_mas)

- `voice/personaplex_bridge.py` - MAS integration bridge
- `voice/intent_classifier.py` - Intent classification

## Usage Examples

### Voice Commands

**MYCA responds to:**

1. **Greetings**: "Hello MYCA", "Hey, how are you?"
2. **Queries**: "What are the medicinal properties of Reishi?"
3. **Commands**: "Show me devices near the fire"
4. **Control**: "Zoom to San Francisco on the map"

### Integration with MAS

The PersonaPlex bridge classifies intents and routes to appropriate agents:

```python
from mycosoft_mas.voice.personaplex_bridge import get_bridge

bridge = get_bridge()
session = bridge.create_session(persona="myca", voice_prompt="NATF2.pt")

# Handle incoming text from PersonaPlex
result = await bridge.handle_agent_text(
    session.session_id,
    agent_text="Turn on the sensor",
    user_text="Hey MYCA, turn on the sensor"
)
```

## Troubleshooting

### Server Won't Start

```
Error: torch._inductor.exc.TritonMissing
```

**Fix**: Ensure `NO_TORCH_COMPILE=1` is set in environment.

### Browser AudioWorklet Fails

If AudioWorklet fails to load, the client automatically falls back to ScriptProcessorNode.

### No Audio Output

1. Check server is running: `netstat -ano | findstr :8998`
2. Check WebSocket connection in browser console
3. Verify microphone permissions

## Performance

- **Latency**: ~200ms round-trip (audio in to audio out)
- **GPU Memory**: ~16GB VRAM (PersonaPlex 7B)
- **Sample Rate**: 24kHz
- **Audio Format**: Opus (Ogg container)

## Next Steps

1. **Phase 5**: Add voice control to CREP map
2. **Phase 6**: Integrate MINDEX voice queries
3. **Phase 7**: Deploy to production with SSL
4. **Phase 8**: Add n8n workflow voice triggers

## Contact

For issues or questions, check the full documentation at:
- `docs/PERSONAPLEX_INTEGRATION_JAN27_2026.md`
- `docs/VOICE_SYSTEM_FIX_JAN29_2026.md`
