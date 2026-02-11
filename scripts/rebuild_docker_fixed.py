#!/usr/bin/env python3
"""Rebuild MAS Docker image - fixed version"""
import os
import time
import paramiko

MAS_VM_IP = "192.168.0.188"
MAS_VM_USER = "mycosoft"
MAS_VM_PASS = os.environ.get("VM_PASSWORD", "REDACTED_VM_SSH_PASSWORD")

def run_cmd(ssh, cmd, timeout=600):
    """Run command without sudo"""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    output = []
    while True:
        line = stdout.readline()
        if not line:
            break
        print(f"    {line.rstrip()}")
        output.append(line)
    return ''.join(output)

def run_sudo(ssh, cmd, password):
    """Execute with sudo"""
    full_cmd = f"echo '{password}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=120, get_pty=True)
    output = stdout.read().decode('utf-8', errors='ignore')
    return output

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(MAS_VM_IP, username=MAS_VM_USER, password=MAS_VM_PASS, timeout=30)

print("=" * 70)
print("REBUILD MAS DOCKER IMAGE")
print("=" * 70)

# Stop container
print("\n[1] Stopping container...")
run_sudo(ssh, "docker stop myca-orchestrator-new", MAS_VM_PASS)
run_sudo(ssh, "docker rm myca-orchestrator-new", MAS_VM_PASS)

# Build image
print("\n[2] Building Docker image...")
output = run_cmd(ssh, "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest --no-cache .")
print("[+] Build complete")

# Start container
print("\n[3] Starting container...")
output = run_sudo(ssh, """docker run -d \\
    --name myca-orchestrator-new \\
    --restart unless-stopped \\
    -p 8001:8000 \\
    --env-file /home/mycosoft/mycosoft/mas/.env \\
    mycosoft/mas-agent:latest""", MAS_VM_PASS)

print(f"[+] Container ID: {output.strip()[:12]}")

ssh.close()

print("\n[4] Waiting 20s for startup...")
time.sleep(20)

# Test
import urllib.request
import json

print("\n[5] Testing API...")
with urllib.request.urlopen(f"http://{MAS_VM_IP}:8001/health", timeout=15) as resp:
    data = json.loads(resp.read().decode())
    print(f"[+] Status: {data.get('status')}")

print("\n" + "=" * 70)
print("Test MYCA:")
print("""
  curl -X POST http://192.168.0.188:8001/api/myca/route \\
    -H "Content-Type: application/json" \\
    -d '{"message": "Tell me about Amanita muscaria"}'
""")
