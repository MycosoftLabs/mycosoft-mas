#!/usr/bin/env python3
"""Pull latest MAS code on VM 188 and restart mas-orchestrator."""
import os
from pathlib import Path

creds = Path(__file__).resolve().parent.parent / ".credentials.local"
pw = ""
if creds.exists():
    for line in creds.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                pw = v.strip()
                break
pw = pw or os.environ.get("VM_PASSWORD", "")
if not pw:
    print("Set VM_PASSWORD")
    exit(1)

import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=15)

def run(cmd, sudo=False):
    if sudo:
        cmd = f"echo {repr(pw)} | sudo -S bash -c {repr(cmd)}"
    _, out, err = c.exec_command(cmd)
    return out.read().decode("utf-8", "replace"), err.read().decode("utf-8", "replace")

mas_dir = "/home/mycosoft/mycosoft/mas"
print("Pulling latest code...")
o, e = run(f"cd {mas_dir} && git fetch origin && git reset --hard origin/main")
print(o or e)
if "error" in (o + e).lower() and "Could not resolve" not in (o + e):
    print("WARN: git may have had issues")

print("Restarting mas-orchestrator...")
o, e = run("systemctl daemon-reload && systemctl restart mas-orchestrator", sudo=True)
print("Restart:", "ok" if not e.strip() else e[:300])

print("Waiting 30s for MAS to start...")
import time
time.sleep(30)

print("Health check...")
o, e = run("curl -s -m 10 http://127.0.0.1:8001/health 2>&1")
print(o or e or "(no response)")

c.close()
print("Done.")
