#!/usr/bin/env python3
"""
Amazon Business CSV → MycoForge Supabase components import.
Processes orders_from_20241201_to_20260306 CSV, cleans data, produces import-ready CSV,
and optionally inserts into Supabase components table.

Usage:
  python scripts/amazon_business_import.py [--csv PATH] [--no-supabase] [--dry-run]

Env: NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (for Supabase insert)
"""

import argparse
import csv
import os
import re
from collections import defaultdict
from pathlib import Path

# Non-inventory categories/keywords to exclude (obvious non-hardware)
EXCLUDE_KEYWORDS = {
    "snack", "candy", "food", "beverage", "drink", "coffee", "tea",
    "apparel", "t-shirt", "shirt", "hoodie", "socks", "hat", "jacket",
    "subscription", "wall art", "poster", "painting", "canvas", "artwork",
    "wall pictures", "wall picture", "framed ready to hang",
    "furniture", "chair", "stool", "table", "shelf", "bookcase", "ottoman",
    "kitchen", "trash can", "waste basket", "bathroom", "garbage",
    "violin", "guitar", "musical instrument", "microphone", "headphones",
    "jewelry", "ring sizer", "pliers", "solder", "drilling", "polisher",
    "eyeglasses", "glasses stand", "organizer tray", "valet",
    "phone mount", "car phone holder", "gym", "fitness",
    "batteries", "aaa ", "aa ", "alkaline",
    "roomba", "robot vacuum", "vacuum",
    "locks", "deadbolt", "yale", "smart lock",
}
# Keep: dev boards, sensors, antennas, cables, 3D printer filament, electronic components, etc.

MYCOFORGE_CATEGORIES = [
    "dev-boards", "sensors", "cameras", "motors-servos",
    "antennas", "chassis-housing", "power", "misc",
]

# Map Amazon category keywords to MycoForge category
CATEGORY_MAP = {
    "personal computer": "dev-boards",
    "system board": "dev-boards",
    "processor": "dev-boards",
    "raspberry": "dev-boards",
    "jetson": "dev-boards",
    "arduino": "dev-boards",
    "esp32": "dev-boards",
    "sensor": "sensors",
    "bme": "sensors",
    "camera": "cameras",
    "motor": "motors-servos",
    "servo": "motors-servos",
    "antenna": "antennas",
    "gnss": "antennas",
    "gps": "antennas",
    "chassis": "chassis-housing",
    "housing": "chassis-housing",
    "case": "chassis-housing",
    "power": "power",
    "battery": "power",
    "cable": "misc",
    "connector": "misc",
    "hdmi": "misc",
    "usb": "misc",
    "thunderbolt": "misc",
    "filament": "misc",
    "3d printer": "misc",
    "pcb": "misc",
    "solder": "misc",
    "electronic": "misc",
}


def strip_excel_formula(val: str) -> str:
    """Convert =\"43201500\" to 43201500, etc."""
    if not val or not isinstance(val, str):
        return str(val or "").strip()
    s = val.strip()
    if s.startswith("=\""):
        return s[2:].rstrip("\"").strip()
    if s.startswith("="):
        return s[1:].strip()
    return s


def parse_float(val) -> float:
    if val is None or val == "" or val == "N/A":
        return 0.0
    s = strip_excel_formula(str(val)).replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_int(val) -> int:
    if val is None or val == "" or val == "N/A":
        return 0
    s = strip_excel_formula(str(val)).replace(",", "")
    try:
        return int(float(s))
    except ValueError:
        return 0


def should_exclude(row: dict) -> bool:
    """Exclude obvious non-inventory items."""
    title = (row.get("Title") or "").lower()
    cat = (row.get("Amazon-Internal Product Category") or "").lower()
    segment = (row.get("Segment") or "").lower()
    text = f"{title} {cat} {segment}"
    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            return True
    return False


