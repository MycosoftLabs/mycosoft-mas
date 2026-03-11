#!/usr/bin/env python3
"""Quick check: is ASANA_PAT set on VM 191?"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

creds = {}
for f in [REPO / ".credentials.local", Path.home() / ".mycosoft-credentials"]:
    if f.exists():
        for line in f.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip()
        break

pw = creds.get("VM_SSH_PASSWORD") or creds.get("VM_PASSWORD") or os.environ.get("VM_PASSWORD")
if not pw:
    print("No VM password")
    sys.exit(1)

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.191", username="mycosoft", password=pw, timeout=15)
_, out, _ = ssh.exec_command("grep -E '^ASANA_PAT=' /opt/myca/.env 2>/dev/null | wc -c")
n = int(out.read().decode().strip())
print("ASANA_PAT length on VM:", n, "(0=missing/empty)")
ssh.close()
