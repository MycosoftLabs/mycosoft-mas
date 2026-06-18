#!/usr/bin/env python3
"""Git pull MAS on 188 (PVE) and MINDEX on 189 (SSH)."""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from load_vm_credentials import load_vm_credentials


def pve188(script: str) -> str:
    pw = os.environ.get("PROXMOX202_PASSWORD") or os.environ.get("PROXMOX_PASSWORD", "")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.202", username="root", password=pw, timeout=20)
    b64 = base64.b64encode(script.encode()).decode()
    _, o, e = ssh.exec_command(
        f"qm guest exec 188 -- bash -lc 'echo {b64} | base64 -d | bash'",
        timeout=180,
    )
    raw = (o.read() + e.read()).decode(errors="replace")
    ssh.close()
    try:
        data = json.loads(raw)
        return (data.get("out-data") or "") + (data.get("err-data") or "")
    except json.JSONDecodeError:
        return raw


def ssh189(cmd: str) -> str:
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.189", username="root", password=pw, timeout=20)
    _, o, e = ssh.exec_command(cmd, timeout=180)
    out = (o.read() + e.read()).decode(errors="replace")
    ssh.close()
    return out


def main() -> int:
    load_vm_credentials()
    print("=== MAS 188 git pull ===")
    print(
        pve188(
            """
sudo -u mycosoft bash -lc 'cd /home/mycosoft/mycosoft/mas && git fetch origin main && git reset --hard origin/main && git log -1 --oneline'
"""
        )
    )
    print("=== MINDEX 189 git pull ===")
    print(
        ssh189(
            """
sudo -u mycosoft bash -lc 'cd /home/mycosoft/mindex && git fetch origin main && git reset --hard origin/main && git log -1 --oneline'
docker restart mindex-api
sleep 8
curl -s http://localhost:8000/health
"""
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
