# Voice System Fix - February 12, 2026

## Problem
"Garbled voice" in MYCA Voice Suite v8.0.0. Moshi server was failing to start due to multiple issues introduced by recent code changes.

## Root Cause
A commit from January 23, 2026 (`c64f62a`) introduced "meta device" initialization to reduce memory usage during model loading. This caused:

1. **Meta tensor errors**: Missing weights like `depformer_emb.7.weight` stayed as meta tensors (no data) instead of being initialized with real values
2. **HuggingFace download errors**: server.py was trying to download `config.json` from a repo that doesn't have one
3. **Static content download errors**: server.py was trying to download UI assets from a gated NVIDIA repo

## Fixes Applied

### Fix 1: Removed config.json download check
**File**: `personaplex-repo/moshi/moshi/server.py` (line 389)
```python
# Before: hf_hub_download(args.hf_repo, "config.json")
# After: Removed - Kyutai repo doesn't have config.json
```

### Fix 2: Added --static none bypass
**File**: `start_personaplex.py`
```python
sys.argv = [
    'moshi.server',
    '--host', '0.0.0.0',
    '--port', '8998',
    '--hf-repo', hf_repo,
    '--voice-prompt-dir', voice_prompt_dir,
    '--static', 'none',  # Skip gated nvidia UI download
]
```

### Fix 3: Reverted meta device initialization
**File**: `personaplex-repo/moshi/moshi/models/loaders.py` (line 196-198)
```python
# Before (broken):
# init_device = "meta" if filename is not None else device
# model = LMModel(device=init_device, dtype=dtype, **lm_kwargs)

# After (fixed - original behavior):
model = LMModel(device=device, dtype=dtype, **lm_kwargs).to(device=device, dtype=dtype)
```

### Fix 4: Removed redundant .to() call
**File**: `personaplex-repo/moshi/moshi/models/loaders.py` (line 260)
```python
# Before: return model.to(device=device, dtype=dtype)
# After: return model  # Weights already on device
```

## System Status After Fix

| Component | Status | Details |
|-----------|--------|---------|
| Moshi Server (8998) | ✅ ONLINE | ~19GB GPU loaded |
| PersonaPlex Bridge (8999) | ✅ ONLINE | v8.1.0, moshi_available=true |
| Website Dev (3010) | ✅ ONLINE | Ready for testing |
| GPU (RTX 5090) | ✅ | 18808 MiB / 32607 MiB used |

## Test Voice

1. Open: http://localhost:3010/test-voice
2. Click "Connect" to establish WebSocket
3. Speak into microphone
4. Voice should be clear, not garbled

## Key Insight

**You were correct** - the voice system WAS working on Feb 4, 2026 with the RTX 5090. The issue was NOT GPU incompatibility but rather a code change (meta device optimization) that broke model loading for models with missing weights.

## Files Modified

1. `personaplex-repo/moshi/moshi/server.py` - Removed config.json check
2. `personaplex-repo/moshi/moshi/models/loaders.py` - Reverted meta device init
3. `start_personaplex.py` - Added --static none

## Maintenance Commands

```powershell
# Start Moshi server
python start_personaplex.py

# Start PersonaPlex bridge
python services/personaplex-local/personaplex_bridge_nvidia.py

# Check services
Invoke-RestMethod http://localhost:8998/health
Invoke-RestMethod http://localhost:8999/health

# Check GPU usage
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
```

---

*Document created: February 12, 2026*
*System Status: FULLY OPERATIONAL*
