#!/usr/bin/env python3
"""Create Production Cloudflare tunnel for mycosoft.com and www.mycosoft.com.

Uses Cloudflare API. Requires:
  CLOUDFLARE_ACCOUNT_ID
  CLOUDFLARE_API_TOKEN (Account: Cloudflare Tunnel Edit, Zone: DNS Edit)
  CLOUDFLARE_ZONE_ID (mycosoft.com zone) - for CNAME records

Outputs tunnel token for use on VM 186. Add to .credentials.local:
  CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION=<token>

Run from MAS repo: python scripts/_cloudflare_create_production_tunnel.py
"""

import os
import sys
from pathlib import Path

import requests

# Load credentials
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
ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID") or os.getenv("CLOUDFLARE_ZONE_ID_PRODUCTION")
TUNNEL_NAME = "mycosoft-production"
SERVICE_URL = "http://localhost:3000"


def main():
    if not ACCOUNT_ID or not TOKEN:
        print("ERROR: CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN required.")
        print("Create API token at https://dash.cloudflare.com/profile/api-tokens")
        print("Permissions: Account > Cloudflare Tunnel > Edit, Zone > DNS > Edit")
        print("\nManual steps:")
        print("  1. Cloudflare Zero Trust > Networks > Tunnels")
        print("  2. Create tunnel: mycosoft-production")
        print("  3. Add Public Hostnames: mycosoft.com, www.mycosoft.com -> http://localhost:3000")
        print("  4. Copy tunnel token, add to VM 186 .env: CLOUDFLARE_TUNNEL_TOKEN=<token>")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

    # 1. Create tunnel
    print(f"Creating tunnel '{TUNNEL_NAME}'...")
    r = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/cfd_tunnel",
        headers=headers,
        json={"name": TUNNEL_NAME, "config_src": "cloudflare"},
        timeout=30,
    )
    if not r.ok:
        print(f"ERROR: Create tunnel failed: {r.status_code} - {r.text}")
        sys.exit(1)
    data = r.json()
    if not data.get("success"):
        print(f"ERROR: {data.get('errors', data)}")
        sys.exit(1)
    tunnel_id = data["result"]["id"]
    tunnel_token = data["result"].get("token")
    if not tunnel_token:
        # Token might be in credentials_file - try GET token endpoint
        rt = requests.get(
            f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/token",
            headers=headers,
            timeout=30,
        )
        if rt.ok and rt.json().get("success"):
            tunnel_token = rt.json().get("result", "")
    print(f"  Tunnel ID: {tunnel_id}")

    # 2. Configure ingress (mycosoft.com, www.mycosoft.com -> localhost:3000)
    config = {
        "config": {
            "ingress": [
                {"hostname": "mycosoft.com", "service": SERVICE_URL, "originRequest": {}},
                {"hostname": "www.mycosoft.com", "service": SERVICE_URL, "originRequest": {}},
                {"service": "http_status:404"},
            ]
        }
    }
    print("Configuring ingress (mycosoft.com, www.mycosoft.com -> localhost:3000)...")
    r2 = requests.put(
        f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/configurations",
        headers=headers,
        json=config,
        timeout=30,
    )
    if not r2.ok:
        print(f"WARN: Ingress config failed: {r2.status_code} - {r2.text}")
    else:
        print("  Ingress configured.")

    # 3. Create CNAME records if zone_id available (tunnel needs DNS)
    if ZONE_ID:
        # Cloudflare tunnel hostname format: <tunnel-id>.cfargotunnel.com
        cname_target = f"{tunnel_id}.cfargotunnel.com"
        for name in ["mycosoft.com", "www.mycosoft.com"]:
            record_name = "@" if name == "mycosoft.com" else "www"
            r3 = requests.post(
                f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
                headers=headers,
                json={
                    "type": "CNAME",
                    "name": record_name,
                    "content": cname_target,
                    "proxied": True,
                    "ttl": 1,
                },
                timeout=30,
            )
            if r3.ok and r3.json().get("success"):
                print(f"  DNS CNAME: {record_name} -> {cname_target}")
            elif r3.status_code == 409:
                print(f"  DNS {record_name}: already exists")
            else:
                print(f"  DNS {record_name}: {r3.status_code} - {r3.text[:200]}")
    else:
        print("  (No ZONE_ID - create CNAME manually: mycosoft.com, www -> <tunnel-id>.cfargotunnel.com)")

    if tunnel_token:
        print("\n" + "=" * 60)
        print("TUNNEL TOKEN (add to VM 186 .env or .credentials.local):")
        print("  CLOUDFLARE_TUNNEL_TOKEN_PRODUCTION=" + tunnel_token[:50] + "...")
        print("\nOn Production VM 186:")
        print("  sudo cloudflared service install <TOKEN>")
        print("  sudo systemctl enable cloudflared && sudo systemctl start cloudflared")
        print("=" * 60)
    else:
        print("\nGet token from Dashboard: Zero Trust > Networks > Tunnels > mycosoft-production > Configure")


if __name__ == "__main__":
    main()
