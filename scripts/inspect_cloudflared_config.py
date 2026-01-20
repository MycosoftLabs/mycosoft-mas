#!/usr/bin/env python3
"""Inspect VM cloudflared ingress rule order (high-signal summary)."""

import paramiko
import sys
from io import StringIO

import yaml

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD)

    _, stdout, _ = ssh.exec_command("cat ~/.cloudflared/config.yml")
    raw = stdout.read().decode("utf-8", errors="replace")

    config = yaml.safe_load(StringIO(raw)) or {}
    ingress = list(config.get("ingress", []))

    print("=" * 100)
    print("cloudflared ingress rules (order matters)")
    print("=" * 100)
    for idx, rule in enumerate(ingress):
        if not isinstance(rule, dict):
            print(f"{idx:02d}. (non-dict) {rule}")
            continue
        host = rule.get("hostname", "")
        path = rule.get("path", "")
        service = rule.get("service", "")
        print(f"{idx:02d}. host={host!s:24} path={path!s:18} -> {service}")

    ssh.close()


if __name__ == "__main__":
    main()