def map_category(row: dict) -> str:
    """Map Amazon data to MycoForge category."""
    title = (row.get("Title") or "").lower()
    cat = (row.get("Amazon-Internal Product Category") or "").lower()
    segment = (row.get("Segment") or "").lower()
    text = f"{title} {cat} {segment}"
    for kw, mf_cat in CATEGORY_MAP.items():
        if kw in text:
            return mf_cat
    return "misc"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None, help="Path to Amazon CSV (default: Downloads)")
    ap.add_argument("--no-supabase", action="store_true", help="Skip Supabase insert")
    ap.add_argument("--dry-run", action="store_true", help="Only produce CSV, no insert")
    args = ap.parse_args()

    csv_path = args.csv
    if not csv_path:
        csv_path = Path.home() / "Downloads" / "orders_from_20241201_to_20260306_20260306_1012.csv"
        if not Path(csv_path).exists():
            alt = Path.home() / "AppData" / "Roaming" / "Claude" / "local-agent-mode-sessions"
            for p in alt.rglob("orders_from_20241201*.csv"):
                csv_path = p
                break
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}")
        return 1

    out_dir = Path(__file__).parent.parent / "data" / "amazon_import"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Read and parse
    rows = []
    with open(csv_path, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Skip cancelled/empty
            if (r.get("Order Status") or "").strip().lower() == "cancelled":
                continue
            qty = parse_int(r.get("Item Quantity"))
            if qty <= 0:
                continue
            asin = strip_excel_formula(r.get("ASIN") or "")
            if not asin:
                continue
            rows.append(r)

    # Filter non-inventory
    kept = [r for r in rows if not should_exclude(r)]
    excluded_count = len(rows) - len(kept)

    # Aggregate by ASIN for components (unique component per ASIN)
    agg: dict[str, dict] = defaultdict(lambda: {
        "asin": "",
        "name": "",
        "sku": "",
        "category": "misc",
        "quantity": 0,
        "unit_cost": 0.0,
        "cost_sum": 0.0,
        "supplier_name": "",
        "order_ids": set(),
        "order_dates": [],
    })
    for r in kept:
        asin = strip_excel_formula(r.get("ASIN") or "")
        name = (r.get("Title") or "").strip()[:255]
        sku = strip_excel_formula(r.get("Part number") or r.get("Item model number") or asin)
        ppu = parse_float(r.get("Purchase PPU"))
        qty = parse_int(r.get("Item Quantity"))
        seller = (r.get("Seller Name") or "").strip()
        order_id = (r.get("Order ID") or "").strip()
        order_date = (r.get("Order Date") or "").strip()

        agg[asin]["asin"] = asin
        agg[asin]["name"] = name or f"Unknown {asin}"
        agg[asin]["sku"] = sku or asin
        agg[asin]["category"] = map_category(r)
        agg[asin]["quantity"] += qty
        agg[asin]["cost_sum"] += ppu * qty
        agg[asin]["supplier_name"] = seller or agg[asin]["supplier_name"]
        agg[asin]["order_ids"].add(order_id)
        agg[asin]["order_dates"].append(order_date)

    components = []
    for asin, d in agg.items():
        qty = d["quantity"]
        cost_avg = d["cost_sum"] / qty if qty else 0
        components.append({
            "id": asin,
            "name": d["name"],
            "sku": d["sku"],
            "category": d["category"],
            "quantity": qty,
            "unit_cost": round(cost_avg, 2),
            "supplier_name": d["supplier_name"] or "Amazon",
            "location": "",
            "reorder_threshold": 0,
            "supplier_lead_time_days": 7,
        })

    # Write cleaned CSV (full detail for master doc / audit)
    full_csv_path = out_dir / "mycoforge_components_import_ready.csv"
    with open(full_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "id", "name", "sku", "category", "quantity", "unit_cost",
            "supplier_name", "location", "reorder_threshold", "supplier_lead_time_days",
        ])
        w.writeheader()
        w.writerows(components)
    print(f"Wrote {len(components)} components to {full_csv_path}")

    # Copy raw for audit
    import shutil
    raw_copy = out_dir / "amazon_business_raw_export.csv"
    shutil.copy(csv_path, raw_copy)
    print(f"Copied raw export to {raw_copy}")

    # Write SQL batches for MCP/execute_sql (no service role key needed)
    BATCH_SIZE = 25
    for i in range(0, len(components), BATCH_SIZE):
        batch = components[i : i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        sql_lines = []
        for c in batch:
            def esc(s):
                return (s or "").replace("\\", "\\\\").replace("'", "''").replace("\n", " ").replace("\r", " ")
            name_esc = esc(c["name"])
            sku_esc = esc(c["sku"])
            supp_esc = esc(c["supplier_name"])
            loc_esc = esc(c["location"])
            unit_cost = c["unit_cost"] or 0
            qty = c["quantity"] or 0
            cat = c["category"] or "misc"
            sql_lines.append(
                f"""INSERT INTO components (id, name, sku, category, quantity, unit_cost, supplier_name, location, reorder_threshold, supplier_lead_time_days)
VALUES ('{c["id"]}', '{name_esc}', '{sku_esc}', '{cat}', {qty}, {unit_cost}, '{supp_esc}', '{loc_esc}', 0, 7)
ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, sku=EXCLUDED.sku, category=EXCLUDED.category, quantity=EXCLUDED.quantity, unit_cost=EXCLUDED.unit_cost, supplier_name=EXCLUDED.supplier_name;"""
            )
        sql_path = out_dir / f"supabase_batch_{batch_num:03d}.sql"
        with open(sql_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sql_lines))
    print(f"Wrote {len(components) // BATCH_SIZE + (1 if len(components) % BATCH_SIZE else 0)} SQL batch files to {out_dir}")

    # Supabase insert
    if not args.no_supabase and not args.dry_run:
        url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            print("WARN: Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY for Supabase insert. Skipping.")
        else:
            try:
                import requests
                headers = {
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates",
                }
                # Insert in batches of 50
                for i in range(0, len(components), 50):
                    batch = components[i : i + 50]
                    resp = requests.post(
                        f"{url.rstrip('/')}/rest/v1/components",
                        json=batch,
                        headers=headers,
                        timeout=30,
                    )
                    if resp.status_code >= 400:
                        print(f"Supabase error {resp.status_code}: {resp.text[:500]}")
                    else:
                        print(f"Inserted batch {i//50 + 1} ({len(batch)} rows)")
            except Exception as e:
                print(f"Supabase insert failed: {e}")

    # Summary report
    report_path = out_dir / "AMAZON_IMPORT_SUMMARY_MAR07_2026.md"
    report = f"""# Amazon Business Import Summary — March 7, 2026

## Report used
- **File:** {csv_path.name}
- **Date range:** Dec 2024 – Mar 2026 (from filename)
- **Raw rows:** {len(rows)}
- **After excluding non-inventory:** {len(kept)} ({excluded_count} excluded)
- **Unique components (by ASIN):** {len(components)}

## Filtering
- Excluded: cancelled orders, zero quantity
- Excluded non-inventory: {', '.join(sorted(EXCLUDE_KEYWORDS)[:15])}...
- Kept ambiguous items for manual review

## Outputs
- `mycoforge_components_import_ready.csv` — {len(components)} rows, ready for Supabase
- `amazon_business_raw_export.csv` — raw copy

## Google Sheets
Paste `mycoforge_components_import_ready.csv` into:
https://docs.google.com/spreadsheets/d/1rhuGmyxZakCVet1zMK3_C2f3SCOzH_dr6HH6EKWGRmc/edit?gid=1289530278#gid=1289530278

## Next steps
1. Review excluded items; add back if needed
2. Set SUPABASE_SERVICE_ROLE_KEY and re-run for Supabase insert
3. Verify in MycoForge: https://mycoforge.tech619.com
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Wrote report to {report_path}")

    return 0


if __name__ == "__main__":
    exit(main())
