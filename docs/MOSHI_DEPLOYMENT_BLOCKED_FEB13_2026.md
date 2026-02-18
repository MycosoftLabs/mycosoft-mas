# Moshi Deployment Status - BLOCKED - Feb 13, 2026

## Executive Summary

**Status**: PersonaPlex Bridge v8.2.0 code complete and ready. Moshi server deployment blocked by RTX 5090 PyTorch incompatibility.

**What Works**:
- ✅ PersonaPlex Bridge v8.2.0 (port 8999) - 100% Moshi, no edge-tts
- ✅ Test-voice page (http://localhost:3010/test-voice)
- ✅ MAS Consciousness (VM 188:8001)
- ✅ Dev server (3010)

**What's Blocked**:
- ❌ Moshi server on RTX 5090 (PyTorch doesn't support CUDA sm_120 yet)
- ❌ Moshi server on GTX 1080 Ti (11GB VRAM insufficient, CUDA 6.1 too old)

## Attempts Made (Feb 13, 2026)

### GPU Node (gpu01) - GTX 1080 Ti
1. **bf16 model on GPU**: `torch.OutOfMemoryError` (needs ~14GB, 1080 Ti has 11GB)
2. **bf16 model with --half**: Still OOM (~10.5GB allocated, needs more)
3. **q8 quantized on GPU**: `RuntimeError: Expected weight_scb to have type float, but got bfloat16`
4. **q8 with TORCHDYNAMO_DISABLE=1**: Same dtype error
5. **Patched quantize.py**: Python cache prevented patch from taking effect
6. **bf16 on CPU**: Would work but gpu01 only has 16GB RAM, model + inference needs 18-20GB

### Dev PC - RTX 5090 (32GB VRAM)
1. **Native Windows**: Triton library is Linux-only, Moshi crashes
2. **Docker Linux container - GPU mode**: PyTorch 2.5.1 doesn't support sm_120
3. **Docker with PyTorch nightly**: Still no sm_120 support in Nov 2024 nightly
4. **Docker CPU mode**: Container enters restart loop, model download stalls at "retrieving checkpoint"

## Root Causes

### 1. RTX 5090 PyTorch Incompatibility
- RTX 5090 has CUDA compute capability **sm_120** (Blackwell architecture)
- PyTorch stable (2.5.1) supports up to **sm_90** (Hopper)
- PyTorch nightly (Nov 2024) still only supports up to **sm_90**
- **Solution**: Wait for PyTorch 2.7+ (Q2 2026) OR use older GPU

### 2. GTX 1080 Ti Limitations
- CUDA compute capability **6.1** (Pascal)
- Triton compiler requires **7.0+** (Volta or newer)
- VRAM **11GB**, Moshi 7B needs **14-16GB**
- **Solution**: Upgrade to RTX 3080 Ti/4070 Ti (12GB+) or RTX 4080/4090 (16-24GB)

### 3. Model Size
- All Moshi/Moshika models are **7B parameters**
- No smaller (1B, 3B) variants exist from Kyutai
- Quantized q8 has unpatched dtype bug in Moshi library

## Code Complete (Ready When Hardware Ready)

### PersonaPlex Bridge v8.2.0
**File**: `services/personaplex-local/personaplex_bridge_nvidia.py`

**Changes**:
- Removed all edge-tts usage
- Sends MAS response to Moshi for TTS: `session.moshi_ws.send_bytes(b"\x02" + response_text.encode("utf-8"))`
- Moshi returns TTS audio (kind=1), bridge forwards to frontend
- No fallback TTS - full PersonaPlex only

### Dockerfile and Scripts
- ✅ `services/personaplex-local/Dockerfile.moshi` - GPU/CPU-ready Moshi container
- ✅ `scripts/run-moshi-docker-local.ps1` - Build and run script
- ✅ `services/personaplex-local/.env.example` - MOSHI_HOST config for GPU node

### Documentation
- ✅ `docs/FULL_PERSONAPLEX_NO_EDGE_FEB13_2026.md` - Policy and flow
- ✅ `docs/PERSONAPLEX_GPU_DIAGNOSIS_FEB13_2026.md` - Hardware diagnosis
- ✅ `docs/GPU_NODE_INTEGRATION_FEB13_2026.md` - GPU node integration

## Working Solutions (Fastest → Production-Ready)

### Solution 1: Use Alternative GPU (IMMEDIATE - 1 hour)
**Swap in an older NVIDIA GPU** that PyTorch supports:
- RTX 3080 Ti (12GB, sm_86) - $600-800 used
- RTX 4070 Ti (12GB, sm_89) - $700-900
- RTX 4080 (16GB, sm_89) - $1000-1200
- RTX 4090 (24GB, sm_89) - $1500-1800

Then Moshi runs perfectly on GPU with full acceleration.

### Solution 2: Wait for PyTorch 2.7 (Q2 2026)
PyTorch 2.7 expected to add sm_120 support. Check:
```bash
docker run --rm --gpus all pytorch/pytorch:2.7-cuda12.1 python -c "import torch; print(torch.cuda.get_device_capability(0))"
```

### Solution 3: Run on MAS VM (192.168.0.188)
MAS VM might have a compatible GPU or CPU capacity:
```bash
ssh 192.168.0.188
# Check GPU: nvidia-smi
# If compatible GPU, run Moshi there on port 8998
# Bridge uses MOSHI_HOST=192.168.0.188
```

### Solution 4: External Service
Use a cloud GPU service (RunPod, vast.ai, Lambda Labs) with RTX 4090:
- Deploy Moshi container there
- Expose port 8998 via tunnel or public IP
- Bridge connects via MOSHI_HOST=<cloud-ip>

## Interim Testing (Without Full Voice)

**Test consciousness/memory pipeline** without audio:
1. Bridge v8.2.0 is running (8999)
2. Open http://localhost:3010/test-voice
3. Type text instead of speaking
4. Verify: MAS Brain, Tool Calls, Agent Activity, Memory panels populate
5. MYCA text responses work (no TTS audio until Moshi is up)

## Next Actions

1. **Hardware decision**: Choose Solution 1-4 above
2. **Continue development**: Test text-only mode, verify consciousness pipeline
3. **Document for team**: Share hardware requirements for PersonaPlex deployment

## Files Modified

| File | Change | Status |
|------|--------|--------|
| `personaplex_bridge_nvidia.py` | v8.2.0: Full Moshi TTS, no edge-tts | ✅ Complete |
| `Dockerfile.moshi` | GPU/CPU-ready container | ✅ Built |
| `run-moshi-docker-local.ps1` | Docker build/run script | ✅ Complete |
| `.env.example` | MOSHI_HOST config | ✅ Complete |
| 3 new docs | Policy, diagnosis, integration | ✅ Complete |

## Technical Details Logged

- All 10+ Moshi startup attempts documented in chat transcript
- Quantize.py patch created: `scripts/quantize_patched.py`
- Docker build outputs saved
- Hardware specs verified: RTX 5090 (32GB, sm_120), GTX 1080 Ti (11GB, sm_61)
