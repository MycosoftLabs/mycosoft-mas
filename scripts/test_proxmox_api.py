#!/usr/bin/env python3
"""Proxmox API probe — credentials from env only (never hardcode secrets)."""

import json
import os
import sys
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

REPO = Path(__file__).resolve().parent.parent


def load_env() -> None:
    cred = REPO / ".credentials.local"
    if cred.exists():
        for line in cred.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.strip().startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    load_env()
    tid = os.environ.get("PROXMOX_TOKEN_ID", "")
    sec = os.environ.get("PROXMOX_TOKEN_SECRET", "")
    host = os.environ.get("PROXMOX_HOST", "192.168.0.202")
    if not tid or not sec:
        print(
            "Set PROXMOX_TOKEN_ID and PROXMOX_TOKEN_SECRET (Datacenter → Permissions → API Tokens)",
            file=sys.stderr,
        )
        return 1
    base_url = f"https://{host}:8006/api2/json"
    session = requests.Session()
    session.verify = False
    session.headers["Authorization"] = f"PVEAPIToken={tid}={sec}"

    r = session.get(f"{base_url}/version", timeout=15)
    print("version:", r.status_code, r.json().get("data", {}))
    r = session.get(f"{base_url}/nodes", timeout=15)
    print("nodes:", r.status_code)
    nodes = r.json().get("data", [])
    node_name = nodes[0].get("node") if nodes else None
    if node_name:
        r = session.get(f"{base_url}/nodes/{node_name}/qemu", timeout=15)
        print("qemu:", r.status_code)
        for vm in r.json().get("data", [])[:20]:
            print(f"  {vm.get('vmid')} {vm.get('name')} {vm.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
