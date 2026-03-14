#!/usr/bin/env python3
"""Execute a single command with sudo over SSH using VM creds."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko


def load_password() -> str:
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if creds.exists():
        for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in {"VM_PASSWORD", "VM_SSH_PASSWORD"} and v.strip():
                pw = v.strip()
                break
    return pw


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: _remote_exec_sudo.py <host> <command...>")
        return 2
    host = sys.argv[1]
    cmd = " ".join(sys.argv[2:])
    pw = load_password()
    if not pw:
        print("ERROR: missing VM password")
        return 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username="mycosoft", password=pw, timeout=20)
    try:
        stdin, stdout, stderr = ssh.exec_command(f"sudo -S bash -lc \"{cmd}\"", get_pty=True, timeout=1800)
        stdin.write(pw + "\n")
        stdin.flush()
        code = stdout.channel.recv_exit_status()
        out = (stdout.read() + stderr.read()).decode("utf-8", errors="replace")
        # Avoid echoing password prompt artifacts.
        cleaned = "\n".join(
            ln for ln in out.splitlines() if "password for" not in ln.lower() and ln.strip() != pw
        )
        safe = cleaned.strip().encode("ascii", errors="replace").decode("ascii", errors="replace")
        print(safe)
        return code
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
