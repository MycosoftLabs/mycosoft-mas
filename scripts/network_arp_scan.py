#!/usr/bin/env python3
"""
Network ARP Scan — Full IP/Device/MAC Map
Fallback when UniFi API login fails. Pings 192.168.0.x, reads ARP table,
optionally resolves hostnames via nslookup/reverse DNS.

Usage:
  python scripts/network_arp_scan.py
  python scripts/network_arp_scan.py --output json
  python scripts/network_arp_scan.py --subnet 192.168.0.0/24
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def ping_subnet(subnet: str = "192.168.0") -> None:
    """Ping all .1–.254 to populate ARP cache (Windows)."""
    import concurrent.futures
    def ping_one(ip: str) -> bool:
        try:
            r = subprocess.run(
                ["ping", "-n", "1", "-w", "500", ip],
                capture_output=True,
                timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            return r.returncode == 0
        except Exception:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        futures = [ex.submit(ping_one, f"{subnet}.{i}") for i in range(1, 255)]
        for f in concurrent.futures.as_completed(futures):
            f.result()


def get_arp_table() -> list[dict]:
    """Parse Windows arp -a output for 192.168.0.x."""
    try:
        out = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        text = out.stdout or ""
    except Exception as e:
        print(f"arp -a failed: {e}", file=sys.stderr)
        return []

    # Windows: 192.168.0.1    aa-bb-cc-dd-ee-ff    dynamic
    # Windows: 192.168.0.50   ff-ee-dd-cc-bb-aa    static
    pattern = re.compile(
        r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+([0-9a-fA-F\-:]+)\s+(dynamic|static|invalid)",
        re.MULTILINE,
    )
    rows: list[dict] = []
    seen: set[str] = set()
    for m in pattern.finditer(text):
        ip, mac_raw, kind = m.groups()
        if ip.startswith("192.168.0.") and ip not in seen:
            seen.add(ip)
            mac = mac_raw.replace("-", ":").upper()
            rows.append({
                "ip": ip,
                "mac": mac,
                "arp_type": kind,
                "hostname": "",  # optional: resolve later
            })
    return sorted(rows, key=lambda x: [int(p) for p in x["ip"].split(".")])


def main() -> int:
    parser = argparse.ArgumentParser(description="Network ARP scan for IP/MAC map")
    parser.add_argument("--output", choices=["table", "json"], default="table")
    parser.add_argument("--no-ping", action="store_true", help="Skip ping sweep, use current ARP cache only")
    parser.add_argument("--subnet", default="192.168.0", help="Subnet prefix, e.g. 192.168.0")
    args = parser.parse_args()

    if not args.no_ping:
        print("Pinging 192.168.0.1–254 to populate ARP cache...", file=sys.stderr)
        ping_subnet(args.subnet)
        print("Reading ARP table...", file=sys.stderr)

    rows = get_arp_table()

    if args.output == "json":
        out = {
            "devices": rows,
            "total": len(rows),
            "subnet": f"{args.subnet}.0/24",
            "source": "arp",
        }
        print(json.dumps(out, indent=2))
        return 0

    print(f"\nNetwork ARP Scan — {args.subnet}.x")
    print("=" * 90)
    print(f"{'IP':<18} {'MAC':<20} {'Type'}  Notes")
    print("-" * 90)
    for r in rows:
        ip = (r.get("ip") or "")[:17].ljust(17)
        mac = (r.get("mac") or "")[:19].ljust(19)
        atype = r.get("arp_type", "")
        host = r.get("hostname", "")
        note = host if host else ""
        print(f"{ip} {mac} {atype:<8} {note}")
    print("-" * 90)
    print(f"Total: {len(rows)} devices")
    return 0


if __name__ == "__main__":
    sys.exit(main())
