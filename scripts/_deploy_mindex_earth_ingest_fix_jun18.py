#!/usr/bin/env python3
"""Deploy fixed earth.py ingest SQL to MINDEX 189."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
MINDEX_ROOT = ROOT.parent.parent / "MINDEX" / "mindex"
LOCAL = MINDEX_ROOT / "mindex_api" / "routers" / "earth.py"
REMOTE_HOST_PATH = "/home/mycosoft/mindex/mindex_api/routers/earth.py"

sys.path.insert(0, str(ROOT / "scripts"))
from load_vm_credentials import load_vm_credentials


def main() -> int:
    load_vm_credentials()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.189", username="root", password=pw, timeout=20)

    sftp = ssh.open_sftp()
    sftp.put(str(LOCAL), REMOTE_HOST_PATH)
    sftp.close()
    print(f"uploaded -> {REMOTE_HOST_PATH}")

    cmds = [
        "docker restart mindex-api",
        "sleep 10",
        "docker ps --filter name=mindex-api --format '{{.Status}}'",
        "curl -s http://localhost:8000/health | head -c 200",
    ]
    for cmd in cmds:
        _, o, e = ssh.exec_command(cmd, timeout=120)
        out = (o.read() + e.read()).decode(errors="replace")
        print(f"$ {cmd}\n{out.strip()}")

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
