"""One-shot: from dev PC SSH to MAS 188 and probe connectivity to Sandbox 187."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko


def main() -> None:
    mas_root = Path(__file__).resolve().parent.parent
    for line in (mas_root / ".credentials.local").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not pw:
        print("no password", file=sys.stderr)
        sys.exit(1)

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(
        "192.168.0.188",
        username="mycosoft",
        password=pw,
        timeout=25,
        allow_agent=False,
        look_for_keys=False,
    )

    def run(cmd: str) -> tuple[int, str, str]:
        stdin, stdout, stderr = c.exec_command(cmd, timeout=45)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        ec = stdout.channel.recv_exit_status()
        return ec, out, err

    for cmd in (
        "echo HOST=$(hostname); ip -br a | head -8",
        "ip route | head -10",
        "ping -c 2 -W 2 192.168.0.187 2>&1; echo ping_exit=$?",
        "command -v nc >/dev/null && nc -zv -w 3 192.168.0.187 22 2>&1 || echo nc_missing_or_failed",
    ):
        ec, o, e = run(cmd)
        print("===", cmd, "ec=", ec, "===")
        print(o)
        if e.strip():
            print("stderr:", e)
    c.close()


if __name__ == "__main__":
    main()
