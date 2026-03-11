#!/usr/bin/env python3
"""Query Supabase components and output for review."""
import os
from pathlib import Path

def load_env():
    mas = Path(__file__).resolve().parent.parent
    for p in [mas.parent.parent / "WEBSITE" / "website" / ".env.local", mas / ".env"]:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

def main():
    load_env()
    url = (os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL") or "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        print("No Supabase URL/key")
        return
    import requests
    r = requests.get(
        f"{url}/rest/v1/components",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        params={"select": "id,name,sku,category", "order": "category,name"},
        timeout=30,
    )
    if r.status_code != 200:
        print("Error:", r.status_code, r.text[:300])
        return
    data = r.json()
    for c in data:
        name = (c.get("name") or "")[:80]
        safe = name.encode("ascii", "replace").decode("ascii")
        print(f"{c.get('id','')}|{safe}|{c.get('category','')}")
    print(f"\n--- Total: {len(data)} components ---")
    # BOM mappings
    r2 = requests.get(
        f"{url}/rest/v1/bom_items",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        params={"select": "product_id,component_id,quantity_needed"},
        timeout=30,
    )
    if r2.status_code == 200:
        bom = r2.json()
        print(f"\n--- BOM: {len(bom)} links (product_id -> component_id, qty) ---")
        by_product = {}
        for b in bom:
            pid = b.get("product_id", "")
            if pid not in by_product:
                by_product[pid] = []
            by_product[pid].append((b.get("component_id"), b.get("quantity_needed")))
        for pid in sorted(by_product.keys()):
            print(f"\n{pid}:")
            for cid, qty in by_product[pid][:10]:
                print(f"  - {cid} x{qty}")
            if len(by_product[pid]) > 10:
                print(f"  ... +{len(by_product[pid])-10} more")

if __name__ == "__main__":
    main()
