# RTX 5090 PyTorch Support Issue - February 12, 2026

## Problem

The **NVIDIA GeForce RTX 5090** uses the **Blackwell architecture** (compute capability sm_120), which is **not yet supported** by PyTorch.

### Error Message
```
NVIDIA GeForce RTX 5090 with CUDA capability sm_120 is not compatible with the current PyTorch installation.
The current PyTorch install supports CUDA capabilities sm_50 sm_60 sm_70 sm_75 sm_80 sm_86 sm_90.
```

### Impact
- Cannot run Moshi with CUDA graphs (required for real-time voice)
- Without CUDA graphs, Moshi runs ~10x slower causing audio garbling
- This affects BOTH Windows and Linux (WSL2)

## What We Tried

| Approach | Result |
|----------|--------|
| PyTorch 2.6.0 (stable) cu124 | sm_120 not supported |
| PyTorch 2.11.0 nightly cu126 | sm_120 not supported |
| WSL2 Ubuntu | Same error - PyTorch issue not OS issue |

## Current Workaround

Running Moshi in **slow mode** (no CUDA graphs):

```powershell
$env:NO_TORCH_COMPILE = "1"
$env:NO_CUDA_GRAPH = "1"
python -m moshi.server --host 0.0.0.0 --port 8998
```

This works but causes **audio garbling** due to slower processing (~200ms vs 30ms per step).

## Solutions

### 1. Wait for PyTorch Support (Recommended for Production)
- Monitor: https://github.com/pytorch/pytorch/issues
- Expected: Q2-Q3 2026 (based on typical 6-month lag for new architectures)
- Track CUDA 13.0 support which includes sm_120

### 2. Use Cloud GPU (Recommended for Now)
Deploy Moshi to a cloud instance with a supported GPU:

| GPU | Compute Capability | Provider | Est. Cost |
|-----|-------------------|----------|-----------|
| RTX 4090 | sm_89 | RunPod | ~$0.30/hr |
| A100 | sm_80 | Lambda Labs | ~$1.10/hr |
| H100 | sm_90 | CoreWeave | ~$3.00/hr |
| RTX 3090 | sm_86 | Vast.ai | ~$0.15/hr |

### 3. Build PyTorch from Source (Complex)
Requires:
- CUDA 13.0 SDK with sm_120 support
- Building PyTorch with `TORCH_CUDA_ARCH_LIST="12.0"`
- May take 2-4 hours to compile

### 4. Use Older GPU for Moshi
If you have an older GPU (RTX 3090, 4090, A100), use that for Moshi while keeping the RTX 5090 for other workloads.

## WSL2 Setup (for when PyTorch adds sm_120)

Ubuntu WSL2 is installed and ready with:
- PyTorch nightly installed
- Triton installed (for CUDA graphs)
- Moshi installed
- GPU passthrough working

Once PyTorch supports sm_120, run:
```bash
wsl -d Ubuntu
source ~/moshi_venv/bin/activate
python -m moshi.server --host 0.0.0.0 --port 8998
```

## Timeline

| Date | Event |
|------|-------|
| Jan 2025 | RTX 5090 released with sm_120 |
| Feb 2026 | PyTorch still doesn't support sm_120 |
| Q2-Q3 2026 | Expected PyTorch sm_120 support (estimate) |

## Related Docs
- `docs/VOICE_GARBLING_FIX_FEB12_2026.md`
- `docs/GPU_SERVER_OPTIONS_FOR_PERSONAPLEX_FEB12_2026.md`
