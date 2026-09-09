"""Inspect hung blue-green on 187. No secrets."""
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
echo === bg ===
ps -ef | grep '/scripts/blue-green-deploy.sh' | grep -v grep || echo none
echo === idle blue ===
docker inspect -f 'name={{.Name}} status={{.State.Status}} pid={{.State.Pid}}' mycosoft-website-blue
BPID=$(docker inspect -f '{{.State.Pid}}' mycosoft-website-blue)
if [ -n "$BPID" ] && [ -r /proc/$BPID/stat ]; then
  echo idle_kernel_state=$(sed -n 's/.*) //p' /proc/$BPID/stat | awk '{print $1}')
fi
echo === green ===
docker inspect -f 'green={{.State.Health.Status}}' mycosoft-website-green
curl -sS -o /dev/null -w 'origin:%{http_code}\n' --max-time 8 http://127.0.0.1:3000/api/health
echo === flock holders ===
fuser "$HOME/.cache/mycosoft-deploy/blue-green.lock" 2>/dev/null || echo no_flock
"""
_, stdout, stderr = client.exec_command(cmd, timeout=40)
print((stdout.read() + stderr.read()).decode("utf-8", "replace"))
client.close()
