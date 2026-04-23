#!/usr/bin/env python3
"""Purge Cloudflare cache for mycosoft.com. Loads CLOUDFLARE_* from website .env.local."""
import os
from pathlib import Path

base = Path(__file__).resolve().parent.parent.parent.parent  # CODE (scripts->mycosoft-mas->MAS->CODE)
env_path = base / "WEBSITE" / "website" / ".env.local"
if not env_path.exists():
    env_path = base / "website" / ".env.local"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

token = os.environ.get("CLOUDFLARE_API_TOKEN")
zone = os.environ.get("CLOUDFLARE_ZONE_ID")
if not token or not zone:
    print("SKIP: CLOUDFLARE_API_TOKEN or CLOUDFLARE_ZONE_ID not set")
    exit(0)

try:
    import urllib.request
    import json
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{zone}/purge_cache",
        data=json.dumps({"purge_everything": True}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    if data.get("success"):
        print("Cloudflare cache purged successfully.")
    else:
        print("Purge request returned:", data)
except Exception as e:
    print("Purge failed:", e)
    exit(1)
