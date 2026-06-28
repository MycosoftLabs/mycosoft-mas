#!/usr/bin/env python3
"""One-shot deploy Psathyrella Jetson forward slice to MAS VM 188."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent.parent
CREDS = ROOT / ".credentials.local"
if CREDS.exists():
    for line in CREDS.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

HOST = os.environ.get("MAS_VM_HOST", "192.168.0.188")
# MAS VM 188 uses mycosoft; .credentials.local may set VM_SSH_USER=root for Proxmox.
USER = os.environ.get("MAS_SSH_USER") or os.environ.get("VM_SSH_USER") or "mycosoft"
if USER == "root" and HOST in ("192.168.0.188", os.environ.get("MAS_VM_IP", "")):
    USER = "mycosoft"
PASSWORD = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
if not PASSWORD:
    sys.exit("VM password missing from .credentials.local")

FILES = [
    "mycosoft_mas/devices/psathyrella/jetson_forward.py",
    "mycosoft_mas/devices/psathyrella/command_handler.py",
    "mycosoft_mas/devices/psathyrella/constants.py",
    "mycosoft_mas/devices/psathyrella/telemetry_builder.py",
]
REMOTE_BASE = "/home/mycosoft/mycosoft/mas"


def main() -> None:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
    sftp = ssh.open_sftp()
    for rel in FILES:
        local = ROOT / rel
        remote = f"{REMOTE_BASE}/{rel.replace(chr(92), '/')}"
        print(f"upload {rel} -> {remote}")
        sftp.put(str(local), remote)
    sftp.close()

    env_cmds = [
        "grep -q PSATHYRELLA_BENCH_SINGLE_MOTOR /home/mycosoft/mycosoft/mas/.env 2>/dev/null "
        "|| echo PSATHYRELLA_BENCH_SINGLE_MOTOR=1 >> /home/mycosoft/mycosoft/mas/.env",
        "grep -q PSATHYRELLA_JETSON_AGENT_URL /home/mycosoft/mycosoft/mas/.env 2>/dev/null "
        "|| echo PSATHYRELLA_JETSON_AGENT_URL=http://192.168.0.123:8787 >> /home/mycosoft/mycosoft/mas/.env",
    ]
    for cmd in env_cmds:
        ssh.exec_command(cmd)

    stdin, stdout, stderr = ssh.exec_command("sudo systemctl restart mas-orchestrator", get_pty=True)
    stdin.write(PASSWORD + "\n")
    stdin.flush()
    stdout.channel.recv_exit_status()
    time.sleep(6)
    _, health_out, _ = ssh.exec_command("curl -s http://localhost:8001/api/psathyrella/health")
    print(health_out.read().decode())
    ssh.close()


if __name__ == "__main__":
    main()
