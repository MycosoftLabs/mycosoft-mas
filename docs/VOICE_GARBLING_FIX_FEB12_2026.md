# Voice Garbling Issue Analysis - February 12, 2026

## Current Status

The MYCA Voice Suite is **working but with garbled audio output**. The handshake succeeds, audio is sent/received, but the voice sounds distorted.

## Root Cause

**Missing CUDA Graphs (Triton not available on Windows)**

Moshi requires CUDA graphs for real-time audio processing:
- **With CUDA graphs**: ~30ms per step (real-time capable)
- **Without CUDA graphs**: ~200ms+ per step (causes audio buffer underruns)

We had to disable CUDA graphs because:
1. `torch.compile` requires Triton
2. Triton is NOT available for Windows via pip
3. Without Triton, we set `NO_TORCH_COMPILE=1` and `NO_CUDA_GRAPH=1`

## Current Voice Stack

| Component | Port | Status |
|-----------|------|--------|
| Moshi Server | 8998 | RUNNING (slow mode) |
| PersonaPlex Bridge | 8999 | RUNNING |
| Website Dev Server | 3010 | RUNNING |
| MAS Orchestrator | 188:8001 | PARTIAL (missing asyncpg) |

## Audio Configuration

| Parameter | Value |
|-----------|-------|
| Encoder Sample Rate | 24000 Hz |
| Decoder Sample Rate | 48000 Hz |
| Opus Frame Size | 20ms |
| Buffer Length | 1920 samples |

## Solutions (in order of difficulty)

### 1. Install Ubuntu on WSL2 (RECOMMENDED)

WSL2 with GPU passthrough allows native Triton:

```powershell
# Install Ubuntu in WSL2
wsl --install -d Ubuntu

# In Ubuntu:
sudo apt update && sudo apt upgrade -y
pip install moshi triton

# Run Moshi with CUDA graphs
python -m moshi.server --host 0.0.0.0 --port 8998
```

Then update `.env.local`:
```
NEXT_PUBLIC_PERSONAPLEX_WS_URL=ws://localhost:8998/api/chat
```

### 2. Run Moshi in Docker Container

If NVIDIA Container Toolkit is properly configured:

```powershell
docker run -d --name moshi-server \
  --gpus all \
  -p 8998:8998 \
  -e CUDA_VISIBLE_DEVICES=0 \
  kyutai/moshi:latest \
  python -m moshi.server --host 0.0.0.0 --port 8998
```

### 3. Wait for Windows Triton Support

OpenAI/Microsoft are working on Windows Triton support. Track:
- https://github.com/openai/triton/issues/Windows

### 4. Use Cloud GPU (for production)

Deploy Moshi on a cloud GPU instance:
- RunPod: ~$0.30/hr for RTX 4090
- Lambda Labs: ~$1.10/hr for A100
- Vast.ai: ~$0.15/hr for RTX 3090

## Temporary Workaround (Current Setup)

Moshi runs in "slow mode" which causes garbling but is functional for testing:

```powershell
$env:NO_TORCH_COMPILE = "1"
$env:NO_CUDA_GRAPH = "1"
python -m moshi.server --host 0.0.0.0 --port 8998
```

## MAS Issues (Separate)

MAS VM (192.168.0.188) has additional issues:
1. **PostgreSQL**: Missing `asyncpg` module in container
2. **Collectors**: Not running
3. **`/api/myca/status`**: Endpoint returns 404

These are **separate** from the voice garbling and need to be fixed in the MAS container.

## Action Items

1. [ ] Install Ubuntu on WSL2 for native Triton support
2. [ ] Update MAS container to include `asyncpg` dependency
3. [ ] Add `/api/myca/status` endpoint to MAS
4. [ ] Test voice with WSL2 Moshi

## Files Modified

- `start_personaplex.py` - Updated to use kyutai model
- `docs/GPU_SERVER_OPTIONS_FOR_PERSONAPLEX_FEB12_2026.md` - GPU options

## References

- Moshi docs: https://github.com/kyutai-labs/moshi
- Triton Windows: https://github.com/openai/triton/issues/Windows
- CUDA graphs: https://developer.nvidia.com/blog/cuda-graphs/
