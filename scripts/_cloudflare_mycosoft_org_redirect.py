#!/usr/bin/env python3
"""Add 301 redirect: mycosoft.org and www.mycosoft.org -> https://mycosoft.com/about.

Requires mycosoft.org zone in Cloudflare. Uses Single Redirect rule (zone-level).
Requires: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID (for zone discovery)
Optional: CLOUDFLARE_ZONE_ID_MYCOSOFT_ORG (mycosoft.org zone ID; auto-discovered if not set)

Run from MAS repo: python scripts/_cloudflare_mycosoft_org_redirect.py
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

TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
ZONE_ID_ORG = os.getenv("CLOUDFLARE_ZONE_ID_MYCOSOFT_ORG")


def _discover_zone_id(headers):
    """List zones and find mycosoft.org zone ID."""
    r = requests.get(
        "https://api.cloudflare.com/client/v4/zones",
        headers=headers,
        params={"name": "mycosoft.org"},
        timeout=30,
    )
    if not r.ok:
        return None
    results = r.json().get("result") or []
    for z in results:
        if z.get("name") == "mycosoft.org":
            return z.get("id")
    return None


def main():
    if not TOKEN:
        print("ERROR: CLOUDFLARE_API_TOKEN required.")
        print("\nManual steps (Cloudflare mycosoft.org zone):")
        print("  1. Rules > Single Redirects")
        print("  2. Create rule: When hostname is mycosoft.org OR www.mycosoft.org")
        print("     Then redirect to https://mycosoft.com/about, status 301")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    zone_id = ZONE_ID_ORG
    if not zone_id:
        zone_id = _discover_zone_id(headers)
    if not zone_id:
        print("ERROR: CLOUDFLARE_ZONE_ID_MYCOSOFT_ORG not set and could not discover mycosoft.org zone.")
        print("  Add CLOUDFLARE_ZONE_ID_MYCOSOFT_ORG to .credentials.local (from Cloudflare dashboard)")
        print("\nManual steps (Cloudflare mycosoft.org zone):")
        print("  1. Rules > Single Redirects")
        print("  2. Create rule: When hostname is mycosoft.org OR www.mycosoft.org")
        print("     Then redirect to https://mycosoft.com/about, status 301")
        sys.exit(1)

    # Get or create http_request_dynamic_redirect phase ruleset
    r = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets",
        headers=headers,
        params={"phase": "http_request_dynamic_redirect"},
        timeout=30,
    )
    if not r.ok:
        print(f"ERROR: List rulesets: {r.status_code} - {r.text}")
        sys.exit(1)
    data = r.json()
    rulesets = data.get("result", []) or []
    ruleset_id = None
    for rs in rulesets:
        if rs.get("phase") == "http_request_dynamic_redirect":
            ruleset_id = rs.get("id")
            break

    rule = {
        "action": "redirect",
        "expression": '(http.host eq "mycosoft.org") or (http.host eq "www.mycosoft.org")',
        "description": "Redirect mycosoft.org to mycosoft.com/about",
        "action_parameters": {
            "from_value": {
                "target_url": {"value": "https://mycosoft.com/about"},
                "status_code": 301,
            }
        },
    }

    if ruleset_id:
        # Get current rules and add ours
        r2 = requests.get(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets/{ruleset_id}",
            headers=headers,
            timeout=30,
        )
        if not r2.ok:
            print(f"ERROR: Get ruleset: {r2.status_code}")
            sys.exit(1)
        rs_data = r2.json().get("result", {})
        rules = rs_data.get("rules", []) or []
        # Avoid duplicate
        for rl in rules:
            if "mycosoft.org" in (rl.get("expression") or ""):
                print("Redirect rule already exists.")
                sys.exit(0)
        rules.append(rule)
        r3 = requests.put(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets/{ruleset_id}",
            headers=headers,
            json={"rules": rules},
            timeout=30,
        )
    else:
        # Create new ruleset
        r3 = requests.post(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets",
            headers=headers,
            json={
                "name": "mycosoft.org redirects",
                "kind": "zone",
                "phase": "http_request_dynamic_redirect",
                "rules": [rule],
            },
            timeout=30,
        )

    if not r3.ok:
        print(f"ERROR: {r3.status_code} - {r3.text}")
        sys.exit(1)
    print("Redirect rule added: mycosoft.org, www.mycosoft.org -> https://mycosoft.com/about (301)")


if __name__ == "__main__":
    main()
