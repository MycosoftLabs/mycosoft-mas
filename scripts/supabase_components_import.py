#!/usr/bin/env python3
"""
Bulk import components from mycoforge_components_import_ready.csv into Supabase.
Uses REST API with upsert (Prefer: resolution=merge-duplicates).
Loads env from website .env.local or MAS .env.

Usage:
  python scripts/supabase_components_import.py

Env: NEXT_PUBLIC_SUPABASE_URL (or SUPABASE_URL), SUPABASE_SERVICE_ROLE_KEY
"""

import csv
import os
from pathlib import Path

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
    csv_path = mas_root / "data" / "amazon_import" / "mycoforge_components_import_ready.csv"

    # Load env (try multiple locations)
    code_root = mas_root.parent.parent  # CODE (parent of MAS)
    for p in [
        code_root / "WEBSITE" / "website" / ".env.local",
        code_root / "website" / "website" / ".env.local",
        mas_root.parent / "website" / ".env.local",
        mas_root / ".env",
        Path.home() / ".mycosoft-credentials",
    ]:
        load_env_from_file(p)

    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 1

    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        print("ERROR: Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        print("  (Service role key bypasses RLS; get from Supabase Dashboard > Settings > API)")
        return 1

    url = url.rstrip("/")
    rest_url = f"{url}/rest/v1/components"

    # Read CSV
    components = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            c = {
                "id": (row.get("id") or "").strip(),
                "name": (row.get("name") or "").strip() or "Unknown",
                "sku": (row.get("sku") or row.get("id") or "").strip(),
                "category": (row.get("category") or "misc").strip(),
                "quantity": int(float(row.get("quantity") or 0)),
                "unit_cost": round(float(row.get("unit_cost") or 0), 2),
                "supplier_name": (row.get("supplier_name") or "Amazon").strip(),
                "location": (row.get("location") or "").strip(),
                "reorder_threshold": int(float(row.get("reorder_threshold") or 0)),
                "supplier_lead_time_days": int(float(row.get("supplier_lead_time_days") or 7)),
            }
            if c["id"]:
                components.append(c)

    if not components:
        print("No components to import")
        return 0

    import requests
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    batch_size = 50
    ok, fail = 0, 0
    for i in range(0, len(components), batch_size):
        batch = components[i : i + batch_size]
        try:
            resp = requests.post(rest_url, json=batch, headers=headers, timeout=60)
            if resp.status_code in (200, 201):
                ok += len(batch)
                print(f"Upserted batch {i // batch_size + 1} ({len(batch)} rows)")
            else:
                fail += len(batch)
                print(f"Error {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            fail += len(batch)
            print(f"Exception: {e}")

    print(f"\nDone: {ok} OK, {fail} failed")
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    exit(main())
