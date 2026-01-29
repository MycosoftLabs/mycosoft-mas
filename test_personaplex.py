#!/usr/bin/env python3
"""Test PersonaPlex full-duplex audio pipeline."""

import asyncio
import websockets
import numpy as np
import sphn

async def test_full_duplex():
    uri = 'ws://localhost:8998/api/chat?voice_prompt=NATF2.pt&text_prompt=You%20are%20MYCA'
    print('Connecting to PersonaPlex...')
    
    async with websockets.connect(uri, close_timeout=5) as ws:
        # Wait for handshake
        msg = await asyncio.wait_for(ws.recv(), timeout=60)
        if msg[0] != 0:
            print('No handshake')
            return False
        print('Handshake OK, server ready!')
        
        # Create Opus encoder for sending audio
        sample_rate = 24000
        opus_writer = sphn.OpusStreamWriter(sample_rate)
        
        # Generate 2 seconds of silence as test audio
        silence = np.zeros(sample_rate * 2, dtype=np.float32)
        opus_data = opus_writer.append_pcm(silence)
        
        if opus_data and len(opus_data) > 0:
            # Send audio with kind=1 prefix
            await ws.send(bytes([1]) + opus_data)
            print(f'Sent {len(opus_data)} bytes of Opus audio')
        
        # Listen for responses
        text_received = ''
        audio_received = 0
        
        print('Listening for responses...')
        for _ in range(100):  # Listen for ~20 seconds
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.2)
                kind = msg[0]
                if kind == 1:  # Audio
                    audio_received += len(msg) - 1
                elif kind == 2:  # Text
                    text = msg[1:].decode('utf-8')
                    text_received += text
                    print(f'{text}', end='', flush=True)
            except asyncio.TimeoutError:
                continue
        
        print(f'\n\nSUMMARY:')
        print(f'  Audio received: {audio_received} bytes')
        print(f'  Text received: "{text_received}"')
        
        if audio_received > 0:
            print('\nSUCCESS: Full duplex audio working!')
            return True
        else:
            print('\nWARNING: No audio received (model may need more input)')
            return False

if __name__ == '__main__':
    asyncio.run(test_full_duplex())
