#!/usr/bin/env python3
"""Reboot the Jetson over SSH."""
import os
import time
from pathlib import Path
import paramiko

creds = Path(__file__).resolve().parents[1] / ".credentials.local"
pw = os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
if not pw and creds.exists():
    for line in creds.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD", "JETSON_SSH_PASSWORD") and v.strip():
                pw = v.strip()
                break
if not pw:
    print("ERROR: No password in env or .credentials.local")
    exit(1)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.123", username="jetson", password=pw, timeout=15)
stdin, stdout, stderr = ssh.exec_command("sudo -S reboot", get_pty=True)
stdin.write(pw + "\n")
stdin.flush()
time.sleep(2)
try:
    ssh.close()
except Exception:
    pass
print("Reboot sent. Jetson will come back in ~60-90 seconds.")
