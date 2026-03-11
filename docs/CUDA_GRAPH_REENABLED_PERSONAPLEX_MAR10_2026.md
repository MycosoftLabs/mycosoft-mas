# CUDA Graph Re-enabled for PersonaPlex

**Date**: March 10, 2026  
**Status**: Complete

## Overview

PersonaPlex requires CUDA graphs to be **on** for real-time voice. A prior RTX 5090 workaround in `start_voice_system.py` forced `NO_CUDA_GRAPH=1`, which caused slow/inadequate performance (~200ms vs ~30ms per step).

## Changes Made

### 1. `scripts/start_voice_system.py`

- **Before:** Always set `NO_CUDA_GRAPH=1`, `NO_TORCH_COMPILE=1`, and related compile flags off.
- **After:** Default to `NO_CUDA_GRAPH=0` and `NO_TORCH_COMPILE=0` so CUDA graphs and torch.compile are enabled. Only override if the user has explicitly set them in the environment.

### 2. `.cursor/rules/myca-voice-system.mdc`

- Updated "GPU Mode 0 (RTX 5090 Blackwell)" section to state that CUDA graphs are **required** for PersonaPlex.
- Corrected manual Moshi startup commands to use `NO_CUDA_GRAPH=0` and `NO_TORCH_COMPILE=0`.
- Added fallback guidance: if sm_120/Blackwell errors occur, users can set `NO_CUDA_GRAPH=1` at the cost of slower/possibly garbled audio.

## Verification

1. Restart Moshi and PersonaPlex Bridge so they run with CUDA graphs enabled.
2. Test voice at `http://localhost:3010/test-voice`.
3. If sm_120 or Blackwell-related PyTorch errors appear, set `NO_CUDA_GRAPH=1` in the environment before starting.

## Related Documents

- [PERSONAPLEX_PERFORMANCE_FIX_FEB03_2026.md](./PERSONAPLEX_PERFORMANCE_FIX_FEB03_2026.md) — CUDA graphs performance on RTX 5090
- [RTX_5090_PYTORCH_SUPPORT_FEB12_2026.md](./RTX_5090_PYTORCH_SUPPORT_FEB12_2026.md) — RTX 5090 / sm_120 context (outdated for PersonaPlex)
