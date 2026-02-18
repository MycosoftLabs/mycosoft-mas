# Voice Female Voice Fix (NATF2.pt) - Feb 12, 2026

## Issue

User reported that the Test Voice page was using a male voice instead of the expected NATF2.pt (Natural Female 2) voice for MYCA.

## Root Cause

The `start_personaplex.py` script was configured to use the Kyutai model (`kyutai/moshiko-pytorch-bf16`) and was pointing `voice_prompt_dir` to an **empty** voices folder in the Kyutai cache:

```python
# WRONG - pointing to empty folder
voice_prompt_dir = r"C:\Users\admin2\.cache\huggingface\hub\models--kyutai--moshiko-pytorch-bf16\snapshots\...\voices"
```

This prevented the Moshi server from loading any voice prompt files, causing it to use its default (male) voice.

## Solution

The voice files already existed locally at:
```
C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\models\personaplex-7b-v1\voices\
```

This folder contains all PersonaPlex voice prompts:
- `NATF0.pt`, `NATF1.pt`, `NATF2.pt`, `NATF3.pt` (Natural Female voices)
- `NATM0.pt`, `NATM1.pt`, `NATM2.pt`, `NATM3.pt` (Natural Male voices)
- `VARF0.pt` - `VARF4.pt` (Variable Female voices)
- `VARM0.pt` - `VARM4.pt` (Variable Male voices)

Updated `start_personaplex.py` to point to the correct directory:

```python
# CORRECT - pointing to local voices with NATF2.pt
voice_prompt_dir = r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\models\personaplex-7b-v1\voices"
```

## Configuration

The PersonaPlex Bridge (`personaplex_bridge_nvidia.py`) was already configured to use NATF2.pt:

```python
DEFAULT_VOICE_PROMPT = os.getenv("VOICE_PROMPT", "NATF2.pt")
```

## Verification

After restarting both GPU services:

1. **Moshi Server (8998)**: Running with correct voice directory
2. **PersonaPlex Bridge (8999)**: Healthy with voice_store_connected=true
3. **MAS Brain API**: Healthy with all components initialized

## Test

Access: http://localhost:3010/test-voice

The voice should now be female (NATF2 - Natural Female 2).

## Files Modified

- `start_personaplex.py` - Updated `voice_prompt_dir` path

## Related Documentation

- `docs/PERSONAPLEX_WORKING_JAN29_2026.md` - Original working configuration
- `docs/VOICE_SYSTEM_FIXES_FEB12_2026.md` - Earlier voice system fixes
