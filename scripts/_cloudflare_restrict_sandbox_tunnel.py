#!/usr/bin/env python3
"""Restrict Sandbox tunnel to serve only sandbox.mycosoft.com.

Removes mycosoft.com and www.mycosoft.com from Sandbox tunnel (Production owns those).
Requires: CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
Optional: CLOUDFLARE_SANDBOX_TUNNEL_ID - if not set, lists tunnels and uses first match for 'sandbox'

Run from MAS repo: python scripts/_cloudflare_restrict_sandbox_tunnel.py
"""

import os
import sys
from pathlib import Path

import requests

def _load_creds():
    for base in (Path(__file__).parent.parent, Path.cwd()):
        for f in (".credentials.local", ".env.local", ".env"):
            p = base / f
            if p.exists():
                for line in p.read_text().splitlines():
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        k, v = k.strip(), v.strip().strip('"\'')
                        if k and k not in os.environ:
                            os.environ[k] = v

_load_creds()

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
TUNNEL_ID = os.getenv("CLOUDFLARE_SANDBOX_TUNNEL_ID")


def main():
    if not ACCOUNT_ID or not TOKEN:
        print("ERROR: CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN required.")
        print("\nManual steps:")
        print("  1. Cloudflare Zero Trust > Networks > Tunnels")
        print("  2. Edit Sandbox tunnel - remove mycosoft.com, www.mycosoft.com from Public Hostnames")
        print("  3. Keep only sandbox.mycosoft.com -> http://localhost:3000")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

    tunnel_id = TUNNEL_ID
    if not tunnel_id:
        # List tunnels
        r = requests.get(
            f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/cfd_tunnel",
            headers=headers,
            timeout=30,
        )
        if not r.ok:
            print(f"ERROR: List tunnels failed: {r.status_code}")
            sys.exit(1)
        data = r.json()
        tunnels = data.get("result", []) or []
        for t in tunnels:
            if "sandbox" in (t.get("name") or "").lower():
                tunnel_id = t["id"]
                print(f"Found Sandbox tunnel: {t.get('name')} ({tunnel_id})")
                break
        if not tunnel_id and tunnels:
            print("Tunnels:", [t.get("name") for t in tunnels])
            print("Set CLOUDFLARE_SANDBOX_TUNNEL_ID to the Sandbox tunnel ID.")
            sys.exit(1)
        elif not tunnel_id:
            print("No tunnels found. Create Sandbox tunnel first.")
            sys.exit(1)

    config = {
        "config": {
            "ingress": [
                {"hostname": "sandbox.mycosoft.com", "service": "http://localhost:3000", "originRequest": {}},
                {"service": "http_status:404"},
            ]
        }
    }
    print(f"Updating tunnel {tunnel_id} to serve only sandbox.mycosoft.com...")
    r2 = requests.put(
        f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/configurations",
        headers=headers,
        json=config,
        timeout=30,
    )
    if not r2.ok:
        print(f"ERROR: {r2.status_code} - {r2.text}")
        sys.exit(1)
    print("Done. Sandbox tunnel now serves only sandbox.mycosoft.com.")


if __name__ == "__main__":
    main()
