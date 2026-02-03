# Voice System Debug Status - February 3, 2026

## Current Status

### What's Working:
- PersonaPlex Bridge v5.1.0 (localhost:8999) - ONLINE
- PersonaPlex Moshi Server (localhost:8998) - ONLINE (23GB GPU loaded)
- MAS Orchestrator (192.168.0.188:8001) - ONLINE with new endpoints
- WebSocket handshake - SUCCEEDS
- Moshi greeting - WORKS ("Hello, this is Mycosoft. How can I help you today?")
- Audio capture - WORKS (opus encoding)
- Audio playback - PARTIAL (packets received but with drops)

### What's NOT Working:
- **Moshi does not respond to user questions after greeting**
- Heavy packet dropping in audio buffer
- User audio may not be processed correctly by Moshi

## Architecture

```
Browser (3010)
    |
    |-- opus audio --> Bridge (8999) --> Moshi (8998)
    |                      |
    |<-- opus audio <------|
    |<-- text output <-----| (Moshi speaking)
    |
    |-- memory clone --> MAS (188:8001) [async, non-blocking]
```

## Identified Issues

### 1. Moshi Full-Duplex Behavior
The PersonaPlex Moshi model:
- Outputs greeting word-by-word via text (kind=2)
- Outputs greeting audio via opus (kind=1)
- But does NOT respond to subsequent user audio

Possible causes:
- Audio format mismatch
- Moshi waiting for specific audio patterns
- Model configuration issue
- Prompt/persona affecting model behavior

### 2. Audio Buffer Issues
```
audio-processor.js: 'Dropping packets' 
audio-processor.js: 'Missed some audio'
audio-processor.js: Increased maxBuffer to 80.0
```
This suggests the audio playback can't keep up with incoming data.

### 3. Test Page Message Handling
Fixed: Now correctly labels Moshi text output as "MYCA:" instead of "You:"

## Files Modified Today

1. `services/personaplex-local/personaplex_bridge_nvidia.py` - v5.1.0
   - Full-duplex mode
   - MAS event stream polling
   - Async memory cloning

2. `mycosoft_mas/core/myca_main.py`
   - Added `/events/stream` and `/events/publish` endpoints
   - Added `/voice/memory/log` endpoint
   - Made n8n optional (fallback to MYCA)
   - Added `import time, threading`

3. `config/myca_personaplex_prompt_short.txt` - Created
   - Condensed prompt for URL parameter limits

4. `C:\...\website\app\test-voice\page.tsx`
   - Fixed message labels (MYCA vs You)

## Recommended Next Steps

### Immediate:
1. **Check Moshi Server Logs** - Need to see what happens when user audio arrives
2. **Test with Different Prompt** - Simplify to minimal prompt
3. **Check Audio Format** - Verify opus encoding matches Moshi's expectations

### Short-term:
1. Consider alternative TTS approach (ElevenLabs) while debugging Moshi
2. Test Moshi with official client to verify it works correctly
3. Check PersonaPlex documentation for known issues

### Architecture Alternative:
If Moshi full-duplex continues to fail, consider:
```
Browser STT (Web Speech API) --> Bridge --> MAS Orchestrator
                                              |
                                              v
Browser Audio <-- ElevenLabs/Piper TTS <-- MAS Response
```

## Commands to Debug

```powershell
# Check GPU/Memory
nvidia-smi

# Check Python processes
Get-Process python*

# Check bridge logs
Get-Content "services\personaplex-local\*.log" -ErrorAction SilentlyContinue

# Test MAS voice endpoint
curl -X POST http://192.168.0.188:8001/voice/orchestrator/chat -H "Content-Type: application/json" -d '{"message": "Hello"}'

# Test bridge health
curl http://localhost:8999/health
```

## Session Timeline

1. Started with "voice was scrambled" issue
2. Fixed transcript batching (word-by-word to sentences)
3. Fixed Moshi health check (426 = OK)
4. Fixed CORS for test page diagnostics
5. Created full-duplex architecture (Moshi handles all voice)
6. Added MAS event stream for real-time feedback
7. Fixed missing `import time` in MAS
8. Fixed prompt length (short version)
9. Fixed test page message labels
10. **Current**: Moshi greets but doesn't respond to questions
