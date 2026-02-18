# PersonaPlex GPU Diagnosis and Solution - Feb 13, 2026

## Problem Summary

**Goal**: Run full PersonaPlex (Moshi STT + TTS, female voice NATF2) with http://localhost:3010/test-voice.

**Issue**: Moshi 7B cannot run on available hardware:

| Hardware | Issue | Result |
|----------|-------|--------|
| **GPU node (gpu01)** - GTX 1080 Ti (11GB) | bf16 models need ~14GB VRAM | `torch.OutOfMemoryError` |
| **GPU node (gpu01)** - GTX 1080 Ti | q8 quantized models have dtype bug | `RuntimeError: Expected weight_scb to have type float, but got bfloat16` |
| **GPU node (gpu01)** - CUDA 6.1 | Triton requires CUDA 7.0+ | Cannot use GPU acceleration even with patch |
| **Dev PC (local)** - RTX 5090 (24GB), Windows | Triton is Linux-only | Moshi crashes during warmup (even though VRAM is sufficient) |

### Technical Root Causes

1. **Triton dependency**: Moshi uses `torch._inductor` and Triton for CUDA graph compilation. Triton:
   - Does not exist on Windows (Linux-only)
   - Requires CUDA compute capability >= 7.0 (GTX 1080 Ti is 6.1)

2. **Model size**: All Moshi/Moshika models are 7B parameters:
   - `bf16`: ~14-15GB VRAM
   - `q8` (quantized): ~4-8GB VRAM but has dtype bug in `moshi/utils/quantize.py`

3. **Patch attempt**: We patched `quantize.py` to auto-convert bfloat16 → float32, but:
   - Python caching prevented immediate effect on gpu01
   - Even with patch, Triton/CUDA 6.1 incompatibility remains

## Current State

| Component | Status | Details |
|-----------|--------|---------|
| Test-voice page | ✅ ONLINE | http://localhost:3010/test-voice |
| Dev server | ✅ ONLINE | Port 3010 |
| PersonaPlex Bridge | ✅ ONLINE | v8.2.0, port 8999, no edge-tts |
| Moshi Server | ❌ OFFLINE | Cannot run on gpu01 (1080 Ti) or Windows (Triton) |
| MAS Orchestrator | ✅ ONLINE | VM 188:8001 |

## Solutions (in order of recommendation)

### Option 1: Run Moshi on GPU Node with Docker + Linux Container (RECOMMENDED)

Use Docker with NVIDIA runtime on gpu01 (Ubuntu) to isolate the environment:

```bash
# On gpu01 (192.168.0.190)
docker run -d --name moshi-voice \
  --gpus all \
  --restart unless-stopped \
  -p 8998:8998 \
  -e TORCHDYNAMO_DISABLE=1 \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  nvidia/cuda:12.1.0-runtime-ubuntu22.04 \
  bash -c "pip install moshi torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
           pip install bitsandbytes websockets huggingface-hub && \
           python3 -m moshi.server --host 0.0.0.0 --port 8998 --hf-repo kyutai/moshika-pytorch-bf16 --device cpu"
```

**Pros**: Isolated environment, CPU mode in container uses RAM not VRAM, 16GB RAM should be sufficient for bf16 on CPU.  
**Cons**: CPU inference will be slower (~2-5x latency vs GPU).

### Option 2: Upgrade GPU Node GPU

Replace GTX 1080 Ti with a GPU that has:
- **16GB+ VRAM** (e.g. RTX 3080 Ti 12GB, RTX 4070 Ti 12GB, RTX 4080 16GB, RTX 4090 24GB)
- **CUDA 7.0+** compute capability

Then bf16 models will run on GPU with full speed.

**Cost**: ~$500-$1500 depending on GPU model.

### Option 3: Use Alternative Voice Stack (NOT full PersonaPlex)

Replace Moshi with:
- **STT**: OpenAI Whisper (`faster-whisper` or `whisperx`) - works on any GPU
- **TTS**: Coqui XTTS, Piper TTS, or Bark - lighter weight

**Pros**: Works on 1080 Ti, good quality.  
**Cons**: Not "full PersonaPlex", different voice (not NATF2/Moshika).

### Option 4: Temporarily Use Dev PC for Moshi via SSH Tunnel

Run Moshi on a **Linux VM on the dev PC** (WSL2 or Hyper-V Ubuntu) with GPU passthrough or Docker Desktop Linux containers:

```bash
# In WSL2 or Linux VM on dev PC
docker run -d --name moshi --gpus all -p 8998:8998 \
  nvidia/cuda:12.1.0-runtime-ubuntu22.04 \
  bash -c "pip install ... && python3 -m moshi.server --host 0.0.0.0 --port 8998 --hf-repo kyutai/moshika-pytorch-bf16"
```

Then PersonaPlex Bridge uses `MOSHI_HOST=localhost` or `MOSHI_HOST=192.168.0.YOUR_DEV_PC_IP`.

**Pros**: RTX 5090 has plenty of VRAM (24GB).  
**Cons**: Moshi runs on your dev PC not gpu01, uses VRAM/resources.

## Immediate Next Step (to unblock testing)

**Use PersonaPlex Bridge in "graceful degradation" mode**:
- Bridge v8.2.0 is already configured to send MAS response to Moshi via `session.moshi_ws.send_bytes(b"\x02" + text)`
- When `session.moshi_ws` is not set (Moshi unavailable), bridge logs "TTS skipped (full PersonaPlex requires Moshi)"
- Frontend receives text but no TTS audio
- **You can test**: STT off (type text), MAS Brain response, Tool Calls, Agent Activity, Memory panels

This lets you develop and test the consciousness/memory pipeline while Moshi GPU issue is resolved.

## Code Changes Made (Full PersonaPlex, No Edge)

- ✅ `personaplex_bridge_nvidia.py` v8.2.0: Removed all `edge-tts`, sends MAS response to Moshi for TTS via `\x02` + text
- ✅ `docs/FULL_PERSONAPLEX_NO_EDGE_FEB13_2026.md`: Policy and flow documented
- ✅ `docs/GPU_NODE_INTEGRATION_FEB13_2026.md`: Updated with PersonaPlex reference
- ✅ `services/personaplex-local/.env.example`: Created (shows `MOSHI_HOST=192.168.0.190` for GPU node)
- ✅ `docs/MASTER_DOCUMENT_INDEX.md`: Added new doc

## Testing Without Moshi (Interim)

You can test http://localhost:3010/test-voice **without voice audio** but with full MAS consciousness:

1. Bridge is running on 8999 (v8.2.0)
2. Click "Start MYCA Voice" 
3. Type text in the input (no mic)
4. Verify: MAS Brain, Tool Calls, Agent Activity, Memory panels populate
5. MYCA response text appears (no audio until Moshi is up)

## Recommended Action

**For production full PersonaPlex**: Implement Option 1 (Docker on gpu01 CPU mode) or Option 2 (upgrade GPU node GPU to 16GB+).

**For immediate testing**: Use the bridge in text mode (no audio) to verify consciousness/memory/tool pipeline, then add Moshi later.
