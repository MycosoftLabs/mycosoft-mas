#!/usr/bin/env python3
"""Add CNAME records for mycosoft.com and www.mycosoft.com to point to the tunnel."""

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

ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
TUNNEL_ID = "bd385313-a44a-47ae-8f8a-581608118127"
TARGET = f"{TUNNEL_ID}.cfargotunnel.com"

def main():
    if not ZONE_ID or not TOKEN:
        print("ERROR: CLOUDFLARE_ZONE_ID and CLOUDFLARE_API_TOKEN required.")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    base = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records"

    # Check existing
    for name in ["mycosoft.com", "www.mycosoft.com"]:
        r = requests.get(base, headers=headers, params={"name": name}, timeout=30)
        if not r.ok:
            print(f"ERROR: {r.status_code} - {r.text[:200]}")
            sys.exit(1)
        recs = r.json().get("result") or []
        if recs:
            rec = recs[0]
            if rec.get("type") == "CNAME" and rec.get("content", "").rstrip(".") == TARGET:
                print(f"  {name} already points to tunnel.")
                continue
            # Update
            r2 = requests.put(f"{base}/{rec['id']}", headers=headers, json={
                "type": "CNAME",
                "name": name,
                "content": TARGET,
                "ttl": 1,
                "proxied": True,
            }, timeout=30)
        else:
            r2 = requests.post(base, headers=headers, json={
                "type": "CNAME",
                "name": name,
                "content": TARGET,
                "ttl": 1,
                "proxied": True,
            }, timeout=30)
        if not r2.ok:
            print(f"ERROR {name}: {r2.status_code} - {r2.text[:300]}")
            sys.exit(1)
        print(f"  {name} -> {TARGET}")

    print("Done. mycosoft.com and www.mycosoft.com should resolve to the tunnel.")

if __name__ == "__main__":
    main()
