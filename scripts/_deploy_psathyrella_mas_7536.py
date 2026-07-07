#!/usr/bin/env python3
"""Deploy latest psathyrella branch commit to MAS VM 188."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

COMMIT = "000412638"
BRANCH = "chore/license-notice-readme-sweep-jun25-2026"
HOST = "192.168.0.188"
USER = "mycosoft"
REPO = "/home/mycosoft/mycosoft/mas"


def load_credentials() -> str:
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if creds.exists():
        for line in creds.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
    if not pw:
        print("Missing VM_PASSWORD", file=sys.stderr)
        sys.exit(1)
    return pw


def main() -> int:
    pw = load_credentials()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=pw, timeout=30)

    def run(cmd: str, sudo: bool = False) -> tuple[int, str, str]:
        if sudo:
            cmd = f"echo {pw!r} | sudo -S bash -lc {cmd!r}"
        _, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        return stdout.channel.recv_exit_status(), out, err

    code, out, err = run(
        f"cd {REPO} && git fetch origin {BRANCH} && git reset --hard {COMMIT} && git log -1 --oneline"
    )
    print(out or err)
    if code:
        ssh.close()
        return code

    code, out, err = run("systemctl restart mas-orchestrator", sudo=True)
    print("restart:", out or err)
    time.sleep(8)
    code, out, err = run("curl -s http://127.0.0.1:8001/health")
    print("health:", out.strip())
    ssh.close()
    return 0 if "healthy" in out.lower() or "ok" in out.lower() else 1


if __name__ == "__main__":
    raise SystemExit(main())
