"""Disconnect D-state leftover from docker DNS. Do not stop green. No secrets."""
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
echo ACTIVE=$(cat /opt/mycosoft/state/active-slot)
echo BLUE=$(docker inspect -f '{{.State.Health.Status}} image={{.Config.Image}}' mycosoft-website-blue)
echo GREEN=$(docker inspect -f '{{.State.Health.Status}}' mycosoft-website-green)
echo EXEC_BLUE=$(docker exec mycosoft-website-blue curl -sS -o /dev/null -w '%{http_code}' --max-time 8 http://localhost:3000/api/health)
echo ORIGIN=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:3000/api/health)
echo === aliases ===
docker inspect -f '{{.Name}} {{range $k,$v := .NetworkSettings.Networks}}{{$k}} aliases={{json $v.Aliases}}{{end}}' mycosoft-website-blue mycosoft-website-blue-wedged-sep09 mycosoft-website-green 2>/dev/null || true
if docker ps -a --format '{{.Names}}' | grep -qx mycosoft-website-blue-wedged-sep09; then
  echo disconnecting wedged
  timeout 15 docker network disconnect -f website_mycosoft-network mycosoft-website-blue-wedged-sep09 && echo disconnected || echo disconnect_timeout
fi
echo ORIGIN2=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:3000/api/health)
echo PROXY=$(docker exec mycosoft-website-proxy wget -q -O - http://127.0.0.1/healthz | head -c 80; echo)
"""
_, stdout, stderr = client.exec_command(cmd, timeout=90)
print((stdout.read() + stderr.read()).decode("utf-8", "replace"))
print("exit", stdout.channel.recv_exit_status())
client.close()
