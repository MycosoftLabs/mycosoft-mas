#!/usr/bin/env python3
"""Generate SQL INSERT statements for Supabase components from import-ready CSV."""
import csv
from pathlib import Path

def esc(s):
    if s is None: return "NULL"
    ss = str(s).strip()
    if ss == "": return "''"
    return "'" + ss.replace("'", "''") + "'"

def main():
    path = Path(__file__).parent.parent / "data/amazon_import/mycoforge_components_import_ready.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    out = []
    for r in rows:
        loc = (r.get("location") or "").strip()
        thresh = int(r.get("reorder_threshold") or 5)
        lead_raw = (r.get("supplier_lead_time_days") or "").strip()
        lead = int(lead_raw) if lead_raw else 7
        name = (r.get("name") or "").strip() or "Unknown"
        sku = (r.get("sku") or r.get("id") or "").strip()
        supp = (r.get("supplier_name") or "Amazon").strip()
        vals = (
            esc(r["id"]), esc(name), esc(sku), esc(r["category"]),
            int(r.get("quantity") or 0), esc(loc), thresh, esc(supp),
            lead, float(r.get("unit_cost") or 0)
        )
        sql = (
            f"INSERT INTO public.components "
            f"(id, name, sku, category, quantity, location, reorder_threshold, supplier_name, supplier_lead_time_days, unit_cost) "
            f"VALUES ({vals[0]}, {vals[1]}, {vals[2]}, {vals[3]}, {vals[4]}, {vals[5]}, {vals[6]}, {vals[7]}, {vals[8]}, {vals[9]}) "
            f"ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, sku=EXCLUDED.sku, category=EXCLUDED.category, "
            f"quantity=EXCLUDED.quantity, location=EXCLUDED.location, reorder_threshold=EXCLUDED.reorder_threshold, "
            f"supplier_name=EXCLUDED.supplier_name, supplier_lead_time_days=EXCLUDED.supplier_lead_time_days, "
            f"unit_cost=EXCLUDED.unit_cost"
        )
        out.append(sql)
    out_path = path.parent / "supabase_inserts.sql"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(";\n".join(out) + ";" if out else "")
    print(f"Wrote {len(out)} statements to {out_path}")
    return out

if __name__ == "__main__":
    main()
