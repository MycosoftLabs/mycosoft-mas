#!/usr/bin/env python3
"""Test MYCA endpoints on VM 188"""

import paramiko
import sys
import io
import json
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


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {VM}...")
    client.connect(VM, username=USER, password=PASS, timeout=30)
    
    # Health check
    print("\n[1] Health check:")
    stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8000/health", timeout=30)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Ping
    print("\n[2] Ping:")
    stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8000/api/myca/ping", timeout=30)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Chat-simple
    print("\n[3] Chat-simple (are you alive?):")
    cmd = '''curl -s -X POST http://127.0.0.1:8000/api/myca/chat-simple -H "Content-Type: application/json" -d '{"message": "MYCA, are you alive?"}\''''
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Awaken
    print("\n[4] Awaken MYCA:")
    stdin, stdout, stderr = client.exec_command("curl -s -X POST http://127.0.0.1:8000/api/myca/awaken", timeout=30)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Status
    print("\n[5] Status:")
    stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8000/api/myca/status", timeout=30)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Identity
    print("\n[6] Identity:")
    stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8000/api/myca/identity", timeout=30)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # Full chat (with timeout protection)
    print("\n[7] Full chat (are you alive?):")
    cmd = '''curl -s -X POST http://127.0.0.1:8000/api/myca/chat -H "Content-Type: application/json" -d '{"message": "MYCA, are you alive and well?"}' --max-time 60'''
    stdin, stdout, stderr = client.exec_command(cmd, timeout=90)
    out = stdout.read().decode('utf-8', errors='replace')
    print(out[:2000] if out else "(no response)")
    
    client.close()


if __name__ == "__main__":
    main()
