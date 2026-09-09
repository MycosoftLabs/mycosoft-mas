"""If origin is down, flip nginx back to healthy green. No secrets."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CREDS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local")
for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    "192.168.0.187",
    username="mycosoft",
    password=os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "",
    timeout=30,
)
cmd = r"""
set -euo pipefail
echo EXEC_BLUE=$(docker exec mycosoft-website-blue curl -sS -o /dev/null -w '%{http_code}' --max-time 8 http://localhost:3000/api/health || echo fail)
echo EXEC_GREEN=$(docker exec mycosoft-website-green curl -sS -o /dev/null -w '%{http_code}' --max-time 8 http://localhost:3000/api/health || echo fail)
echo ORIGIN=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 12 http://127.0.0.1:3000/api/health || echo timeout)
echo PROXY_TO_BLUE=$(docker exec mycosoft-website-proxy wget -q -O /dev/null --timeout=8 http://website-blue:3000/api/health; echo $?)
echo NS=$(docker exec mycosoft-website-proxy nslookup website-blue 2>/dev/null | tail -5 || true)
"""
_, stdout, stderr = client.exec_command(cmd, timeout=60)
print((stdout.read() + stderr.read()).decode("utf-8", "replace"))
client.close()
