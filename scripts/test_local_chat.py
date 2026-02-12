#!/usr/bin/env python3
"""Test chat from within MAS VM"""

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

# Test chat from within VM
cmd = '''curl -s -X POST http://127.0.0.1:8000/api/myca/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello MYCA, are you alive?"}' \
  --max-time 30 \
  -w "\\n\\nHTTP_CODE: %{http_code}"'''

print("Testing chat from within VM...")
stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
output = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')

print("STDOUT:", output[:2000] if output else "(empty)")
print("STDERR:", err[:500] if err else "(none)")

# Also get latest logs
print("\n=== Latest logs ===")
stdin, stdout, stderr = client.exec_command('docker logs myca-orchestrator-new 2>&1 | tail -30', timeout=30)
output = stdout.read().decode('utf-8', errors='replace')
output = ''.join(c if ord(c) < 128 else '?' for c in output)
print(output)

client.close()
