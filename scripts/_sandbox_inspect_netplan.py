#!/usr/bin/env python3
"""Inspect netplan on sandbox (connect via SANDBOX_SSH_HOST or 248 then 187)."""
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
hosts = [
    os.environ.get("SANDBOX_SSH_HOST", "").strip(),
    "192.168.0.248",
    "192.168.0.187",
]
hosts = [h for h in hosts if h]

def main() -> None:
    if not pw:
        print("no VM password")
        sys.exit(1)
    cmd = "ls -la /etc/netplan/ 2>&1; echo '---'; for f in /etc/netplan/*.yaml /etc/netplan/*.yml; do [ -f \"$f\" ] && echo \"=== $f ===\" && cat \"$f\"; done 2>&1"
    for host in hosts:
        print(f"\n===== {host} =====")
        try:
            s = paramiko.SSHClient()
            s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            s.connect(host, username="mycosoft", password=pw, timeout=15)
            i, o, e = s.exec_command(cmd, timeout=30)
            print(o.read().decode(errors="replace"))
            err = e.read().decode(errors="replace")
            if err.strip():
                print("stderr:", err)
            s.close()
            return
        except Exception as ex:
            print("FAIL:", ex)


if __name__ == "__main__":
    main()
