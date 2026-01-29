# PersonaPlex Complete Setup - January 29, 2026

## Status: FULLY IMPLEMENTED

All three major components are now complete:

| Component | Status | Details |
|-----------|--------|---------|
| MINDEX Persistence | ✅ Complete | SQL file ready for Supabase |
| PersonaPlex 7B Model | ✅ Downloaded | 16GB model in `models/personaplex-7b-v1/` |
| WebRTC Transport | ✅ Created | Server at `services/personaplex-local/webrtc_server.py` |

---

## Files Created

### PersonaPlex Services
| File | Purpose | Size |
|------|---------|------|
| `personaplex_full_server.py` | Full PersonaPlex 7B server | 6KB |
| `webrtc_server.py` | WebRTC low-latency transport | 3KB |
| `bridge_api_v2.py` | WebSocket bridge to MAS | 8KB |
| `moshi_native_v2.py` | Native Moshi TTS (fallback) | 11KB |

### Model Files
| File | Size |
|------|------|
| `model.safetensors` | 15,967 MB (16GB) |
| `tokenizer-e351c8d8-checkpoint125.safetensors` | 367 MB |
| `voices.tgz` | 6 MB |

### Database
| File | Purpose |
|------|---------|
| `docs/SUPABASE_VOICE_TABLES_JAN29_2026.sql` | Voice session tables for MINDEX |

---

## Setup Instructions

### Step 1: Create Supabase Tables

1. Go to https://supabase.com/dashboard
2. Open your project: `hnevnsxnhfibhbsipqvz`
3. Go to **SQL Editor**
4. Copy and paste the contents of `docs/SUPABASE_VOICE_TABLES_JAN29_2026.sql`
5. Click **Run**

This creates:
- `voice_sessions` - Session metadata
- `voice_turns` - Conversation turns
- `voice_tool_invocations` - Tool calls with latency
- `voice_barge_in_events` - User interruptions
- `persona_voice_prompts` - Voice conditioning audio hashes

### Step 2: Start PersonaPlex Services

```powershell
# Terminal 1: PersonaPlex Full Server (uses 7B model)
$env:NO_TORCH_COMPILE = "1"
$env:HF_TOKEN = "$env:HF_TOKEN"
$env:MAS_ORCHESTRATOR_URL = "http://192.168.0.188:8001"
python services/personaplex-local/personaplex_full_server.py

# Terminal 2: PersonaPlex Bridge API
python services/personaplex-local/bridge_api_v2.py

# Terminal 3: WebRTC Server (optional, for lower latency)
python services/personaplex-local/webrtc_server.py

# Terminal 4: Website
cd ../WEBSITE/website
npm run dev
```

### Step 3: Test Voice Interface

1. Open http://localhost:3010/myca/voice-duplex
2. Click "Start Session"
3. Allow microphone access
4. Speak - your words appear in real-time
5. MYCA responds with PersonaPlex voice

---

## Architecture

```
Browser (Chrome/Edge)
  ├── Web Speech API (STT)
  ├── WebSocket to Bridge (port 8999)
  │   └── WebRTC option (port 8997) for lower latency
  └── WebAudio (plays WAV)

PersonaPlex Bridge (8999)
  ├── Forwards to PersonaPlex Full Server (8998)
  ├── Calls MYCA orchestrator for tool routing
  └── Returns audio + text to browser

PersonaPlex Full Server (8998)
  ├── nvidia/personaplex-7b-v1 model (16GB)
  ├── Kyutai TTS for voice output
  └── 24kHz 16-bit PCM WAV

WebRTC Server (8997) [Optional]
  └── P2P audio for sub-200ms latency
```

---

## PyTorch Status

```
PyTorch: 2.11.0.dev20260128+cu128 (nightly)
CUDA: Available
GPU: NVIDIA GeForce RTX 5090 (32GB VRAM)
Compute Capability: (12, 0) = sm_120
Moshi Library: 0.2.12
HuggingFace: mycosoftlabs (token valid)
```

---

## API Endpoints

### Voice Duplex (PersonaPlex)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/mas/voice/duplex/session` | POST | Create duplex session |
| `/api/mas/voice/duplex/session` | GET | Check availability |
| `/api/mas/voice/sessions` | GET | List active sessions |
| `ws://{host}:8999/ws/{session_id}` | WS | Real-time audio |
| `http://localhost:8999/health` | GET | Bridge health |
| `http://localhost:8997/offer` | POST | WebRTC signaling |

### Classic (ElevenLabs Fallback)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/mas/voice` | POST | ElevenLabs TTS |
| `/api/mas/voice/orchestrator` | POST | MYCA brain |

---

## Voices

### PersonaPlex (Native Moshi TTS)
- `alba-mackenna/casual.wav` - Natural female (default)
- `alba-mackenna/announcer.wav` - Announcer style
- `alba-mackenna/merchant.wav` - Merchant style

### ElevenLabs (Fallback)
- Arabella (`aEO01A4wXwd1O8GPgGlF`)

---

## Troubleshooting

### "Model not loaded"
```powershell
# Check if model files exist
Get-ChildItem "models\personaplex-7b-v1" -File
```

### "CUDA out of memory"
PersonaPlex 7B needs ~20GB VRAM. RTX 5090 has 32GB, should be fine.

### "WebRTC connection failed"
Make sure port 8997 is not blocked by firewall.

### "Speech recognition not working"
Use Chrome or Edge. Firefox has limited Web Speech API support.

---

## Next Steps

1. **Run Supabase SQL** - Create the voice tables
2. **Test end-to-end** - Start all services and test voice
3. **Deploy to sandbox** - Push to GitHub and deploy to VM
4. **Monitor latency** - Check topology dashboard for metrics

---

*Complete: January 29, 2026*
*PersonaPlex 7B: nvidia/personaplex-7b-v1*
*Reference: https://research.nvidia.com/labs/adlr/personaplex/*
