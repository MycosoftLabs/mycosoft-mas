"""
Test Voice Control for CREP Map - February 5, 2026

This script lets you test voice commands to control the map.
It uses Whisper for speech-to-text and the voice command router.

Usage:
    python _test_voice_map_control.py

Or for text-only testing (no mic):
    python _test_voice_map_control.py --text
"""

import asyncio
import sys
import json

# Check if we have the voice router
try:
    from scripts.voice_command_router import route_voice_command, VoiceCommandRouter
    from scripts.map_voice_handler import process_map_voice
    from scripts.earth2_voice_handler import process_earth2_voice
    VOICE_ROUTER_OK = True
except ImportError as e:
    print(f"[WARN] Voice router not available: {e}")
    VOICE_ROUTER_OK = False

# Check for audio
try:
    import pyaudio
    import wave
    PYAUDIO_OK = True
except ImportError:
    PYAUDIO_OK = False

# Check for httpx
try:
    import httpx
    HTTPX_OK = True
except ImportError:
    HTTPX_OK = False


# Available voice commands for the map
MAP_COMMANDS = """
=================================================================
VOICE COMMANDS FOR CREP MAP
=================================================================

NAVIGATION:
  "go to Tokyo"
  "fly to New York"
  "navigate to London"
  "center on San Francisco"
  "show me Hawaii"

ZOOM:
  "zoom in"
  "zoom out"
  "zoom to level 8"
  "get closer"

PAN:
  "pan left"
  "pan right"
  "move up"
  "go north"

LAYERS:
  "show satellites layer"
  "show aircraft"
  "hide vessels"
  "toggle seismic"
  "show weather layer"

FILTERS (CREP):
  "show only seismic events"
  "filter by high severity"
  "clear filters"

EARTH2 WEATHER:
  "show me a 24 hour forecast"
  "run a nowcast"
  "load the FCN model"
  "show temperature layer"
  "show wind layer"

RESET:
  "reset the map"
  "show the whole world"
  "global view"
=================================================================
"""

async def test_text_command(text: str):
    """Test a text command through the voice router."""
    print(f"\n[INPUT] '{text}'")
    
    if VOICE_ROUTER_OK:
        result = await route_voice_command(text)
        print(f"[RESULT] {json.dumps(result, indent=2)}")
        
        if result.get("speak"):
            print(f"\n[MYCA SAYS] \"{result['speak']}\"")
        
        if result.get("frontend_command"):
            print(f"[MAP COMMAND] {result['frontend_command']}")
        
        return result
    else:
        # Fallback to direct handlers
        map_result = process_map_voice(text)
        if map_result.get("matched"):
            print(f"[MAP RESULT] {json.dumps(map_result, indent=2)}")
            return map_result
        
        earth2_result = await process_earth2_voice(text)
        if earth2_result.get("matched"):
            print(f"[EARTH2 RESULT] {json.dumps(earth2_result, indent=2)}")
            return earth2_result
        
        print("[NO MATCH] Command not recognized")
        return {"success": False, "error": "Not recognized"}


async def send_to_bridge(text: str):
    """Send a command to the PersonaPlex bridge."""
    if not HTTPX_OK:
        print("[WARN] httpx not installed, can't send to bridge")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            # Try the voice route endpoint
            response = await client.post(
                "http://localhost:8999/voice/route",
                json={"text": text, "user_id": "test"},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[BRIDGE ERROR] Status {response.status_code}")
                return None
    except Exception as e:
        print(f"[BRIDGE ERROR] {e}")
        return None


async def record_and_transcribe():
    """Record audio from mic and transcribe with Whisper."""
    if not PYAUDIO_OK:
        print("[ERROR] PyAudio not installed. Run: pip install pyaudio")
        return None
    
    if not HTTPX_OK:
        print("[ERROR] httpx not installed. Run: pip install httpx")
        return None
    
    print("\n[RECORDING] Speak now... (3 seconds)")
    
    # Record audio
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    RECORD_SECONDS = 3
    
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    frames = []
    for i in range(int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    print("[RECORDING] Done. Transcribing...")
    
    # Save to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wf = wave.open(f.name, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        temp_path = f.name
    
    # Send to Whisper
    try:
        async with httpx.AsyncClient() as client:
            with open(temp_path, "rb") as audio_file:
                files = {"file": ("audio.wav", audio_file, "audio/wav")}
                response = await client.post(
                    "http://localhost:8765/v1/audio/transcriptions",
                    files=files,
                    data={"model": "whisper-1"},
                    timeout=30.0
                )
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("text", "").strip()
                    print(f"[WHISPER] Transcribed: '{text}'")
                    return text
                else:
                    print(f"[WHISPER ERROR] Status {response.status_code}")
                    return None
    except Exception as e:
        print(f"[WHISPER ERROR] {e}")
        return None
    finally:
        import os
        os.unlink(temp_path)


async def voice_loop():
    """Continuous voice command loop."""
    print("\n" + "=" * 60)
    print("VOICE-TO-MAP CONTROL TEST")
    print("Speak commands to control the CREP map!")
    print("Press Ctrl+C to exit")
    print("=" * 60)
    
    while True:
        try:
            text = await record_and_transcribe()
            if text:
                result = await test_text_command(text)
                
                # Also try sending to bridge
                bridge_result = await send_to_bridge(text)
                if bridge_result:
                    print(f"[BRIDGE] {bridge_result}")
            
            await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n[EXIT] Goodbye!")
            break


async def text_loop():
    """Text-only command testing."""
    print(MAP_COMMANDS)
    print("\nEnter voice commands to test (type 'quit' to exit):")
    
    while True:
        try:
            text = input("\n[YOU] > ").strip()
            if text.lower() in ("quit", "exit", "q"):
                break
            if not text:
                continue
            
            await test_text_command(text)
            
        except (KeyboardInterrupt, EOFError):
            break
    
    print("\n[EXIT] Goodbye!")


async def main():
    if "--text" in sys.argv or not PYAUDIO_OK:
        if not PYAUDIO_OK:
            print("[INFO] PyAudio not available, running in text mode")
        await text_loop()
    else:
        await voice_loop()


if __name__ == "__main__":
    print("=" * 60)
    print("CREP MAP VOICE CONTROL TEST")
    print("=" * 60)
    print(f"Voice Router: {'OK' if VOICE_ROUTER_OK else 'MISSING'}")
    print(f"PyAudio (mic): {'OK' if PYAUDIO_OK else 'MISSING - text mode only'}")
    print(f"HTTPX: {'OK' if HTTPX_OK else 'MISSING'}")
    
    asyncio.run(main())
