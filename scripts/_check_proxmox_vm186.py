#!/usr/bin/env python3
"""Check if VM 186 exists and its status on Proxmox. Run from MAS repo."""
import os
import sys
from pathlib import Path

for f in (Path(__file__).parent.parent / ".credentials.local",
          Path(__file__).parent.parent.parent / "website" / ".credentials.local"):
    if f.exists():
        for line in f.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))

import paramiko

PROXMOX = "192.168.0.202"
PW = os.getenv("PROXMOX202_PASSWORD") or os.getenv("PROXMOX_PASSWORD") or os.getenv("VM_PASSWORD")

if not PW:
    print("No Proxmox password in credentials")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect(PROXMOX, username="root", password=PW, timeout=10)
    _, out, _ = ssh.exec_command("qm list")
    print("=== All VMs ===")
    print(out.read().decode())
    _, out2, err = ssh.exec_command("qm status 186 2>&1")
    code = out2.channel.recv_exit_status()
    status = out2.read().decode() + err.read().decode()
    print("=== VM 186 status ===")
    print(status.strip() or "(no output)")
    ssh.close()
except Exception as e:
    print("Error:", e)
    sys.exit(1)
