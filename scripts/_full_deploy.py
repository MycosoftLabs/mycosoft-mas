#!/usr/bin/env python3
"""Full MAS Deployment - Pull code, rebuild Docker, restart container"""
import paramiko
import os
import time

VM_IP = "192.168.0.188"
VM_USER = "mycosoft"
VM_PASS = os.environ.get("VM_PASSWORD", "Mushroom1!Mushroom1!")

def run_cmd(ssh, cmd, timeout=600, show=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    if show:
        for line in (output + error).strip().split('\n')[:30]:
            if line.strip():
                print(f"  {line}")
    return output + error

def run_sudo(ssh, cmd, password, timeout=120, show=True):
    full_cmd = f"echo '{password}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout, get_pty=True)
    output = stdout.read().decode('utf-8', errors='ignore')
    if show:
        for line in output.strip().split('\n')[:30]:
            if line.strip() and 'password' not in line.lower():
                print(f"  {line}")
    return output

print("=" * 70)
print("FULL MAS DEPLOYMENT")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("\n[1] Connecting to VM...")
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
print("  Connected")

print("\n[2] Pulling latest code from GitHub...")
output = run_cmd(ssh, "cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main")
print("  Code updated")

print("\n[3] Stopping container...")
run_sudo(ssh, "docker stop myca-orchestrator-new 2>/dev/null || true", VM_PASS, show=False)
run_sudo(ssh, "docker rm myca-orchestrator-new 2>/dev/null || true", VM_PASS, show=False)
print("  Container stopped")

print("\n[4] Building Docker image (this takes ~3 minutes)...")
output = run_cmd(ssh, "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest --no-cache . 2>&1 | tail -20", timeout=600)
print("  Build complete")

print("\n[5] Starting container...")
run_sudo(ssh, """docker run -d \
    --name myca-orchestrator-new \
    --restart unless-stopped \
    -p 8001:8000 \
    --env-file /home/mycosoft/mycosoft/mas/.env \
    mycosoft/mas-agent:latest""", VM_PASS)
print("  Container started")

print("\n[6] Waiting 15s for startup...")
time.sleep(15)

print("\n[7] Checking container status...")
output = run_cmd(ssh, "docker ps --filter name=myca-orchestrator-new --format '{{.Names}}: {{.Status}}'")

print("\n[8] Checking logs...")
output = run_cmd(ssh, "docker logs myca-orchestrator-new --tail 20 2>&1")

ssh.close()

print("\n[9] Testing API endpoint...")
import urllib.request
import json
try:
    with urllib.request.urlopen(f"http://{VM_IP}:8001/health", timeout=10) as resp:
        data = json.loads(resp.read().decode())
        print(f"  Status: {data.get('status', 'OK')}")
        print("  API is responding!")
except Exception as e:
    print(f"  API check failed: {e}")
    print("  Container may still be starting up...")

print("\n" + "=" * 70)
print("DEPLOYMENT COMPLETE")
print("=" * 70)
print(f"""
MAS VM: {VM_IP}
API: http://{VM_IP}:8001/health
Docs: http://{VM_IP}:8001/docs

Test MYCA:
  curl -X POST http://{VM_IP}:8001/api/myca/route \\
    -H "Content-Type: application/json" \\
    -d '{{"message": "Hello MYCA"}}'
""")
