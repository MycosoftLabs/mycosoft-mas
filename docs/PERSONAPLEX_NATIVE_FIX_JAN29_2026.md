# PersonaPlex Native Moshi Fix - January 29, 2026

## Problem Solved

The PersonaPlex voice system was falling back to ElevenLabs because the HuggingFace Transformers implementation had breaking changes in version 5.0.0:

```
ERROR: AttentionMaskConverter._unmask_unattended expects a float expanded_mask, got a BoolTensor
ERROR: 'StaticSlidingWindowLayer' object has no attribute 'max_batch_size'
```

## Solution

Bypassed HuggingFace Transformers entirely and used **Kyutai's native moshi library** directly, which works correctly on RTX 5090 (sm_120 / CUDA capability 12.0).

---

## Key Findings

### PyTorch Works on RTX 5090

```python
# PyTorch nightly cu128 is compatible with RTX 5090
torch: 2.11.0.dev20260128+cu128
cuda: True
capability: (12, 0)  # sm_120
```

### The Problem Was Transformers, Not PyTorch

The native moshi library (`moshi.models.loaders`) works perfectly:

```python
from moshi.models.loaders import get_mimi, get_moshi_lm
mimi = get_mimi(mimi_path, device='cuda')  # Works!
lm = get_moshi_lm(model_path, device='cuda')  # Works!
```

### Triton Requires Workaround

The `torch.compile` feature requires Triton, which doesn't support sm_120 yet. Solution:

```bash
NO_TORCH_COMPILE=1 python moshi_native_v2.py
```

---

## Files Created

### 1. `services/personaplex-local/moshi_native_v2.py`

Native Moshi TTS server using Kyutai's library:
- Uses `moshi.models.tts.TTSModel` for text-to-speech
- Uses `kyutai/tts-1.6b-en_fr` model (1.6B parameters)
- Generates 24kHz WAV audio
- WebSocket server on port 8998

### 2. `services/personaplex-local/bridge_api_v2.py`

Updated bridge API:
- Health check reports PersonaPlex availability
- Proxies WebSocket connections to moshi server
- Encodes audio as base64 for REST API
- FastAPI server on port 8999

---

## How to Start

### Option 1: Manual Start

```powershell
# Terminal 1: Native Moshi Server
$env:NO_TORCH_COMPILE = "1"
$env:MAS_ORCHESTRATOR_URL = "http://192.168.0.188:8001"
python services/personaplex-local/moshi_native_v2.py

# Terminal 2: Bridge API
python services/personaplex-local/bridge_api_v2.py

# Terminal 3: Website
cd ../WEBSITE/website
npm run dev
```

### Option 2: Use the startup script

```powershell
.\services\personaplex-local\start_native.ps1
```

---

## Test Results

### Health Check

```json
GET http://localhost:8999/health

{
  "status": "healthy",
  "service": "personaplex-bridge",
  "personaplex": true,
  "personaplex_url": "ws://localhost:8998",
  "timestamp": "2026-01-29T01:15:25.249034+00:00"
}
```

### Chat with Audio

```json
POST http://localhost:8999/chat
{ "session_id": "test", "text": "Hello MYCA" }

Response:
{
  "response_text": "Hello! I am MYCA - Mycosoft Autonomous Cognitive Agent...",
  "has_audio": true,
  "audio_mime": "audio/wav",
  "audio_base64": "UklGRi..."  // ~387KB WAV file
}
```

### Website Session

```json
POST http://localhost:3010/api/mas/voice/duplex/session
{ "mode": "personaplex", "persona": "myca" }

Response:
{
  "mode": "personaplex",
  "personaplex_available": true,
  "transport": {
    "type": "websocket",
    "url": "ws://localhost:8999/ws/session-..."
  }
}
```

---

## Voice Options

Default voice: `alba-mackenna/casual.wav` (female, natural)

Available voices from `kyutai/tts-voices`:
- `alba-mackenna/casual.wav` - Casual female
- `alba-mackenna/announcer.wav` - Announcer style
- `alba-mackenna/merchant.wav` - Merchant style
- 580+ other voices in French and English

---

## Technical Details

### Model Stack

| Component | Version | Source |
|-----------|---------|--------|
| PyTorch | 2.11.0.dev (cu128) | PyTorch nightly |
| moshi | 0.2.12 | kyutai-labs |
| TTS Model | tts-1.6b-en_fr | HuggingFace |
| Audio Codec | Mimi | Kyutai |

### Hardware

| Spec | Value |
|------|-------|
| GPU | NVIDIA GeForce RTX 5090 |
| VRAM | 32GB |
| CUDA | 13.0 (driver) |
| Compute | sm_120 |

### Latency

- Model load: ~10 seconds
- TTS generation: ~3-4 seconds for typical sentence
- Total round-trip: ~10-12 seconds (including MAS response)

---

## Next Steps

1. **Optimize latency** - Pre-warm model, cache responses
2. **Add streaming** - Stream audio chunks as they're generated
3. **Voice cloning** - Use custom voice embeddings
4. **Deploy to production** - Set up on dedicated GPU server

---

## Troubleshooting

### "No module named 'torch'"

```bash
pip install torch --index-url https://download.pytorch.org/whl/nightly/cu128
```

### "Triton not found"

```bash
export NO_TORCH_COMPILE=1  # Linux
$env:NO_TORCH_COMPILE = "1"  # PowerShell
```

### "PersonaPlex not available"

1. Check if moshi server is running: `netstat -ano | findstr :8998`
2. Check bridge server: `netstat -ano | findstr :8999`
3. Test health: `curl http://localhost:8999/health`

---

*Fixed: January 29, 2026*
*Author: Claude (Cursor AI)*
