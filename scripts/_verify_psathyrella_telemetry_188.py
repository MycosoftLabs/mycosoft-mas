#!/usr/bin/env python3
"""Verify Psathyrella telemetry endpoint on MAS VM 188."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_vm_credentials import load_vm_credentials, vm_ssh_password

load_vm_credentials()
password = vm_ssh_password()
if not password:
    print("Missing VM_PASSWORD")
    sys.exit(1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.188", username="mycosoft", password=password, timeout=30)

checks = [
    ("health", "curl -s -m 25 http://127.0.0.1:8001/health"),
    ("telemetry_code", 'curl -s -o /dev/null -w "%{http_code}" -m 25 http://127.0.0.1:8001/api/psathyrella/telemetry'),
    ("telemetry", "curl -s -m 25 http://127.0.0.1:8001/api/psathyrella/telemetry"),
    ("git_sha", "cd /home/mycosoft/mycosoft/mas && git rev-parse --short HEAD"),
]

for label, cmd in checks:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=90)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    print(f"{label}={out[:2000]}")
    if err:
        print(f"{label}_err={err[:300]}")

ssh.close()
