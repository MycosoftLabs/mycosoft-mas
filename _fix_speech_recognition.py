#!/usr/bin/env python3
"""Fix the test-voice page to start speech recognition after handshake"""

page_path = r'c:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\app\test-voice\page.tsx'

with open(page_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the handshake handler and add startSpeechRecognition call
old_handshake = '''initDecoderWorker().catch(e => addLog("error", `Decoder init failed: ${e}`))
            startAudioCapture(ws)
            return'''

new_handshake = '''initDecoderWorker().catch(e => addLog("error", `Decoder init failed: ${e}`))
            startAudioCapture(ws)
            
            // CRITICAL: Start speech recognition for orchestrator integration
            // This transcribes user speech and sends to MYCA Orchestrator
            startSpeechRecognition(ws)
            addLog("info", "Speech recognition started - orchestrator connected!")
            return'''

if old_handshake in content:
    content = content.replace(old_handshake, new_handshake)
    print("Added startSpeechRecognition call after handshake")
else:
    print("Could not find handshake handler")

with open(page_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
