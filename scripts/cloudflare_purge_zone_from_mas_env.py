"""Load MAS .credentials.local (utf-8) and purge Cloudflare zone cache (purge_everything)."""
import json
import os
import urllib.request
from pathlib import Path

mas = Path(__file__).resolve().parent.parent
_force = {"CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_ZONE_ID", "CLOUDFLARE_ZONE_ID_PRODUCTION"}
for line in (mas / ".credentials.local").read_text(encoding="utf-8", errors="replace").splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        val = v.strip().strip('"').strip("'")
        k = k.strip()
        if k in _force or k not in os.environ:
            os.environ[k] = val

token = os.environ.get("CLOUDFLARE_API_TOKEN")
zone = os.environ.get("CLOUDFLARE_ZONE_ID")
if not token or not zone:
    raise SystemExit("CLOUDFLARE_API_TOKEN or CLOUDFLARE_ZONE_ID missing")

req = urllib.request.Request(
    f"https://api.cloudflare.com/client/v4/zones/{zone}/purge_cache",
    data=json.dumps({"purge_everything": True}).encode(),
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
    method="POST",
)
with urllib.request.urlopen(req, timeout=20) as r:
    data = json.loads(r.read().decode())
print("Cloudflare:", "purged" if data.get("success") else data)
