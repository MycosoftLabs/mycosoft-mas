#!/usr/bin/env python3
"""Diagnose and disable duplicate uvicorn :8000 on MAS 188."""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from load_vm_credentials import load_vm_credentials

SCRIPT = r"""
echo '=== systemd mas/uvicorn ==='
systemctl list-units --type=service --all | grep -Ei 'mas|uvicorn|orchestrator' || true
echo '=== docker all ==='
docker ps -a --format '{{.ID}} {{.Names}} {{.Status}} {{.Ports}}'
echo '=== port 8000 process ==='
pid=$(ps aux | grep 'port 8000' | grep uvicorn | grep -v grep | awk '{print $2}' | head -1)
if [ -n "$pid" ]; then
  ps -o pid,ppid,user,cmd -p "$pid"
  cat /proc/$pid/cgroup 2>/dev/null | head -3
fi
echo '=== compose projects ==='
docker compose ls 2>/dev/null || true
for cid in $(docker ps -aq); do
  ports=$(docker port "$cid" 2>/dev/null)
  if echo "$ports" | grep -q 8000; then
    echo "container $cid maps 8000: $(docker inspect -f '{{.Name}} restart={{.HostConfig.RestartPolicy.Name}}' $cid)"
  fi
done
echo '=== stop all docker with 8000 ==='
for cid in $(docker ps -aq); do
  if docker port "$cid" 2>/dev/null | grep -q 8000; then
    docker update --restart=no "$cid" 2>/dev/null || true
    docker stop -t 3 "$cid" 2>/dev/null || true
    docker rm -f "$cid" 2>/dev/null || true
  fi
done
pkill -9 -f 'uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8000' || true
sleep 4
ps aux | grep 'port 8000' | grep uvicorn | grep -v grep || echo 'port 8000 clear'
"""


def run(script: str) -> str:
    pw = os.environ.get("PROXMOX202_PASSWORD") or os.environ.get("PROXMOX_PASSWORD", "")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.202", username="root", password=pw, timeout=20)
    b64 = base64.b64encode(script.encode()).decode()
    _, o, e = ssh.exec_command(
        f"qm guest exec 188 -- bash -lc 'echo {b64} | base64 -d | bash'",
        timeout=120,
    )
    raw = (o.read() + e.read()).decode(errors="replace")
    ssh.close()
    try:
        data = json.loads(raw)
        return (data.get("out-data") or "") + (data.get("err-data") or "")
    except json.JSONDecodeError:
        return raw


def main() -> int:
    load_vm_credentials()
    print(run(SCRIPT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
