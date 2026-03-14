#!/usr/bin/env python3
"""Quick Proxmox diagnostic - storage and VM 103 config."""
import os
from pathlib import Path
import paramiko

REPO = Path(__file__).resolve().parent.parent
for f in (REPO / ".credentials.local", REPO.parent / "website" / ".credentials.local"):
    if f.exists():
        for line in f.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))
p = os.environ.get("PROXMOX202_PASSWORD") or os.environ.get("PROXMOX_PASSWORD") or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.202", username="root", password=p, timeout=15)
for cmd in ["pvesm status", "qm config 103"]:
    print("---", cmd, "---")
    i, o, e = ssh.exec_command(cmd)
    print(o.read().decode())
    err = e.read().decode()
    if err:
        print(err)
ssh.close()
