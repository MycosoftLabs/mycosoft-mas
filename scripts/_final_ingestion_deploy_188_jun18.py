#!/usr/bin/env python3
"""Final deploy: stagger+cap fixes, stop docker dup, enable collectors."""
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

MAS_PATH = "/home/mycosoft/mycosoft/mas"
ENV_PATH = f"{MAS_PATH}/.env"

UPLOADS = [
    "mycosoft_mas/core/myca_main.py",
    "mycosoft_mas/collectors/base_collector.py",
    "mycosoft_mas/collectors/opensky_collector.py",
    "mycosoft_mas/collectors/orchestrator.py",
    "mycosoft_mas/collectors/norad_collector.py",
    "mycosoft_mas/monitoring/health_check.py",
    "mycosoft_mas/core/routers/crep_collectors_api.py",
]


class Pve188:
    def __init__(self) -> None:
        pw = os.environ.get("PROXMOX202_PASSWORD") or os.environ.get("PROXMOX_PASSWORD", "")
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect("192.168.0.202", username="root", password=pw, timeout=20)

    def bash(self, script: str, timeout: int = 180) -> str:
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


def upload(pve: Pve188, rel: str) -> None:
    local = ROOT / rel
    remote = f"{MAS_PATH}/{rel}"
    data = local.read_bytes()
    tmp = f"{remote}.uploading"
    pve.bash(f"mkdir -p $(dirname '{remote}') && rm -f '{tmp}'")
    chunk_bytes = 20000
    for i in range(0, len(data), chunk_bytes):
        part_b64 = base64.b64encode(data[i : i + chunk_bytes]).decode()
        pve.bash(f"echo '{part_b64}' | base64 -d >> '{tmp}'", timeout=120)
    out = pve.bash(f"mv '{tmp}' '{remote}' && wc -c '{remote}'")
    print(f"upload {rel}: {out.strip()[:100]}")


def set_env(pve: Pve188, key: str, val: str) -> None:
    esc = val.replace("\\", "\\\\")
    print(
        pve.bash(
            f"if grep -q '^{key}=' '{ENV_PATH}'; then sed -i 's|^{key}=.*|{key}={esc}|' '{ENV_PATH}'; "
            f"else echo '{key}={esc}' >> '{ENV_PATH}'; fi && grep '^{key}=' '{ENV_PATH}'"
        )
    )


def bbox() -> dict:
    base = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
    token = os.environ.get("MINDEX_INTERNAL_TOKEN", "")
    headers = {"X-Internal-Token": token} if token else {}
    q = "lat_min=-90&lat_max=90&lng_min=-180&lng_max=180&limit=5"
    out = {}
    for layer in ("aircraft", "vessels", "satellites"):
        r = httpx.get(
            f"{base}/api/mindex/earth/map/bbox?layer={layer}&{q}",
            headers=headers,
            timeout=20,
        )
        out[layer] = r.json().get("total", 0)
    return out


def main() -> int:
    load_vm_credentials()
    pve = Pve188()
    try:
        print("=== stop docker duplicate MAS :8000 ===")
        print(
            pve.bash(
                """
for cid in $(docker ps -q); do
  if docker port "$cid" 2>/dev/null | grep -q 8000; then
    echo stopping $cid
    docker stop "$cid" || true
  fi
done
pkill -9 -f 'uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8000' || true
sleep 2
ps aux | grep 'port 8000' | grep uvicorn | grep -v grep || echo 'port 8000 clear'
"""
            )
        )

        print("=== upload files ===")
        for rel in UPLOADS:
            upload(pve, rel)

        print("=== env ===")
        for k, v in {
            "MAS_INGESTION_ONLY_STARTUP": "1",
            "MAS_SKIP_BACKGROUND_STARTUP": "0",
            "MOVER_INGEST_MODE": "api",
            "OEI_AIS_PROXY": "http://192.168.0.187:3000/api/oei/aisstream",
            "OPENSKY_MAX_AIRCRAFT": "500",
            "COLLECTOR_STAGGER_SEC": "3",
            "STATIC_BUILD_ON_STARTUP": "0",
            "WORKFLOW_AUTO_MONITOR_ENABLED": "0",
            "HEALTH_DB_TIMEOUT_SEC": "1",
            "HEALTH_REDIS_TIMEOUT_SEC": "1",
            "HEALTH_OPTIONAL_TIMEOUT_SEC": "1",
            "HEALTH_CREP_HTTP_TIMEOUT_SEC": "1",
        }.items():
            set_env(pve, k, v)

        print("=== restart ===")
        print(pve.bash("systemctl restart mas-orchestrator && sleep 25 && systemctl is-active mas-orchestrator"))

        ok = False
        for i in range(12):
            try:
                live = httpx.get("http://192.168.0.188:8001/live", timeout=8)
                health = httpx.get("http://192.168.0.188:8001/health", timeout=20)
                body = health.json()
                coll = next(
                    (c for c in body.get("components", []) if c.get("name") == "collectors"),
                    {},
                )
                print(
                    f"probe {i+1}: live={live.status_code} status={body.get('status')} "
                    f"collectors={coll.get('message') or coll.get('status')}"
                )
                if live.status_code == 200 and body.get("status") in ("healthy", "degraded"):
                    if coll.get("message") != "Collectors skipped (MAS_SKIP_BACKGROUND_STARTUP)":
                        ok = True
                        if i >= 3:
                            break
            except Exception as exc:
                print(f"probe {i+1}: {exc}")
            time.sleep(10)

        print("=== cpu ===")
        print(pve.bash("ps aux --sort=-%cpu | head -5"))

        print("=== journal ===")
        print(
            pve.bash(
                "journalctl -u mas-orchestrator --since '4 min ago' --no-pager | "
                "grep -Ei 'collector|ingest|opensky|ais|norad|earth ingest|fetched|startup' | tail -35"
            )[:4000]
        )

        try:
            ch = httpx.get("http://192.168.0.188:8001/api/crep/collectors/health", timeout=15)
            print("crep:", ch.status_code, ch.text[:300])
        except Exception as exc:
            print("crep:", exc)

        print("bbox start:", bbox())
        for i in range(8):
            time.sleep(30)
            b = bbox()
            print(f"bbox {i+1}: {b}")
            if b.get("aircraft", 0) > 10 or b.get("vessels", 0) > 0 or b.get("satellites", 0) > 0:
                print("SUCCESS")
                return 0
        return 0 if ok else 1
    finally:
        pve.close()


if __name__ == "__main__":
    raise SystemExit(main())
