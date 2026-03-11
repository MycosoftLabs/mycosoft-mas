#!/usr/bin/env python3
"""Diagnose /channels on VM 191."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

creds = {}
for f in [REPO / ".credentials.local", Path.home() / ".mycosoft-credentials"]:
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip()
        break
password = creds.get("VM_SSH_PASSWORD") or creds.get("VM_PASSWORD") or os.environ.get("VM_PASSWORD")
if not password:
    print("ERROR: No VM password")
    sys.exit(1)

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.191", username="mycosoft", password=password, timeout=15)


def run(cmd, encoding="utf-8", errors="replace"):
    _, so, se = client.exec_command(cmd, timeout=10)
    raw = so.read() + se.read()
    return raw.decode(encoding, errors=errors)


def safe_print(s):
    """Print without Windows cp1252 encoding errors."""
    print(s.encode("ascii", errors="replace").decode())


safe_print("=== All listeners (ss -tlnp) ===")
safe_print(run("ss -tlnp 2>/dev/null || echo 'ss not available'"))
safe_print("")
safe_print("=== Port 8100 in use? ===")
safe_print(run("ss -tlnp 2>/dev/null | grep -E '8100|:8100' || echo 'none'"))
safe_print("")
safe_print("=== Process using port 8100 (fuser) ===")
safe_print(run("fuser -v 8100/tcp 2>&1 || echo 'fuser not available'"))
safe_print("")
safe_print("=== Processes using 8100 (lsof if available) ===")
safe_print(run("lsof -i :8100 2>/dev/null || echo 'lsof not available'"))
safe_print("")
safe_print("=== systemctl status myca-os ===")
safe_print(run("LANG=C systemctl status myca-os 2>&1 | head -25"))
safe_print("")
safe_print("=== curl -v 127.0.0.1:8100/channels (verbose) ===")
safe_print(run("curl -v --connect-timeout 3 http://127.0.0.1:8100/channels 2>&1"))
safe_print("")
safe_print("=== curl 127.0.0.1:8100/health ===")
safe_print(run("curl -s --connect-timeout 3 http://127.0.0.1:8100/health 2>&1"))
safe_print("")
safe_print("=== journalctl myca-os last 60 lines ===")
safe_print(run("journalctl -u myca-os -n 60 --no-pager 2>&1"))
safe_print("")
safe_print("=== myca_os.log: Gateway lines ===")
safe_print(run("grep -E 'Gateway failed|Gateway listening|MYCA Gateway' /opt/myca/logs/myca_os.log 2>/dev/null | tail -10 || echo 'none'"))
safe_print("")
safe_print("=== myca_os.log last 30 lines ===")
safe_print(run("tail -30 /opt/myca/logs/myca_os.log 2>/dev/null || echo 'No log'"))
safe_print("")
safe_print("=== myca_os_error.log (last 40 lines) ===")
safe_print(run("tail -40 /opt/myca/logs/myca_os_error.log 2>/dev/null || echo 'No error log'"))
safe_print("")
safe_print("=== PyYAML in venv? ===")
safe_print(run("/home/mycosoft/repos/mycosoft-mas/.venv/bin/python -c 'import yaml; print(\"PyYAML ok\")' 2>&1"))
safe_print("")
safe_print("=== Python/myca processes ===")
safe_print(run("ps aux | grep -E 'python|uvicorn|myca' | grep -v grep"))
client.close()
