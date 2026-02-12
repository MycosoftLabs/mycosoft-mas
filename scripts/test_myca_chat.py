#!/usr/bin/env python3
"""Test MYCA chat and check logs"""

import paramiko
import requests
import threading
import time
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

# Send a test message
def send_chat():
    try:
        print("Sending chat request...")
        r = requests.post(
            f'http://{VM}:8000/api/myca/chat',
            json={'message': 'Hello MYCA, are you alive?'},
            timeout=30
        )
        print(f"Response: {r.status_code}")
        if r.ok:
            print(f"Reply: {r.text[:500]}")
        else:
            print(f"Error: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

# Start chat in background
t = threading.Thread(target=send_chat)
t.start()

# Wait a bit then check logs
time.sleep(5)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VM, username=USER, password=PASS, timeout=30)

stdin, stdout, stderr = client.exec_command(
    'docker logs myca-orchestrator-new 2>&1 | tail -50',
    timeout=30
)
print("\n=== CONTAINER LOGS ===")
print(stdout.read().decode('utf-8', errors='replace'))

client.close()

t.join(timeout=30)
