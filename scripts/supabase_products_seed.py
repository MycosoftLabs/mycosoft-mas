#!/usr/bin/env python3
"""
Seed Supabase products table with all device variants from the canonical registry.
Aligns with WEBSITE/website/lib/device-products.ts (getAllProductIds).
Uses REST API with upsert (Prefer: resolution=merge-duplicates).

Usage:
  python scripts/supabase_products_seed.py

Env: NEXT_PUBLIC_SUPABASE_URL (or SUPABASE_URL), SUPABASE_SERVICE_ROLE_KEY
"""

import os
from pathlib import Path

# Canonical product list - must match lib/device-products.ts getAllProductIds()
# Format: (id, name, description)
DEVICE_PRODUCTS = [
    # Mushroom 1
    ("mushroom1-mini", "Mushroom 1 Mini", "Compact sensing platform"),
    ("mushroom1-standard", "Mushroom 1 Standard", "Flagship quadrupedal sensing platform"),
    ("mushroom1-large", "Mushroom 1 Large", "Extended deployment platform"),
    ("mushroom1-defense", "Mushroom 1 Defense", "Defense & security variant"),
    # SporeBase, ALARM
    ("sporebase", "SporeBase", "Biological collection system"),
    ("alarm", "Mycosoft Alarm", "Indoor environmental monitor"),
    # MycoNODE (8 colors)
    ("myconode-white", "MycoNODE White", "Subsurface bioelectric probe — White"),
    ("myconode-black", "MycoNODE Black", "Subsurface bioelectric probe — Black"),
    ("myconode-purple", "MycoNODE Purple", "Subsurface bioelectric probe — Purple"),
    ("myconode-blue", "MycoNODE Blue", "Subsurface bioelectric probe — Blue"),
    ("myconode-orange", "MycoNODE Orange", "Subsurface bioelectric probe — Orange"),
    ("myconode-red", "MycoNODE Red", "Subsurface bioelectric probe — Red"),
    ("myconode-yellow", "MycoNODE Yellow", "Subsurface bioelectric probe — Yellow"),
    ("myconode-camo-green", "MycoNODE Camo Green", "Subsurface bioelectric probe — Camo Green"),
    # Hypha 1
    ("hypha1-compact", "Hypha 1 Compact", "Single-point monitoring"),
    ("hypha1-standard", "Hypha 1 Standard", "Modular sensor platform"),
    ("hypha1-industrial", "Hypha 1 Industrial", "Maximum capacity"),
]


def load_env_from_file(path: Path) -> None:
    """Load KEY=VALUE from file into os.environ."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                os.environ[key] = value


def main() -> int:
    mas_root = Path(__file__).resolve().parent.parent

    # Load env (try multiple locations)
    code_root = mas_root.parent.parent
    for p in [
        code_root / "WEBSITE" / "website" / ".env.local",
        code_root / "website" / "website" / ".env.local",
        mas_root.parent / "website" / ".env.local",
        mas_root / ".env",
        Path.home() / ".mycosoft-credentials",
    ]:
        load_env_from_file(p)

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        print("ERROR: Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return 1

    url = url.rstrip("/")
    rest_url = f"{url}/rest/v1/products"

    products = [
        {"id": pid, "name": name, "description": desc or "", "image_url": None}
        for pid, name, desc in DEVICE_PRODUCTS
    ]

    import requests
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    try:
        resp = requests.post(rest_url, json=products, headers=headers, timeout=60)
        if resp.status_code in (200, 201):
            print(f"Upserted {len(products)} products to Supabase")
            return 0
        print(f"Error {resp.status_code}: {resp.text[:500]}")
        return 1
    except Exception as e:
        print(f"Exception: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
