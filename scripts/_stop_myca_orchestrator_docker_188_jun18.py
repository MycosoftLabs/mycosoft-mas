#!/usr/bin/env python3
"""Stop duplicate myca-orchestrator-new Docker on 188; keep systemd :8001 only."""
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
echo '=== before ==='
docker ps --filter name=myca-orchestrator --format '{{.Names}} {{.Status}} {{.Ports}}'
ps aux | grep 'port 8000' | grep uvicorn | grep -v grep || echo no_8000

echo '=== stop duplicate docker MAS ==='
docker update --restart=no myca-orchestrator-new 2>/dev/null || true
docker stop -t 5 myca-orchestrator-new 2>/dev/null || true
docker rm -f myca-orchestrator-new 2>/dev/null || true
cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.yml stop mas-orchestrator 2>/dev/null || true

pkill -9 -f 'uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8000' || true
sleep 3

echo '=== after ==='
docker ps --filter name=myca-orchestrator --format '{{.Names}} {{.Status}}' || echo no_orchestrator_container
ps aux | grep 'port 8000' | grep uvicorn | grep -v grep || echo port_8000_clear
systemctl is-active mas-orchestrator
curl -s -o /dev/null -w 'live_8001=%{http_code}\n' http://127.0.0.1:8001/live
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
