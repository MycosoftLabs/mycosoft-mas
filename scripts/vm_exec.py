#!/usr/bin/env python3
"""Run a shell command on the sandbox VM via SSH and print stdout/stderr.

This script is intentionally small and robust because it's used heavily during deployments.

Usage examples:
  python scripts/vm_exec.py docker ps
  python scripts/vm_exec.py "docker ps"
  python scripts/vm_exec.py -- "bash -lc 'echo hello'"
"""

from __future__ import annotations

import argparse
import shlex

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run on VM (use -- to pass a single string)")
    args = ap.parse_args()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    cmd_parts = list(args.cmd)
    if cmd_parts and cmd_parts[0] == "--":
        cmd_parts = cmd_parts[1:]

    # Accept both:
    # - vm_exec.py docker ps
    # - vm_exec.py "docker ps"
    cmd = " ".join(cmd_parts).strip()
    if not cmd:
        raise SystemExit("No command provided. Example: python scripts/vm_exec.py docker ps")

    stdin, stdout, stderr = ssh.exec_command(cmd)
    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")

    print(f"[CMD] {cmd}")
    print(f"[RC] {rc}")
    if out:
        print(out.rstrip("\n"))
    if err.strip():
        print(err.rstrip("\n"), file=sys.stderr)

    ssh.close()


if __name__ == "__main__":
    main()

