#!/usr/bin/env python3
"""Start website and tunnel - Feb 6, 2026"""
import paramiko
import time
import requests
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {VM_IP}...")
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
print("Connected!\n")

def run(cmd, timeout=120):
    print(f"[CMD] {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    stdout.channel.settimeout(timeout)
    try:
        out = stdout.read().decode('utf-8', errors='replace')
        if out.strip():
            print(out[:800])
        return out
    except:
        print("(timeout)")
        return ""

# Start website container
print("=== Starting Website Container ===")
run("docker start mycosoft-website 2>&1")
time.sleep(5)

# Check if running
print("\n=== Checking Website ===")
result = run("docker ps | grep mycosoft-website")

if "mycosoft-website" in result:
    print("Website container is running!")
else:
    # Try recreating it
    print("Container not running, recreating...")
    run("docker rm mycosoft-website 2>&1")
    run("cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1", timeout=300)
    time.sleep(10)
    run("docker ps | grep mycosoft-website")

# Start cloudflare tunnel
print("\n=== Looking for Cloudflare Tunnel ===")
run("docker ps -a | grep -i cloud")
run("docker ps -a | grep -i tunnel")

# Find and start tunnel
print("\n=== Checking for cloudflared ===")
result = run("which cloudflared || ls /usr/local/bin/cloudflared || ls /opt/cloudflared 2>&1")
result2 = run("docker images | grep -i cloudflare")

print("\n=== Port Status ===")
run("ss -tlnp | head -20")

print("\n=== Website Container Status ===")
run("docker ps | grep website")
run("docker logs mycosoft-website 2>&1 | tail -20")

ssh.close()

# Wait and test
print("\n=== Waiting 30 seconds ===")
time.sleep(30)

print("\n=== Testing ===")
try:
    r = requests.get('https://sandbox.mycosoft.com/', timeout=30)
    print(f"sandbox.mycosoft.com: {r.status_code}")
except Exception as e:
    print(f"Error: {e}")

try:
    r = requests.get('http://192.168.0.187:3000/', timeout=10)
    print(f"Direct IP:3000: {r.status_code}")
except Exception as e:
    print(f"Direct IP: {e}")

print("\nDone!")
