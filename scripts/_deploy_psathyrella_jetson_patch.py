#!/usr/bin/env python3
"""Hot-patch Psathyrella jetson forward files on MAS 188 and restart orchestrator."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent


def load_creds() -> str:
    creds = REPO / ".credentials.local"
    for line in creds.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        raise SystemExit("No VM_PASSWORD")
    return pw


def main() -> None:
    pw = load_creds()
    user = os.environ.get("VM_SSH_USER", "mycosoft")
    remote_base = "/home/mycosoft/mycosoft/mas"
    files = [
        "mycosoft_mas/devices/psathyrella/jetson_forward.py",
        "mycosoft_mas/devices/psathyrella/command_handler.py",
        "mycosoft_mas/core/routers/device_registry_api.py",
    ]

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.188", username=user, password=pw, timeout=45)

    sftp = ssh.open_sftp()
    for rel in files:
        local = REPO / rel
        remote = f"{remote_base}/{rel.replace(chr(92), '/')}"
        sftp.put(str(local), remote)
        print(f"uploaded {rel}")
    sftp.close()

    ch = ssh.get_transport().open_session()
    ch.get_pty()
    ch.exec_command("sudo -S systemctl restart mas-orchestrator")
    ch.send(pw + "\n")
    for _ in range(120):
        if ch.exit_status_ready():
            break
        time.sleep(0.25)
    ch.close()

    time.sleep(10)
    _, stdout, _ = ssh.exec_command("curl -s http://127.0.0.1:8001/health")
    print(stdout.read().decode())
    ssh.close()


if __name__ == "__main__":
    main()
