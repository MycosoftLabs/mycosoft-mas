#!/usr/bin/env python3
"""From Proxmox root SSH: ping 187, qm config 103, qm list, optional guest agent."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent

for f in (REPO / ".credentials.local", REPO.parent / "website" / ".credentials.local"):
    if f.exists():
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.strip().startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))

p = (
    os.environ.get("PROXMOX202_PASSWORD")
    or os.environ.get("PROXMOX_PASSWORD")
    or os.environ.get("VM_PASSWORD")
    or os.environ.get("VM_SSH_PASSWORD")
)
if not p:
    print("ERROR: no Proxmox password")
    sys.exit(1)

cmds = [
    "echo '=== ping 187 ===' && ping -c 3 -W 2 192.168.0.187 2>&1; echo exit=$?",
    "echo '=== ping 188 ===' && ping -c 2 -W 2 192.168.0.188 2>&1; echo exit=$?",
    "echo '=== ip neigh 187 ===' && ip neigh show 192.168.0.187 2>&1 || true",
    "echo '=== qm config 103 (net/ip) ===' && qm config 103 2>&1 | grep -E '^(name|net|ipconfig|agent)' || qm config 103 2>&1 | head -40",
    "echo '=== qm list ===' && qm list",
    "echo '=== guest agent network (may fail) ===' && qm guest cmd 103 network-get-interfaces 2>&1 || true",
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.202", username="root", password=p, timeout=25)
for cmd in cmds:
    print("\n" + "=" * 60)
    i, o, e = ssh.exec_command(cmd, timeout=90)
    out = o.read().decode(errors="replace")
    err = e.read().decode(errors="replace")
    print(out)
    if err.strip():
        print("stderr:", err)
ssh.close()
