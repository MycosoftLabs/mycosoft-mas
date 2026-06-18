#!/usr/bin/env python3
"""Hard kill hung MAS on 188, restart skip=1, diagnose CPU."""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path

import httpx
import paramiko

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from load_vm_credentials import load_vm_credentials

ENV_PATH = "/home/mycosoft/mycosoft/mas/.env"


class Pve188:
    def __init__(self) -> None:
        pw = os.environ.get("PROXMOX202_PASSWORD") or os.environ.get("PROXMOX_PASSWORD", "")
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect("192.168.0.202", username="root", password=pw, timeout=20)

    def bash(self, script: str, timeout: int = 120) -> str:
        b64 = base64.b64encode(script.encode()).decode()
        cmd = f"qm guest exec 188 -- bash -lc 'echo {b64} | base64 -d | bash'"
        _, o, e = self.ssh.exec_command(cmd, timeout=timeout)
        raw = (o.read() + e.read()).decode(errors="replace")
        try:
            data = json.loads(raw)
            return (data.get("out-data") or "") + (data.get("err-data") or "")
        except json.JSONDecodeError:
            return raw

    def close(self) -> None:
        self.ssh.close()


def main() -> int:
    load_vm_credentials()
    pve = Pve188()
    try:
        print("=== env grep ===")
        print(pve.bash(f"grep -E 'MAS_SKIP|MOVER|STATIC|WORKFLOW' '{ENV_PATH}' || true"))

        print("=== before kill: top python ===")
        print(pve.bash("ps aux | grep -E 'myca_main|uvicorn|python' | grep -v grep | head -10"))

        print("=== hard stop ===")
        script = """
systemctl stop mas-orchestrator || true
sleep 2
pkill -9 -f 'myca_main' || true
pkill -9 -f 'uvicorn' || true
sleep 2
ss -ltnp | grep 8001 || echo 'port 8001 free'
"""
        print(pve.bash(script))

        print("=== set MAS_SKIP=1 only ===")
        for k, v in {
            "MAS_SKIP_BACKGROUND_STARTUP": "1",
            "MOVER_INGEST_MODE": "api",
            "STATIC_BUILD_ON_STARTUP": "0",
            "WORKFLOW_AUTO_MONITOR_ENABLED": "0",
        }.items():
            esc = v.replace("\\", "\\\\")
            pve.bash(
                f"if grep -q '^{k}=' '{ENV_PATH}'; then sed -i 's|^{k}=.*|{k}={esc}|' '{ENV_PATH}'; "
                f"else echo '{k}={esc}' >> '{ENV_PATH}'; fi"
            )

        print("=== start mas-orchestrator ===")
        print(pve.bash("systemctl start mas-orchestrator && sleep 15 && systemctl is-active mas-orchestrator"))

        for i in range(6):
            time.sleep(5)
            try:
                r = httpx.get("http://192.168.0.188:8001/live", timeout=5)
                print(f"live {i+1}: {r.status_code}")
                if r.status_code == 200:
                    break
            except Exception as exc:
                print(f"live {i+1}: {exc}")

        try:
            h = httpx.get("http://192.168.0.188:8001/health", timeout=12)
            print("health:", h.status_code, h.text[:500])
        except Exception as exc:
            print("health fail:", exc)

        print("=== journal startup ===")
        print(
            pve.bash(
                "journalctl -u mas-orchestrator --since '2 min ago' --no-pager | tail -40"
            )[:4000]
        )

        print("=== top after start ===")
        print(pve.bash("ps aux --sort=-%cpu | head -8"))
    finally:
        pve.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
