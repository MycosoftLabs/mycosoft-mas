# MYCA Voice System Fixes - February 3, 2026

## Issues Addressed

| Issue | Fix Applied |
|-------|-------------|
| Random responses ("I like sushi") | Lowered temperature from 0.7 to 0.4 |
| Moshi showing OFFLINE | Fixed health check to recognize 426 WebSocket response |
| Doesn't know Morgan | Added Morgan context to MYCA prompt |
| Too fast/talking over itself | Added pacing instructions in prompt |
| Can't do math/reasoning | **Architectural limitation** - see below |

## Current Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser   │────▶│  PersonaPlex │────▶│    Moshi    │
│  (Voice UI) │◀────│    Bridge    │◀────│   (7B LLM)  │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           │ Text Clone (background)
                           ▼
                    ┌─────────────┐
                    │     MAS     │
                    │ Orchestrator│
                    └─────────────┘
```

**Key Point**: Moshi is a full-duplex 7B LLM that responds in real-time. It handles:
- Speech-to-speech directly
- Immediate responses (30-80ms per step)

**Limitation**: Moshi can't do complex reasoning, math, or access external knowledge. MAS is cloned to in the background but can't provide input before Moshi responds.

## Fixes Applied

### 1. Bridge v7.0.0 (`personaplex_bridge_nvidia.py`)
- Temperature: text=0.4 (was 0.7)
- Improved health check
- Better persona loading

### 2. MYCA Prompt (`myca_personaplex_prompt_1000.txt`)
- Added Morgan context
- Added pacing instructions
- Added math handling hint

### 3. Voice UI (`test-voice/page.tsx`)
- Fixed Moshi health check for 426 responses
- Better error handling

## Services Status

| Service | Port | Function |
|---------|------|----------|
| Moshi Server | 8998 | PersonaPlex 7B voice LLM |
| PersonaPlex Bridge | 8999 | WebSocket proxy + MAS integration |
| MAS Orchestrator | 8001 (VM) | Agent registry + tools |
| Website Dev | 3010 | Test voice UI |

## Test URL

http://localhost:3010/test-voice

## Known Limitations

1. **Math/Reasoning**: Moshi-7B has limited reasoning capability
2. **Real-time Knowledge**: Can't query external APIs before responding
3. **Full-Duplex Trade-off**: Immediate response = less intelligent

## Future Improvements

For truly intelligent voice:
1. **Hybrid Mode**: Use MAS as primary brain, Moshi for voice I/O only
2. **Pre-query MAS**: Route question to MAS first, inject answer, then speak
3. **Larger Model**: Upgrade to PersonaPlex 70B when available

## Commands

```powershell
# Start Moshi (if not running)
python c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\start_personaplex.py

# Start Bridge
python c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\services\personaplex-local\personaplex_bridge_nvidia.py

# Check Bridge Health
Invoke-RestMethod -Uri "http://localhost:8999/health"
```
