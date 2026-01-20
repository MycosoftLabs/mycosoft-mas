#!/usr/bin/env python3
"""Show the mycosoft-website service definition from the VM always-on compose file."""

from __future__ import annotations

import paramiko
import sys
from io import StringIO

import yaml

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"
COMPOSE_PATH = "/home/mycosoft/mycosoft/mas/docker-compose.always-on.yml"


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

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    raw = run(ssh, f"cat {COMPOSE_PATH}")
    doc = yaml.safe_load(StringIO(raw)) or {}
    svc = ((doc.get("services") or {}).get("mycosoft-website")) or {}
    print(yaml.dump({"mycosoft-website": svc}, sort_keys=False))

    ssh.close()


if __name__ == "__main__":
    main()

