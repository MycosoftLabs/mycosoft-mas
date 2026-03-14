#!/usr/bin/env python3
"""
Probe UniFi Drive (NAS at 192.168.0.105) for API endpoints.
Credentials: read from .credentials.local (UNIFI_USERNAME, UNIFI_PASSWORD). Never prompt.

Usage:
  python scripts/_probe_unifi_drive_api.py
  python scripts/_probe_unifi_drive_api.py --nas 192.168.0.105
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
        os.environ.get("UNIFI_NAS_IP", "192.168.0.105"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe UniFi Drive API")
    parser.add_argument("--nas", default=None, help="NAS IP (default: 192.168.0.105)")
    args = parser.parse_args()

    username, password, nas_ip = load_credentials()
    nas_ip = args.nas or nas_ip
    base = f"https://{nas_ip}"

    if not username or not password:
        print(
            "UniFi credentials missing. Ensure UNIFI_USERNAME and UNIFI_PASSWORD are in .credentials.local.",
            file=sys.stderr,
        )
        return 1

    session = requests.Session()
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {"username": username, "password": password}

    # Login paths to try (UniFi OS, Drive, Network proxy)
    login_paths = [
        "/api/auth/login",
        "/proxy/drive/api/login",
        "/proxy/network/api/login",
        "/api/login",
    ]

    logged_in = False
    for path in login_paths:
        try:
            r = session.post(
                f"{base}{path}",
                headers=headers,
                json=payload,
                verify=False,
                timeout=10,
            )
            print(f"POST {path} -> {r.status_code}")
            if r.status_code in (200, 201):
                data = r.json() if r.text else {}
                if isinstance(data, dict) and data.get("meta", {}).get("rc") == "ok":
                    logged_in = True
                    print(f"  Login OK via {path}")
                    break
                if "token" in str(data).lower() or "data" in data or "success" in str(data).lower():
                    logged_in = True
                    print(f"  Login OK via {path}")
                    break
        except Exception as e:
            print(f"  Error: {e}")

    if not logged_in:
        print("Login failed on all paths. NAS may use different auth.", file=sys.stderr)
        # Continue probing anyway - some endpoints might work unauthenticated

    # Probe likely API paths for NFS / shares / services
    probe_paths = [
        "/api/drive/nfs",
        "/api/drive/nfs/hosts",
        "/api/drive/services/nfs",
        "/proxy/drive/api/nfs",
        "/proxy/drive/api/settings/nfs",
        "/api/v1/nfs",
        "/api/nfs",
        "/api/settings/services/nfs",
        "/api/shares",
        "/api/volumes",
        "/proxy/drive/api/shares",
    ]

    print("\n--- Probing API paths ---")
    for path in probe_paths:
        try:
            r = session.get(
                f"{base}{path}",
                headers={"Accept": "application/json"},
                verify=False,
                timeout=5,
            )
            if r.status_code == 200:
                try:
                    j = r.json()
                    print(f"GET {path} -> 200 OK")
                    print(f"  {json.dumps(j, indent=2)[:500]}...")
                except Exception:
                    print(f"GET {path} -> 200 (non-JSON)")
            elif r.status_code == 401:
                print(f"GET {path} -> 401 Unauthorized")
            elif r.status_code == 404:
                pass  # skip 404 clutter
            else:
                print(f"GET {path} -> {r.status_code}")
        except Exception as e:
            print(f"GET {path} -> Error: {e}")

    # Also try /api root to discover structure
    print("\n--- Discovery ---")
    for path in ["/api", "/api/", "/proxy/", "/drive/api/"]:
        try:
            r = session.get(
                f"{base}{path}",
                headers={"Accept": "application/json"},
                verify=False,
                timeout=5,
            )
            if r.status_code == 200 and r.text:
                print(f"GET {path} -> {r.status_code}")
                print(r.text[:300])
        except Exception as e:
            print(f"GET {path} -> {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
