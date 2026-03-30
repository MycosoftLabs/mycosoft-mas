#!/usr/bin/env python3
"""One-shot: hostname, IPs, sandbox netplan on lab VMs. No secrets in output."""
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


def run(host: str, cmd: str) -> tuple[str, str]:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username="mycosoft", password=pw, timeout=15, banner_timeout=15, auth_timeout=15)
    _, out, err = c.exec_command(cmd, timeout=30)
    o = out.read().decode(errors="replace")
    e = err.read().decode(errors="replace")
    c.close()
    return o, e


def main() -> int:
    for label, ip in [
        ("SANDBOX", "192.168.0.187"),
        ("MAS", "192.168.0.188"),
        ("MINDEX", "192.168.0.189"),
        ("MYCA", "192.168.0.191"),
    ]:
        try:
            o, e = run(ip, "hostname; echo ---; ip -4 -br addr show 2>/dev/null | head -12")
            print(f"=== {label} {ip} ===")
            print(o.strip())
            if e.strip():
                print("stderr:", e.strip())
        except Exception as ex:
            print(f"=== {label} {ip} FAIL === {ex}")

    try:
        o, _ = run(
            "192.168.0.187",
            "ls -la /etc/netplan 2>/dev/null; echo ---; "
            "f=/etc/netplan/99-mycosoft-static.yaml; "
            "if [ -f \"$f\" ]; then "
            "if [ -r \"$f\" ]; then cat \"$f\"; "
            "else echo \"99-mycosoft-static.yaml: present (root-only); sudo cat $f on host\"; fi; "
            "else echo NO_99_FILE; fi",
        )
        print("=== SANDBOX netplan ===")
        print(o.strip())
    except Exception as ex:
        print("=== SANDBOX netplan FAIL ===", ex)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
