#!/usr/bin/env python3
"""Check MAS container environment"""

import paramiko
import sys
import os

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

stdin, stdout, stderr = client.exec_command(
    'docker exec myca-orchestrator-new printenv | grep -E "API_KEY|ANTHROPIC|OPENAI|GROQ|GEMINI|XAI"',
    timeout=30
)
print("Environment variables in container:")
print(stdout.read().decode('utf-8', errors='replace'))

client.close()
