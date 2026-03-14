#!/usr/bin/env python3
"""SSH to Proxmox 202 as root and run showmount -e against NAS. One-off diagnostic."""
from __future__ import annotations

import os
from pathlib import Path

import paramiko


def main() -> None:
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    pw = os.environ.get("PROXMOX202_PASSWORD", "")
    if creds.exists():
        for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "PROXMOX202_PASSWORD" and v.strip():
                pw = v.strip()
                break

    if not pw:
        print("ERROR: PROXMOX202_PASSWORD not in .credentials.local or env")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.202", username="root", password=pw, timeout=15)
    try:
        _stdin, stdout, stderr = ssh.exec_command("showmount -e 192.168.0.105", timeout=10)
        out = (stdout.read() + stderr.read()).decode("utf-8", errors="replace")
        print(out.strip())
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
