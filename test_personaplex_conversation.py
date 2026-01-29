#!/usr/bin/env python3
"""
Test PersonaPlex full-duplex conversation with actual audio synthesis.
This simulates what the browser client does.
"""

import asyncio
import websockets
import numpy as np
import sphn
import wave
import os
import sys

# Text-to-speech to generate test audio
def generate_speech_audio(text: str, sample_rate: int = 24000) -> np.ndarray:
    """Generate simple sine wave modulated audio to simulate speech."""
    duration = len(text) * 0.05  # ~50ms per character
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    
    # Create a more complex waveform to simulate speech
    freq = 200 + np.random.randint(0, 100)
    audio = 0.3 * np.sin(2 * np.pi * freq * t)
    audio += 0.1 * np.sin(2 * np.pi * (freq * 2) * t)
    audio += 0.05 * np.sin(2 * np.pi * (freq * 3) * t)
    
    # Add amplitude modulation
    mod_freq = 5 + np.random.rand() * 5
    audio *= 0.5 + 0.5 * np.sin(2 * np.pi * mod_freq * t)
    
    return audio.astype(np.float32)


async def test_conversation():
    uri = 'ws://localhost:8998/api/chat?voice_prompt=NATF2.pt&text_prompt=You%20are%20MYCA%20the%20Mycosoft%20AI%20assistant'
    print('=' * 60)
    print('PersonaPlex Full Duplex Conversation Test')
    print('=' * 60)
    print(f'Connecting to: {uri[:50]}...')
    
    async with websockets.connect(uri, close_timeout=5) as ws:
        # Wait for handshake
        print('Waiting for server handshake (loading voice prompt)...')
        msg = await asyncio.wait_for(ws.recv(), timeout=120)
        if msg[0] != 0:
            print('ERROR: No handshake received')
            return False
        print('SUCCESS: Handshake received! Server ready for conversation.')
        print('=' * 60)
        
        # Create Opus encoder/decoder
        sample_rate = 24000
        opus_writer = sphn.OpusStreamWriter(sample_rate)
        opus_reader = sphn.OpusStreamReader(sample_rate)
        
        # Generate test speech audio (simulating "Hello MYCA")
        test_audio = generate_speech_audio("Hello MYCA, how are you today?", sample_rate)
        print(f'Generated {len(test_audio) / sample_rate:.2f}s of test audio')
        
        # Encode to Opus
        opus_data = opus_writer.append_pcm(test_audio)
        if opus_data and len(opus_data) > 0:
            await ws.send(bytes([1]) + opus_data)
            print(f'Sent {len(opus_data)} bytes of Opus audio')
        
        # Also send some silence to give the model time to respond
        silence = np.zeros(sample_rate * 3, dtype=np.float32)  # 3 seconds
        opus_silence = opus_writer.append_pcm(silence)
        if opus_silence and len(opus_silence) > 0:
            await ws.send(bytes([1]) + opus_silence)
            print(f'Sent {len(opus_silence)} bytes of silence')
        
        # Listen for responses
        text_received = ''
        audio_chunks = []
        audio_bytes_received = 0
        
        print('=' * 60)
        print('Listening for MYCA response...')
        print('=' * 60)
        
        for _ in range(200):  # Listen for ~40 seconds max
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.2)
                kind = msg[0]
                if kind == 1:  # Audio
                    audio_bytes_received += len(msg) - 1
                    # Decode audio
                    pcm = opus_reader.append_bytes(msg[1:])
                    if pcm is not None and len(pcm) > 0:
                        audio_chunks.append(pcm)
                elif kind == 2:  # Text
                    text = msg[1:].decode('utf-8')
                    text_received += text
                    print(f'{text}', end='', flush=True)
            except asyncio.TimeoutError:
                continue
        
        print('\n')
        print('=' * 60)
        print('CONVERSATION SUMMARY')
        print('=' * 60)
        print(f'Text received: "{text_received}"')
        print(f'Audio bytes received: {audio_bytes_received}')
        
        if audio_chunks:
            total_audio = np.concatenate(audio_chunks)
            print(f'Audio duration: {len(total_audio) / sample_rate:.2f} seconds')
            
            # Save audio to file
            output_file = 'myca_response.wav'
            with wave.open(output_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                audio_int16 = (total_audio * 32767).astype(np.int16)
                wf.writeframes(audio_int16.tobytes())
            print(f'Audio saved to: {output_file}')
        
        if audio_bytes_received > 0 and len(text_received) > 0:
            print('=' * 60)
            print('SUCCESS: Full duplex conversation working!')
            print('=' * 60)
            return True
        else:
            print('WARNING: Limited response received')
            return False


if __name__ == '__main__':
    try:
        result = asyncio.run(test_conversation())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)
