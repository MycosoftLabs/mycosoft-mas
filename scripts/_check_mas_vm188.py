#!/usr/bin/env python3
"""Quick MAS diagnostic on VM 188 via SSH."""
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

import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=15)

def run(cmd):
    _, out, err = c.exec_command(cmd)
    return out.read().decode("utf-8", "replace"), err.read().decode("utf-8", "replace")

def safe_print(s):
    print((s or "").encode("ascii", "replace").decode())

print("=== MAS status ===")
o, e = run("systemctl status mas-orchestrator --no-pager 2>&1 | head -25")
safe_print(o or e)

print("=== Ports 8000-8001, 5678 ===")
o, e = run("ss -tlnp 2>/dev/null")
for line in (o or e).splitlines():
    if "800" in line or "5678" in line:
        safe_print(line)

print("=== MAS health ===")
o, e = run("curl -s -m 10 http://127.0.0.1:8001/health 2>&1")
safe_print(o or e or "(no response)")

print("=== sync-both response ===")
o, e = run("curl -s -m 30 -X POST http://127.0.0.1:8001/api/workflows/sync-both -H 'Content-Type: application/json' -d '{}' 2>&1")
safe_print(o or e or "(no response)")

print("=== MAS journal (last 40 lines) ===")
o, e = run("journalctl -u mas-orchestrator -n 40 --no-pager 2>&1")
safe_print(o or e)

c.close()
