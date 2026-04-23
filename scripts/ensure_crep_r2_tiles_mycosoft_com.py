#!/usr/bin/env python3
"""
Idempotent: create R2 bucket crep-tiles-prod, attach custom domain tiles.mycosoft.com, set CORS.

Loads CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_ZONE_ID from
MAS .credentials.local (same pattern as other scripts). No secrets to stdout.
Apr 17, 2026
Use: python ensure_crep_r2_tiles_mycosoft_com.py [--verify]  (verify: only GET /user/tokens/verify)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

BUCKET = "crep-tiles-prod"
TILE_HOST = "tiles.mycosoft.com"


def _load_creds() -> None:
    for base in (Path(__file__).resolve().parent.parent, Path.cwd()):
        for name in (".credentials.local",):
            p = base / name
            if not p.exists():
                continue
            _force = {
                "CLOUDFLARE_API_TOKEN",
                "CLOUDFLARE_R2_API_TOKEN",
                "CF_ACCOUNT_R2_TOKEN",
                "CLOUDFLARE_ACCOUNT_ID",
                "CLOUDFLARE_ZONE_ID",
            }
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"\'')
                if not k:
                    continue
                if k in _force or k not in os.environ:
                    os.environ[k] = v


def _r2_token_source() -> tuple[str, str]:
    # Prefer unified CLOUDFLARE_API_TOKEN (often updated with R2) before legacy R2-only keys,
    # so a stale CLOUDFLARE_R2_API_TOKEN in .credentials.local does not win.
    for k in (
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_R2_API_TOKEN",
        "CF_ACCOUNT_R2_TOKEN",
    ):
        t = (os.environ.get(k) or "").strip()
        if t:
            return k, t
    return "", ""


def _api_headers() -> tuple[dict[str, str], str]:
    src, t = _r2_token_source()
    if not t:
        return {}, ""
    return {
        "Authorization": f"Bearer {t}",
        "Content-Type": "application/json",
    }, src


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("--verify", "-V"):
        _load_creds()
        h, token_key = _api_headers()
        if not h:
            print("ERROR: no API token in env / .credentials.local", file=sys.stderr)
            return 1
        rv = requests.get(
            "https://api.cloudflare.com/client/v4/user/tokens/verify",
            headers={"Authorization": h["Authorization"]},
            timeout=30,
        )
        print("Token source:", token_key)
        print("GET /user/tokens/verify", rv.status_code, rv.text[:2500])
        if not rv.ok:
            print(
                "If 401 with code 1000: the string in CLOUDFLARE_API_TOKEN is not valid. "
                "Create a new API token in Cloudflare (or re-copy) and paste the full value into .credentials.local.",
                file=sys.stderr,
            )
            return 1
        return 0
    _load_creds()
    h, token_key = _api_headers()
    if not h:
        print("ERROR: set CLOUDFLARE_R2_API_TOKEN (Account R2:Edit) or CLOUDFLARE_API_TOKEN", file=sys.stderr)
        return 1
    print("Using API credentials from", token_key, file=sys.stderr)
    acc = (os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    zone = (os.environ.get("CLOUDFLARE_ZONE_ID") or "").strip()
    if not acc:
        print("ERROR: CLOUDFLARE_ACCOUNT_ID", file=sys.stderr)
        return 1
    if not zone:
        print("ERROR: CLOUDFLARE_ZONE_ID (mycosoft.com zone) required for R2 custom domain", file=sys.stderr)
        return 1

    base = f"https://api.cloudflare.com/client/v4/accounts/{acc}/r2/buckets"

    r = requests.get(base, headers=h, params={"per_page": 200}, timeout=60)
    if not r.ok:
        print("LIST buckets", r.status_code, f"token={token_key}", r.text[:2000], file=sys.stderr)
        try:
            for err in (r.json() or {}).get("errors") or ():
                if str(err.get("code")) == "10042" or "enable R2" in (err.get("message") or ""):
                    print(
                        "HINT: R2 is not enabled on this account. Open Cloudflare Dashboard → R2 →"
                        " Get started / create a bucket, then re-run this script.",
                        file=sys.stderr,
                    )
        except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
            pass
        if r.status_code in (401, 403) and "10042" not in (r.text or ""):
            print(
                "HINT: token needs Account R2 read/write, or .credentials is stale; "
                "or remove duplicate CLOUDFLARE_R2_API_TOKEN if narrow.",
                file=sys.stderr,
            )
        return 1
    data = r.json()
    res = data.get("result")
    if isinstance(res, dict):
        rb = res.get("buckets") or []
    else:
        rb = res or []
    names = set()
    for b in rb or []:
        if isinstance(b, dict) and b.get("name"):
            names.add(b.get("name"))

    if BUCKET not in names:
        r2 = requests.post(
            base, headers=h, data=json.dumps({"name": BUCKET}), timeout=60
        )
        if not r2.ok and "already exists" not in (r2.text or "").lower():
            print("CREATE bucket", r2.status_code, r2.text[:2000], file=sys.stderr)
            if r2.status_code not in (200, 201, 409):
                return 1
    print("OK: bucket", BUCKET)

    durl = f"https://api.cloudflare.com/client/v4/accounts/{acc}/r2/buckets/{BUCKET}/domains/custom"
    dr = requests.get(durl, headers=h, timeout=60)
    have = False
    if dr.ok:
        doms = (dr.json().get("result") or {}).get("domains") or []
        for d in doms:
            if isinstance(d, dict) and d.get("domain") == TILE_HOST:
                have = True
                break
    if not have:
        body = json.dumps(
            {
                "domain": TILE_HOST,
                "enabled": True,
                "minTLS": "1.2",
                "zoneId": zone,
            }
        )
        r3 = requests.post(durl, headers=h, data=body, timeout=90)
        if not r3.ok and "already" not in (r3.text or "").lower():
            print("ATTACH domain", r3.status_code, r3.text[:2000], file=sys.stderr)
            if r3.status_code not in (200, 400):
                return 1
    print("OK: custom domain", TILE_HOST, "(SSL may take a few minutes)")

    # Public read CORS for MapLibre / web clients
    cput = f"https://api.cloudflare.com/client/v4/accounts/{acc}/r2/buckets/{BUCKET}/cors"
    cors = {
        "rules": [
            {
                "id": "crep-web",
                "allowed": {
                    "origins": ["*"],
                    "methods": ["GET", "HEAD"],
                    "headers": ["*"],
                },
                "maxAgeSeconds": 3600,
            }
        ]
    }
    r4 = requests.put(cput, headers=h, data=json.dumps(cors), timeout=60)
    if r4.ok:
        print("OK: CORS updated")
    else:
        print("WARN: CORS", r4.status_code, r4.text[:500], file=sys.stderr)

    r5_endpoint = f"https://{acc}.r2.cloudflarestorage.com"
    print("R2_ENDPOINT (for GHA / aws s3):", r5_endpoint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
