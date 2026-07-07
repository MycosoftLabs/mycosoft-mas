"""One-shot: SSH to MAS VM and check Psathyrella keepalive logs + registry."""
from __future__ import annotations

import os
from pathlib import Path

import paramiko


def load_creds() -> None:
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if creds.exists():
        for line in creds.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()


def main() -> None:
    load_creds()
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.188", username="mycosoft", password=password, timeout=30)
    commands = [
        "curl -s -m 3 http://192.168.0.123:8788/health | head -c 120",
        "curl -s -m 3 http://127.0.0.1:8001/api/devices/psathyrella-1",
        "journalctl -u mas-orchestrator -n 800 --no-pager | grep -i Psathyrella | tail -20",
        "journalctl -u mas-orchestrator -n 800 --no-pager | grep -i keepalive | tail -10",
        "journalctl -u mas-orchestrator -n 800 --no-pager | grep 'MAS Orchestrator starting' | tail -5",
        "journalctl -u mas-orchestrator -n 800 --no-pager | grep 'Telemetry pipeline' | tail -5",
        "grep -E 'MAS_INGESTION_ONLY|PSATHYRELLA_REGISTRY' /home/mycosoft/mycosoft/mas/.env 2>/dev/null || true",
        "systemctl show mas-orchestrator -p Environment 2>/dev/null | tr ' ' '\\n' | grep -E 'INGESTION|PSATHYRELLA' || true",
    ]
    for cmd in commands:
        print("\n>>>", cmd)
        _stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out.strip():
            print(out)
        if err.strip():
            print("stderr:", err)
    ssh.close()


if __name__ == "__main__":
    main()
