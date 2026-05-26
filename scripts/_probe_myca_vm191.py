#!/usr/bin/env python3
"""Probe MYCA VM 191 via SSH key or password; check services."""
import os
import socket
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

host = "192.168.0.191"
pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
key_paths = [
    os.environ.get("VM_SSH_KEY_PATH", ""),
    str(Path.home() / ".ssh" / "id_rsa"),
    str(Path.home() / ".ssh" / "mycosoft"),
]

for port in (22, 8000, 443, 5679, 9000):
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect((host, port))
        print(f"TCP {host}:{port} OPEN")
    except Exception as e:
        print(f"TCP {host}:{port} closed/timeout: {e}")
    finally:
        s.close()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
connected = False
for key_path in key_paths:
    if key_path and Path(key_path).exists():
        try:
            ssh.connect(host, username="mycosoft", key_filename=key_path, timeout=15)
            print(f"SSH OK with key {key_path}")
            connected = True
            break
        except Exception as e:
            print(f"SSH key {key_path} failed: {e}")

if not connected and pw:
    for user in ("mycosoft", "root", "ubuntu"):
        try:
            ssh.connect(host, username=user, password=pw, timeout=15)
            print(f"SSH OK with password user={user}")
            connected = True
            break
        except Exception as e:
            print(f"SSH password {user} failed: {e}")

if connected:
    for cmd in (
        "hostname",
        "systemctl is-active myca-fastapi 2>/dev/null || systemctl is-active caddy 2>/dev/null || true",
        "ss -tlnp | head -20",
        "curl -s -m 3 http://127.0.0.1:8000/health 2>/dev/null || echo no_local_8000",
    ):
        _, stdout, _ = ssh.exec_command(cmd, timeout=20)
        print(f">>> {cmd}")
        print(stdout.read().decode(errors="replace")[:800])
    ssh.close()
else:
    print("Could not SSH to MYCA VM 191")
