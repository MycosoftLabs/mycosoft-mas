#!/usr/bin/env python3
"""Scan local COM ports and report MycoBrain detection status.

This script is intentionally small and deterministic (the previous version became duplicated/corrupt).

What it does:
- Lists Windows COM ports via pyserial
- Calls the local MycoBrain service (default http://localhost:8003) to fetch:
  - /health
  - /ports
  - /devices

Use this to quickly confirm:
- whether the desk device enumerated as a COM port at all
- whether the MycoBrain service marked it as is_mycobrain and/or connected
"""

from __future__ import annotations

import json
import sys
from typing import Any

import requests

try:
    import serial.tools.list_ports
except Exception:  # pragma: no cover
    serial = None  # type: ignore


SERVICE_URL = "http://localhost:8003"


def fetch_json(path: str, timeout_sec: int = 8) -> tuple[int, Any]:
    url = f"{SERVICE_URL}{path}"
    r = requests.get(url, timeout=timeout_sec)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("=" * 80)
    print("MycoBrain COM Port / Service Scan")
    print("=" * 80)
    print(f"SERVICE_URL: {SERVICE_URL}")

    # 1) Windows COM ports
    com_ports: list[str] = []
    if serial and hasattr(serial.tools, "list_ports"):
        com_ports = [p.device for p in serial.tools.list_ports.comports()]
    print("\n[1] Windows COM ports:")
    print(json.dumps(com_ports, indent=2))

    # 2) Service health
    print("\n[2] MycoBrain service health:")
    try:
        status, data = fetch_json("/health", timeout_sec=5)
        print(f"HTTP {status}")
        print(json.dumps(data, indent=2) if isinstance(data, dict) else str(data)[:400])
    except Exception as e:
        print(f"[ERROR] Cannot reach {SERVICE_URL}/health: {e}")
        sys.exit(1)

    # 3) Ports known to the service
    print("\n[3] Service /ports:")
    status, data = fetch_json("/ports", timeout_sec=8)
    print(f"HTTP {status}")
    if isinstance(data, dict):
        ports = data.get("ports", [])
        print(f"ports: {len(ports)}")
        # Print only the MycoBrain ports + any connected ports
        interesting = [
            p
            for p in ports
            if p.get("is_mycobrain") or p.get("is_connected")
        ]
        print("interesting ports:")
        print(json.dumps(interesting, indent=2)[:4000])
    else:
        print(str(data)[:800])

    # 4) Devices currently connected
    print("\n[4] Service /devices:")
    status, data = fetch_json("/devices", timeout_sec=8)
    print(f"HTTP {status}")
    if isinstance(data, dict):
        devices = data.get("devices", [])
        print(f"devices: {len(devices)}")
        print(json.dumps(devices, indent=2)[:4000])
    else:
        print(str(data)[:800])

    print("\nDone.")


if __name__ == "__main__":
    main()

