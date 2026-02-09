#!/usr/bin/env python3
"""Start website after reboot - Feb 6, 2026"""
import paramiko
import time
import requests
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

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
