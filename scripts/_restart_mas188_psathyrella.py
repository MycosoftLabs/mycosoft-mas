#!/usr/bin/env python3
"""Diagnose and restart mas-orchestrator on 188."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_vm_credentials import load_vm_credentials, vm_ssh_password

load_vm_credentials()
password = vm_ssh_password()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.188", username="mycosoft", password=password, timeout=30)

commands = [
    "ss -tlnp | grep 8001 || true",
    "pgrep -af myca_main || pgrep -af uvicorn || true",
    f"echo '{password}' | sudo -S journalctl -u mas-orchestrator -n 50 --no-pager 2>&1",
    f"echo '{password}' | sudo -S systemctl restart mas-orchestrator",
    "sleep 25",
    "curl -s -m 10 http://127.0.0.1:8001/health || echo HEALTH_FAIL",
    "curl -s -o /dev/null -w '%{http_code}' -m 10 http://127.0.0.1:8001/api/psathyrella/telemetry || echo TELEM_FAIL",
]

for cmd in commands:
    print("=== CMD:", cmd[:80], "===")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out[:4000])
    if err.strip():
        print("STDERR:", err[:1000])

ssh.close()
