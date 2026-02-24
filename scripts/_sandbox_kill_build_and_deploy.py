#!/usr/bin/env python3
"""Kill orphan docker build on Sandbox VM, then run clean deploy via website _rebuild_sandbox."""
import os
import sys
from pathlib import Path

# Load credentials from MAS .credentials.local
MAS_ROOT = Path(__file__).resolve().parent.parent
CREDS = MAS_ROOT / ".credentials.local"
if CREDS.exists():
    for line in CREDS.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
os.environ.setdefault("VM_PASSWORD", os.environ.get("VM_SSH_PASSWORD", ""))

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.187", username="mycosoft", password=os.environ.get("VM_PASSWORD"), timeout=30)

print("Killing orphan docker build processes...")
stdin, stdout, stderr = client.exec_command(
    "pkill -9 -f 'docker build.*mycosoft-always-on-mycosoft-website' 2>/dev/null || true", timeout=30
)
stdout.channel.recv_exit_status()
import time
time.sleep(3)
stdin, stdout, stderr = client.exec_command("ps aux | grep -E 'docker build' | grep -v grep || true", timeout=10)
remaining = stdout.read().decode().strip()
client.close()
if remaining:
    print("WARN: Orphan build may still be running:\n", remaining)
else:
    print("Orphan build killed (or was already gone).")
print()

# Run _rebuild_sandbox from website repo
website_root = MAS_ROOT.parent / "WEBSITE" / "website"
if not website_root.exists():
    website_root = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
if not (website_root / "_rebuild_sandbox.py").exists():
    print("ERROR: _rebuild_sandbox.py not found in", website_root)
    sys.exit(1)

# Ensure creds are available for _rebuild_sandbox (it loads from env)
if not os.environ.get("VM_PASSWORD") and not os.environ.get("VM_SSH_PASSWORD"):
    print("ERROR: VM_PASSWORD not set")
    sys.exit(1)

print("Running _rebuild_sandbox.py...")
import subprocess
result = subprocess.run(
    [sys.executable, str(website_root / "_rebuild_sandbox.py")],
    cwd=str(website_root),
    env=os.environ.copy(),
)
sys.exit(result.returncode)
