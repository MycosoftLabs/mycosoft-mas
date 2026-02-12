#!/usr/bin/env python3
"""Test LLM directly from VM using curl"""

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

# Get the API key first
stdin, stdout, stderr = client.exec_command('docker exec myca-orchestrator-new printenv GEMINI_API_KEY', timeout=10)
gemini_key = stdout.read().decode('utf-8', errors='replace').strip()
print(f"Gemini key length: {len(gemini_key)}")

# Test Gemini API directly
cmd = f'''curl -s 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}' \\
  -H 'Content-Type: application/json' \\
  -d '{{"contents":[{{"parts":[{{"text":"Say hello in one sentence."}}]}}],"generationConfig":{{"maxOutputTokens":50}}}}' \\
  --max-time 30'''

print("\nTesting Gemini API directly via curl...")
stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
output = stdout.read().decode('utf-8', errors='replace')
output = ''.join(c if ord(c) < 128 else '?' for c in output)
print(f"Response: {output[:1000]}")

client.close()
