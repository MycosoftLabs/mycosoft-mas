#!/usr/bin/env python3
import os
from pathlib import Path

import paramiko

for fname in (
    Path(__file__).resolve().parents[1] / ".credentials.local",
):
    if fname.exists():
        for line in fname.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"\'')

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.188", username="mycosoft", password=pw, timeout=30)

checks = [
    ("GET", "/health", None),
    ("POST", "/api/myca/chat", '{"message":"ping","user_id":"earth-sim-smoke"}'),
    ("GET", "/api/devices", None),
    ("GET", "/api/memory/health", None),
    ("GET", "/api/registry/agents", None),
]
for method, path, body in checks:
    if method == "GET":
        cmd = f'curl -s -o /dev/null -w "{path}:%{{http_code}}" "http://localhost:8001{path}"'
    else:
        cmd = (
            f'curl -s -o /dev/null -w "{path}:%{{http_code}}" '
            f'-X POST "http://localhost:8001{path}" '
            f'-H "Content-Type: application/json" -d \'{body}\''
        )
    _, stdout, _ = ssh.exec_command(cmd, timeout=30)
    print(stdout.read().decode().strip())

ssh.close()
