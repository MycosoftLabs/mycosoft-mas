#!/usr/bin/env python3
"""Read a file from the sandbox VM and print it to stdout (UTF-8 safe)."""

from __future__ import annotations

import argparse
import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip("\n")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--head", type=int, default=260)
    args = ap.parse_args()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    cmd = f"sed -n '1,{args.head}p' {args.path} 2>/dev/null || echo 'MISSING_FILE'"
    print(run(ssh, cmd))

    ssh.close()


if __name__ == "__main__":
    main()

