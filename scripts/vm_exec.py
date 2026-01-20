#!/usr/bin/env python3
"""Run an arbitrary shell command on the sandbox VM via SSH and print stdout/stderr."""

from __future__ import annotations

import argparse
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
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="Shell command to run on VM")
    args = ap.parse_args()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    cmd_parts = list(args.cmd)
    if cmd_parts and cmd_parts[0] == "--":
        cmd_parts = cmd_parts[1:]
    cmd = " ".join(cmd_parts).strip()
    if not cmd:
        raise SystemExit("No command provided.")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out:
        print(out.rstrip("\n"))
    if err.strip():
        print(err.rstrip("\n"), file=sys.stderr)

    ssh.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Execute a single command on the VM via SSH (Paramiko) and print output.

Usage:
  python scripts/vm_exec.py "docker ps"
"""

import sys
import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if len(sys.argv) < 2:
        print('Usage: python scripts/vm_exec.py "<command>"')
        sys.exit(2)

    cmd = sys.argv[1]

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

    stdin, stdout, stderr = ssh.exec_command(cmd)
    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")

    print(f"[CMD] {cmd}")
    print(f"[RC] {rc}")
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print("\n[STDERR]")
        print(err.rstrip())

    ssh.close()


if __name__ == "__main__":
    main()

