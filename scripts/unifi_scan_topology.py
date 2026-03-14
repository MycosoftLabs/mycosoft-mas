#!/usr/bin/env python3
"""
UniFi Dream Machine Topology Scan
Fetches all devices and clients from Ubiquiti UDM/UDM-Pro via REST API.
Outputs MAC, IP, vendor, hostname for topology mapping and Ubiquiti labeling.

Credentials: read from .credentials.local (UNIFI_USERNAME, UNIFI_PASSWORD). Never prompt.
UDM IP: UNIFI_UDM_IP (default 192.168.0.1)

Usage:
  python scripts/unifi_scan_topology.py
  python scripts/unifi_scan_topology.py --output json
  python scripts/unifi_scan_topology.py --udm 192.168.0.1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add repo root for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_credentials() -> tuple[str, str, str]:
    """Load UniFi credentials from .credentials.local or env."""
    creds_file = REPO_ROOT / ".credentials.local"
    if creds_file.exists():
        for line in creds_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                os.environ[k] = v
    return (
        os.environ.get("UNIFI_USERNAME", ""),
        os.environ.get("UNIFI_PASSWORD", ""),
        os.environ.get("UNIFI_UDM_IP", "192.168.0.1"),
    )


def unifi_login(session: "requests.Session", base_url: str, username: str, password: str) -> bool:
    """Login to UniFi Controller. Tries Network app login then UniFi OS auth."""
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {"username": username, "password": password}
    verify = False

    # Try Network app login (common for UDM)
    for path in ["/proxy/network/api/login", "/api/login"]:
        try:
            r = session.post(
                f"{base_url}{path}",
                headers=headers,
                json=payload,
                verify=verify,
                timeout=15,
            )
            if r.status_code in (200, 201):
                data = r.json() if r.text else {}
                if isinstance(data, dict) and data.get("meta", {}).get("rc") == "ok":
                    return True
                if "token" in str(data).lower() or "data" in data:
                    return True
        except Exception as e:
            continue

    # Try UniFi OS auth
    try:
        r = session.post(
            f"{base_url}/api/auth/login",
            headers=headers,
            json=payload,
            verify=verify,
            timeout=15,
        )
        if r.status_code in (200, 201):
            return True
    except Exception:
        pass
    return False


def fetch_json(session: "requests.Session", base_url: str, path: str) -> list | dict:
    """GET JSON from UniFi API."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    r = session.get(
        f"{base_url}{path}",
        headers={"Accept": "application/json"},
        verify=False,
        timeout=15,
    )
    r.raise_for_status()
    return r.json() if r.text else []


def main() -> int:
    import requests

    parser = argparse.ArgumentParser(description="UniFi UDM topology scan")
    parser.add_argument("--udm", default=None, help="UDM IP (default: UNIFI_UDM_IP or 192.168.0.1)")
    parser.add_argument("--output", choices=["table", "json"], default="table")
    parser.add_argument("--site", default="default", help="UniFi site name")
    args = parser.parse_args()

    username, password, udm_ip = load_credentials()
    udm_ip = args.udm or udm_ip
    base_url = f"https://{udm_ip}"
    if ":" not in udm_ip and not udm_ip.endswith("/"):
        base_url = f"https://{udm_ip}"

    if not username or not password:
        print(
            "UniFi credentials missing. Ensure UNIFI_USERNAME and UNIFI_PASSWORD are in .credentials.local.",
            file=sys.stderr,
        )
        return 1

    session = requests.Session()
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if not unifi_login(session, base_url, username, password):
        print("UniFi login failed. Check credentials and UDM IP.", file=sys.stderr)
        return 1

    # Fetch clients (connected devices) and all users (including offline)
    clients: list = []
    devices: list = []
    all_users: list = []

    for path, name in [
        (f"/proxy/network/api/s/{args.site}/stat/sta", "clients"),
        (f"/proxy/network/api/s/{args.site}/stat/alluser", "all_users"),
        (f"/proxy/network/api/s/{args.site}/stat/device", "devices"),
    ]:
        try:
            data = fetch_json(session, base_url, path)
            if isinstance(data, dict) and "data" in data:
                data = data["data"]
            if name == "clients":
                clients = data if isinstance(data, list) else []
            elif name == "all_users":
                all_users = data if isinstance(data, list) else []
            else:
                devices = data if isinstance(data, list) else []
        except Exception as e:
            print(f"Warning: could not fetch {path}: {e}", file=sys.stderr)

    # Merge: prefer clients (online) data, augment with all_users for offline
    seen_mac: set[str] = set()
    rows: list[dict] = []
    for c in clients:
        mac = (c.get("mac") or "").upper().replace("-", ":")
        if mac and mac not in seen_mac:
            seen_mac.add(mac)
            ip = c.get("ip") or c.get("fixed_ip") or ""
            hostname = c.get("hostname") or c.get("name") or ""
            rows.append({
                "mac": mac,
                "ip": ip,
                "hostname": hostname,
                "vendor": c.get("oui", ""),
                "type": c.get("type", "unknown"),
                "online": True,
            })
    for u in all_users:
        mac = (u.get("mac") or "").upper().replace("-", ":")
        if mac and mac not in seen_mac:
            seen_mac.add(mac)
            ip = u.get("ip") or u.get("fixed_ip") or ""
            hostname = u.get("hostname") or u.get("name") or ""
            rows.append({
                "mac": mac,
                "ip": ip,
                "hostname": hostname,
                "vendor": u.get("oui", ""),
                "type": u.get("type", "unknown"),
                "online": u.get("last_seen", 0) > 0,
            })

    # Add UniFi devices (APs, switches, UDM itself)
    for d in devices:
        mac = (d.get("mac") or "").upper().replace("-", ":")
        if mac and mac not in seen_mac:
            seen_mac.add(mac)
            ip = d.get("ip") or ""
            name = d.get("name") or d.get("hostname") or ""
            rows.append({
                "mac": mac,
                "ip": ip,
                "hostname": name,
                "vendor": d.get("oui", ""),
                "type": "unifi_device",
                "online": True,
            })

    # Filter to 192.168.0.x
    def in_subnet(ip: str) -> bool:
        if not ip:
            return False
        parts = ip.split(".")
        return len(parts) == 4 and parts[0] == "192" and parts[1] == "168" and parts[2] == "0"

    rows = [r for r in rows if in_subnet(r.get("ip", "")) or not r.get("ip")]

    if args.output == "json":
        print(json.dumps({"devices": rows, "total": len(rows)}, indent=2))
        return 0

    # Table output
    print(f"\nUniFi Topology Scan — 192.168.0.x (UDM: {udm_ip})")
    print("=" * 80)
    print(f"{'IP':<18} {'MAC':<20} {'Hostname':<25} {'Vendor/Type':<20} {'Online'}")
    print("-" * 80)
    for r in sorted(rows, key=lambda x: (x.get("ip") or "zzz")):
        ip = (r.get("ip") or "")[:17].ljust(17)
        mac = (r.get("mac") or "")[:19].ljust(19)
        hostname = (r.get("hostname") or "")[:24].ljust(24)
        vendor = (r.get("vendor") or r.get("type") or "")[:19].ljust(19)
        online = "yes" if r.get("online") else "no"
        print(f"{ip} {mac} {hostname} {vendor} {online}")
    print("-" * 80)
    print(f"Total: {len(rows)} devices")
    return 0


if __name__ == "__main__":
    sys.exit(main())
