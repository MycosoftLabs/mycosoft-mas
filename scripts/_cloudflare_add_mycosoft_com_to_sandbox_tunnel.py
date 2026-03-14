#!/usr/bin/env python3
"""Add mycosoft.com and www.mycosoft.com to Sandbox tunnel (VM 187).

Sandbox-as-production: same tunnel serves sandbox + production domains.
Requires: CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
Optional: CLOUDFLARE_SANDBOX_TUNNEL_ID - if not set, lists tunnels and uses first match for 'sandbox'

Run from MAS repo: python scripts/_cloudflare_add_mycosoft_com_to_sandbox_tunnel.py
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
        print("\nManual steps (Cloudflare Zero Trust > Networks > Tunnels):")
        print("  1. Edit Sandbox tunnel (VM 187)")
        print("  2. Public Hostnames: Add mycosoft.com -> http://localhost:3000")
        print("  3. Public Hostnames: Add www.mycosoft.com -> http://localhost:3000")
        print("  4. Keep sandbox.mycosoft.com -> http://localhost:3000")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

    tunnel_id = TUNNEL_ID
    if not tunnel_id:
        r = requests.get(
            f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/cfd_tunnel",
            headers=headers,
            timeout=30,
        )
        if not r.ok:
            print(f"ERROR: List tunnels failed: {r.status_code} - {r.text}")
            sys.exit(1)
        data = r.json()
        tunnels = data.get("result", []) or []
        for t in tunnels:
            name = (t.get("name") or "").lower()
            if "sandbox" in name:
                tunnel_id = t["id"]
                print(f"Found Sandbox tunnel: {t.get('name')} ({tunnel_id})")
                break
        if not tunnel_id and tunnels:
            # Fallback: mycosoft-tunnel typically serves VM 187 (sandbox.mycosoft.com)
            for t in tunnels:
                if (t.get("name") or "").lower() == "mycosoft-tunnel":
                    tunnel_id = t["id"]
                    print(f"Using mycosoft-tunnel as Sandbox tunnel: {tunnel_id}")
                    break
        if not tunnel_id and tunnels:
            print("Tunnels:", [t.get("name") for t in tunnels])
            print("Set CLOUDFLARE_SANDBOX_TUNNEL_ID to the Sandbox tunnel ID.")
            sys.exit(1)
        elif not tunnel_id:
            print("No tunnels found. Create Sandbox tunnel first.")
            sys.exit(1)

    # Sandbox-as-production: serve mycosoft.com, www, and sandbox from same tunnel
    config = {
        "config": {
            "ingress": [
                {"hostname": "mycosoft.com", "service": "http://localhost:3000", "originRequest": {}},
                {"hostname": "www.mycosoft.com", "service": "http://localhost:3000", "originRequest": {}},
                {"hostname": "sandbox.mycosoft.com", "service": "http://localhost:3000", "originRequest": {}},
                {"service": "http_status:404"},
            ]
        }
    }
    print(f"Updating tunnel {tunnel_id} to serve mycosoft.com, www.mycosoft.com, sandbox.mycosoft.com...")
    r2 = requests.put(
        f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/configurations",
        headers=headers,
        json=config,
        timeout=30,
    )
    if not r2.ok:
        print(f"ERROR: {r2.status_code} - {r2.text}")
        print("\nManual steps: Cloudflare Zero Trust > Networks > Tunnels > Sandbox > add hostnames.")
        sys.exit(1)
    print("Done. Sandbox tunnel now serves mycosoft.com, www.mycosoft.com, sandbox.mycosoft.com.")


if __name__ == "__main__":
    main()
