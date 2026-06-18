#!/usr/bin/env python3
"""Stop duplicate Docker uvicorn on MAS VM 188 port 8000 via Proxmox guest exec."""
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
set -e
echo '=== containers on 8000 ==='
docker ps --format '{{.ID}} {{.Names}} {{.Ports}}' | grep 8000 || true
for cid in $(docker ps -q); do
  if docker port "$cid" 2>/dev/null | grep -q 8000; then
    echo "STOPPING $cid"
    docker stop -t 5 "$cid" || true
    docker rm -f "$cid" || true
  fi
done
pkill -9 -f 'uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8000' || true
sleep 2
echo '=== after ==='
docker ps --format '{{.ID}} {{.Names}} {{.Ports}}' | grep 8000 || echo no_8000_containers
ps aux | grep 'port 8000' | grep uvicorn | grep -v grep || echo no_uvicorn_8000
ps aux --sort=-%cpu | head -4
"""


def main() -> int:
    load_vm_credentials()
    pw = os.environ.get("PROXMOX202_PASSWORD") or os.environ.get("PROXMOX_PASSWORD", "")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.202", username="root", password=pw, timeout=20)
    b64 = base64.b64encode(SCRIPT.encode()).decode()
    _, o, e = ssh.exec_command(
        f"qm guest exec 188 -- bash -lc 'echo {b64} | base64 -d | bash'",
        timeout=120,
    )
    raw = (o.read() + e.read()).decode(errors="replace")
    try:
        data = json.loads(raw)
        print((data.get("out-data") or "") + (data.get("err-data") or ""))
    except json.JSONDecodeError:
        print(raw)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
