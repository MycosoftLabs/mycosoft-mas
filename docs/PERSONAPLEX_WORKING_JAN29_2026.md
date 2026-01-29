# PersonaPlex NVIDIA Integration - WORKING - January 29, 2026

## Status: ✅ FULLY OPERATIONAL

PersonaPlex is now properly integrated with NVIDIA's Moshi server and MYCA orchestrator as intended.

---

## 7-Day System Assessment Summary

### Infrastructure Status (All Online)

| System | IP/Location | Status | Notes |
|--------|-------------|--------|-------|
| **Proxmox Main** | 192.168.0.202 | ✅ ONLINE | Hosts all VMs |
| **Proxmox Secondary** | 192.168.0.90 | ✅ ONLINE | Standby |
| **Dream Machine Pro Max** | 192.168.0.1 | ✅ ONLINE | Gateway |
| **USW Pro Max 24 PoE** | 192.168.0.2 | ✅ ONLINE | Switch |
| **NAS** | 192.168.0.105 | ✅ ONLINE | Storage |
| **Sandbox VM** | 192.168.0.187 | ✅ ONLINE | Website, MINDEX |
| **MAS VM** | 192.168.0.188 | ✅ ONLINE | Orchestrator, n8n |
| **Windows Dev PC** | 192.168.0.172 | ✅ ONLINE | RTX 5090 |

### Services Running

| Service | Port | Status | Host |
|---------|------|--------|------|
| **NVIDIA Moshi Server** | 8998 | ✅ Running | Windows (RTX 5090) |
| **PersonaPlex Bridge** | 8999 | ✅ Running | Windows |
| **Website (Dev)** | 3010 | ✅ Running | Windows |
| **MAS Orchestrator** | 8001 | ✅ Running | VM 192.168.0.188 |
| **n8n** | 5678 | ✅ Running | VM 192.168.0.188 |
| **Website (Prod)** | 3000 | ✅ Running | VM 192.168.0.187 |

---

## What Was Fixed

### The Problem
The PersonaPlex bridge (bridge_api_v2.py) was expecting a JSON WebSocket handshake `{"type": "connected"}` but the NVIDIA Moshi server uses:
1. Endpoint `/api/chat` (not root `/`)
2. Binary Opus audio protocol
3. Query parameters for prompts
4. Handshake byte `0x00`

### The Solution
Created new `personaplex_bridge_nvidia.py` that:
1. Connects to `ws://localhost:8998/api/chat` with proper query params
2. Handles binary Opus audio protocol
3. Properly detects Moshi server availability by checking the web UI
4. Integrates with MYCA orchestrator for tool execution
5. Uses MYCA persona prompt with NATF2.pt (Natural Female 2) voice

---

## How PersonaPlex Works (NVIDIA's Intent)

```
User speaks into browser microphone
            │
            ▼
    [Web Speech API - Browser STT]
            │
            ▼
    PersonaPlex Bridge (8999)
        │
        ├──→ Routes to NVIDIA Moshi Server (8998)
        │         │
        │         ▼
        │    Full-Duplex Speech-to-Speech
        │    (kyutai/moshiko-pytorch-bf16)
        │         │
        │         ├── Opus audio streaming
        │         ├── Natural interruptions
        │         ├── Backchannels ("mm-hmm")
        │         └── ~40ms frame latency
        │
        └──→ Routes to MYCA Orchestrator (192.168.0.188:8001)
                  │
                  ▼
            Tool Execution
            (Proxmox, UniFi, Agents, n8n)
                  │
                  ▼
            Results injected back to PersonaPlex
```

---

## Current Configuration

### GPU
| Spec | Value |
|------|-------|
| GPU | NVIDIA GeForce RTX 5090 |
| VRAM | 32GB (20GB used by Moshi) |
| Driver | 580.97 |
| Compute | sm_120 (CUDA 12.0) |

### PersonaPlex/Moshi
| Setting | Value |
|---------|-------|
| Model | kyutai/moshiko-pytorch-bf16 |
| Voice | NATF2.pt (Natural Female 2) |
| Persona | MYCA (custom prompt) |
| Frame Latency | ~40ms |
| Audio Format | Opus (24kHz) |

