#!/usr/bin/env python3
"""One-off MAS deploy to VM 192.168.0.188. Loads credentials from .credentials.local."""

import os
import sys
from pathlib import Path

# Load credentials
creds_file = Path(__file__).parent / ".credentials.local"
if not creds_file.exists():
    print("ERROR: .credentials.local not found")
    sys.exit(1)
for line in creds_file.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
if not password:
    print("ERROR: VM_PASSWORD not set in .credentials.local")
    sys.exit(1)

import paramiko

host = "192.168.0.188"
user = "mycosoft"

cmds = [
    "cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main",
    "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest --no-cache .",
    "docker stop myca-orchestrator-new 2>/dev/null || true",
    "docker rm myca-orchestrator-new 2>/dev/null || true",
    "docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 mycosoft/mas-agent:latest",
]

print(f"Connecting to {user}@{host}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=60)
print("Connected.\n")

for i, cmd in enumerate(cmds, 1):
    print(f"--- Step {i}: {cmd[:80]}{'...' if len(cmd) > 80 else ''}")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=False)
    # Build commands can take a long time - wait for completion
    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        # For long output (e.g. docker build), show last 50 lines
        lines = out.split("\n")
        if len(lines) > 50:
            print("\n".join(lines[-50:]))
        else:
            print(out)
    if err:
        print(err, file=sys.stderr)
    print(f"[exit code {rc}]\n")
    if rc != 0:
        print(f"FAILED at step {i}")
        ssh.close()
        sys.exit(1)

# Verify (container may take 30-60s to be ready; retry a few times)
print("--- Verifying health...")
for attempt in range(1, 7):
    stdin, stdout, stderr = ssh.exec_command("curl -s --connect-timeout 10 http://localhost:8001/health")
    rc = stdout.channel.recv_exit_status()
    body = stdout.read().decode("utf-8", errors="replace").strip()
    if rc == 0 and body and "mas" in body.lower():
        print(body)
        print(f"\n[OK] MAS deployed and healthy on 192.168.0.188:8001 (attempt {attempt})")
        ssh.close()
        sys.exit(0)
    if attempt < 6:
        stdin, stdout, stderr = ssh.exec_command("sleep 10")
        stdout.channel.recv_exit_status()
ssh.close()
print(body if body else "(no response)")
print(f"\n[WARN] Health check did not pass after 6 attempts (rc={rc})")
sys.exit(1)
