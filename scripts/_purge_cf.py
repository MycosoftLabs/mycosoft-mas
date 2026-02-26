#!/usr/bin/env python3
"""Purge Cloudflare cache for mycosoft.com."""
import os, urllib.request, json
from pathlib import Path

env = Path(__file__).parent.parent.parent.parent / "WEBSITE" / "website" / ".env.local"
for line in env.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

token = os.environ.get("CLOUDFLARE_API_TOKEN")
zone = os.environ.get("CLOUDFLARE_ZONE_ID")
if not token or not zone:
    print("No CF credentials found"); exit(1)

req = urllib.request.Request(
    f"https://api.cloudflare.com/client/v4/zones/{zone}/purge_cache",
    method="POST"
)
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Content-Type", "application/json")
req.data = json.dumps({"purge_everything": True}).encode()

with urllib.request.urlopen(req, timeout=15) as r:
    data = json.loads(r.read())
    if data.get("success"):
        print("Cloudflare cache purged successfully.")
    else:
        print("CF purge response:", data)
