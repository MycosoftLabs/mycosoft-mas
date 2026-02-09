#!/usr/bin/env python3
"""Patch bridge to add audio logging"""

import re

BRIDGE_PATH = r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\services\personaplex-local\personaplex_bridge_nvidia.py"

with open(BRIDGE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Find the audio handling section and add logging
old_audio = '''                                if kind == 1:  # Audio
                                    audio_recv += 1
                                    await websocket.send_bytes(msg.data)'''

new_audio = '''                                if kind == 1:  # Audio
                                    audio_recv += 1
                                    if audio_recv <= 10 or audio_recv % 50 == 0:
                                        logger.info(f"[{session_id[:8]}] Audio packet #{audio_recv}: {len(msg.data)} bytes")
                                    await websocket.send_bytes(msg.data)'''

if old_audio in content:
    content = content.replace(old_audio, new_audio)
    with open(BRIDGE_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched bridge with audio logging")
else:
    # Check if already patched
    if "Audio packet #" in content:
        print("Bridge already has audio logging")
    else:
        print("Could not find audio section to patch")
