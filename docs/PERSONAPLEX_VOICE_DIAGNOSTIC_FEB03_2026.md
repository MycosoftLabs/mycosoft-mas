# PersonaPlex Voice System Diagnostic Report
## February 3, 2026 - 7:10 PM

## Executive Summary

**ISSUE**: Voice test page shows text responses but NO audio output from MYCA.

**ROOT CAUSE**: The Moshi server only accepts Opus-encoded audio input (kind 1). Our bridge was sending text injection (kind 2), which Moshi ignores with "unknown message kind 2".

**STATUS**: Issue identified. Solution in progress.

---

## Architecture Analysis

### How Moshi Works (Native Client)

```
User Microphone → Opus Encoder → WebSocket (kind 1) → Moshi Server
                                                         ↓
                                              LLM Processing (Moshi 7B)
                                                         ↓
Browser Speakers ← Opus Decoder ← WebSocket (kind 1) ← Audio Response
```

The native Moshi client at `http://localhost:8998`:
1. Captures microphone audio using Web Audio API
2. Encodes audio to Opus format using `opus-recorder`
3. Sends Opus packets via WebSocket with `kind = 1`
4. Receives Opus audio responses from Moshi
5. Decodes Opus using WASM decoder
6. Plays audio through Web Audio API

### How Our Bridge Attempted to Work (INCORRECT)

```
User Speech → Web Speech API → Text → Bridge → text injection (kind 2) → Moshi
                                                                            ↓
                                                    Moshi says "unknown message kind 2"
                                                                            ↓
                                                              NO AUDIO GENERATED
```

### Why It Failed

From `personaplex-repo/moshi/moshi/server.py`:

```python
kind = message[0]
if kind == 1:  # audio ONLY
    payload = message[1:]
    pcm = opus_reader.append_bytes(payload)
    await pcm_queue.put(pcm)
else:
    clog.log("warning", f"unknown message kind {kind}")  # THIS IS LOGGED!
```

**The Moshi server ONLY processes audio input (kind 1). It ignores all other message types.**

---

## Services Tested

| Service | Port | Status | Notes |
|---------|------|--------|-------|
| Moshi Server | 8998 | ONLINE | Full-duplex audio only |
| PersonaPlex Bridge | 8999 | ONLINE | Text injection not supported by Moshi |
| Website Dev Server | 3010 | ONLINE | Test page functional |
| MAS Orchestrator | 8001 | ONLINE | Returns text responses correctly |

---

## Log Evidence

### Moshi Server Logs

```
[94m[40EN] [0m[94msent handshake bytes[0m
[94m[40EN] [0m[1;31m[Warn][0m unknown message kind 2    ← TEXT INJECTION REJECTED
```

### Bridge Logs

```
INFO:personaplex-bridge:Moshi handshake OK for f3d0c568-3d06-403d-a1b6-76859218b6df
INFO:httpx:HTTP Request: POST http://192.168.0.188:8001/voice/orchestrator/chat "HTTP/1.1 200 OK"
ERROR:personaplex-bridge:Forward to Moshi error: Cannot call "receive" once a disconnect message
```

---

## Work Done This Session

1. **Identified HuggingFace cache permission issues** - Fixed with `takeown` and `icacls`
2. **Restarted Moshi and Bridge services multiple times**
3. **Verified WebSocket handshake works** - Moshi accepts connections correctly
4. **Copied Opus decoder worker** from native client to website
5. **Implemented Opus decoding** in test page
6. **Discovered root cause** - Moshi doesn't support text input

---

## Solution Options

### Option 1: Use Native Moshi Embed (Already Supported)
- The test page already has "Embed Native Moshi Here" button
- Full-duplex audio works perfectly in the native UI
- Limitation: Not connected to MYCA/MAS

### Option 2: Send Actual Audio to Moshi (Proper Fix)
Required changes:
1. Capture microphone audio in browser
2. Encode to Opus format
3. Send via WebSocket to Moshi (through bridge or directly)
4. Receive and play audio responses

