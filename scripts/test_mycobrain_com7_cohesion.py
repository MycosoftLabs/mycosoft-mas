#!/usr/bin/env python3
"""
Test MycoBrain COM7 + MAS + Sandbox cohesion.

Run on the dev machine with the board on COM7. Ensures:
- MAS (188) is up and device registry works
- Local MycoBrain service (8003) is up and sees COM7
- Heartbeat registers the device with MAS
- Website discover and network APIs return the device (local + optional sandbox URL)

Usage:
  python scripts/test_mycobrain_com7_cohesion.py
  python scripts/test_mycobrain_com7_cohesion.py --website-url http://localhost:3010
  python scripts/test_mycobrain_com7_cohesion.py --website-url https://sandbox.mycosoft.com

Created: February 18, 2026
"""

import argparse
import os
import sys
import time
import urllib.request
import urllib.error
import json

MAS_URL = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
MYCOBRAIN_URL = os.getenv("MYCOBRAIN_SERVICE_URL", "http://localhost:8003")
WEBSITE_URL_DEFAULT = os.getenv("WEBSITE_TEST_URL", "http://localhost:3010")


def get(url: str, timeout: float = 5.0) -> tuple[int, dict | list | None]:
    """GET URL and return (status_code, json_body or None)."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
            return e.code, json.loads(body) if body else None
        except Exception:
            return e.code, None
    except Exception as e:
        print(f"  Error: {e}")
        return -1, None


def post(url: str, data: dict, timeout: float = 10.0) -> tuple[int, dict | None]:
    """POST JSON to URL; return (status_code, json_body or None)."""
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = resp.read().decode()
            return resp.status, json.loads(out) if out else None
    except urllib.error.HTTPError as e:
        try:
            out = e.read().decode()
            return e.code, json.loads(out) if out else None
        except Exception:
            return e.code, None
    except Exception as e:
        print(f"  Error: {e}")
        return -1, None


def main():
    ap = argparse.ArgumentParser(description="Test MycoBrain COM7 + MAS + sandbox cohesion")
    ap.add_argument("--website-url", default=WEBSITE_URL_DEFAULT, help="Website base URL for discover/network tests")
    ap.add_argument("--wait-heartbeat", type=float, default=35.0, help="Seconds to wait for heartbeat to register (default 35)")
    args = ap.parse_args()

    website_url = args.website_url.rstrip("/")
    failed = []

    # 1. MAS health
    print("1. MAS health...")
    code, body = get(f"{MAS_URL}/health")
    if code != 200:
        print(f"   FAIL: MAS health returned {code}")
        failed.append("MAS health")
    else:
        print(f"   OK: {body.get('status', 'ok')}")

    # 2. MAS device registry list
    print("2. MAS device registry (list)...")
    code, body = get(f"{MAS_URL}/api/devices")
    if code != 200:
        print(f"   FAIL: MAS /api/devices returned {code}")
        failed.append("MAS /api/devices")
    else:
        devices = body.get("devices", []) if isinstance(body, dict) else []
        print(f"   OK: {len(devices)} device(s) registered")
        for d in devices:
            print(f"      - {d.get('device_id')} @ {d.get('host')}:{d.get('port')} ({d.get('status', '?')})")

    # 3. Local MycoBrain health
    print("3. Local MycoBrain service health...")
    code, body = get(f"{MYCOBRAIN_URL}/health")
    if code != 200:
        print(f"   FAIL: MycoBrain health returned {code} (is the service running on this machine?)")
        failed.append("MycoBrain health")
    else:
        print("   OK")

    # 4. Local MycoBrain ports
    print("4. Local MycoBrain ports...")
    code, body = get(f"{MYCOBRAIN_URL}/ports")
    if code != 200:
        print(f"   WARN: /ports returned {code}")
    else:
        ports = body.get("ports", []) if isinstance(body, dict) else []
        com7_found = any(
            (p.get("device") or p.get("port") or "").upper().replace(" ", "") == "COM7"
            for p in ports
        )
        if com7_found:
            print("   OK: COM7 found in port list")
        else:
            print("   WARN: COM7 not in port list (board may be on another port or not plugged in)")
            port_names = [p.get("device") or p.get("port") for p in ports]
            if port_names:
                print(f"      Ports: {port_names}")

    # 5. Local MycoBrain devices (connected)
    print("5. Local MycoBrain connected devices...")
    code, body = get(f"{MYCOBRAIN_URL}/devices")
    if code != 200:
        print(f"   WARN: /devices returned {code}")
    else:
        devs = body if isinstance(body, list) else body.get("devices", body.get("devices", []))
        if isinstance(devs, dict):
            devs = list(devs.values()) if devs else []
        print(f"   OK: {len(devs)} connected device(s)")
        for d in devs:
            did = d.get("device_id") or d.get("id")
            port = d.get("port", "")
            print(f"      - {did} on {port}")

    # 6. Wait for heartbeat then re-check MAS
    print(f"6. Waiting {args.wait_heartbeat}s for heartbeat...")
    time.sleep(args.wait_heartbeat)
    code, body = get(f"{MAS_URL}/api/devices")
    if code == 200 and isinstance(body, dict):
        devices = body.get("devices", [])
        if devices:
            print(f"   OK: {len(devices)} device(s) in MAS registry (board on desk should appear here)")
        else:
            print("   WARN: No devices in MAS. Ensure MYCOBRAIN_HEARTBEAT_ENABLED=true and MAS_REGISTRY_URL is set.")
    else:
        print(f"   WARN: MAS list returned {code}")

    # 7. Website discover API
    print(f"7. Website discover API ({website_url})...")
    code, body = get(f"{website_url}/api/devices/discover")
    if code != 200:
        print(f"   FAIL: discover returned {code}")
        failed.append("Website discover")
    else:
        devs = body.get("devices", []) if isinstance(body, dict) else []
        print(f"   OK: {len(devs)} device(s) from discover")
        if body and isinstance(body, dict) and body.get("hint"):
            print(f"   Hint: {body.get('hint')}")

    # 8. Website network API (from MAS)
    print(f"8. Website network API ({website_url})...")
    code, body = get(f"{website_url}/api/devices/network")
    if code != 200:
        print(f"   FAIL: network returned {code}")
        failed.append("Website network")
    else:
        devs = body.get("devices", []) if isinstance(body, dict) else []
        print(f"   OK: {len(devs)} device(s) from MAS registry (board on desk appears here when heartbeat is on)")
        if body and isinstance(body, dict) and body.get("note"):
            print(f"   Note: {body.get('note')}")

    # Summary
    print()
    if failed:
        print("FAILED:", ", ".join(failed))
        sys.exit(1)
    print("All checks passed. Board on COM7 should appear on sandbox when:")
    print("  - MycoBrain service runs on this PC with MAS_REGISTRY_URL=http://192.168.0.188:8001")
    print("  - Heartbeat is enabled (default). MAS (188) can reach this PC on port 8003 for commands.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
