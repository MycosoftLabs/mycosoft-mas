#!/usr/bin/env python3
"""Add mycosoft.com and www.mycosoft.com to Supabase Auth redirect URLs.

Requires: SUPABASE_ACCESS_TOKEN (Personal Access Token from https://supabase.com/dashboard/account/tokens)
Project: Mycosoft.com Production (ref: hnevnsxnhfibhbsipqvz)

Run from MAS repo: python scripts/_supabase_add_mycosoft_com_redirect_urls.py
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

PROJECT_REF = "hnevnsxnhfibhbsipqvz"
TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")

# URLs to add for mycosoft.com production
REDIRECT_URLS = [
    "https://mycosoft.com",
    "https://www.mycosoft.com",
    "https://mycosoft.com/**",
    "https://www.mycosoft.com/**",
    "https://sandbox.mycosoft.com",
    "https://sandbox.mycosoft.com/**",
    "http://localhost:3010",
    "http://localhost:3010/**",
]


def main():
    if not TOKEN:
        print("ERROR: SUPABASE_ACCESS_TOKEN required.")
        print("\n1. Go to https://supabase.com/dashboard/account/tokens")
        print("2. Create a Personal Access Token")
        print("3. Set: export SUPABASE_ACCESS_TOKEN=your_token")
        print("   Or add to .credentials.local: SUPABASE_ACCESS_TOKEN=...")
        print("\nManual alternative: Supabase Dashboard -> Mycosoft.com Production ->")
        print("  Authentication -> URL Configuration -> Redirect URLs")
        print("  Add: https://mycosoft.com, https://www.mycosoft.com, https://mycosoft.com/**, https://www.mycosoft.com/**")
        sys.exit(1)

    url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/config/auth"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    # Get current config first
    r = requests.get(url, headers=headers, timeout=30)
    if not r.ok:
        print(f"ERROR: GET failed {r.status_code} - {r.text[:400]}")
        sys.exit(1)

    data = r.json()
    existing = set(data.get("redirect_urls") or [])
    combined = existing | set(REDIRECT_URLS)
    new_urls = sorted(combined)

    # PATCH to update
    payload = {
        "site_url": "https://mycosoft.com",
        "redirect_urls": new_urls,
    }

    r2 = requests.patch(url, headers=headers, json=payload, timeout=30)
    if not r2.ok:
        print(f"ERROR: PATCH failed {r2.status_code} - {r2.text[:400]}")
        sys.exit(1)

    print("Done. Auth redirect URLs updated:")
    for u in new_urls:
        print(f"  - {u}")
    print("\nSite URL set to https://mycosoft.com")


if __name__ == "__main__":
    main()
