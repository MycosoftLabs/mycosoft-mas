#!/usr/bin/env python3
"""Full MAS rebuild: git pull, docker build, restart with env-file."""
import os
import paramiko
import time
from pathlib import Path

creds = Path(__file__).parent.parent / ".credentials.local"
for line in creds.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

pw = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.188", username="mycosoft", password=pw, timeout=30)
ENV_PATH = "/home/mycosoft/mycosoft/mas/.env"

def run(cmd, timeout=600):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    combined = (out + err).strip()
    for line in combined.splitlines()[-20:]:
        print(f"  {line}")
    return combined, rc

print("=== Git pull latest ===")
run("cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main && echo PULL_OK")

print("\n=== Docker build ===")
run("cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest --no-cache . 2>&1 | tail -10", timeout=600)

print("\n=== Restart container ===")
run("docker stop myca-orchestrator-new 2>/dev/null; docker rm myca-orchestrator-new 2>/dev/null; echo STOPPED")
out, rc = run(
    f"docker run -d --name myca-orchestrator-new --restart unless-stopped "
    f"-p 8001:8000 --env-file {ENV_PATH} mycosoft/mas-agent:latest",
    timeout=30,
)
print(f"Started: rc={rc}")

print("\n=== Waiting 20s for startup ===")
time.sleep(20)

print("\n=== Health check ===")
out, _ = run("curl -s http://localhost:8001/health | head -c 200")

print("\n=== Test: chula vista temperature ===")
out, _ = run(
    "curl -s -X POST http://localhost:8001/api/myca/chat "
    "-H 'Content-Type: application/json' "
    "-d '{\"message\": \"what is the temperature outside in chula vista right now\", \"session_id\": \"prod-test\", \"context\": {}}' "
    "--max-time 30",
    timeout=35,
)

client.close()
print("\nDone.")