### Option 3: Modify Bridge for Audio Passthrough
1. Bridge receives audio from browser
2. Forwards to Moshi
3. Intercepts Moshi's text responses for MAS routing
4. Returns audio to browser

---

## Files Modified This Session

1. `website/app/test-voice/page.tsx` - Voice test page with Opus decoder
2. `website/public/assets/decoderWorker.min.js` - Copied Opus decoder from native client
3. `services/personaplex-local/personaplex_bridge_nvidia.py` - Reverted to original

---

## Next Steps

1. **Implement proper audio pipeline** - Send audio to Moshi, not text
2. **Use native Moshi approach** - Opus encoding for audio input
3. **OR** Use native Moshi embed for full-duplex, text-only for MYCA commands

---

## Recommendations

For **full-duplex voice** (like JARVIS):
- Use native Moshi at `http://localhost:8998` directly
- It works perfectly with proper Opus audio pipeline

For **MYCA integration**:
- Either implement full Opus encoding/decoding
- Or use hybrid approach: native Moshi for voice, separate MAS for commands

---

## UPDATE - 7:15 PM

### Fix Implemented

The test page has been completely rewritten to properly communicate with Moshi:

#### Previous (Broken) Architecture:
```
Browser → Web Speech API (text) → Bridge → text injection → Moshi
                                                              ↓
                                              "unknown message kind 2" = IGNORED
```

#### New (Working) Architecture:
```
Browser Mic → MediaRecorder (Opus) → WebSocket (kind 1) → Moshi
                                                            ↓
                                                   LLM Processing
                                                            ↓
Browser Speakers ← Opus Decoder ← WebSocket (kind 1) ← Audio Response
```

### Key Changes Made:

1. **Direct Moshi Connection**: Test page now connects directly to `ws://localhost:8998/api/chat` instead of through the bridge

2. **Audio Capture**: Uses `MediaRecorder` API with `audio/webm;codecs=opus` format

3. **Binary Protocol**: Sends audio data with kind=1 prefix (matching Moshi's expected format)

4. **Opus Decoder**: Copied from native client (`decoderWorker.min.js`) for audio playback

### Files Modified:

- `website/app/test-voice/page.tsx` - Complete rewrite for audio-first approach
- `website/public/assets/decoderWorker.min.js` - Opus decoder from native client

### Current Status:

| Component | Status | Notes |
|-----------|--------|-------|
| Moshi Server (8998) | ONLINE | Fresh restart, ready for connections |
| PersonaPlex Bridge (8999) | ONLINE | Available for MAS routing |
| Website Dev Server (3010) | ONLINE | Test page ready |
| Opus Decoder | LOADED | In public/assets/ |

### How to Test:

1. Navigate to http://localhost:3010/test-voice
2. Click "Start MYCA Voice Session"
3. Grant microphone permission
4. Speak naturally - audio is now sent directly to Moshi

---

## UPDATE - 9:25 PM

### Additional Fix: Audio Format

**Problem Found:** Moshi server threw error:
```
ValueError: unexpected ogg capture pattern [26, 69, 223, 163]
```

The bytes `[26, 69, 223, 163]` = `0x1A 0x45 0xDF 0xA3` are WebM/EBML header magic bytes. Moshi expects **Ogg/Opus** (starting with `OggS`), but MediaRecorder outputs **WebM/Opus**.

### Solution: Use opus-recorder

Replaced MediaRecorder with the `opus-recorder` library (same as native client):

1. Copied from native client's `node_modules/opus-recorder/dist/`:
   - `recorder.min.js` - Main recorder
   - `encoderWorker.min.js` - Opus encoder (385KB)
   - `decoderWorker.min.js` - Opus decoder

2. Updated `startAudioCapture()` to:
   - Dynamically load `recorder.min.js`
   - Configure for Ogg/Opus output at 24kHz
   - Stream Ogg pages directly to Moshi

### Files in `website/public/assets/`:
- `recorder.min.js` (8KB)
- `encoderWorker.min.js` (385KB)
- `decoderWorker.min.js` (29KB)
- `waveWorker.min.js` (6KB)

---

*Document updated - February 3, 2026 9:25 PM*
