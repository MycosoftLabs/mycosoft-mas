#!/usr/bin/env python3
"""Try SSH to sandbox at known IPs; print hostname and primary IPv4."""
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

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
if not pw:
    print("no VM password")
    sys.exit(1)

cmd = "hostname; ip -4 route show default; ip -4 -br addr show scope global"
for host in ("192.168.0.248", "192.168.0.187"):
    print(f"\n--- {host} ---")
    try:
        s = paramiko.SSHClient()
        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        s.connect(host, username="mycosoft", password=pw, timeout=15)
        i, o, e = s.exec_command(cmd, timeout=20)
        print(o.read().decode(errors="replace"))
        err = e.read().decode(errors="replace")
        if err.strip():
            print("stderr:", err)
        s.close()
    except Exception as ex:
        print("FAIL:", ex)
