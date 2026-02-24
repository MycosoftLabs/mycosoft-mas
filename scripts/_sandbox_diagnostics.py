#!/usr/bin/env python3
"""Run diagnostics on Sandbox VM 187. Loads creds from .credentials.local."""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS_FILE = REPO_ROOT / ".credentials.local"
if not CREDS_FILE.exists():
    print("ERROR: .credentials.local not found")
    sys.exit(1)
for line in CREDS_FILE.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()
password = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
if not password:
    print("ERROR: VM_SSH_PASSWORD or VM_PASSWORD not set")
    sys.exit(1)

try:
    import paramiko
except ImportError:
    print("ERROR: paramiko not installed")
    sys.exit(1)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.187", username="mycosoft", password=password, timeout=30)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    return out, err, code

cmds = [
    'docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"',
    'docker images mycosoft-always-on-mycosoft-website --format "{{.Tag}} {{.CreatedAt}}"',
    "ps aux | grep -E 'docker build|rebuild_sandbox' | grep -v grep || true",
    "docker container prune -f",
    'curl -s -o /dev/null -w "%{http_code}" http://localhost:3000',
]
for i, cmd in enumerate(cmds, 1):
    print(f"--- CMD {i} ---")
    out, err, code = run(cmd)
    print(out if out else "(empty)")
    if err and code != 0:
        print("stderr:", err[:500])
    print()

client.close()
print("Done.")
