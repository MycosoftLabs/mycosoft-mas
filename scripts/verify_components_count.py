#!/usr/bin/env python3
"""Quick verify of components count in Supabase."""
import os
import requests
from pathlib import Path

def load_env(p):
    if p.exists():
        for L in p.read_text(encoding="utf-8").splitlines():
            if L and not L.startswith("#") and "=" in L:
                k, _, v = L.partition("=")
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

root = Path(__file__).resolve().parent.parent
for p in [root.parent.parent / "WEBSITE" / "website" / ".env.local", root / ".env"]:
    load_env(p)
url = (os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or ""
if not url or not key:
    print("Env not loaded")
    exit(1)
r = requests.get(
    f"{url}/rest/v1/components",
    headers={"apikey": key, "Authorization": f"Bearer {key}", "Prefer": "count=exact"},
    params={"select": "id"},
    timeout=10,
)
if r.ok:
    count = r.headers.get("Content-Range", "").split("/")[-1]
    print(f"Components count: {count}")
else:
    print(f"Error {r.status_code}: {r.text[:300]}")
