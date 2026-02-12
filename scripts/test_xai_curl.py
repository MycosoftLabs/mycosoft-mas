#!/usr/bin/env python3
"""Test xAI API directly from VM using curl"""

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
stdin, stdout, stderr = client.exec_command('docker exec myca-orchestrator-new printenv XAI_API_KEY', timeout=10)
xai_key = stdout.read().decode('utf-8', errors='replace').strip()
print(f"xAI key length: {len(xai_key)}")

# Test xAI API directly (uses OpenAI-compatible format)
cmd = f'''curl -s 'https://api.x.ai/v1/chat/completions' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer {xai_key}' \\
  -d '{{"model":"grok-beta","max_tokens":100,"messages":[{{"role":"user","content":"Say hello in one sentence."}}]}}' \\
  --max-time 30'''

print("\nTesting xAI (Grok) API directly via curl...")
stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
output = stdout.read().decode('utf-8', errors='replace')
output = ''.join(c if ord(c) < 128 else '?' for c in output)
print(f"Response: {output[:1500]}")

client.close()
