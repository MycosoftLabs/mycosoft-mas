"""One-shot SSH reachability for Meshtastic integration plan (no secrets printed)."""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path


def load_credentials() -> None:
    p = Path(__file__).resolve().parent.parent / ".credentials.local"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    load_credentials()
    hosts = [
        ("192.168.0.196", "broker"),
        ("192.168.0.187", "sandbox"),
        ("192.168.0.188", "mas"),
        ("192.168.0.189", "mindex"),
    ]
    for ip, name in hosts:
        try:
            s = socket.create_connection((ip, 22), 3)
            s.close()
            print(f"tcp22_ok {name} {ip}")
        except OSError as e:
            print(f"tcp22_fail {name} {ip} {e}")
    try:
        import paramiko
    except ImportError:
        print("paramiko_missing_install_for_full_ssh_test")
        return 0
    pw = (os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "").strip()
    if not pw:
        print("no_vm_password_in_env")
        return 0
    for ip, name in hosts:
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(ip, username="mycosoft", password=pw, timeout=12, allow_agent=False, look_for_keys=False)
            _, stdout, _ = c.exec_command("hostname", timeout=10)
            hn = stdout.read().decode().strip()
            c.close()
            print(f"ssh_ok {name} hostname={hn}")
        except Exception as e:
            print(f"ssh_fail {name} {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
