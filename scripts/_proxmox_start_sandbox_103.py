#!/usr/bin/env python3
"""Start Sandbox VM 103 on Proxmox if stopped; poll until SSH to 187 works."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent


def load_env() -> None:
    for f in (REPO / ".credentials.local", REPO.parent / "website" / ".credentials.local"):
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.strip().startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def proxmox_password() -> str:
    return (
        os.environ.get("PROXMOX202_PASSWORD")
        or os.environ.get("PROXMOX_PASSWORD")
        or os.environ.get("VM_PASSWORD")
        or os.environ.get("VM_SSH_PASSWORD")
        or ""
    )


def vm_password() -> str:
    return os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""


def main() -> int:
    load_env()
    pp = proxmox_password()
    if not pp:
        print("ERROR: no Proxmox/root password (PROXMOX202_PASSWORD or VM_PASSWORD)")
        return 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.202", username="root", password=pp, timeout=25)

    for cmd in ("qm status 103",):
        print("---", cmd, "---")
        _i, o, e = ssh.exec_command(cmd, timeout=40)
        out = o.read().decode(errors="replace")
        err = e.read().decode(errors="replace")
        print(out or "(empty)")
        if err.strip():
            print(err)

    _i, o, _e = ssh.exec_command("qm status 103", timeout=40)
    status_line = o.read().decode(errors="replace").strip()
    print("Parsed:", repr(status_line))

    if "stopped" in status_line.lower():
        print("Starting VM 103...")
        _i, o, e = ssh.exec_command("qm start 103", timeout=120)
        print(o.read().decode(errors="replace"))
        err = e.read().decode(errors="replace")
        if err.strip():
            print("stderr:", err)
    elif "running" in status_line.lower():
        print("VM 103 already running.")
    else:
        print("Unexpected qm status; attempting qm start anyway (idempotent if running)...")
        _i, o, e = ssh.exec_command("qm start 103 2>&1", timeout=120)
        print(o.read().decode(errors="replace"))
        print(e.read().decode(errors="replace"))

    ssh.close()

    vmpw = vm_password()
    if not vmpw:
        print("No VM password for SSH test to 187; Proxmox step done.")
        return 0

    print("Polling SSH mycosoft@192.168.0.187 (up to 180s)...")
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            s2 = paramiko.SSHClient()
            s2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            s2.connect("192.168.0.187", username="mycosoft", password=vmpw, timeout=15)
            _i, o, _e = s2.exec_command("hostname && uptime", timeout=30)
            print(o.read().decode(errors="replace"))
            s2.close()
            print("OK: 187 SSH works.")
            return 0
        except Exception as ex:
            print(f"  wait... ({ex!s:.80})")
            time.sleep(10)

    print("TIMEOUT: 187 did not accept SSH in 180s")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
