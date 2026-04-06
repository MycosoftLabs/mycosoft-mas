#!/usr/bin/env python3
"""Probe key MAS endpoints from inside VM 188."""
from __future__ import annotations

import os
from pathlib import Path

import paramiko


def load_password() -> str:
    creds_file = Path(__file__).resolve().parent.parent / ".credentials.local"
    for line in creds_file.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not password:
        raise RuntimeError("VM password missing")
    return password


def main() -> int:
    password = load_password()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.188", username="mycosoft", password=password, timeout=45)

    cmd = (
        "for u in /version /live /ready /health /api/myca/ping; do "
        "echo \"---${u}---\"; "
        "curl -sS -m 6 -w '\\nCODE:%{http_code}\\n' \"http://127.0.0.1:8001${u}\" || true; "
        "done"
    )
    _stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    print(stdout.read().decode("utf-8", errors="replace"))
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print("stderr:", err)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
