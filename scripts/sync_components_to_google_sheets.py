#!/usr/bin/env python3
"""
Sync MycoForge inventory from Supabase to the master Google Sheet.

1. Fetches all components from Supabase public.components
2. Writes master_sheet_inventory.csv (ready for import)
3. If --push and gspread + credentials exist, replaces the master sheet tab content

Master sheet: https://docs.google.com/spreadsheets/d/1rhuGmyxZakCVet1zMK3_C2f3SCOzH_dr6HH6EKWGRmc/edit?gid=1289530278#gid=1289530278

Usage:
  python scripts/sync_components_to_google_sheets.py              # CSV only
  python scripts/sync_components_to_google_sheets.py --push       # CSV + push to Google Sheets (requires gspread + creds)

Env:
  NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (for fetch)
  GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SHEETS_CREDENTIALS_JSON (for push)
"""

import argparse
import csv
import json
import os
from pathlib import Path

# Master sheet tab gid from URL
MASTER_SHEET_SPREADSHEET_ID = "1rhuGmyxZakCVet1zMK3_C2f3SCOzH_dr6HH6EKWGRmc"
MASTER_SHEET_TAB_GID = "1289530278"

# CSV columns matching amazon_business_import output (master doc format)
MASTER_CSV_COLUMNS = [
    "id", "name", "sku", "category", "quantity", "unit_cost",
    "supplier_name", "location", "reorder_threshold", "supplier_lead_time_days",
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


def fetch_components_from_supabase() -> list[dict]:
    """Fetch all components from Supabase via REST API."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    url = url.rstrip("/")
    rest_url = f"{url}/rest/v1/components?select=id,name,sku,category,quantity,unit_cost,supplier_name,location,reorder_threshold,supplier_lead_time_days"
    import requests
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    resp = requests.get(rest_url, headers=headers, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected response: {type(data)}")
    return data


def row_for_master_sheet(c: dict) -> dict:
    """Convert Supabase row to master-sheet CSV row."""
    return {
        "id": str(c.get("id") or "").strip(),
        "name": str(c.get("name") or "").strip() or "Unknown",
        "sku": str(c.get("sku") or c.get("id") or "").strip(),
        "category": str(c.get("category") or "misc").strip(),
        "quantity": int(float(c.get("quantity") or 0)),
        "unit_cost": round(float(c.get("unit_cost") or 0), 2),
        "supplier_name": str(c.get("supplier_name") or "Amazon").strip(),
        "location": str(c.get("location") or "").strip(),
        "reorder_threshold": int(float(c.get("reorder_threshold") or 0)),
        "supplier_lead_time_days": int(float(c.get("supplier_lead_time_days") or 7)),
    }


def push_to_google_sheets(rows: list[dict], tab_name_or_gid: str = MASTER_SHEET_TAB_GID) -> bool:
    """Replace master sheet tab content with current inventory. Returns True on success."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("Install: pip install gspread google-auth")
        return False

    creds_path = (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("GOOGLE_SERVICE_ACCOUNT_PATH")
        or os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY")
    )
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_path and not creds_json:
        print("Set GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON) or GOOGLE_SHEETS_CREDENTIALS_JSON")
        return False

    if creds_json:
        try:
            info = json.loads(creds_json)
        except json.JSONDecodeError:
            print("GOOGLE_SHEETS_CREDENTIALS_JSON must be valid JSON")
            return False
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    else:
        creds = Credentials.from_service_account_file(creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets"])

    gc = gspread.authorize(creds)
    sh = gc.open_by_key(MASTER_SHEET_SPREADSHEET_ID)
    ws = sh.get_worksheet_by_id(int(tab_name_or_gid)) if tab_name_or_gid.isdigit() else sh.worksheet(tab_name_or_gid)
    vals = [MASTER_CSV_COLUMNS] + [[r[k] for k in MASTER_CSV_COLUMNS] for r in rows]
    ws.clear()
    ws.update(vals, "A1", value_input_option="USER_ENTERED")
    print(f"Updated sheet '{ws.title}' with {len(rows)} rows")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true", help="Push to Google Sheets (requires gspread + credentials)")
    ap.add_argument("--csv", default=None, help="Output CSV path (default: data/amazon_import/master_sheet_inventory.csv)")
    args = ap.parse_args()

    mas_root = Path(__file__).resolve().parent.parent
    code_root = mas_root.parent.parent
    for p in [
        code_root / "WEBSITE" / "website" / ".env.local",
        code_root / "website" / "website" / ".env.local",
        mas_root.parent / "website" / ".env.local",
        mas_root / ".env",
        Path.home() / ".mycosoft-credentials",
    ]:
        load_env_from_file(p)

    csv_path = Path(args.csv) if args.csv else mas_root / "data" / "amazon_import" / "master_sheet_inventory.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    print("Fetching components from Supabase...")
    raw = fetch_components_from_supabase()
    rows = [row_for_master_sheet(c) for c in raw]
    print(f"Fetched {len(rows)} components")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MASTER_CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {csv_path}")

    if args.push:
        if push_to_google_sheets(rows):
            print("Google Sheets push complete")
        else:
            print("Google Sheets push skipped (see above)")
    else:
        print("\nTo push to the master sheet:")
        print("  1. Open:", f"https://docs.google.com/spreadsheets/d/{MASTER_SHEET_SPREADSHEET_ID}/edit?gid={MASTER_SHEET_TAB_GID}")
        print("  2. Paste the contents of", csv_path)
        print("  Or run: python scripts/sync_components_to_google_sheets.py --push")
        print("    (requires: pip install gspread google-auth, and GOOGLE_APPLICATION_CREDENTIALS)")

    return 0


if __name__ == "__main__":
    exit(main())
