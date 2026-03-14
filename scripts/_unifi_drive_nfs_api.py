#!/usr/bin/env python3
"""
Use UniFi API to configure NFS on UniFi Drive (NAS) so Proxmox 202 can back up VMs.
Logs into UDM at 192.168.0.1, then accesses Drive/NFS via /proxy/drive on the console.
NAS is adopted by UDM — API lives on UDM, not on NAS IP.

Credentials: Read from .credentials.local (UNIFI_USERNAME, UNIFI_PASSWORD). Never prompt.
UDM: 192.168.0.1 (UNIFI_UDM_IP)
Proxmox to allow: 192.168.0.202

Usage:
  python scripts/_unifi_drive_nfs_api.py              # Probe + add NFS host
  python scripts/_unifi_drive_nfs_api.py --probe-only # Just probe, no changes
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_credentials() -> tuple[str, str, str]:
    creds_file = REPO_ROOT / ".credentials.local"
    if creds_file.exists():
        for line in creds_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
    return (
        os.environ.get("UNIFI_USERNAME", "morgan@mycosoft.org"),
        os.environ.get("UNIFI_PASSWORD", ""),
        os.environ.get("UNIFI_UDM_IP", "192.168.0.1"),
    )


def login_udm(session: requests.Session, base: str, username: str, password: str, debug: bool = False) -> bool:
    """Login to UDM — UniFi OS uses /api/auth/login; Network app uses /proxy/network/api/login."""
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {"username": username, "password": password}

    # UniFi OS first (UDM/UDM-Pro), then Network app
    for path in ["/api/auth/login", "/proxy/network/api/login", "/api/login"]:
        try:
            r = session.post(f"{base}{path}", headers=headers, json=payload, verify=False, timeout=15)
            if debug:
                print(f"POST {path} -> {r.status_code} | body: {r.text[:500]}", file=sys.stderr)
            if r.status_code in (200, 201):
                data = r.json() if r.text else {}
                # Legacy: meta.rc == "ok"
                if isinstance(data, dict) and data.get("meta", {}).get("rc") == "ok":
                    return True
                # UniFi OS: returns user profile (_id, username, roles)
                if isinstance(data, dict) and ("_id" in data or "username" in data or "token" in str(data).lower()):
                    return True
                if "token" in str(data).lower() or "data" in data or "success" in str(data).lower():
                    return True
            elif r.status_code in (401, 403) and debug:
                print(f"POST {path} -> {r.status_code}: {r.text[:300]}", file=sys.stderr)
        except Exception as e:
            if debug:
                print(f"POST {path} -> Exception: {e}", file=sys.stderr)
            continue
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="UniFi Drive NFS API — add Proxmox as NFS host")
    parser.add_argument("--udm", default=None, help="UDM IP (default: 192.168.0.1)")
    parser.add_argument("--proxmox-ip", default="192.168.0.202", help="Proxmox IP to allow NFS access")
    parser.add_argument("--probe-only", action="store_true", help="Probe endpoints only, no changes")
    parser.add_argument("--debug", action="store_true", help="Print login debug output")
    args = parser.parse_args()

    username, password, udm_ip = load_credentials()
    udm_ip = args.udm or udm_ip
    base = f"https://{udm_ip}"

    if not username or not password:
        print("UniFi credentials missing. Ensure UNIFI_USERNAME and UNIFI_PASSWORD are in .credentials.local.", file=sys.stderr)
        return 1

    session = requests.Session()

    if not login_udm(session, base, username, password, debug=args.debug):
        print("Login to UDM failed. Check credentials.", file=sys.stderr)
        return 1
    print("Logged in to UDM.")

    # Drive endpoints on UDM — when NAS is adopted, Drive app runs on console
    probe_paths = [
        "/proxy/drive/api/settings",
        "/proxy/drive/api/nfs",
        "/proxy/drive/api/settings/nfs",
        "/proxy/drive/api/nfs/hosts",
        "/proxy/drive/api/shares",
        "/proxy/drive/api/volumes",
        "/proxy/drive/api/settings/services",
    ]

    print("\n--- Probing Drive API on UDM ---")
    found = []
    for path in probe_paths:
        try:
            r = session.get(f"{base}{path}", headers={"Accept": "application/json"}, verify=False, timeout=10)
            if r.status_code == 200:
                try:
                    j = r.json()
                    found.append(path)
                    print(f"GET {path} -> 200 OK")
                    print(f"  {json.dumps(j, indent=2)[:800]}")
                except Exception:
                    print(f"GET {path} -> 200 (non-JSON, {len(r.text)} bytes)")
            elif r.status_code == 401:
                print(f"GET {path} -> 401 Unauthorized (session may not cover Drive)")
            elif r.status_code == 404:
                print(f"GET {path} -> 404")
            else:
                print(f"GET {path} -> {r.status_code}")
        except Exception as e:
            print(f"GET {path} -> Error: {e}")

    if not found:
        print("\nNo Drive API endpoints responded 200. Drive app may not be installed or NAS not adopted.")
        return 1

    if args.probe_only:
        print("\nProbe complete (--probe-only). No changes made.")
        return 0

    # Try to add NFS host — structure varies by UniFi version
    nfs_hosts_paths = ["/proxy/drive/api/nfs/hosts", "/proxy/drive/api/settings/nfs/hosts", "/proxy/drive/api/nfs"]
    for path in nfs_hosts_paths:
        try:
            r = session.get(f"{base}{path}", headers={"Accept": "application/json"}, verify=False, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json() if r.text else {}
            print(f"\nNFS config from {path}: {json.dumps(data, indent=2)[:1200]}")

            # Try POST to add host — common structures
            for payload in [
                {"host": args.proxmox_ip, "share": "share"},
                {"ip": args.proxmox_ip, "share": "share"},
                {"hosts": [args.proxmox_ip], "shares": ["share"]},
                {"address": args.proxmox_ip},
            ]:
                try:
                    pr = session.post(
                        f"{base}{path}",
                        headers={"Accept": "application/json", "Content-Type": "application/json"},
                        json=payload,
                        verify=False,
                        timeout=10,
                    )
                    if pr.status_code in (200, 201, 204):
                        print(f"POST {path} with {payload} -> {pr.status_code} OK")
                        print("NFS host added. Run: showmount -e 192.168.0.105 from Proxmox to verify.")
                        return 0
                    elif pr.status_code in (400, 409):
                        print(f"POST {path} -> {pr.status_code}: {pr.text[:300]}")
                except Exception as e:
                    pass
        except Exception as e:
            pass

    print("\nCould not add NFS host via API. Configure manually: UniFi Drive > Settings > Services > NFS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
