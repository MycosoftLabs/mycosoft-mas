#!/usr/bin/env python3
"""Quick check of OpenClaw on Jetson 123."""
import os
from pathlib import Path
import paramiko
import time

creds = Path(__file__).parent.parent / ".credentials.local"
if creds.exists():
    for line in creds.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
pw = os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD") or ""
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.123", username="jetson", password=pw, timeout=15)
time.sleep(6)
def safe_print(s: str) -> None:
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", errors="replace").decode("ascii"))

for cmd in [
    "systemctl --user status openclaw-gateway --no-pager 2>&1",
    "ss -tlnp 2>/dev/null | grep 18789 || echo '(no listener)'",
    "tail -30 /home/jetson/.local/state/openclaw-gateway.log 2>/dev/null",
]:
    _, stdout, _ = ssh.exec_command(cmd)
    safe_print(stdout.read().decode(errors="replace"))
_, stdout, _ = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18789/ 2>/dev/null || echo fail")
safe_print("HTTP: " + stdout.read().decode(errors="replace").strip())
ssh.close()
