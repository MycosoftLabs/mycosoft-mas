#!/usr/bin/env python3
"""Start website after reboot - Feb 6, 2026"""
import paramiko
import time
import requests
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load credentials from environment
VM_IP = os.environ.get("SANDBOX_VM_IP", "192.168.0.187")
VM_USER = os.environ.get("VM_USER", "mycosoft")
VM_PASS = os.environ.get("VM_PASSWORD")

if not VM_PASS:
    print("ERROR: VM_PASSWORD environment variable is not set.")
    print("Please set it before running this script:")
    print("  $env:VM_PASSWORD = 'your-password'  # PowerShell")
    print("  export VM_PASSWORD='your-password'  # Bash")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {VM_IP}...")
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
print("Connected!\n")

def run(cmd, timeout=60):
    print(f"[CMD] {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    stdout.channel.settimeout(timeout)
    try:
        out = stdout.read().decode('utf-8', errors='replace')
        if out.strip():
            print(out[:500])
        return out
    except:
        print("(timeout)")
        return ""

# Check Docker
print("=== Checking Docker ===")
result = run("docker ps")

if "CONTAINER ID" not in result:
    print("Docker not ready, waiting 30s...")
    time.sleep(30)
    result = run("docker ps")

# Check memory
print("\n=== Memory Status ===")
run("free -h")

# Pull latest code
print("\n=== Pulling Latest Code ===")
run("cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main", timeout=120)

# Start website
print("\n=== Starting Website ===")
result = run("cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1", timeout=300)

ssh.close()

# Wait for container to start
print("\n=== Waiting 90 seconds for website to start ===")
time.sleep(90)

# Test
print("\n=== Testing Endpoints ===")
tests = [
    'https://sandbox.mycosoft.com/api/mycobrain/health',
    'https://sandbox.mycosoft.com/api/health',
    'https://sandbox.mycosoft.com/'
]

for url in tests:
    try:
        r = requests.get(url, timeout=30)
        print(f"{url}: {r.status_code}")
        if r.status_code == 200 and 'mycobrain' in url:
            print(f"  Response: {r.json()}")
    except Exception as e:
        print(f"{url}: Error - {e}")

print("\nDone!")
