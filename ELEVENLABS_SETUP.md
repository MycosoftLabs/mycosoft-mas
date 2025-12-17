# ElevenLabs Premium Voice Setup

## 🎙️ Get Scarlett Johansson Style Voice

ElevenLabs offers professional voice cloning and premium voices that can match the style you want.

### Step 1: Get ElevenLabs API Key

1. Sign up at https://elevenlabs.io
2. Navigate to **Profile** → **API Keys**
3. Click **Create API Key**
4. Copy the key (starts with `sk_...`)

### Step 2: Find Your Perfect Voice

1. Go to https://elevenlabs.io/app/voice-library
2. **Search for voices similar to Scarlett Johansson**:
   - Filter by: **Female**, **English**, **Conversational**
   - Listen to previews
   - Popular choices for that style:
     - **"Scarlett"** (if available in library)
     - **"Bella"** (warm, expressive, conversational)
     - **"Rachel"** (calm, mature, professional)
     - **"Domi"** (confident, clear)
3. Click on your chosen voice
4. Copy the **Voice ID** (e.g., `EXAVITQu4vr4xnSDxMaL`)

### Step 3: Configure MYCA

Add to your `.env.local`:

```bash
# ElevenLabs Configuration
ELEVENLABS_API_KEY=sk_your_actual_key_here
```

### Step 4: Update Voice Mapping

Edit `mycosoft_mas/services/elevenlabs_proxy.py`:

```python
# Voice mapping: OpenAI voice names -> ElevenLabs voice IDs
VOICE_MAP = {
    "alloy": "YOUR_PREFERRED_VOICE_ID",  # Replace with your chosen voice ID
    "echo": "21m00Tcm4TlvDq8ikWAM",      # Rachel
    "fable": "pNInz6obpgDQGcFmaJgB",     # Adam
    "onyx": "VR6AewLTigWG4xSOukaG",      # Arnold
    "nova": "EXAVITQu4vr4xnSDxMaL",      # Sarah
    "shimmer": "ThT5KcBeYPX3keUQqHPh",   # Dorothy
    "scarlett": "YOUR_SCARLETT_VOICE_ID",  # ← Put your chosen voice ID here
}
```

### Step 5: Start ElevenLabs Service

```bash
# Rebuild and start with voice-premium profile
docker-compose --profile voice-premium up -d --build elevenlabs-proxy

# Restart voice-ui to use ElevenLabs endpoint
docker-compose restart voice-ui
```

### Step 6: Test Your Voice

```bash
# Test ElevenLabs API directly
curl -X POST http://localhost:5501/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"tts-1","voice":"scarlett","input":"Hello, I am MYCA, your voice assistant"}' \
  -o test_scarlett_voice.mp3

# Play the audio file to verify it sounds right
```

## 🎨 Advanced Voice Customization

### Clone Your Own Voice

ElevenLabs allows you to clone voices (Professional Plan required):

1. Go to **Voice Lab** → **Instant Voice Cloning**
2. Upload 1+ minute of clear audio samples
3. Name your voice (e.g., "Custom MYCA")
4. Get the voice ID
5. Add to `VOICE_MAP` in `elevenlabs_proxy.py`

### Adjust Voice Settings

Edit `mycosoft_mas/services/elevenlabs_proxy.py`, find `_elevenlabs_tts()`:

```python
"voice_settings": {
    "stability": 0.5,         # 0-1: lower = more expressive, higher = more stable
    "similarity_boost": 0.75, # 0-1: how closely to match original voice
    "style": 0.0,             # 0-1: exaggeration (Premium voices only)
    "use_speaker_boost": True # Enhance clarity
}
```

**For Scarlett Johansson style**:
```python
"voice_settings": {
    "stability": 0.4,         # Slightly expressive
    "similarity_boost": 0.8,  # High fidelity
    "style": 0.2,             # Subtle style
    "use_speaker_boost": True
}
```

## 💰 ElevenLabs Pricing & Usage

- **Free Tier**: 10,000 characters/month
- **Starter**: $5/month, 30,000 characters
- **Creator**: $22/month, 100,000 characters + voice cloning
- **Pro**: $99/month, 500,000 characters + commercial license

**Tip**: For development, use local TTS (OpenedAI Speech) and only enable ElevenLabs for production/demos.

## 🔄 Fallback Behavior

The ElevenLabs proxy **automatically falls back** to local TTS if:
- `ELEVENLABS_API_KEY` is not set
- ElevenLabs API is unreachable
- Rate limit exceeded
- Any other error

This ensures **MYCA always responds** even if external API fails.

## 🧪 Testing Different Voices

Create a test script `test_voices.sh`:

```bash
#!/bin/bash
for voice in alloy echo fable onyx nova shimmer scarlett; do
  echo "Testing voice: $voice"
  curl -X POST http://localhost:5501/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"tts-1\",\"voice\":\"$voice\",\"input\":\"Hello, I am MYCA with the $voice voice\"}" \
    -o "test_voice_$voice.mp3"
  echo "Saved to test_voice_$voice.mp3"
done
```

Run and listen to all voices:
```bash
bash test_voices.sh
```

## 📝 Voice Selection in Workflows

### In n8n
Add an HTTP Request node to generate speech:
```
POST http://mas-orchestrator:8000/voice/orchestrator/chat
Body:
{
  "message": "{{ $json.user_message }}",
  "want_audio": true
}
```

The orchestrator will automatically use ElevenLabs if configured, or fall back to local TTS.

### Via Voice UI
The voice UI (`localhost:8090`) automatically uses the configured TTS provider. No code changes needed—just set `ELEVENLABS_API_KEY` and restart services.

## 🎯 Recommended Voice for "Scarlett Johansson" Style

Based on ElevenLabs voice library (as of Dec 2024):

**Top Recommendations**:
1. **"Bella"** (`EXAVITQu4vr4xnSDxMaL`) - Warm, mature, conversational
2. **"Rachel"** (`21m00Tcm4TlvDq8ikWAM`) - Calm, professional, smooth
3. **"Freya"** (check library for ID) - If available, often cited as Scarlett-like

**Custom Clone** (Pro Plan): Upload clips from Her (2013) for best match (ensure legal rights).

## 🔧 Troubleshooting

### "TTS failed" in voice responses
```bash
# Check ElevenLabs proxy logs
docker logs mycosoft-mas-elevenlabs-proxy-1 --tail 100

# Verify API key is set
docker exec mycosoft-mas-elevenlabs-proxy-1 env | grep ELEVENLABS

# Test direct ElevenLabs call
curl -X GET https://api.elevenlabs.io/v1/voices \
  -H "xi-api-key: YOUR_KEY_HERE"
```

### Voice quality issues
- Increase `similarity_boost` in voice_settings (higher = more accurate)
- Try different voice IDs from the library
- Ensure input text is clean (no special chars that cause mispronunciation)

### Quota exceeded
- Check your ElevenLabs dashboard usage
- Temporarily disable: comment out `ELEVENLABS_API_KEY` in `.env.local`
- System will automatically use local TTS fallback

## 📚 References

- ElevenLabs API Docs: https://docs.elevenlabs.io/api-reference
- Voice Library: https://elevenlabs.io/app/voice-library
- Pricing: https://elevenlabs.io/pricing
- Voice Lab (cloning): https://elevenlabs.io/voice-lab
