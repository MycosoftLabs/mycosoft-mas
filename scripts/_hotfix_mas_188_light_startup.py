#!/usr/bin/env python3
"""Hotfix MAS VM 188 startup profile for immediate API recovery.

Sets STATIC_BUILD_ON_STARTUP=0 in remote .env, restarts mas-orchestrator,
then verifies /live and /api/myca/ping.
"""
from __future__ import annotations

import os
import time
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
        raise RuntimeError("VM password is missing in .credentials.local")
    return password


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 180) -> tuple[int, str, str]:
    _stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def main() -> int:
    password = load_password()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.188", username="mycosoft", password=password, timeout=45)

    commands = [
        "cp /home/mycosoft/mycosoft/mas/.env /home/mycosoft/mycosoft/mas/.env.bak_hotfix_$(date +%Y%m%d_%H%M%S)",
        (
            "if grep -q '^STATIC_BUILD_ON_STARTUP=' /home/mycosoft/mycosoft/mas/.env; then "
            "sed -i \"s/^STATIC_BUILD_ON_STARTUP=.*/STATIC_BUILD_ON_STARTUP=0/\" /home/mycosoft/mycosoft/mas/.env; "
            "else echo 'STATIC_BUILD_ON_STARTUP=0' >> /home/mycosoft/mycosoft/mas/.env; fi"
        ),
        "sudo -S systemctl restart mas-orchestrator",
        "sleep 10",
        "curl -sS -m 12 -w '\\nCODE:%{http_code}\\n' http://127.0.0.1:8001/live || true",
        "curl -sS -m 12 -w '\\nCODE:%{http_code}\\n' http://127.0.0.1:8001/api/myca/ping || true",
    ]

    for idx, cmd in enumerate(commands, start=1):
        if cmd.startswith("sudo -S"):
            chan = ssh.get_transport().open_session()
            chan.get_pty()
            chan.exec_command(cmd)
            chan.send(password + "\n")
            while not chan.exit_status_ready():
                time.sleep(0.25)
            rc = chan.recv_exit_status()
            print(f"\n[{idx}] {cmd}\nrc={rc}")
            chan.close()
            continue

        rc, out, err = run(ssh, cmd, timeout=180)
        print(f"\n[{idx}] {cmd}\nrc={rc}\n{out[:2000]}")
        if err.strip():
            print("stderr:", err[:500])

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