### MYCA Integration
| Setting | Value |
|---------|-------|
| Orchestrator | http://192.168.0.188:8001 |
| Chat Endpoint | /voice/orchestrator/chat |
| Agents | 16 active |
| n8n Workflows | 11 active |

---

## How to Use

### Option 1: Native Moshi UI (Recommended)
1. Open http://localhost:8998
2. Click **Connect**
3. Allow microphone access
4. Start speaking naturally

### Option 2: Bridge API
1. Open http://localhost:8999/health to verify status
2. Create session: POST to http://localhost:8999/session
3. Connect WebSocket to ws://localhost:8999/ws/{session_id}

### Option 3: Website Voice Page
1. Open http://localhost:3010/myca/voice-duplex
2. Toggle "Embedded Mode" to use Moshi UI
3. Or use "Custom UI" for bridge connection

---

## API Reference

### Bridge Endpoints (Port 8999)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with Moshi status |
| `/session` | POST | Create voice session |
| `/sessions` | GET | List active sessions |
| `/session/{id}` | DELETE | End session |
| `/voices` | GET | List available voices |
| `/ws/{session_id}` | WS | WebSocket for audio |

### MAS Orchestrator Endpoints (Port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/voice/orchestrator/chat` | POST | MYCA brain |
| `/agents` | GET | List agents |
| `/tasks` | GET | List tasks |

---

## Startup Commands

### Start All Services
```powershell
# From MAS directory
.\services\personaplex-local\start_personaplex.ps1
```

### Manual Start
```powershell
# Terminal 1: Moshi Server
$env:NO_TORCH_COMPILE = "1"
$env:HF_TOKEN = "$env:HF_TOKEN"
python -m moshi.server --host 0.0.0.0 --port 8998

# Terminal 2: Bridge
python services/personaplex-local/personaplex_bridge_nvidia.py

# Terminal 3: Website (optional)
cd ../WEBSITE/website
npm run dev
```

---

## Available Voices

| ID | Name | Gender | Style |
|----|------|--------|-------|
| **NATF2.pt** | Natural Female 2 (MYCA Default) | Female | Conversational |
| NATF0.pt | Natural Female 0 | Female | Formal |
| NATF1.pt | Natural Female 1 | Female | Neutral |
| NATF3.pt | Natural Female 3 | Female | Neutral |
| NATM0.pt | Natural Male 0 | Male | Formal |
| NATM1.pt | Natural Male 1 | Male | Neutral |
| NATM2.pt | Natural Male 2 | Male | Conversational |
| NATM3.pt | Natural Male 3 | Male | Neutral |

---

## Troubleshooting

### "Moshi not available"
1. Check if port 8998 is listening: `netstat -ano | findstr :8998`
2. Restart Moshi server with `$env:NO_TORCH_COMPILE = "1"`
3. Verify GPU: `nvidia-smi`

### "Connect button not working"
1. Try Chrome or Edge (Firefox has limited support)
2. Check browser console for errors
3. Verify microphone permissions

### "Audio garbled/broken"
1. Make sure using Opus decoder in browser
2. Check that audio format is correct (24kHz)
3. Verify WebSocket connection is stable

### "MYCA not responding"
1. Check MAS orchestrator: `curl http://192.168.0.188:8001/health`
2. Verify n8n is running: `curl http://192.168.0.188:5678/healthz`
3. Check Docker containers on MAS VM

---

## Files Changed/Created

| File | Purpose |
|------|---------|
| `services/personaplex-local/personaplex_bridge_nvidia.py` | New NVIDIA-compatible bridge |
| `services/personaplex-local/start_personaplex.ps1` | Startup script |
| `docs/PERSONAPLEX_WORKING_JAN29_2026.md` | This status document |

---

## Next Steps

1. **Deploy to sandbox.mycosoft.com** - Push changes to GitHub and deploy
2. **Configure Cloudflare tunnel** - Route personaplex.mycosoft.com to local server
3. **Voice cloning** - Create custom MYCA voice embedding
4. **WebRTC transport** - Upgrade for sub-100ms latency

---

*Fixed: January 29, 2026*
*PersonaPlex: nvidia/personaplex-7b-v1*
*Moshi: kyutai/moshiko-pytorch-bf16*
*MYCA Voice: NATF2.pt (Natural Female 2)*
