# Local GPU Services for Dev Server
## February 5, 2026

---

## Overview

This document describes the Local GPU Services system, which runs all GPU-intensive workloads on the local Windows development machine with RTX 5090 and exposes them to the dev server at `localhost:3010`.

### Why Local GPU?

The RTX 5090 GPU (32GB VRAM) is physically installed in the **Windows Dev PC**, not the Proxmox server. Until a GPU is added to the server infrastructure, all GPU-accelerated features run locally:

- **Earth2Studio** - Weather/climate AI models (FCN, Pangu, GraphCast)
- **PersonaPlex/Moshi** - Real-time voice AI with CUDA graphs
- **Future**: Omniverse Kit, CorrDiff, StormScope

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LOCAL GPU SERVICES ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DEV SERVER (localhost:3010)                                         │   │
│  │  Next.js / React                                                     │   │
│  │                                                                       │   │
│  │  Components:                                                          │   │
│  │  ├── useLocalGPU()      - Gateway connection hook                    │   │
│  │  ├── useEarth2()        - Weather model inference                    │   │
│  │  └── useVoiceBridge()   - Voice AI integration                       │   │
│  │                                                                       │   │
│  │  API Routes:                                                          │   │
│  │  └── /api/gpu           - Proxy to GPU services                       │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│                                 │ HTTP/WebSocket                            │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  GPU GATEWAY (localhost:8300)                                        │   │
│  │  FastAPI / Unified Entry Point                                       │   │
│  │                                                                       │   │
│  │  Endpoints:                                                           │   │
│  │  ├── GET /           - Service discovery                             │   │
│  │  ├── GET /health     - All services health                           │   │
│  │  ├── GET /gpu/status - Detailed GPU info                             │   │
│  │  ├── /earth2/*       - Proxy to Earth2Studio                         │   │
│  │  └── /voice/*        - Proxy to Voice Bridge                          │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                           │
│         ┌───────────────────────┼───────────────────────┐                   │
│         │                       │                       │                   │
│         ▼                       ▼                       ▼                   │
│  ┌─────────────┐    ┌─────────────────────┐    ┌─────────────────┐         │
│  │ Earth2Studio │    │ PersonaPlex Bridge  │    │ Moshi Server    │         │
│  │ :8220        │    │ :8999               │    │ :8998           │         │
│  │              │    │                     │    │                 │         │
│  │ Models:      │    │ Routes:             │    │ WebSocket:      │         │
│  │ - FCN        │    │ - /session          │    │ /api/chat       │         │
│  │ - Pangu      │    │ - /ws/{id}          │    │                 │         │
│  │ - GraphCast  │    │ - /health           │    │ Uses ~23GB VRAM │         │
│  │ - SFNO       │    │                     │    │ CUDA Graphs     │         │
│  └─────────────┘    └─────────────────────┘    └─────────────────┘         │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  NVIDIA GeForce RTX 5090 (31.8 GB VRAM)                              │   │
│  │  CUDA 12.8 | cuDNN 9.1002 | PyTorch 2.10.0                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Start GPU Services

```batch
:: Double-click or run from terminal
START_LOCAL_GPU.bat
```

Or manually:
```powershell
python scripts\local_gpu_services.py
```

### 2. Verify Services

Open in browser:
- **Gateway**: http://localhost:8300/docs
- **Earth2 API**: http://localhost:8220/docs
- **Moshi UI**: http://localhost:8998
- **Voice Health**: http://localhost:8999/health

### 3. Start Dev Server

```bash
cd website
npm run dev
# Opens localhost:3010
```

---

## Service Ports

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| GPU Gateway | 8300 | http://localhost:8300 | Unified entry point |
| Earth2Studio | 8220 | http://localhost:8220 | Weather AI API |
| PersonaPlex Bridge | 8999 | http://localhost:8999 | Voice routing |
| Moshi Server | 8998 | ws://localhost:8998 | Voice AI WebSocket |

---

## Environment Configuration

The following environment variables are configured in `website/.env.local`:

```bash
# Local GPU Services (RTX 5090)
NEXT_PUBLIC_GPU_GATEWAY_URL=http://localhost:8300
NEXT_PUBLIC_EARTH2_URL=http://localhost:8220
NEXT_PUBLIC_VOICE_BRIDGE_URL=http://localhost:8999
NEXT_PUBLIC_MOSHI_URL=ws://localhost:8998
NEXT_PUBLIC_USE_LOCAL_GPU=true

# Internal (server-side)
LOCAL_GPU_GATEWAY=http://localhost:8300
LOCAL_EARTH2_URL=http://localhost:8220
LOCAL_BRIDGE_URL=http://localhost:8999
LOCAL_MOSHI_URL=ws://localhost:8998/api/chat
```

---

## React Hooks

### useLocalGPU

Basic gateway connection:

```tsx
import { useLocalGPU } from '@/hooks/use-local-gpu';

function GPUStatus() {
  const { isConnected, gatewayStatus, error } = useLocalGPU();

  if (!isConnected) return <div>GPU services offline</div>;

  return (
    <div>
      <p>GPU: {gatewayStatus?.gpu.name}</p>
      <p>Memory: {gatewayStatus?.gpu.memory_gb} GB</p>
    </div>
  );
}
```

### useEarth2

Weather model inference:

```tsx
import { useEarth2 } from '@/hooks/use-local-gpu';

function WeatherForecast() {
  const { models, gpuStatus, loadModel, runInference } = useEarth2();

  const handleForecast = async () => {
    // Load FCN model
    await loadModel('fcn');

    // Run 24-hour forecast
    const result = await runInference({
      model: 'fcn',
      lead_time: 24,
    });

    console.log(result);
  };

  return (
    <div>
      <h3>Available Models</h3>
      {models.map(m => (
        <button key={m.name} onClick={() => loadModel(m.name)}>
          {m.name} {m.loaded ? '(loaded)' : ''}
        </button>
      ))}
    </div>
  );
}
```

### useVoiceBridge

Voice AI integration:

```tsx
import { useVoiceBridge } from '@/hooks/use-local-gpu';

function VoiceChat() {
  const { isConnected, createSession, getWebSocketUrl } = useVoiceBridge();

  const startVoice = async () => {
    const sessionId = await createSession();
    const wsUrl = getWebSocketUrl(sessionId);

    // Connect to WebSocket
    const ws = new WebSocket(wsUrl);
    // ... handle audio
  };

  return (
    <button onClick={startVoice} disabled={!isConnected}>
      Start Voice Chat
    </button>
  );
}
```

### useGPUServices

Combined hook for all services:

```tsx
import { useGPUServices } from '@/hooks/use-local-gpu';

function Dashboard() {
  const { isReady, gateway, earth2, voice } = useGPUServices();

  if (!isReady) return <div>Loading GPU services...</div>;

  return (
    <div>
      <p>GPU: {gateway.gatewayStatus?.gpu.name}</p>
      <p>Earth2 Models: {earth2.models.length}</p>
      <p>Voice: {voice.isConnected ? 'Ready' : 'Offline'}</p>
    </div>
  );
}
```

---

## API Routes

### GET /api/gpu

Get status of all GPU services:

```bash
curl http://localhost:3010/api/gpu
```

Response:
```json
{
  "enabled": true,
  "gateway": { "version": "1.0.0", "gpu": {...}, "services": {...} },
  "gpu": { "available": true, "name": "NVIDIA GeForce RTX 5090", "memory_gb": 31.8 },
  "voice": { "status": "healthy", "moshi_available": true },
  "endpoints": {
    "gateway": "http://localhost:8300",
    "earth2": "http://localhost:8220",
    "voice": "http://localhost:8999",
    "moshi": "ws://localhost:8998/api/chat"
  }
}
```

### POST /api/gpu

Proxy to specific services:

```bash
# Get Earth2 models
curl -X POST http://localhost:3010/api/gpu \
  -H "Content-Type: application/json" \
  -d '{"service": "earth2", "action": "models"}'

# Load a model
curl -X POST http://localhost:3010/api/gpu \
  -H "Content-Type: application/json" \
  -d '{"service": "earth2", "action": "load", "model": "fcn"}'

# Create voice session
curl -X POST http://localhost:3010/api/gpu \
  -H "Content-Type: application/json" \
  -d '{"service": "voice", "action": "session"}'
```

---

## Available Earth2 Models

| Model | Description | Max Lead Time | VRAM Usage |
|-------|-------------|---------------|------------|
| `fcn` | FourCastNet (NVIDIA) | 240h | ~2GB |
| `pangu` | Pangu-Weather (Huawei) | 168h | ~4GB |
| `graphcast` | GraphCast (DeepMind) | 240h | ~8GB |
| `sfno` | Spherical FNO | 168h | ~3GB |

---

## VRAM Management

The RTX 5090 has 32GB VRAM. Approximate usage:

| Service | VRAM | Notes |
|---------|------|-------|
| Moshi (PersonaPlex) | ~23GB | Voice AI with CUDA graphs |
| Earth2 FCN | ~2GB | Can run alongside Moshi |
| Earth2 Pangu | ~4GB | May need to unload other models |
| Earth2 GraphCast | ~8GB | Larger model |

**Recommendation**: Keep Moshi running (primary voice AI) and load Earth2 models on-demand.

---

## Troubleshooting

### Services not starting

```powershell
# Check if ports are in use
netstat -an | findstr "8220 8300 8998 8999"

# Kill stuck Python processes
taskkill /f /im python.exe
```

### CUDA out of memory

```powershell
# Unload models via API
curl -X POST http://localhost:8220/models/fcn/unload
```

### Voice not working

1. Check Moshi is running: http://localhost:8998
2. Check Bridge health: http://localhost:8999/health
3. Verify CUDA graphs compiled (first connection takes 60-90s)

---

## Files Created

### MAS Repository
- `scripts/local_gpu_services.py` - Unified GPU service manager
- `scripts/earth2_api_server.py` - Earth2Studio API server
- `START_LOCAL_GPU.bat` - Quick start script
- `docs/LOCAL_GPU_SERVICES_FEB05_2026.md` - This document

### Website Repository
- `hooks/use-local-gpu.ts` - React hooks for GPU services
- `app/api/gpu/route.ts` - API route for GPU proxy
- `.env.local` - Environment configuration (updated)

---

## Future Improvements

1. **GPU on Server**: When GPU is added to Proxmox, migrate services
2. **Load Balancing**: Split workloads between local and server GPU
3. **Model Caching**: Keep frequently used models warm in VRAM
4. **WebRTC Streaming**: Stream Omniverse content from GPU

---

## Related Documentation

- [GPU Passthrough and Earth2 Deployment](./GPU_PASSTHROUGH_AND_EARTH2_DEPLOYMENT_FEB05_2026.md)
- [Search Memory Integration](./SEARCH_MEMORY_INTEGRATION_FEB05_2026.md)
- [PersonaPlex Voice Integration](./MYCA_VOICE_REAL_INTEGRATION_FEB03_2026.md)

---

**Author**: Cursor AI Agent  
**Project**: MYCOSOFT MAS  
**Status**: ✓ Operational (Local GPU Mode)
