#!/usr/bin/env python3
"""Test LLM directly from VM"""

import paramiko
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load credentials from environment
VM = os.environ.get("MAS_VM_IP", "192.168.0.188")
USER = os.environ.get("VM_USER", "mycosoft")
PASS = os.environ.get("VM_PASSWORD")

if not PASS:
    print("ERROR: VM_PASSWORD environment variable is not set.")
    print("Please set it before running this script:")
    print("  $env:VM_PASSWORD = 'your-password'  # PowerShell")
    print("  export VM_PASSWORD='your-password'  # Bash")
    sys.exit(1)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VM, username=USER, password=PASS, timeout=30)

# Test Gemini API directly
test_script = '''
python3 -c "
import os
import httpx
import json

gemini_key = os.getenv('GEMINI_API_KEY')
if not gemini_key:
    # Get from container
    import subprocess
    result = subprocess.run(['docker', 'exec', 'myca-orchestrator-new', 'printenv', 'GEMINI_API_KEY'], capture_output=True, text=True)
    gemini_key = result.stdout.strip()
    
print(f'Key found: {len(gemini_key) if gemini_key else 0} chars')

if gemini_key:
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}'
    payload = {
        'contents': [{'parts': [{'text': 'Say hello in one sentence.'}]}],
        'generationConfig': {'maxOutputTokens': 50}
    }
    try:
        r = httpx.post(url, json=payload, timeout=30)
        print(f'Status: {r.status_code}')
        print(f'Response: {r.text[:500]}')
    except Exception as e:
        print(f'Error: {e}')
" 2>&1
'''

print("Testing Gemini API directly...")
stdin, stdout, stderr = client.exec_command(test_script, timeout=60)
output = stdout.read().decode('utf-8', errors='replace')
output = ''.join(c if ord(c) < 128 else '?' for c in output)
print(output)

client.close()
