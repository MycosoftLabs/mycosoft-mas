#!/usr/bin/env python3
"""Dump a file from inside the mindex-api container on the VM with line numbers."""

from __future__ import annotations

import argparse
import base64
import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=220)
    args = ap.parse_args()

    py = f"""
from pathlib import Path
p = Path({args.path!r})
start = {args.start}
end = {args.end}
text = p.read_text(encoding='utf-8', errors='replace').splitlines()
for i, line in enumerate(text, start=1):
    if start <= i <= end:
        print(f\"{{i}}:{{line}}\")
"""
    encoded = base64.b64encode(py.encode("utf-8")).decode("ascii")
    cmd = "docker exec mindex-api python -c " + repr(
        f"import base64; exec(base64.b64decode('{encoded}').decode('utf-8'))"
    )

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
    print(run(ssh, cmd))
    ssh.close()


if __name__ == "__main__":
    main()

