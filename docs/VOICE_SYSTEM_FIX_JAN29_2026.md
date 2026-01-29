# Voice System Fix - January 29, 2026

## Complete PersonaPlex Integration

This document describes the full PersonaPlex integration for MYCA voice, following the NVIDIA PersonaPlex architecture for real-time full-duplex conversational AI.

**Reference:** [NVIDIA PersonaPlex](https://research.nvidia.com/labs/adlr/personaplex/)

---

## Issues Fixed

### 1. Broken Voice Audio
**Problem:** The voice-duplex page was not correctly handling WAV audio format from the PersonaPlex/Moshi TTS server. When WAV files arrived via WebSocket, the code tried to interpret them as raw PCM (including the WAV headers), producing garbled/broken audio.

**Fix:** Updated `playRawAudio()` function in `/myca/voice-duplex/page.tsx` to detect WAV format (RIFF magic bytes) and play using the Audio element instead of raw PCM processing.

### 2. WebSocket URL Hardcoded to Localhost
**Problem:** The voice session API was returning `ws://localhost:8999/...` for WebSocket URLs, which only works when accessing the website from the same machine as the PersonaPlex server.

**Fix:** Updated `/api/mas/voice/duplex/session/route.ts` to dynamically generate WebSocket URLs based on the request host, so connections work from any machine on the network.

### 3. Microphone Not Being Used
**Problem:** The code requested microphone permission but never actually captured or processed voice input. The microphone stream was acquired but just sat unused.

**Fix:** Added browser-based speech recognition using the Web Speech API:
- Real-time speech-to-text transcription in the browser
- Interim results displayed while speaking
- Final transcripts sent to PersonaPlex server
- Mute/unmute functionality that pauses/resumes recognition

---

## Architecture

PersonaPlex becomes a **new duplex conversation transport + speech generator**, but **MYCA remains the orchestrator**, and n8n remains the automation bus.

```
Browser (WebAudio + Web Speech API)
     |
     v
PersonaPlex Gateway (port 8999)
     |
     +---> Native Moshi TTS Server (port 8998)
     |          |
     |          +---> kyutai/tts-1.6b-en_fr model
     |          +---> 24kHz WAV audio output
     |
     +---> Duplex Bridge
              |
              +---> POST /api/mas/voice/orchestrator (MYCA brain)
              |
              +---> n8n webhooks (intent routing, safety)
              |
              v
          Tool Results → Inject back into PersonaPlex → Speak naturally
```

---

## Files Changed

### Website Project
- `app/api/mas/voice/duplex/session/route.ts` - Dynamic WebSocket URL generation
- `app/myca/voice-duplex/page.tsx` - Complete voice input/output overhaul:
  - WAV audio format detection and playback
  - Web Speech API integration for voice input
  - Interim transcript display
  - Improved status indicators

### MAS Project
- `services/personaplex-local/moshi_native_v2.py` - Native Moshi TTS server
- `services/personaplex-local/bridge_api_v2.py` - PersonaPlex bridge with WebSocket
- `migrations/004_voice_sessions.sql` - MINDEX voice tables

## Current Voice System Status

| Component | Status | Port |
|-----------|--------|------|
| Moshi Native TTS Server | Running | 8998 |
| PersonaPlex Bridge API | Running | 8999 |
| Website Voice Page | Available | 3010 |

## Audio Format
- Format: WAV (RIFF/WAVE)
- Channels: 1 (Mono)
- Sample Rate: 24000 Hz
- Bits per Sample: 16-bit PCM

## Voices Available

### PersonaPlex (Native Moshi TTS)
- `alba-mackenna/casual.wav` - Casual female (default)
- `alba-mackenna/announcer.wav` - Announcer style
- `alba-mackenna/merchant.wav` - Merchant style

### ElevenLabs (Fallback)
- Arabella (`aEO01A4wXwd1O8GPgGlF`) - Premium cloud voice

## Testing

1. Go to http://localhost:3010/myca/voice-duplex
2. Click "Start Session"
3. Status should show "PersonaPlex" (green indicator) not "ElevenLabs (Fallback)"
4. Voice audio should play clearly in WAV format

## Troubleshooting

If voice still sounds broken:
1. Check browser console for audio playback errors
2. Verify PersonaPlex health: `curl http://localhost:8999/health`
3. Test chat endpoint: `curl -X POST http://localhost:8999/chat -H "Content-Type: application/json" -d '{"session_id":"test","text":"Hello"}'`
4. Check Moshi server logs for TTS generation errors

---

## API Endpoints

### Existing (Preserved)
| Endpoint | Purpose |
|----------|---------|
| `POST /api/mas/voice` | ElevenLabs TTS (fallback) |
| `POST /api/mas/voice/orchestrator` | MYCA brain pipeline |
| `POST /webhook/myca/speech_turn` | n8n intent routing |
| `POST /webhook/myca/speech_safety` | n8n safety confirmation |

### New (PersonaPlex)
| Endpoint | Purpose |
|----------|---------|
| `POST /api/mas/voice/duplex/session` | Create duplex session |
| `GET /api/mas/voice/duplex/session` | Check availability |
| `GET /api/mas/voice/sessions` | List active sessions |
| `WS ws://{host}:8999/ws/{session_id}` | WebSocket for real-time audio |
| `GET http://localhost:8999/health` | PersonaPlex bridge health |
| `POST http://localhost:8999/chat` | REST chat with audio response |

---

## PyTorch & CUDA Status

| Component | Version |
|-----------|---------|
| PyTorch | 2.11.0.dev20260128+cu128 (nightly) |
| CUDA | 12.8 |
| GPU | NVIDIA GeForce RTX 5090 |
| Compute Capability | sm_120 (12.0) |
| Moshi Library | 0.2.12 |

---

## Roadmap

### Current Phase: Native Moshi TTS
- Browser STT (Web Speech API) → Text → Moshi TTS → Audio

### Next Phase: Full PersonaPlex
- Install NVIDIA PersonaPlex 7B model (requires HuggingFace license)
- True speech-to-speech with full duplex
- Voice conditioning via audio prompts
- Natural interruptions and backchannels

### Future: WebRTC Transport
- Upgrade from WebSocket to WebRTC for sub-200ms latency
- P2P audio streams with STUN/TURN

---

## Starting the Services

```powershell
# Terminal 1: Native Moshi TTS Server
$env:NO_TORCH_COMPILE = "1"
$env:HF_TOKEN = "hf_your_token_here"
$env:MAS_ORCHESTRATOR_URL = "http://192.168.0.188:8001"
python services/personaplex-local/moshi_native_v2.py

# Terminal 2: PersonaPlex Bridge
python services/personaplex-local/bridge_api_v2.py

# Terminal 3: Website
cd ../WEBSITE/website
npm run dev
```

---

*Fixed: January 29, 2026*
